<template>
  <div class="chat-stream">
    <div ref="historyRef" class="chat-history">
      <div v-if="messages.length === 0" class="welcome">
        我不懂你的全部，但我懂你的旅途。
      </div>
      <template v-for="(msg, i) in messages" :key="i">
        <!-- 工具调用状态行：详情富卡片由左侧查询面板渲染，对话内仅回显工具名 -->
        <div v-if="msg.role === 'tool'" class="msg-tool-line">
          🛠️ 已查询 {{ (msg.data as { tool?: string })?.tool ?? '工具' }}
        </div>
        <ChatMessage v-else :role="msg.role" :content="msg.content" :time="msg.time" />
      </template>
      <div v-if="messages.length === 0" class="hello-bubble">
        <n-button size="small" secondary @click="sayHello">你好</n-button>
      </div>
    </div>
    <div class="input-bar">
      <n-input
        v-model:value="inputText"
        placeholder="说点什么..."
        :disabled="loading"
        @keydown.enter="send"
      />
      <n-button type="primary" :loading="loading" :disabled="!inputText.trim()" @click="send">
        发送
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 全局 Agent 对话流组件：SSE 流式对话 + 打字机渲染，自包含、可复用。
 *
 * 工具结果（tool_result）以富卡片（ToolResultCard 四型判别）内嵌消息流渲染；
 * POI 型结果同时通过 tool-result 事件抛出，由宿主（AgentPanel）写入待选栏。
 * 对话状态保存在本组件内部，组件常驻（挂在 App.vue router-view 外）时跨页面不丢失。
 *
 * Props:
 *   apiPath: string   — SSE 接口路径，默认 /api/chat
 * Emits:
 *   tool-result: (payload: { tool: string; result: unknown; city?: string })
 *     — 工具结果整包（供宿主写入左侧查询面板 store.queryResults）
 */
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import ChatMessage from '@/components/ChatMessage.vue'
import { useTypewriter } from '@/composables/useTypewriter'
import { useTaskPolling } from '@/composables/useTaskPolling'
import { useSuggestCache } from '@/composables/useSuggestCache'
import { usePlanStore } from '@/stores/plan'
import type { SuggestResult } from '@/services/api'

interface Props {
  apiPath?: string
}

interface ToolResultPayload {
  tool: string
  result: unknown
  city?: string
}

defineOptions({ name: 'ChatStream' })

const props = withDefaults(defineProps<Props>(), { apiPath: '/api/chat' })
const emit = defineEmits<{ (e: 'tool-result', payload: ToolResultPayload): void }>()
const store = usePlanStore()
const cache = useSuggestCache()
const router = useRouter()
const { startPolling } = useTaskPolling()

const historyRef = ref<HTMLDivElement | null>(null)
const inputText = ref('')
const { displayText, append, reset, stop, finish } = useTypewriter()
// 当前 SSE 请求的 AbortController：组件卸载（AgentPanel 关闭）时中止流，
// 避免 fetch 继续运行、闭包写入已卸载组件的 ref
let abortController: AbortController | null = null

// 对话状态（messages/loading）上提 plan store（方案 A）：
// AgentPanel 用 v-if 控制显隐，收起会卸载组件，组件局部 ref 状态会丢失；
// 存 store 后「同一次规划内收起/重开会话保留，新建规划 reset 清空」
const { chatMessages: messages, chatLoading: loading } = storeToRefs(store)

// 当前正在流式输出的 assistant 消息索引（打字机逐字弹出时回写目标）。
// 打字机 displayText 是独立 ref，定时器弹出不会自动同步到 messages[].content，
// 必须 watch 到最新值再写回气泡，否则气泡一直为空。
let streamingIndex = -1
// 是否已进入「优雅收尾」（done 分支走 finish 异步收尾），此时末尾不复位 loading，
// 交由打字机缓冲弹空后的 finish 回调复位，避免提前解锁。
let gracefulDone = false
watch(displayText, (v) => {
  if (streamingIndex !== -1) {
    messages.value[streamingIndex].content = v
    // 打字机弹出期间跟随滚动：nextTick 等 DOM 高度更新后再判断，
    // 避免弹字过快时 nearBottom 基于旧高度误判而卡在底部上方；
    // 用户上划（距底 >=40px）时暂停自动滚，保留阅读位置
    nextTick(() => scrollToBottom())
  }
})

