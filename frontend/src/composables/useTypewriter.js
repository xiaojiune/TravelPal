import { ref } from 'vue'

/**
 * 打字机效果组合式函数。
 * 适用于 SSE 流式逐字追加渲染 —— start 用于一次性设置完整文本，
 * append 用于持续追加（SSE 逐 token 场景）。
 *
 * @param {{ speed?: number }} options - speed: 每字符间隔毫秒数（默认 30）
 * @returns {{ displayText: import('vue').Ref<string>, start: Function, append: Function, stop: Function }}
 */
export function useTypewriter({ speed = 30 } = {}) {
  const displayText = ref('')
  let buffer = ''
  let index = 0
  let timer = null

  // 一次性设置完整文本并开始打字动画
  function start(text) {
    stop()
    buffer = text
    index = 0
    displayText.value = ''
    timer = setInterval(() => {
      if (index >= buffer.length) {
        clearInterval(timer)
        timer = null
        return
      }
      displayText.value += buffer[index]
      index++
    }, speed)
  }

  // SSE 逐 token 追加：直接渲染，不等待 timer
  function append(chunk) {
    displayText.value += chunk
  }

  // 重置：清空显示文本和缓冲区
  function reset() {
    stop()
    displayText.value = ''
    buffer = ''
    index = 0
  }

  // 停止打字动画
  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  return { displayText, start, append, reset, stop }
}
