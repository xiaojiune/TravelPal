<template>
  <div class="page-plan">
    <h2>规划结果</h2>

    <div v-if="!store.planResult" class="empty-state">
      <p>暂无规划结果，请先获取方案建议。</p>
      <router-link to="/" class="btn btn-primary">返回首页</router-link>
    </div>

    <template v-else>
      <div class="metrics-bar">
        <div class="metric"><span class="metric-label">总成本</span><span class="metric-value">{{ solution.total_cost.toFixed(1) }} min</span></div>
        <div class="metric"><span class="metric-label">旅行成本</span><span class="metric-value">{{ solution.total_dist.toFixed(1) }} min</span></div>
        <div class="metric"><span class="metric-label">等待惩罚</span><span class="metric-value">{{ solution.wait.toFixed(1) }} min</span></div>
        <div class="metric"><span class="metric-label">迟到惩罚</span><span class="metric-value">{{ solution.late.toFixed(1) }} min</span></div>
      </div>

      <div v-if="store.planResult?.commentary" class="commentary">
        💬 {{ store.planResult.commentary }}
      </div>

      <div class="action-bar">
        <button class="btn btn-outline" @click="sharePlan" :disabled="sharing">📤 分享此方案</button>
        <button v-if="!showMap" class="btn btn-outline" @click="showMap = true">🗺️ 显示地图</button>
        <button v-else class="btn btn-outline" @click="showMap = false">🗺️ 收起地图</button>
      </div>

      <div class="plan-layout">
        <div v-if="showMap" class="plan-map">
          <AmapMap :routes="solution.routes" :spots="store.planResult?.spots || {}" :polylines="store.planResult?.polylines" :daily-schedules="store.planResult?.daily_schedules" :highlight-day="highlightDay" :highlight-spot="highlightSpot" :amap-key="(store.planResult?.amap_api_key) || ''" :security-code="(store.planResult?.amap_security_code) || ''" /><!-- 路线/景点/真实轨迹 + 高德 JS API 凭据 -->
        </div>
        <div class="plan-schedule">
          <SchedulePanel :daily-schedules="store.planResult?.daily_schedules" :active-day="highlightDay" @select-day="highlightDay = $event" @select-spot="highlightSpot = $event" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
// ====== 状态定义 ======
import { ref, computed, watch } from 'vue'
import { usePlanStore } from '@/stores/plan'
import AmapMap from '@/components/AmapMap.vue'
import SchedulePanel from '@/components/SchedulePanel.vue'
import type { PlanResultSolution } from '@/types'
import { postHistory, getDeviceId } from '@/services/api'

const store = usePlanStore()
const solution = computed<PlanResultSolution>(() => (store.planResult?.solution || { routes: [], total_cost: 0, total_dist: 0, wait: 0, late: 0, valid: false }) as PlanResultSolution)

/** 当前高亮日索引，-1 表示全部显示。点击 SchedulePanel 日期标题切换。 */
const highlightDay = ref(-1)
/** 地图是否已显示（懒加载，首次点击按钮后常驻）。 */
const showMap = ref(false)
/** 行程表中点击的景点名，用于地图 marker 高亮。 */
const highlightSpot = ref('')
/** 分享按钮加载状态 */
const sharing = ref(false)

/** 手动分享当前方案到分享站（PostgreSQL）。 */
async function sharePlan() {
  const r = store.planResult
  if (!r || sharing.value) return
  const note = prompt('添加备注（可选，方便其他访客了解此方案）：')
  if (note === null) return
  sharing.value = true
  try {
    await postHistory({
      device_id: getDeviceId(),
      note: note || undefined,
      city: r.city || store.city,
      hotel: store.hotelName,
      n_days: r.best_days,
      cost: r.solution?.total_cost,
      spot_count: store.spots.length,
      plan_result: r as unknown as Record<string, unknown>,
    })
    alert('✅ 方案已分享到分享站！可在"历史记录"页面查看。')
  } catch {
    alert('❌ 分享失败，请稍后重试。')
  } finally {
    sharing.value = false
  }
}

watch(() => store.planResult, (val) => {
  if (val) {
    highlightDay.value = -1
    showMap.value = false
    highlightSpot.value = ''
  }
})


</script>

<style scoped>
.page-plan { max-width: 1200px; margin: 0 auto; }
.empty-state { text-align: center; padding: 60px 0; color: #999; }
.empty-state .btn { display: inline-block; margin-top: 16px; text-decoration: none; }
.metrics-bar { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.metric {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 12px 20px; text-align: center; flex: 1; min-width: 100px;
}
.metric-label { display: block; font-size: 11px; color: #888; margin-bottom: 4px; }
.metric-value { font-size: 20px; font-weight: 700; color: #333; }
.metric-action { display: flex; align-items: center; justify-content: center; }
.commentary {
  background: #f0f7ff; border: 1px solid #d0e3ff; border-radius: 8px;
  padding: 10px 16px; margin-bottom: 16px; font-size: 14px; color: #1a56db;
}
.btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; text-decoration: none; display: inline-block; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { background: #fff; color: #1a73e8; border: 1px solid #1a73e8; }
.plan-layout { display: flex; gap: 20px; }
.plan-map { flex: 2; height: 550px; }
.plan-schedule { flex: 1; min-width: 320px; }
.btn { padding: 10px 28px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; text-decoration: none; display: inline-block; }
.btn-primary { background: #1a73e8; color: #fff; }
.action-bar { display: flex; justify-content: center; gap: 12px; margin-bottom: 16px; }
.metric-days { gap: 6px; }
.days-input { width: 52px; text-align: center; padding: 6px 4px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
.add-poi-panel { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; }
.add-poi-panel .form-row { display: flex; gap: 8px; margin-bottom: 8px; }
.add-poi-panel .form-row input { flex: 1; padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; }
.add-poi-panel .result-row { display: flex; align-items: center; gap: 12px; font-size: 13px; }
.add-poi-panel .result-row .coord { font-family: monospace; color: #333; }
.add-poi-panel .hint.error { color: #e74c3c; font-size: 13px; }
.btn-sm { padding: 6px 14px; font-size: 12px; }
</style>
