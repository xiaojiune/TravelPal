<template>
  <div class="page-plan">
    <h2>规划结果</h2>

    <div v-if="!store.planResult" class="empty-state">
      <p>暂无规划结果，请先获取方案建议。</p>
      <n-button type="primary" @click="router.push('/')">返回首页</n-button>
    </div>

    <template v-else>
      <div class="metrics-bar">
        <div class="metric">
          <span class="metric-label">总成本</span
          ><span class="metric-value">{{ solution.total_cost.toFixed(1) }} min</span>
        </div>
        <div class="metric">
          <span class="metric-label">旅行成本</span
          ><span class="metric-value">{{ solution.total_dist.toFixed(1) }} min</span>
        </div>
        <div class="metric">
          <span class="metric-label">等待惩罚</span
          ><span class="metric-value">{{ solution.wait.toFixed(1) }} min</span>
        </div>
        <div class="metric">
          <span class="metric-label">迟到惩罚</span
          ><span class="metric-value">{{ solution.late.toFixed(1) }} min</span>
        </div>
      </div>

      <n-alert v-if="store.planResult?.commentary" type="info" :bordered="false" class="commentary">
        💬 {{ store.planResult.commentary }}
      </n-alert>

      <n-collapse
        v-if="store.historyRequestParams"
        v-model:expanded-names="paramsExpanded"
        class="params-collapse"
      >
        <n-collapse-item title="📋 原始请求参数" name="params">
          <div class="params-body">
            <div class="param-row">
              <span class="param-label">城市</span
              ><span>{{ store.historyRequestParams.city }}</span>
            </div>
            <div class="param-row">
              <span class="param-label">酒店</span
              ><span
                >{{ store.historyRequestParams.hotel_name }} ({{
                  store.historyRequestParams.hotel_lon
                }}, {{ store.historyRequestParams.hotel_lat }})</span
              >
            </div>
            <div class="param-row">
              <span class="param-label">启程时间</span
              ><span>{{ fmtParamTime(store.historyRequestParams.day_start as number) }}</span>
            </div>
            <div class="param-row">
              <span class="param-label">迟到惩罚</span
              ><span>{{ store.historyRequestParams.penalty_weight }}</span>
            </div>
            <div class="param-row">
              <span class="param-label">等待惩罚</span
              ><span>{{ store.historyRequestParams.early_wait_weight }}</span>
            </div>
            <div class="param-row">
              <span class="param-label">晚归惩罚</span
              ><span>{{ store.historyRequestParams.late_return_weight }}</span>
            </div>
            <div class="param-row param-section-title">景点列表</div>
            <div
              v-for="(s, i) in (store.historyRequestParams.spots as any[]) || []"
              :key="i"
              class="param-spot-row"
            >
              <span class="param-spot-name">{{ i + 1 }}. {{ s.name }}</span>
              <span class="param-spot-detail">停留 {{ s.stay }}分</span>
              <span class="param-spot-detail">预计 {{ fmtParamTime(s.expected_arrival) }}</span>
            </div>
          </div>
        </n-collapse-item>
      </n-collapse>

      <div class="action-bar">
        <n-button v-if="store.historyRecordId" secondary disabled>✅ 已在分享站</n-button>
        <n-button v-else secondary :disabled="sharing" @click="sharePlan">📤 分享此方案</n-button>
        <n-button v-if="!showMap" secondary @click="showMap = true">🗺️ 显示地图</n-button>
        <n-button v-else secondary @click="showMap = false">🗺️ 收起地图</n-button>
      </div>

      <div class="plan-layout">
        <div v-if="showMap" class="plan-map">
          <AmapMap
            :routes="solution.routes"
            :spots="store.planResult?.spots || {}"
            :polylines="store.planResult?.polylines"
            :daily-schedules="store.planResult?.daily_schedules"
            :highlight-days="[...highlightDays]"
            :highlight-spot="highlightSpot"
            :amap-key="store.planResult?.amap_api_key || ''"
            :security-code="store.planResult?.amap_security_code || ''"
          /><!-- 路线/景点/真实轨迹 + 高德 JS API 凭据 -->
        </div>
        <div class="plan-schedule">
          <SchedulePanel
            :daily-schedules="store.planResult?.daily_schedules"
            :all-expanded="!showMap"
            :highlight-days="[...highlightDays]"
            @toggle-day="toggleDay"
            @select-spot="highlightSpot = $event"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/** 规划结果页：展示成本指标、地图(AmapMap) + 行程(SchedulePanel) 左右联动、分享到分享站。 */
