/** 打字机效果 composable：缓冲逐字弹出，用于 SSE 流式聊天渲染。 */
import { ref } from 'vue'
import type { Ref } from 'vue'

/** 逐字弹出的间隔（毫秒）。SSE 收到整块文本时按此节奏逐字显示，形成打字机效果。 */
const DEFAULT_INTERVAL = 30

interface TypewriterReturn {
  displayText: Ref<string>
  /** 将 chunk 追加到待显示缓冲并启动/维持逐字弹出。用于 SSE 实时流式追加。 */
  append: (chunk: string) => void
  /** 立即显示剩余全部缓冲并停止定时器（流中断 / 组件卸载时调用）。 */
  stop: () => void
  /** 优雅收尾：等缓冲按打字机节奏弹空后调用回调（流正常结束时调用，保持打字机效果）。 */
  finish: (cb: () => void) => void
  /** 重置显示文本与缓冲（新消息开始时调用）。 */
  reset: () => void
}

export function useTypewriter(interval: number = DEFAULT_INTERVAL): TypewriterReturn {
  const displayText = ref('')
  /** 尚未逐字弹出的待显示文本（stop 时一次性补全）。 */
  const buffer = ref('')
  let timer: ReturnType<typeof setInterval> | null = null
  /** finish() 注册的收尾回调：缓冲弹空后触发一次，随后清空。 */
  let finishCb: (() => void) | null = null

  function flush() {
    if (timer !== null) return
    timer = setInterval(() => {
      if (buffer.value.length > 0) {
        displayText.value += buffer.value[0]
        buffer.value = buffer.value.slice(1)
      }
      if (buffer.value.length === 0 && timer !== null) {
        clearInterval(timer)
        timer = null
        // 缓冲弹空：触发 finish 回调（若已注册），保持打字机完整节奏
        if (finishCb) {
          const cb = finishCb
          finishCb = null
          cb()
        }
      }
    }, interval)
  }

  function append(chunk: string) {
    if (!chunk) return
    buffer.value += chunk
    flush()
  }

  function stop() {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
    // 流中断/卸载：剩余缓冲一次性显示，避免内容滞留不完整
    if (buffer.value.length > 0) {
      displayText.value += buffer.value
      buffer.value = ''
    }
    finishCb = null
  }

  /** 优雅收尾：缓冲弹空后执行 cb（不清空已完成内容）。 */
  function finish(cb: () => void) {
    finishCb = cb
    if (buffer.value.length === 0) {
      const c = finishCb
      finishCb = null
      c()
    }
  }

  function reset() {
    stop()
    displayText.value = ''
    buffer.value = ''
    finishCb = null
  }

  return { displayText, append, stop, finish, reset }
}
