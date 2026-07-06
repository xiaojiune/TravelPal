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

  // 一次性设置完整文本并开始打字，先 stop() 清理上一个动画
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

  // SSE 场景：持续追加 token 到 buffer，若已暂停则重启打字
  function append(chunk) {
    buffer += chunk
    if (!timer) {
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
  }

  // 停止打字动画并清空定时器
  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  return { displayText, start, append, stop }
}