// ====== 状态定义 ======
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import { usePlanStore } from '@/stores/plan'
import AmapMap from '@/components/AmapMap.vue'
import SchedulePanel from '@/components/SchedulePanel.vue'
import type { PlanResultSolution } from '@/types'
import { postHistory, getDeviceId } from '@/services/api'

const store = usePlanStore()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const solution = computed<PlanResultSolution>(
  () =>
    (store.planResult?.solution || {
      routes: [],
      total_cost: 0,
      total_dist: 0,
      wait: 0,
      late: 0,
      valid: false,
    }) as PlanResultSolution,
)

/** 当前高亮日集合，空集合表示全部显示。SchedulePanel 高显按钮切换。 */
const highlightDays = ref<Set<number>>(new Set())
function toggleDay(di: number) {
  const next = new Set(highlightDays.value)
  if (next.has(di)) {
    next.delete(di)
  } else {
    next.add(di)
  }
  highlightDays.value = next
}
/** 地图是否已显示（懒加载，首次点击按钮后常驻）。 */
const showMap = ref(false)
/** 行程表中点击的景点名，用于地图 marker 高亮。 */
const highlightSpot = ref('')
/** 分享按钮加载状态 */
const sharing = ref(false)
/** 原始请求参数面板是否展开（n-collapse 展开名列表） */
const paramsExpanded = ref<string[]>([])

/** 将分钟数转换为 HH:MM 格式，用于参数面板展示。 */
function fmtParamTime(m: number) {
  if (m == null || m <= 0) return '-'
  const h = Math.floor(m / 60)
  return `${h}:${String(m % 60).padStart(2, '0')}`
}

/** 分享确认弹窗：收集分享意图，确认后执行分享。 */
function sharePlan() {
  dialog.warning({
    title: '分享此方案',
    content: '方案将公开到分享站，其他访客可在"历史记录"页查看。',
    positiveText: '分享',
    negativeText: '取消',
    onPositiveClick: () => doShare(),
  })
}

/** 手动分享当前方案到分享站（PostgreSQL）。 */
async function doShare() {
  const r = store.planResult
  if (!r || sharing.value) return
  sharing.value = true
  try {
    await postHistory({
      device_id: getDeviceId(),
      city: r.city || store.city,
      hotel: store.hotelName,
      n_days: r.best_days ?? 1,
      cost: r.solution?.total_cost,
      spot_count: store.spots.length,
      plan_result: r as unknown as Record<string, unknown>,
      request_params: store.buildRequest(r.best_days ?? null),
    })
    message.success('方案已分享到分享站！可在"历史记录"页面查看。')
  } catch {
    message.error('分享失败，请稍后重试。')
  } finally {
    sharing.value = false
  }
}

// 新方案加载时重置 UI 状态：全部折叠 → 收起地图 → 清空选中景点
watch(
  () => store.planResult,
  (val) => {
    if (val) {
      highlightDays.value = new Set()
      showMap.value = false
      highlightSpot.value = ''
    }
  },
)
</script>

<style scoped>
.page-plan {
  max-width: 1200px;
  margin: 0;
}
.empty-state {
  text-align: center;
  padding: 60px 0;
  color: var(--tp-text-3);
}
.metrics-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.metric {
  background: var(--tp-bg-card);
  border: 1px solid var(--tp-card-border);
  border-radius: 8px;
  padding: 12px 20px;
  text-align: center;
  flex: 1;
  min-width: 100px;
  box-shadow: var(--tp-card-shadow);
  transition: box-shadow 0.15s, transform 0.15s;
}
.metric:hover {
  box-shadow: var(--tp-card-shadow-hover);
  transform: translateY(-1px);
}
.metric-label {
  display: block;
  font-size: 11px;
  color: var(--tp-text-3);
  margin-bottom: 4px;
}
.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--tp-text);
}
.commentary {
  margin-bottom: 16px;
}
.params-collapse {
  margin-bottom: 16px;
}
.params-body {
  font-size: 12px;
}
.param-row {
  display: flex;
  gap: 12px;
  padding: 3px 0;
}
.param-label {
  color: var(--tp-text-3);
  min-width: 70px;
  flex-shrink: 0;
}
.param-section-title {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed var(--tp-border);
  color: var(--tp-text-2);
  font-weight: 600;
}
.param-spot-row {
  display: flex;
  gap: 12px;
  padding: 2px 0 2px 10px;
}
.param-spot-name {
  color: var(--tp-text);
}
.param-spot-detail {
  color: var(--tp-text-3);
  font-size: 11px;
}
.plan-layout {
  display: flex;
  gap: 20px;
}
.plan-map {
  flex: 2;
  height: 550px;
}
.plan-schedule {
  flex: 1;
  min-width: 320px;
}
.action-bar {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 16px;
}
</style>
