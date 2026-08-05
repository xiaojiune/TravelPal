<template>
  <teleport to="body">
    <!-- 半透明遮罩：点击面板外区域收起（分层时序 B：关闭时先淡出，面板后收回） -->
    <Transition name="agent-fade">
      <div v-if="show" class="agent-overlay" @click="show = false" />
    </Transition>
    <!-- 对话面板：以 🤖 按钮为锚点等比扩散/收回（球式），宽度可拖拽，双击恢复默认 -->
    <Transition name="agent-panel">
      <div v-if="show" class="agent-panel" :style="{ width: panelWidth + 'px' }">
        <div
          class="resize-handle"
          title="拖拽调整宽度，双击恢复默认"
          @mousedown.prevent="onResizeStart"
          @dblclick="resetPanelWidth"
        >
          <span class="handle-grip">⋮</span>
        </div>
        <div class="context-bar">
          <div class="context-title">TravelPal</div>
          <div class="context-status">{{ sessionStatus.dot }} {{ sessionStatus.text }}</div>
        </div>
        <ChatStream class="chat-stream-area" @tool-result="store.addPendingPoi" />
      </div>
    </Transition>
  </teleport>
</template>

<script setup lang="ts">
/**
 * 全局 Agent 对话面板：导航栏右侧 🤖 图标点击后浮出。
 *
 * - 覆盖页面内容但不遮导航栏（导航栏 z-index 高于遮罩）
 * - 底部延伸到页面底端，右侧贴窗口边缘，宽度可拖拽调节
 *   （最小 25vw、最大 50vw、默认 1/3 页面宽，双击左边缘手柄恢复默认）
 * - 动画为「球式」：以导航栏 🤖 按钮为锚点（transform-origin 指向球心）
 *   等比 scale 扩散展开/收回，分层时序 B——打开时面板先动、遮罩后淡入；
 *   关闭时遮罩先淡出、面板后收回
 * - 待选栏在左侧 PendingPanel（共享 plan store.pendingPois），
 *   查询结果经 tool-result 事件写入 store
 */
import { computed, ref } from 'vue'
import ChatStream from '@/components/ChatStream.vue'
import { usePlanStore } from '@/stores/plan'

defineOptions({ name: 'AgentPanel' })

const show = defineModel<boolean>('show', { default: false })

const store = usePlanStore()

// ====== 会话上下文状态栏 ======
/** 顶部上下文栏状态三态：根据表单景点与规划结果判定 Agent 当前能做什么。 */
const sessionStatus = computed(() => {
  if (store.planResult) return { dot: '🔵', text: '方案已生成，可调整' }
  if (store.spots.length > 0) {
    return { dot: '🟡', text: `规划进行中... 已选 ${store.spots.length} 个景点` }
  }
  return { dot: '🟢', text: '准备出发' }
})

// ====== 面板宽度拖拽 ======
/** 面板右侧固定偏移（与 .agent-panel 的 right 一致，贴窗口右缘）。 */
const RIGHT_OFFSET = 0

const panelWidth = ref(window.innerWidth / 3)
const dragging = ref(false)

/** 最小宽度：页面 1/4。 */
function minPanelWidth() {
  return window.innerWidth * 0.25
}
/** 最大宽度：页面 1/2。 */
function maxPanelWidth() {
  return window.innerWidth * 0.5
}
/** 默认宽度：页面 1/3。 */
function defaultPanelWidth() {
  return window.innerWidth / 3
}

/** 按下手柄开始拖拽：注册全局监听，防止拖出面板后失去事件。 */
function onResizeStart() {
  dragging.value = true
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
}

/** 拖拽中：右边缘固定，宽度 = 窗口宽 - 右偏移 - 鼠标 X，clamp 到 [min, max]。 */
function onResizeMove(e: MouseEvent) {
  if (!dragging.value) return
  const newWidth = window.innerWidth - RIGHT_OFFSET - e.clientX
  panelWidth.value = Math.min(Math.max(newWidth, minPanelWidth()), maxPanelWidth())
}

/** 松开结束拖拽，清理全局监听与选中锁。 */
function onResizeEnd() {
  dragging.value = false
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
}

/** 双击手柄恢复默认宽度（页面 1/3）。 */
function resetPanelWidth() {
  panelWidth.value = defaultPanelWidth()
}
</script>

<style scoped>
/* 遮罩：覆盖页面内容，层级低于导航栏（2001）与面板（2000） */
.agent-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 1999;
}
/* 面板：右上角锚点（transform-origin 球按钮位置），顶部悬空圆角、底部贴底直角。
   米白暖底 + 青绿细边框（卡片 token），浮层投影保留以承载悬浮层级语义 */
.agent-panel {
  position: fixed;
  top: 57px;
  bottom: 0;
  right: 0;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  background: var(--tp-bg-card);
  border: 1px solid var(--tp-card-border);
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  /* 以导航栏 🤖 按钮中心为锚点（右缘内 28px、顶缘上方 28px），等比扩散/收回 */
  transform-origin: calc(100% - 28px) -28px;
}
/* 顶部上下文栏：全宽、上下高度减半（紧凑），标题左对齐大字，状态徽章居中靠下叠加在下半部分 */
.context-bar {
  position: relative;
  min-height: 48px;
  padding: 0 12px;
  border-bottom: 1px solid var(--tp-border);
  background: var(--tp-bg-card);
  overflow: hidden;
}
.context-title {
  position: absolute;
  left: 12px;
  top: 2px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 2px;
  white-space: nowrap;
  color: var(--tp-primary);
}
.context-status {
  position: absolute;
  bottom: 3px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 13px;
  line-height: 1.2;
  color: var(--tp-text-2);
}
/* 宽度拖拽手柄：面板左边缘竖条 + 视觉把手 */
.resize-handle {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 6px;
  cursor: col-resize;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}
.resize-handle:hover {
  background: var(--tp-primary);
  opacity: 0.5;
}
.handle-grip {
  width: 16px;
  height: 36px;
  border-radius: 8px;
  background: var(--tp-text-3);
  opacity: 0.35;
  color: var(--tp-surface);
  font-size: 14px;
  line-height: 36px;
  text-align: center;
  transition: opacity 0.15s;
}
.resize-handle:hover .handle-grip {
  opacity: 1;
}
.chat-stream-area {
  flex: 1;
  min-height: 0;
}
/* 球式扩散动画（分层时序 B）：
   打开——面板先从球按钮位置等比扩散，遮罩 0.1s 后淡入；
   关闭——遮罩先淡出，面板 0.1s 后缩回球按钮位置 */
.agent-panel-enter-active {
  transition:
    opacity 0.22s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}
.agent-panel-leave-active {
  transition:
    opacity 0.18s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.18s cubic-bezier(0.22, 1, 0.36, 1) 0.1s;
}
.agent-panel-enter-from,
.agent-panel-leave-to {
  opacity: 0;
  transform: scale(0.3);
}
.agent-panel-enter-to,
.agent-panel-leave-from {
  opacity: 1;
  transform: scale(1);
}
.agent-fade-enter-active {
  transition: opacity 0.22s ease 0.1s;
}
.agent-fade-leave-active {
  transition: opacity 0.18s ease;
}
.agent-fade-enter-from,
.agent-fade-leave-to {
  opacity: 0;
}
</style>
