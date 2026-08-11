<template>
  <div class="tool-rail">
    <!-- 查询面板（默认激活）：点击图标 toggle 展开/收起 -->
    <button
      class="rail-btn"
      :class="{ active: active === 'query' }"
      title="查询结果"
      @click="toggle('query')"
    >
      🔍
    </button>
    <!-- 操作面板（占位：v1.1 接入 add_poi/remove_poi 历史） -->
    <button
      class="rail-btn"
      :class="{ active: active === 'ops' }"
      title="方案操作（v1.1 接入）"
      @click="toggle('ops')"
    >
      🛠️
    </button>
    <!-- 任务面板（占位：v1.1 接入 Celery 任务列表） -->
    <button
      class="rail-btn"
      :class="{ active: active === 'tasks' }"
      title="异步任务（v1.1 接入）"
      @click="toggle('tasks')"
    >
      📋
    </button>
    <div class="rail-divider"></div>
    <!-- 反馈（动作型按钮：点击弹全局居中弹窗，不参与面板 toggle） -->
    <button class="rail-btn rail-action" title="提交反馈" @click="emit('feedback')">
      📮
    </button>
  </div>
</template>

<script setup lang="ts">
/**
 * 左侧工具栏竖条：面板切换骨架（点击图标 toggle 展开/收起）+ 反馈动作按钮。
 *
 * 当前仅「查询」面板可用（Agent 对话查询结果暂存区）；
 * 「操作 / 任务」面板为占位（v1.1 接入 add_poi/remove_poi 历史与 Celery 任务列表），
 * 点击显示「开发中」占位内容（见 ToolPanel）。
 * 「反馈」为动作型按钮：emit feedback 事件由 App.vue 打开全局弹窗，不改变面板状态。
 */
defineOptions({ name: 'ToolRail' })

const emit = defineEmits<{ feedback: [] }>()

/** 工具栏面板类型：查询（可用）/ 操作、任务（v1.1 占位）。 */
type ToolPanelKind = 'query' | 'ops' | 'tasks'

const active = defineModel<ToolPanelKind | null>('active', { default: 'query' })

/** 点击图标切换：同项再点收起（null 隐藏面板），异项切换。 */
function toggle(k: ToolPanelKind) {
  active.value = active.value === k ? null : k
}
</script>

<style scoped>
.tool-rail {
  width: 48px;
  min-width: 48px;
  border-right: 1px solid var(--tp-border);
  background: var(--tp-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0;
  gap: 4px;
}
.rail-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--tp-text-2);
}
.rail-btn:hover {
  background: var(--tp-primary-soft);
}
.rail-btn.active {
  background: var(--tp-primary-soft);
  color: var(--tp-primary);
}
/* 反馈按钮与面板切换按钮的分隔线 */
.rail-divider {
  width: 24px;
  height: 1px;
  background: var(--tp-border);
  margin: 4px 0;
}
/* 反馈动作按钮：独立于面板状态，hover 用 info 靛蓝呼应全局指示语义 */
.rail-action:hover {
  background: var(--tp-info-soft);
  color: var(--tp-info);
}
</style>
