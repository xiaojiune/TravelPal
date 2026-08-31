<template>
  <aside v-if="active" class="tool-panel">
    <!-- 查询面板：Agent 查询结果暂存（POI 待选 + 其它结果仅展示） -->
    <template v-if="active === 'query'">
      <div class="panel-head">
        <span class="panel-title">🔍 查询结果</span>
        <span v-if="store.pendingPois.length" class="panel-count">{{
          store.pendingPois.length
        }}</span>
      </div>

      <!-- 第一节：POI 待选（可添加 / 全部加入 / 取消） -->
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
      <div v-for="(poi, i) in store.pendingPois" :key="`poi-${i}`" class="panel-card">
        <ToolResultCard :data="poi" />
        <div class="panel-actions">
          <n-button size="tiny" type="primary" @click="store.addPoiToForm(poi)">
            {{ poi.poi_type === 'hotel' ? '🏨 设为酒店' : '➕ 添加' }}
          </n-button>
          <n-button size="tiny" quaternary @click="store.removePendingPoi(poi)">
            ✕ 取消
          </n-button>
        </div>
      </div>

      <!-- 第二节：其它查询结果（仅展示，可删除） -->
      <template v-if="otherResults.length">
        <div class="panel-section-title">其它查询结果</div>
        <div v-for="(q, i) in otherResults" :key="`other-${i}`" class="panel-card">
          <div class="panel-card-head">
            <span class="panel-card-tool">{{ q.tool }}</span>
            <span class="panel-card-time">{{ q.time }}</span>
            <n-button size="tiny" quaternary class="panel-card-del" @click="store.removeQueryResult(i)">
              ✕
            </n-button>
          </div>
          <ToolResultCard :data="q.result" />
        </div>
      </template>
    </template>

    <!-- 异步任务面板：任务集合（生命周期在 store，后台轮询更新状态） -->
    <template v-else-if="active === 'tasks'">
      <div class="panel-head">
        <span class="panel-title">📋 异步任务</span>
      </div>
      <div v-if="taskItems.length === 0" class="panel-empty">暂无任务（提交后在此查看进度）</div>
      <template v-for="(t, index) in taskItems" :key="t.task_id">
        <div v-if="index === 1" class="panel-section-title">历史</div>
        <div class="panel-card" :style="{ borderColor: statusColor(t.status) }">
        <div class="panel-card-head">
          <span class="panel-task-name"
            >任务{{ taskItems.length - index }}-{{ taskTypeLabel(t.task_type) }}</span
          >
          <span class="panel-task-status" :style="{ color: statusColor(t.status) }">
            {{ statusLabel(t.status) }}
          </span>
        </div>
        <div class="panel-task-meta">提交于 {{ t.created_at ? formatTime(t.created_at) : '—' }}</div>
        <div v-if="canCancel(t.status) || t.status === 'done'" class="panel-actions">
          <n-button
            v-if="canCancel(t.status)"
            size="tiny"
            tertiary
            type="error"
            @click="doCancel(t.task_id)"
          >
            ✕ 取消
          </n-button>
          <n-button v-if="t.status === 'done'" size="tiny" type="primary" @click="viewResult(t.task_id)">
            查看结果
          </n-button>
        </div>
        </div>
      </template>
    </template>

    <!-- 操作面板：v1.1 占位 -->
    <template v-else>
      <div class="panel-head">
        <span class="panel-title">🛠️ 方案操作</span>
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
 * - 查询面板两节：POI 待选（上，可添加/全部加入/取消，收编自原 PendingPanel，
 *   由 store.pendingPois 派生）+ 其它查询结果（下，仅展示，如 get_driving）。
 * - 异步任务面板：渲染 store.taskItems（任务生命周期单点在 store，后台轮询更新状态）；
 *   非终态可取消，已完成可查看结果（暂跳 /or，端点问题后续修）。
 * - 操作面板：v1.1 占位，点击显示「未实现，v1.1 接入」。
 */
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import type { SuggestionItem, SpotDictItem } from '@/types'
import { cancelTask, getTask } from '@/services/api'
import { useSuggestCache } from '@/composables/useSuggestCache'
import { usePlanStore, isPoiQuery } from '@/stores/plan'
import ToolResultCard from '@/components/ToolResultCard.vue'

defineOptions({ name: 'ToolPanel' })

