/** 打字机效果 composable：缓冲逐字弹出，用于 SSE 流式聊天渲染。 */
import { ref } from 'vue'
import type { Ref } from 'vue'

/** 逐字弹出的间隔（毫秒）。SSE 收到整块文本时按此节奏逐字显示，形成打字机效果。 */
const DEFAULT_INTERVAL = 30

interface TypewriterReturn {
  displayText: Ref<string>
  /** 将 chunk 追加到待显示缓冲并启动/维持逐字弹出。用于 SSE 实时流式追加。 */
  append: (chunk: string) => void
  /** 立即显示剩余全部缓冲并停止定时器（流结束 / 中断时调用）。 */
  stop: () => void
  /** 重置显示文本与缓冲（新消息开始时调用）。 */
  reset: () => void
}

export function useTypewriter(interval: number = DEFAULT_INTERVAL): TypewriterReturn {
  const displayText = ref('')
  /** 尚未逐字弹出的待显示文本（stop 时一次性补全）。 */
  const buffer = ref('')
  let timer: ReturnType<typeof setInterval> | null = null

  function flush() {
    if (timer !== null) return
    timer = setInterval(() => {
      if (buffer.value.length > 0) {
        displayText.value += buffer.value[0]
        buffer.value = buffer.value.slice(1)
      } else if (timer !== null) {
        clearInterval(timer)
        timer = null
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
    // 流结束/中断：剩余缓冲一次性显示，避免内容滞留不完整
    if (buffer.value.length > 0) {
      displayText.value += buffer.value
      buffer.value = ''
    }
  }

  function reset() {
    stop()
    displayText.value = ''
    buffer.value = ''
  }

  return { displayText, append, stop, reset }
}
