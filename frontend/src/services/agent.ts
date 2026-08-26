/**
 * Agent SSE 流接口：与后端 /api/chat 建立流式对话。
 *
 * 接口接入与流解析收敛于此（对应"api 只做接入，业务下沉"），
 * 调用方组件只负责 UI 渲染（打字机/消息气泡/滚动），不直接 fetch。
 *
 * 使用 fetch + ReadableStream 而非 EventSource：需要 POST 携带 message/plan_result/
 * form_context。事件类型 content/tool_result/done/error 由回调分发。
 */
import type { PlanRequestPayload } from '@/types'

/** 工具结果事件载荷（tool_result 事件由后端下发的结构化数据）。 */
export interface ToolResultEvent {
  tool: string
  result: unknown
  city?: string
}

/** 流式回调：调用方按需订阅事件（均为可选）。 */
export interface AgentStreamCallbacks {
  /** content 事件：流式文本增量，交由打字机逐字渲染。 */
  onContent?: (text: string) => void
  /** tool_result 事件：结构化工具结果，供宿主写入查询面板/待选栏。 */
  onToolResult?: (event: ToolResultEvent) => void
  /** done 事件：流正常结束（调用方做优雅收尾）。 */
  onDone?: () => void
  /** error 事件：后端返回的错误消息（调用方写入气泡展示）。 */
  onError?: (message: string) => void
}

/** 请求载荷：对话内容与页面感知上下文。 */
export interface AgentStreamPayload {
  message: string
  planResult: unknown
  formContext: PlanRequestPayload
}

/**
 * 建立 Agent SSE 流式对话并解析到 done/error（或抛错）。
 *
 * - HTTP 非 2xx / 响应体为空：抛带中文 message 的 Error（调用方 catch 展示）。
 * - 网络层失败（fetch reject / 流中断）：原样向上抛（调用方按 AbortError/网络错误区分）。
 * - 非 JSON 行（畸形事件/纯文本）：按普通文本追加，容错处理。
 */
export async function streamChat(
  payload: AgentStreamPayload,
  apiPath = '/api/chat',
  cb: AgentStreamCallbacks = {},
  opts: { signal?: AbortSignal } = {},
): Promise<void> {
  const { onContent, onToolResult, onDone, onError } = cb

  const resp = await fetch(apiPath, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: payload.message,
      plan_result: payload.planResult,
      form_context: payload.formContext,
    }),
    signal: opts.signal,
  })
  if (!resp.ok) {
    throw new Error('请求失败，请重试')
  }
  const body = resp.body
  if (!body) {
    throw new Error('响应体为空')
  }

  // SSE 手动解析：逐 chunk 读取字节流，拼行长尾后按换行符分割，取 'data: ' 前缀
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let partial = ''
  let streamDone = false

  while (!streamDone) {
    const { done, value } = await reader.read()
    if (done) break
    partial += decoder.decode(value, { stream: true })
    const lines = partial.split('\n')
    partial = lines.pop() || ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6)
      try {
        const parsed = JSON.parse(data)
        if (parsed.type === 'done') {
          onDone?.()
          streamDone = true
          break
        }
        if (parsed.type === 'error' && parsed.data) {
          onError?.(String(parsed.data))
          streamDone = true
          break
        }
        if (parsed.type === 'content' && parsed.data) {
          onContent?.(parsed.data)
        }
        if (parsed.type === 'tool_result' && parsed.data) {
          const tool = String(parsed.data.tool ?? 'tool')
          const result = parsed.data.result ?? parsed.data
          onToolResult?.({ tool, result, city: parsed.data.city })
        }
      } catch {
        // 非 JSON 行（畸形事件/纯文本）：当作普通文本内容追加，避免整条流中断
        onContent?.(data)
      }
    }
  }
}