onUnmounted(() => {
  abortController?.abort()
  abortController = null
  stop() // 停止打字机定时器，避免卸载后残留计时器
  streamingIndex = -1
  gracefulDone = false
  // 收起面板中断 SSE 后：复位 loading，并移除未完成的 assistant 空气泡
  store.chatLoading = false
  const last = messages.value[messages.value.length - 1]
  if (last && last.role === 'assistant' && last.content === '') {
    messages.value.pop()
  }
})

/** 当前时间格式化为 HH:MM，作为消息时间戳。 */
function formatTime(d: Date): string {
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

/** 预设气泡「你好」：点击以「你好」作为用户消息发起对话。 */
function sayHello() {
  if (loading.value) return
  inputText.value = '你好'
  send()
}

/**
 * 发送用户消息，读取 SSE 流式响应并逐字打字机渲染。
 *
 * 使用 fetch + ReadableStream 而非 EventSource，因为需要 POST 方法传递消息体。
 * 后端返回 SSE text/event-stream，前端手动 parse 'data: ' 前缀。
 * tool_result 事件数据经 emit 抛给宿主，本组件不持有待选栏状态。
 */
async function send() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  const now = formatTime(new Date())
  inputText.value = ''
  messages.value.push({ role: 'user', content: text, time: now })
  // 先占位空气泡，SSE 流式追加内容
  messages.value.push({ role: 'assistant', content: '', time: now })
  loading.value = true
  reset()
  // 发新消息强制滚底（用户可能在阅读历史）；nextTick 等 DOM 渲染新消息后再滚，
  // 否则 scrollHeight 还是旧值，滚不到新消息位置
  nextTick(() => forceScrollBottom())
  const msgIndex = messages.value.length - 1
  streamingIndex = msgIndex // 打字机弹出期间持续回写此气泡
  abortController = new AbortController()

  try {
    // form_context：首页表单当前输入快照（供 submit_plan_form 等工具感知用户已填内容）
    const formContext = store.buildRequest(null)
    const resp = await fetch(props.apiPath, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        plan_result: store.planResult ?? null,
        form_context: formContext,
      }),
      signal: abortController.signal,
    })
    if (!resp.ok) {
      messages.value[msgIndex].content = '请求失败，请重试'
      loading.value = false
      return
    }
    // SSE 手动解析：逐 chunk 读取字节流，拼行长尾后按 \n 分割
    const body = resp.body
    if (!body) {
      messages.value[msgIndex].content = '响应体为空'
      loading.value = false
      return
    }
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
            // 优雅收尾：不调用 stop()（否则剩余缓冲一次性蹦出，打字机效果丢失），
            // 让打字机按节奏弹完剩余缓冲后复位 streamingIndex 并解锁 loading。
            // 注意此回调异步触发（缓冲弹空后），期间不能提前复位 streamingIndex
            gracefulDone = true
            finish(() => {
              messages.value[msgIndex].content = displayText.value
              streamingIndex = -1
              loading.value = false
              forceScrollBottom()
            })
            streamDone = true
            break
          }
          if (parsed.type === 'error' && parsed.data) {
            stop()
            messages.value[msgIndex].content = String(parsed.data)
            streamingIndex = -1
            streamDone = true
            break
          }
          if (parsed.type === 'content' && parsed.data) {
            append(parsed.data)
            messages.value[msgIndex].content = displayText.value
          }
          if (parsed.type === 'tool_result' && parsed.data) {
            // 结构化 tool_result：{ tool, result, city? }。富卡片交由左侧查询面板
            // （store.queryResults）渲染，对话内仅回显「🛠️ 已查询 {tool}」状态行，
            // 同时整包 emit 供宿主（AgentPanel）写入查询结果区
            const tool = String(parsed.data.tool ?? 'tool')
            const result = parsed.data.result ?? parsed.data
            messages.value.push({ role: 'tool', content: '', time: now, data: { tool, result } })
            // submit_plan_form 是「规划任务」语义：返回 task_id，需轮询任务完成
            // 后把方案建议写入 store 并跳转 SuggestPage（与 HomePage 提交行为一致）
            if (tool === 'submit_plan_form' && typeof result === 'object' && result !== null && 'task_id' in result) {
              void handlePlanTask(String((result as { task_id: string }).task_id))
            } else {
              emit('tool-result', { tool, result, city: parsed.data.city })
            }
            scrollToBottom()
          }
        } catch {
          append(data)
          messages.value[msgIndex].content = displayText.value
        }
      }
      await nextTick()
      scrollToBottom()
    }
  } catch (e) {
    // 组件卸载主动 abort 时静默退出，不覆盖消息内容
    if (e instanceof DOMException && e.name === 'AbortError') return
    stop()
    messages.value[msgIndex].content = '网络错误，请检查连接'
  }

  abortController = null
  if (!gracefulDone) {
    // done 分支已交 finish 异步收尾（打字机弹空后复位）；其余路径在此同步复位
    streamingIndex = -1
    loading.value = false
  }
  scrollToBottom()
}

