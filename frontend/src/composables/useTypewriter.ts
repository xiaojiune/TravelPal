/** 打字机效果 composable：提供逐字追加 / 定时播放两种模式，用于 SSE 流式聊天渲染。 */
import { ref } from 'vue'
import type { Ref } from 'vue'

interface TypewriterReturn {
  displayText: Ref<string>
  /** 按 speed(ms) 逐字播放一个完整文本。用于模拟打字效果。 */
  start: (text: string) => void
  /** 直接将 chunk 追加到显示文本尾部。用于 SSE 实时流式追加。 */
  append: (chunk: string) => void
  /** 重置显示文本，停止定时器。 */
  reset: () => void
  /** 停止定时器（保留当前文本）。 */
  stop: () => void
}

export function useTypewriter({ speed = 30 } = {}): TypewriterReturn {
  const displayText = ref('')
  let buffer = ''
  let index = 0
  let timer: ReturnType<typeof setInterval> | null = null

  function start(text: string) {
    stop()
    buffer = text
    index = 0
    displayText.value = ''
    timer = setInterval(() => {
      if (index >= buffer.length) {
        clearInterval(timer!)
        timer = null
        return
      }
      displayText.value += buffer[index]
      index++
    }, speed)
  }

  function append(chunk: string) {
    displayText.value += chunk
  }

  function reset() {
    stop()
    displayText.value = ''
    buffer = ''
    index = 0
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  return { displayText, start, append, reset, stop }
}
