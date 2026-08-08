<template>
  <aside v-if="active" class="tool-panel">
    <!-- 查询面板：Agent 查询结果暂存（POI 待选 + 收编自原 PendingPanel） -->
    <template v-if="active === 'query'">
      <div class="panel-head">
        <span class="panel-title">🔍 查询结果</span>
        <span v-if="store.pendingPois.length" class="panel-count">{{
          store.pendingPois.length
        }}</span>
      </div>
      <n-button
        v-if="store.pendingPois.length > 0"
        size="small"
        type="primary"
        block
        class="panel-add-all"
        @click="store.addAllPendingPois()"
      >
        ➕ 全部加入行程
      </n-button>
      <div v-if="store.pendingPois.length === 0" class="panel-empty">
        对话中查询的 POI 将出现在这里
      </div>
      <!-- 卡片复用 ToolResultCard 渲染 POI 型 -->
      <div v-for="(poi, i) in store.pendingPois" :key="i" class="panel-card">
        <ToolResultCard :data="poi" />
        <div class="panel-actions">
          <n-button size="tiny" type="primary" @click="store.addPoiToForm(poi)">
            {{ poi.poi_type === 'hotel' ? '🏨 设为酒店' : '➕ 添加' }}
          </n-button>
          <n-button size="tiny" quaternary @click="store.removePendingPoi(i)">
            ✕ 取消
          </n-button>
        </div>
      </div>
    </template>

    <!-- 操作 / 任务面板：v1.1 占位 -->
    <template v-else>
      <div class="panel-head">
        <span class="panel-title">{{ active === 'ops' ? '🛠️ 方案操作' : '📋 异步任务' }}</span>
      </div>
      <div class="panel-placeholder">
        <n-empty description="开发中">
          <template #extra>
            <span class="placeholder-note">未实现，v1.1 接入</span>
          </template>
        </n-empty>
      </div>
    </template>
  </aside>
</template>

<script setup lang="ts">
/**
 * 左侧工具面板容器：随 ToolRail 激活的面板切换内容。
 *
 * 收起交互：active 为 null 时整个面板不渲染（v-if），由 ToolRail 图标
 * 点击 toggle 控制展开/收起（同项再点收起）。面板头标题下方带浅色分割线。
 *
 * - 查询面板：Agent 对话查询结果暂存区（POI 待选栏，收编自原 PendingPanel），
 *   卡片复用 ToolResultCard 渲染，加入行程/全部加入/取消逻辑保留。
 * - 操作/任务面板：v1.1 占位，点击显示「未实现，v1.1 接入」（页面占位即记忆，不写文档）。
 */
import { usePlanStore } from '@/stores/plan'
import ToolResultCard from '@/components/ToolResultCard.vue'

defineOptions({ name: 'ToolPanel' })

type ToolPanelKind = 'query' | 'ops' | 'tasks'
const props = defineProps<{ active: ToolPanelKind | null }>()

const store = usePlanStore()
</script>

<style scoped>
.tool-panel {
  width: 260px;
  min-width: 260px;
  border-right: 1px solid var(--tp-border);
  background: var(--tp-bg);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  transition:
    width 0.2s ease,
    min-width 0.2s ease;
}
.panel-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--tp-border-light);
  color: var(--tp-text);
  font-weight: 600;
  font-size: 14px;
  user-select: none;
}
.panel-count {
  background: var(--tp-primary);
  color: var(--tp-on-primary);
  border-radius: 8px;
  font-size: 11px;
  padding: 0 6px;
  line-height: 16px;
}
.panel-add-all {
  margin: 10px 12px;
}
.panel-empty {
  font-size: 13px;
  color: var(--tp-text-3);
  text-align: center;
  margin-top: 40px;
  padding: 0 8px;
}
.panel-card {
  padding: 10px;
  margin: 0 8px 8px;
  border: 1px solid var(--tp-card-border);
  border-radius: 8px;
  background: var(--tp-bg-card);
  box-shadow: var(--tp-card-shadow);
  transition: box-shadow 0.15s, transform 0.15s;
}
.panel-card:hover {
  box-shadow: var(--tp-card-shadow-hover);
  transform: translateY(-1px);
}
.panel-actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}
.panel-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 80px;
}
.placeholder-note {
  font-size: 12px;
  color: var(--tp-text-3);
}
</style>
