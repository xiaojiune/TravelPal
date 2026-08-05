<template>
  <div class="chat-stream">
    <div ref="historyRef" class="chat-history">
      <div v-if="messages.length === 0" class="welcome">
        你想到哪了，我们就从哪开始。
      </div>
      <ChatMessage
        v-for="(msg, i) in messages"
        :key="i"
        :role="msg.role"
        :content="msg.content"
        :time="msg.time"
      />
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
 * 从原 AgentPage 抽取，与待选栏解耦——工具查询结果通过 tool-result 事件抛出，
 * 由宿主（AgentDrawer）决定如何消费（如写入待选栏）。对话状态保存在本组件内部，
 * 组件常驻（挂在 App.vue router-view 外）时跨页面不丢失。
 *
 * Props:
 *   apiPath: string   — SSE 接口路径，默认 /api/chat
 * Emits:
 *   tool-result: (payload: PoiItem) — 工具调用结果（tool_result 事件数据）
 */
import { ref, nextTick } from 'vue'
import ChatMessage from '@/components/ChatMessage.vue'
import { useTypewriter } from '@/composables/useTypewriter'
import type { ChatMessage as ChatMessageType, PoiItem } from '@/types'

interface Props {
  apiPath?: string
}

defineOptions({ name: 'ChatStream' })

const props = withDefaults(defineProps<Props>(), { apiPath: '/api/chat' })
const emit = defineEmits<{ (e: 'tool-result', payload: PoiItem): void }>()

const historyRef = ref<HTMLDivElement | null>(null)
const inputText = ref('')
const loading = ref(false)
const messages = ref<ChatMessageType[]>([])
const { displayText, append, reset } = useTypewriter({ speed: 30 })

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
  const msgIndex = messages.value.length - 1

  try {
    const resp = await fetch(props.apiPath, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
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
    while (true) {
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
          if (parsed.type === 'done') break
          if (parsed.type === 'error' && parsed.data) {
            messages.value[msgIndex].content = String(parsed.data)
            break
          }
          if (parsed.type === 'content' && parsed.data) {
            append(parsed.data)
            messages.value[msgIndex].content = displayText.value
          }
          if (parsed.type === 'tool_result' && parsed.data) {
            if (parsed.data.error) {
              messages.value[msgIndex].content = '查询失败：' + parsed.data.error
            } else {
              messages.value[msgIndex].content = '找到 ' + (parsed.data.name || '') + ' 的信息'
              emit('tool-result', parsed.data)
            }
          }
        } catch {
          append(data)
          messages.value[msgIndex].content = displayText.value
        }
      }
      await nextTick()
      scrollToBottom()
    }
  } catch {
    messages.value[msgIndex].content = '网络错误，请检查连接'
  }

  loading.value = false
  scrollToBottom()
}

/** 将聊天历史容器滚动到底部，确保最新消息可见。 */
function scrollToBottom() {
  if (historyRef.value) {
    historyRef.value.scrollTop = historyRef.value.scrollHeight
  }
}
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
.input-bar {
  display: flex;
  gap: 8px;
  /* 聊天框上抬：不贴面板底缘，留一个字左右空白 */
  padding: 10px 12px;
  margin: 0 8px 12px;
  border: 1px solid var(--tp-border);
  border-radius: 8px;
  background: var(--tp-surface);
}
</style>
