/** 打字机效果 composable：提供逐字追加 / 重置，用于 SSE 流式聊天渲染。 */
import { ref } from 'vue'
import type { Ref } from 'vue'

interface TypewriterReturn {
  displayText: Ref<string>
  /** 将 chunk 追加到显示文本尾部。用于 SSE 实时流式追加。 */
  append: (chunk: string) => void
  /** 重置显示文本。 */
  reset: () => void
}

export function useTypewriter(): TypewriterReturn {
  const displayText = ref('')

  function append(chunk: string) {
    displayText.value += chunk
  }

  function reset() {
    displayText.value = ''
  }

  return { displayText, append, reset }
}
