<template>
  <!-- 右侧共创栏（固定右栏）：与主内容并排 flex 行，展开时主内容让宽度；无遮罩 -->
  <Transition name="agent-slide">
    <aside v-if="show" ref="panelRef" class="agent-panel" :style="{ width: panelWidth + 'px' }">
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
      <ChatStream class="chat-stream-area" @tool-result="onToolResult" />
    </aside>
  </Transition>
</template>

<script setup lang="ts">
/**
 * 全局 Agent 共创栏（固定右栏）：与主内容区并排，右侧常驻，收起时可整体滑出。
 *
 * - 不覆盖内容/无遮罩：作为 .app-body 的 flex 子项，展开时主内容区自适应让出宽度。
 * - 宽度可拖拽（25%~35vw，默认 28%），双击左缘恢复默认。
 * - 动效：右侧滑入/滑出（translateX），配淡入淡出；打开时主内容随宽度过渡让出。
 * - 对话/工具结果与左侧工具栏分工：本栏承载「对话共创」，结果的 POI 待选等进左侧
 *   toolPanel（store.queryResults），供用户选用。
 */
import { computed, ref, onMounted, onUnmounted } from 'vue'
import ChatStream from '@/components/ChatStream.vue'
import { usePlanStore } from '@/stores/plan'

defineOptions({ name: 'AgentPanel' })

const show = defineModel<boolean>('show', { default: false })

const store = usePlanStore()

/** 面板 DOM 引用：用于判断点击是否在面板内（外部点击收起）。 */
const panelRef = ref<HTMLElement | null>(null)

/** 点击面板外部（主内容区空白处）收起 Agent。 */
function onDocMousedown(e: MouseEvent) {
  if (!show.value) return
  const el = panelRef.value
  if (el && e.target instanceof Node && el.contains(e.target)) return
  show.value = false
}

onMounted(() => document.addEventListener('mousedown', onDocMousedown))
onUnmounted(() => document.removeEventListener('mousedown', onDocMousedown))

/** 接收 ChatStream 抛出的工具结果（{ tool, result, city }），写入 store 查询结果区。 */
function onToolResult(payload: { tool: string; result: unknown; city?: string }) {
  store.addQueryResult(payload.tool, payload.result, payload.city)
}

// ====== 会话上下文状态栏 ======
/** 顶部上下文栏状态三态：根据表单景点与规划结果判定 Agent 当前能做什么。 */
const sessionStatus = computed(() => {
  if (store.planResult) return { dot: '🔵', text: '方案已生成，可调整' }
  if (store.spots.length > 0) {
    return { dot: '🟡', text: `规划进行中... 已选 ${store.spots.length} 个景点` }
  }
  return { dot: '🟢', text: '准备出发' }
})

// ====== 面板宽度拖拽（默认 28%，clamp 25%~40%） ======
/** 面板右侧固定偏移（贴右缘，与 .agent-panel 的 right 对齐）。 */
const RIGHT_OFFSET = 0

const panelWidth = ref(Math.round(window.innerWidth * 0.28))
const dragging = ref(false)

/** 最小宽度：页面 25%。 */
function minPanelWidth() {
  return window.innerWidth * 0.25
}
/** 最大宽度：页面 35%。 */
function maxPanelWidth() {
  return window.innerWidth * 0.35
}
/** 默认宽度：页面 28%。 */
function defaultPanelWidth() {
  return window.innerWidth * 0.28
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

/** 双击手柄恢复默认宽度（页面 28%）。 */
function resetPanelWidth() {
  panelWidth.value = defaultPanelWidth()
}
</script>

<style scoped>
/* 右侧共创栏：作为 .app-body 的 flex 子项，贴右缘、与内容并排；stretch 撑满高度至页底(footer 上方) */
.agent-panel {
  position: relative;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  background: var(--tp-bg-card);
  border-left: 1px solid var(--tp-card-border);
  overflow: hidden;
  box-shadow: -2px 0 12px rgba(0, 0, 0, 0.06);
}
/* 顶部上下文栏：紧凑，标题左对齐大字，状态徽章居中靠下 */
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
  top: 50%;
  transform: translateY(-50%);
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
/* 右侧滑入/滑出动效（过渡宽度+位移，主内容随 flex 自动让出） */
.agent-slide-enter-active,
.agent-slide-leave-active {
  transition:
    width 0.28s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.22s ease;
}
.agent-slide-enter-from,
.agent-slide-leave-to {
  width: 0 !important;
  opacity: 0;
}
</style>
