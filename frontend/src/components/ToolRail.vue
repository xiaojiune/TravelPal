<template>
  <div class="tool-rail">
    <!-- 查询面板（默认激活） -->
    <button
      class="rail-btn"
      :class="{ active: active === 'query' }"
      title="查询结果"
      @click="active = 'query'"
    >
      🔍
    </button>
    <!-- 操作面板（占位：v1.1 接入 add_poi/remove_poi 历史） -->
    <button
      class="rail-btn"
      :class="{ active: active === 'ops' }"
      title="方案操作（v1.1 接入）"
      @click="active = 'ops'"
    >
      🛠️
    </button>
    <!-- 任务面板（占位：v1.1 接入 Celery 任务列表） -->
    <button
      class="rail-btn"
      :class="{ active: active === 'tasks' }"
      title="异步任务（v1.1 接入）"
      @click="active = 'tasks'"
    >
      📋
    </button>
  </div>
</template>

<script setup lang="ts">
/**
 * 左侧工具栏竖条：面板切换骨架。
 *
 * 当前仅「查询」面板可用（Agent 对话查询结果暂存区）；
 * 「操作 / 任务」面板为占位（v1.1 接入 add_poi/remove_poi 历史与 Celery 任务列表），
 * 点击显示「开发中」占位内容（见 ToolPanel）。
 */
defineOptions({ name: 'ToolRail' })

/** 工具栏面板类型：查询（可用）/ 操作、任务（v1.1 占位）。 */
type ToolPanelKind = 'query' | 'ops' | 'tasks'

const active = defineModel<ToolPanelKind>('active', { default: 'query' })
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
</style>
