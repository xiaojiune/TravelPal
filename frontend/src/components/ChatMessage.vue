<template>
  <div class="chat-message" :class="role">
    <div class="avatar">{{ role === 'user' ? '👤' : '🤖' }}</div>
    <div class="bubble">{{ content }}</div>
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
 */
interface Props {
  role: string
  content: string
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
  background: #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.bubble {
  background: #f0f0f0;
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.chat-message.user .bubble {
  background: #007aff;
  color: #fff;
}
</style>
