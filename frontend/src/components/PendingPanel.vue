<template>
  <aside class="pending-panel" :class="{ collapsed }">
    <!-- 标题栏：点击切换折叠。折叠态只显示图标 + 数量 -->
    <div class="pending-head" @click="collapsed = !collapsed">
      <span class="pending-title">📋 待选</span>
      <span v-if="store.pendingPois.length" class="pending-count">{{
        store.pendingPois.length
      }}</span>
      <span class="pending-fold">{{ collapsed ? '▶' : '◀' }}</span>
    </div>
    <template v-if="!collapsed">
      <n-button
        v-if="store.pendingPois.length > 0"
        size="small"
        type="primary"
        block
        class="pending-add-all"
        @click="store.addAllPendingPois()"
      >
        ➕ 全部加入行程
      </n-button>
      <div v-if="store.pendingPois.length === 0" class="pending-empty">
        对话中查询的 POI 将出现在这里
      </div>
      <div v-for="(poi, i) in store.pendingPois" :key="i" class="pending-card">
        <div class="pending-header">
          {{ poi.name }}
          <n-tag :type="poi.poi_type === 'hotel' ? 'success' : 'primary'" size="small">
            {{ poi.poi_type === 'hotel' ? '🏨 酒店' : '🏛️ 景点' }}
          </n-tag>
        </div>
        <div class="pending-detail">📍 {{ poi.address }}</div>
        <div class="pending-detail">
          {{ poi.lon?.toFixed(4) }}, {{ poi.lat?.toFixed(4) }}
          <template v-if="poi.tw_start != null && poi.tw_end != null">
            · {{ Math.floor(poi.tw_start! / 60) }}:{{
              String(poi.tw_start! % 60).padStart(2, '0')
            }}~{{ Math.floor(poi.tw_end! / 60) }}:{{ String(poi.tw_end! % 60).padStart(2, '0') }}
          </template>
        </div>
        <div class="pending-actions">
          <n-button size="tiny" type="primary" @click="store.addPoiToForm(poi)">
            {{ poi.poi_type === 'hotel' ? '🏨 设为酒店' : '➕ 添加' }}
          </n-button>
          <n-button size="tiny" quaternary @click="store.removePendingPoi(i)"> ✕ 取消 </n-button>
        </div>
      </div>
    </template>
  </aside>
</template>

<script setup lang="ts">
/**
 * 全局左侧待选栏：Agent 对话查询到的 POI 暂存，常驻页面左侧，可折叠。
 *
 * 数据源为 plan store 的 pendingPois（全局共享——ChatStream 查询结果经
 * AgentPanel 转发写入，本栏只读展示与操作），保证「查询在面板、暂存在侧栏」。
 * 折叠后仅保留图标 + 数量徽标，主内容区恢复全宽。
 */
import { ref } from 'vue'
import { usePlanStore } from '@/stores/plan'

defineOptions({ name: 'PendingPanel' })

const store = usePlanStore()
/** 折叠状态：true 时只显示窄条图标。 */
const collapsed = ref(false)
</script>

<style scoped>
.pending-panel {
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
.pending-panel.collapsed {
  width: 44px;
  min-width: 44px;
  overflow: hidden;
}
.pending-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  cursor: pointer;
  color: var(--tp-text);
  font-weight: 600;
  font-size: 14px;
  user-select: none;
}
.pending-panel.collapsed .pending-head {
  justify-content: center;
  padding: 10px 0;
}
.pending-count {
  background: var(--tp-primary);
  color: #fff;
  border-radius: 8px;
  font-size: 11px;
  padding: 0 6px;
  line-height: 16px;
}
.pending-fold {
  margin-left: auto;
  font-size: 12px;
  color: var(--tp-text-3);
}
.pending-panel.collapsed .pending-fold {
  margin-left: 0;
}
.pending-add-all {
  margin: 0 12px 10px;
}
.pending-empty {
  font-size: 13px;
  color: var(--tp-text-3);
  text-align: center;
  margin-top: 40px;
  padding: 0 8px;
}
.pending-card {
  padding: 10px;
  margin: 0 8px 8px;
  border: 1px solid var(--tp-border);
  border-radius: 8px;
  background: var(--tp-surface);
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
.pending-detail {
  font-size: 12px;
  color: var(--tp-text-2);
  margin-bottom: 2px;
}
.pending-actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}
</style>
