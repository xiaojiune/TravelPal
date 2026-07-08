import { ref } from 'vue'
import type { Ref } from 'vue'

interface TypewriterReturn {
  displayText: Ref<string>
  start: (text: string) => void
  append: (chunk: string) => void
  reset: () => void
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
