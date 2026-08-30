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

    <!-- 异步任务面板：当前用户任务列表 + 取消入口 -->
    <template v-else-if="active === 'tasks'">
      <div class="panel-head">
        <span class="panel-title">📋 异步任务</span>
        <n-button size="tiny" quaternary class="panel-refresh" @click="loadTasks">↻ 刷新</n-button>
      </div>
      <div v-if="tasksLoading" class="panel-empty">加载中…</div>
      <div v-else-if="tasks.length === 0" class="panel-empty">暂无任务</div>
      <div v-for="t in tasks" :key="t.task_id" class="panel-card">
        <div class="panel-card-head">
          <span class="panel-card-tool">{{ taskTypeLabel(t.task_type) }}</span>
          <span class="panel-task-status" :style="{ color: statusColor(t.status) }">
            {{ statusLabel(t.status) }}
          </span>
        </div>
        <div class="panel-task-meta">创建于 {{ t.created_at ? formatTime(t.created_at) : '—' }}</div>
        <div v-if="canCancel(t.status)" class="panel-actions">
          <n-button size="tiny" tertiary type="error" @click="doCancel(t.task_id)">
            ✕ 取消
          </n-button>
        </div>
      </div>
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
 * - 异步任务面板：列出当前登录用户任务（GET /api/tasks），非终态（pending/running）
 *   可取消，激活时拉取 + 5s 周期刷新，离开清理定时器。
 * - 操作面板：v1.1 占位，点击显示「未实现，v1.1 接入」。
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'
import type { TaskListItem } from '@/types'
import { cancelTask, listTasks } from '@/services/api'
import { usePlanStore, isPoiQuery } from '@/stores/plan'
import ToolResultCard from '@/components/ToolResultCard.vue'

defineOptions({ name: 'ToolPanel' })

type ToolPanelKind = 'query' | 'ops' | 'tasks'
const props = defineProps<{ active: ToolPanelKind | null }>()

const store = usePlanStore()
const message = useMessage()

/** 非 POI 型查询结果（仅展示，不可添加行程）。 */
const otherResults = computed(() => store.queryResults.filter((q) => !isPoiQuery(q.tool)))

// ================== 异步任务面板 ==================

const tasks = ref<TaskListItem[]>([])
const tasksLoading = ref(false)
let tasksTimer: number | null = null

/** 状态展示元数据。 */
const STATUS_META: Record<string, { label: string; color: string; cancellable: boolean }> = {
  pending: { label: '排队中', color: '#d4a72c', cancellable: true },
  running: { label: '执行中', color: '#2f6fed', cancellable: true },
  done: { label: '已完成', color: '#2fa84f', cancellable: false },
  failed: { label: '失败', color: '#e5484d', cancellable: false },
  canceled: { label: '已取消', color: '#8a8f99', cancellable: false },
}

const TASK_TYPE_LABEL: Record<string, string> = {
  suggest: '建议',
  plan: '规划',
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

async function loadTasks() {
  tasksLoading.value = true
  try {
    const res = await listTasks(20)
    tasks.value = res.tasks
  } catch {
    // 网络/权限异常：保留现有列表，不打断面板
  } finally {
    tasksLoading.value = false
  }
}

async function doCancel(taskId: string) {
  try {
    const res = await cancelTask(taskId)
    message.success(res.status === 'canceled' ? '任务已取消' : '操作完成')
    void loadTasks()
  } catch (e: unknown) {
    message.error('取消失败: ' + (e instanceof Error ? e.message : '未知错误'))
  }
}

function startTasksTimer() {
  stopTasksTimer()
  tasksTimer = window.setInterval(() => void loadTasks(), 5000)
}
function stopTasksTimer() {
  if (tasksTimer !== null) {
    clearInterval(tasksTimer)
    tasksTimer = null
  }
}

// 切换到任务面板时拉取一次并启动周期刷新；离开清理
watch(
  () => props.active,
  (a) => {
    if (a === 'tasks') {
      void loadTasks()
      startTasksTimer()
    } else {
      stopTasksTimer()
    }
  },
)

onMounted(() => {
  if (props.active === 'tasks') startTasksTimer()
})
onUnmounted(() => stopTasksTimer())
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
.panel-refresh {
  margin-left: auto;
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
