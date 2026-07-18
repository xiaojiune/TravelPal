<template>
  <div class="agent-page">
    <div ref="historyRef" class="chat-history">
      <div v-if="messages.length === 0" class="welcome">
        <h2>👋 你好！我是你的旅行伴侣</h2>
        <p>聊聊天吧——可以聊聊今天的规划，或者让我给点建议～</p>
      </div>
      <ChatMessage
        v-for="(msg, i) in messages"
        :key="i"
        :role="msg.role"
        :content="msg.content"
      />
      <div v-if="lastPoiResult" class="poi-card">
        <div class="poi-header">{{ lastPoiResult.name }}</div>
        <div class="poi-detail">📍 {{ lastPoiResult.address }}</div>
        <div class="poi-detail">坐标：{{ lastPoiResult.lon?.toFixed(4) }}, {{ lastPoiResult.lat?.toFixed(4) }}</div>
        <div v-if="lastPoiResult.tw_start != null && lastPoiResult.tw_end != null" class="poi-detail">
          营业时间：{{ Math.floor(lastPoiResult.tw_start! / 60) }}:{{ String(lastPoiResult.tw_start! % 60).padStart(2, '0') }} ~
          {{ Math.floor(lastPoiResult.tw_end! / 60) }}:{{ String(lastPoiResult.tw_end! % 60).padStart(2, '0') }}
        </div>
        <button class="btn-add" :disabled="poiAdded" @click="addPoiToForm">
          {{ poiAdded ? '✅ 已添加' : '➕ 添加该景点' }}
        </button>
      </div>
    </div>
    <div class="input-bar">
      <input
        v-model="inputText"
        placeholder="说点什么..."
        :disabled="loading"
        @keydown.enter="send"
      />
      <button :disabled="loading || !inputText.trim()" @click="send">
        {{ loading ? '…' : '发送' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 智能 Agent 对话页：支持 SSE 流式响应 + 打字机效果渲染 + Function Calling 工具结果展示。 */
// ====== 状态定义 ======
import { ref, nextTick } from 'vue'
import ChatMessage from '@/components/ChatMessage.vue'
import { useTypewriter } from '@/composables/useTypewriter'
import { usePlanStore } from '@/stores/plan'
import type { ChatMessage as ChatMessageType } from '@/types'

defineOptions({ name: 'AgentPage' })

const store = usePlanStore()
const historyRef = ref<HTMLDivElement | null>(null)
const inputText = ref('')
const loading = ref(false)
const messages = ref<ChatMessageType[]>([])
// 打字机速度 30ms/字，适合 Mock 流式节奏
const { displayText, append, reset, stop } = useTypewriter({ speed: 30 })

/** POI 查询结果卡片展示 */
interface PoiResult { name?: string; lon?: number; lat?: number; address?: string; tw_start?: number; tw_end?: number; error?: string }
const lastPoiResult = ref<PoiResult | null>(null)
const poiAdded = ref(false)

/** 将 POI 添加到 HomePage 景点列表并提示用户。 */
function addPoiToForm() {
  const poi = lastPoiResult.value
  if (!poi || poiAdded.value || !poi.name || poi.lon == null || poi.lat == null) return
  store.addSpot({
    name: poi.name,
    lon: poi.lon,
    lat: poi.lat,
    twStart: poi.tw_start ?? 480,
    twEnd: poi.tw_end ?? 1020,
    stay: 0,
    address: poi.address,
  })
  poiAdded.value = true
}

// ====== 聊天逻辑 ======

/**
 * 发送用户消息，读取 SSE 流式响应并逐字打字机渲染。
 *
 * 使用 fetch + ReadableStream 而非 EventSource，因为需要 POST 方法传递消息体。
 * 后端返回 SSE text/event-stream，前端手动 parse 'data: ' 前缀。
 */
async function send() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  inputText.value = ''
  messages.value.push({ role: 'user', content: text })
  // 先占位空气泡，SSE 流式追加内容
  messages.value.push({ role: 'assistant', content: '' })
  loading.value = true
  reset()
  const msgIndex = messages.value.length - 1

  try {
    const resp = await fetch('/api/chat', {
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
    if (!body) { messages.value[msgIndex].content = '响应体为空'; loading.value = false; return }
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
          if (parsed.type === 'content' && parsed.data) {
            append(parsed.data)
            messages.value[msgIndex].content = displayText.value
          }
          if (parsed.type === 'tool_result' && parsed.data) {
            if (parsed.data.error) {
              messages.value[msgIndex].content = '查询失败：' + parsed.data.error
            } else {
              messages.value[msgIndex].content = '找到 ' + (parsed.data.name || '') + ' 的信息'
              lastPoiResult.value = parsed.data
              poiAdded.value = false
            }
          }
        } catch {
          append(data)
          messages.value[msgIndex].content = displayText.value
        }
      }
      // 每次读完后刷新 DOM 再滚动，确保打字机新内容可见
      await nextTick()
      scrollToBottom()
    }
  } catch {
    messages.value[msgIndex].content = '网络错误，请检查连接'
  }

  loading.value = false
  scrollToBottom()
}

// ====== 工具函数 ======

/** 将聊天历史容器滚动到底部，确保最新消息可见。 */
function scrollToBottom() {
  if (historyRef.value) {
    historyRef.value.scrollTop = historyRef.value.scrollHeight
  }
}
</script>

<style scoped>
.agent-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  max-width: 800px;
  margin: 0 auto;
}
.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
}
.welcome {
  text-align: center;
  margin-top: 60px;
  color: #666;
}
.welcome h2 {
  margin-bottom: 8px;
}
.poi-card {
  margin: 8px 16px;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  background: #f9f9f9;
}
.poi-header {
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 6px;
}
.poi-detail {
  font-size: 13px;
  color: #555;
  margin-bottom: 2px;
}
.btn-add {
  margin-top: 8px;
  padding: 6px 16px;
  border: none;
  border-radius: 6px;
  background: #007aff;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.btn-add:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.input-bar {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
  background: #fff;
}
.input-bar input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  font-size: 14px;
}
.input-bar button {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: #007aff;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.input-bar button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