type ToolPanelKind = 'query' | 'ops' | 'tasks'
const props = defineProps<{ active: ToolPanelKind | null }>()

const store = usePlanStore()
const message = useMessage()
const router = useRouter()
const cache = useSuggestCache()

/** 任务集合（生命周期在 store；后台轮询更新 status）。 */
const { taskItems } = storeToRefs(store)

/** 非 POI 型查询结果（仅展示，不可添加行程）。 */
const otherResults = computed(() => store.queryResults.filter((q) => !isPoiQuery(q.tool)))

// ================== 异步任务面板 ==================

/** 状态展示元数据。 */
const STATUS_META: Record<string, { label: string; color: string; cancellable: boolean }> = {
  pending: { label: '排队中', color: '#d4a72c', cancellable: true },
  running: { label: '执行中', color: '#2f6fed', cancellable: true },
  done: { label: '已完成', color: '#2fa84f', cancellable: false },
  failed: { label: '失败', color: '#e5484d', cancellable: false },
  canceled: { label: '已取消', color: '#8a8f99', cancellable: false },
}

const TASK_TYPE_LABEL: Record<string, string> = {
  'or-ca': '求解',
  'or-vns': '求解',
  adjust: '调整',
}

function statusLabel(status: string): string {
  return STATUS_META[status]?.label ?? status
}
function statusColor(status: string): string {
  return STATUS_META[status]?.color ?? '#8a8f99'
}
function canCancel(status: string): boolean {
  return STATUS_META[status]?.cancellable ?? false
}
function taskTypeLabel(type: string): string {
  return TASK_TYPE_LABEL[type] ?? type
}
function formatTime(iso: string): string {
  // Iso 字符串 → YYYY-MM-DD HH:mm（本地时区）
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function doCancel(taskId: string) {
  try {
    await cancelTask(taskId)
    store.setTaskStatus(taskId, 'canceled')
    message.success('任务已取消')
  } catch (e: unknown) {
    message.error('取消失败: ' + (e instanceof Error ? e.message : '未知错误'))
  }
}

/** 查看已完成任务结果：拉取 result → 写入 store 建议区 → 跳 /or（后续端点修好再细化）。 */
async function viewResult(taskId: string) {
  try {
    const detail = await getTask(taskId)
    const result = detail.result as
      | (Record<string, unknown> & { suggestions?: unknown[]; amap_api_key?: unknown; amap_security_code?: unknown })
      | undefined
    if (result) {
      if (Array.isArray(result.suggestions)) {
        store.suggestions = result.suggestions as SuggestionItem[]
      }
      if (typeof result.amap_api_key === 'string') store.amapApiKey = result.amap_api_key
      if (typeof result.amap_security_code === 'string') store.amapSecurityCode = result.amap_security_code
      // 回填 suggest 缓存：/or 页点建议卡 buildPlanResultFromSuggestion 依赖 spots/polylines；
      // 不补则 /show 地图无覆盖物、setFitView 失效而停留在默认中心(北京)，且无道路。
      if (result.spots && typeof result.spots === 'object') {
        cache.suggestSpots.value = result.spots as Record<string, SpotDictItem>
      }
      if (result.polylines && typeof result.polylines === 'object') {
        cache.suggestPolylines.value = result.polylines as Record<string, string>
      }
      if (typeof result.algo_time === 'number') cache.suggestAlgoTime.value = result.algo_time
    }
    router.push('/or')
  } catch (e: unknown) {
    message.error('获取结果失败: ' + (e instanceof Error ? e.message : '未知错误'))
  }
}
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
.panel-section-title {
  font-size: 12px;
  color: var(--tp-text-3);
  padding: 6px 12px 2px;
  border-top: 1px solid var(--tp-border-light);
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
.panel-card-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.panel-card-tool {
  font-size: 11px;
  color: var(--tp-primary);
  font-weight: 600;
}
.panel-task-name {
  font-size: 11px;
  color: var(--tp-text);
  font-weight: 600;
}
.panel-card-time {
  font-size: 11px;
  color: var(--tp-text-3);
  margin-right: auto;
}
.panel-card-del {
  color: var(--tp-text-3);
}
.panel-task-status {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
}
.panel-task-meta {
  font-size: 11px;
  color: var(--tp-text-3);
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
