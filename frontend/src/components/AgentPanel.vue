<template>
  <teleport to="body">
    <!-- 半透明遮罩：点击面板外区域收起，淡入淡出 -->
    <Transition name="agent-fade">
      <div v-if="show" class="agent-overlay" @click="show = false" />
    </Transition>
    <!-- 对话面板：导航栏下方浮出，底部延伸到页面底端，飞入/飞出动画 -->
    <Transition name="agent-panel">
      <div v-if="show" class="agent-panel">
        <ChatStream class="chat-stream-area" @tool-result="store.addPendingPoi" />
      </div>
    </Transition>
  </teleport>
</template>

<script setup lang="ts">
/**
 * 全局 Agent 对话面板：导航栏右侧 🤖 图标点击后浮出，飞入/飞出动画。
 *
 * - 覆盖页面内容但不遮导航栏（导航栏 z-index 高于遮罩）
 * - 底部延伸到页面底端（top 固定导航栏下沿，bottom:0 随窗口高度自适应）
 * - 待选栏已拆分到页面左侧 PendingPanel（全局共享 plan store.pendingPois），
 *   本面板只承载 ChatStream 对话流；查询结果经 tool-result 事件写入 store
 */
import ChatStream from '@/components/ChatStream.vue'
import { usePlanStore } from '@/stores/plan'

defineOptions({ name: 'AgentPanel' })

const show = defineModel<boolean>('show', { default: false })

const store = usePlanStore()
</script>

<style scoped>
/* 遮罩：覆盖页面内容，层级低于导航栏（2001）与面板（2000） */
.agent-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 1999;
}
/* 面板：导航栏下方右侧对齐，顶部悬空圆角、底部贴底直角，随窗口高度自适应 */
.agent-panel {
  position: fixed;
  top: 57px;
  bottom: 0;
  right: 24px;
  z-index: 2000;
  width: 440px;
  background: var(--tp-surface);
  border: 1px solid var(--tp-border);
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}
.chat-stream-area {
  height: 100%;
}
/* 面板飞入/飞出动画：自上而下滑入 + 淡入 */
.agent-panel-enter-active,
.agent-panel-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.agent-panel-enter-from,
.agent-panel-leave-to {
  opacity: 0;
  transform: translateY(-16px);
}
/* 遮罩淡入淡出 */
.agent-fade-enter-active,
.agent-fade-leave-active {
  transition: opacity 0.22s ease;
}
.agent-fade-enter-from,
.agent-fade-leave-to {
  opacity: 0;
}
</style>
