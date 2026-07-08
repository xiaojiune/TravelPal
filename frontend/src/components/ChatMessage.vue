<template>
  <div class="chat-message" :class="role">
    <div class="avatar">{{ role === 'user' ? '👤' : '🤖' }}</div>
    <div class="bubble">{{ content }}</div>
  </div>
</template>

<script setup lang="ts">
// role 区分用户(右侧蓝色)和助手(左侧灰)，content 由父组件通过 SSE 逐字符追加
defineProps({
  role: { type: String, required: true },
  content: { type: String, default: '' },
})
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
