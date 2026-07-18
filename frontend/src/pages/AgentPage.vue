<template>
  <div class="agent-page">
    <div class="agent-body">
      <aside class="pending-panel">
        <h3 class="panel-title">📋 待选</h3>
        <div v-if="pendingPois.length === 0" class="pending-empty">
          对话中查询的 POI 将出现在这里
        </div>
        <div v-for="(poi, i) in pendingPois" :key="i" class="pending-card">
          <div class="pending-header">
            {{ poi.name }}
            <span v-if="poi.poi_type === 'hotel'" class="poi-badge hotel">🏨 酒店</span>
            <span v-else class="poi-badge spot">🏛️ 景点</span>
          </div>
          <div class="pending-detail">📍 {{ poi.address }}</div>
          <div class="pending-detail">
            {{ poi.lon?.toFixed(4) }}, {{ poi.lat?.toFixed(4) }}
            <template v-if="poi.tw_start != null && poi.tw_end != null">
              · {{ Math.floor(poi.tw_start! / 60) }}:{{ String(poi.tw_start! % 60).padStart(2, '0') }}~{{ Math.floor(poi.tw_end! / 60) }}:{{ String(poi.tw_end! % 60).padStart(2, '0') }}
            </template>
          </div>
          <div class="pending-actions">
            <button class="btn-add" @click="addPoiToForm(poi)">{{ poi.poi_type === 'hotel' ? '🏨 设为酒店' : '➕ 添加' }}</button>
            <button class="btn-cancel" @click="removePoi(i)">✕ 取消</button>
          </div>
        </div>
      </aside>
      <div class="chat-area">
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
    </div>
  </div>
</template>

<script setup lang="ts">
/** 智能 Agent 对话页：SSE 流式对话 + 左侧待选栏（POI 查询结果暂存）。 */
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
const { displayText, append, reset, stop } = useTypewriter({ speed: 30 })

interface PoiItem {
  name?: string; lon?: number; lat?: number; address?: string
  tw_start?: number; tw_end?: number; poi_type?: string
}
/** 左侧待选栏：对话中查询到的 POI 暂存列表。 */
const pendingPois = ref<PoiItem[]>([])

/** 将待选 POI 添加到首页输入列表，然后从待选栏移除。 */
function addPoiToForm(poi: PoiItem) {
  if (!poi.name || poi.lon == null || poi.lat == null) return
  store.addSpot({
    name: poi.name,
    lon: poi.lon,
    lat: poi.lat,
    twStart: poi.tw_start ?? 480,
    twEnd: poi.tw_end ?? 1020,
    stay: 0,
    address: poi.address,
    poi_type: poi.poi_type,
  })
  const idx = pendingPois.value.findIndex(p => p.name === poi.name)
  if (idx !== -1) pendingPois.value.splice(idx, 1)
}

/** 从待选栏移除（不做其他操作）。 */
function removePoi(index: number) {
  pendingPois.value.splice(index, 1)
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
              const name = parsed.data.name
              if (name && !pendingPois.value.some(p => p.name === name)) {
                pendingPois.value.push(parsed.data)
              }
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
  height: calc(100vh - 120px);
  max-width: 1060px;
  margin: 0 auto;
}
.agent-body {
  display: flex;
  height: 100%;
  gap: 0;
}
.pending-panel {
  width: 260px;
  min-width: 260px;
  border-right: 1px solid #e0e0e0;
  padding: 16px;
  overflow-y: auto;
  background: #fafafa;
}
.panel-title {
  font-size: 14px;
  margin: 0 0 12px 0;
  color: #333;
}
.pending-empty {
  font-size: 13px;
  color: #999;
  text-align: center;
  margin-top: 40px;
}
.pending-card {
  padding: 10px;
  margin-bottom: 8px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  background: #fff;
}
.pending-header {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.poi-badge {
  font-size: 10px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 3px;
}
.poi-badge.hotel { background: #e8f5e9; color: #2e7d32; }
.poi-badge.spot  { background: #e3f2fd; color: #1565c0; }
.pending-detail {
  font-size: 12px;
  color: #666;
  margin-bottom: 2px;
}
.pending-actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}
.btn-add {
  flex: 1;
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  background: #007aff;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}
.btn-cancel {
  padding: 4px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  color: #666;
  font-size: 12px;
  cursor: pointer;
}
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
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