/**
 * 处理规划任务工具（submit_plan_form）的异步轮询：
 * 轮询任务到 done → 把 SuggestResult 写入 store.suggestions + 缓存 → 跳转 /suggest。
 * 与 HomePage.fetchSuggest 的写入/跳转行为保持一致（done 即跳转）。
 */
async function handlePlanTask(taskId: string) {
  try {
    const data = (await startPolling(taskId)) as unknown as SuggestResult
    store.suggestions = data.suggestions || []
    if (data.spots) cache.suggestSpots.value = data.spots
    if (data.algo_time) cache.suggestAlgoTime.value = data.algo_time
    if (data.polylines) cache.suggestPolylines.value = data.polylines
    if (data.amap_api_key) store.amapApiKey = data.amap_api_key
    if (data.amap_security_code) store.amapSecurityCode = data.amap_security_code
    router.push('/suggest')
  } catch {
    // 任务失败：通过打字机追加一条提示（不打断当前对话流）
    append('（规划失败，请检查首页表单内容后重试）')
  }
}

/**
 * 聊天历史容器滚动控制。
 * - 距底部 < 40px（视为贴底）时跟随自动滚底；
 * - 用户上划离开底部后暂停自动滚（保留阅读位置），仅 send() 发新消息时强制滚底。
 */
function scrollToBottom() {
  const el = historyRef.value
  if (!el) return
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  if (nearBottom) {
    el.scrollTop = el.scrollHeight
  }
}

/** 强制滚动到底部（发新消息时无视阅读位置）。 */
function forceScrollBottom() {
  const el = historyRef.value
  if (el) el.scrollTop = el.scrollHeight
}

onMounted(() => {
  forceScrollBottom()
})
</script>

<style scoped>
.chat-stream {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
}
.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
}
/* 中间背板欢迎语（C 同行者型）：消息为空时居中展示 */
.welcome {
  text-align: center;
  margin-top: 80px;
  padding: 0 24px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--tp-text-2);
}
/* 底部预设气泡「你好」：贴近聊天框左边、带边框装饰，点击发起对话 */
.hello-bubble {
  margin-top: auto;
  display: flex;
  justify-content: flex-start;
  padding: 8px 0 12px;
}
/* 工具调用状态行：左对齐浅色小字，与聊天气泡区分 */
.msg-tool-line {
  align-self: flex-start;
  font-size: 12px;
  color: var(--tp-text-3);
  margin-bottom: 8px;
}
.input-bar {
  position: relative;
  display: flex;
  gap: 8px;
  /* 输入框气泡化：圆角卡片 + 柔和阴影 + 左下尖角尾巴 */
  padding: 10px 12px;
  margin: 0 12px 16px;
  border: 1px solid var(--tp-border);
  border-radius: 14px;
  background: var(--tp-surface);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
/* 气泡尖角尾巴：指向聊天区（上缘），纯 CSS 三角 */
.input-bar::before {
  content: '';
  position: absolute;
  top: -7px;
  left: 22px;
  width: 12px;
  height: 12px;
  background: inherit;
  border-left: 1px solid var(--tp-border);
  border-top: 1px solid var(--tp-border);
  transform: rotate(45deg);
}
</style>
