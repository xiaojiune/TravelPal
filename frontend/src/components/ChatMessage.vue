<template>
  <div class="chat-message" :class="role">
    <div class="avatar">{{ role === 'user' ? '👤' : '🤖' }}</div>
    <div class="msg-body">
      <div class="bubble">{{ content }}</div>
      <div v-if="time" class="msg-time">{{ time }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 单条聊天气泡组件。
 * role=user 靠右蓝色，role=assistant 靠左灰色。
 * content 由父组件通过 SSE 逐字符追加，支持打字机效果。
 *
 * Props:
 *   role: 'user' | 'assistant'   — 消息角色
 *   content: string               — 消息内容（父组件 SSE 追加）
 *   time: string                  — 消息发送时间（HH:MM），可选
 */
interface Props {
  role: string
  content: string
  time?: string
}
defineProps<Props>()
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  max-width: 80%;
}
.chat-message.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--tp-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.bubble {
  background: var(--tp-border-light);
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.chat-message.user .bubble {
  background: var(--tp-primary);
  color: var(--tp-on-primary);
}
.msg-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.chat-message.user .msg-body {
  align-items: flex-end;
}
.msg-time {
  font-size: 10px;
  color: var(--tp-text-3);
}
</style>
