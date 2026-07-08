<template>
  <div class="page-plan">
    <h2>规划结果</h2>

    <div v-if="!store.planResult" class="empty-state">
      <p>暂无规划结果，请先获取方案建议。</p>
      <router-link to="/" class="btn btn-primary">返回首页</router-link>
    </div>

    <template v-else>
      <div class="metrics-bar">
        <div class="metric"><span class="metric-label">总成本</span><span class="metric-value">{{ solution.total_cost.toFixed(1) }}</span></div>
        <div class="metric"><span class="metric-label">旅行成本</span><span class="metric-value">{{ solution.total_dist.toFixed(1) }}</span></div>
        <div class="metric"><span class="metric-label">等待惩罚</span><span class="metric-value">{{ solution.wait.toFixed(1) }}</span></div>
        <div class="metric"><span class="metric-label">迟到惩罚</span><span class="metric-value">{{ solution.late.toFixed(1) }}</span></div>
        <div class="metric"><span class="metric-label">算法耗时</span><span class="metric-value">{{ store.planResult?.algo_time?.toFixed(1) }}s</span></div>
        <div class="metric metric-action">
          <button class="btn btn-outline" :disabled="balancing" @click="doBalance">
            {{ balancing ? '均衡中...' : '⚖️ 均衡分配' }}
          </button>
        </div>
        <div class="metric metric-action metric-days">
          <input v-model.number="newDays" type="number" min="1" class="days-input" />
          <button class="btn btn-outline" :disabled="adjusting" @click="onAdjustDays">
            {{ adjusting ? '调整中...' : '📅 调整天数' }}
          </button>
        </div>
      </div>

      <div v-if="store.planResult?.commentary" class="commentary">
        💬 {{ store.planResult.commentary }}
      </div>

      <div class="plan-layout">
        <div class="plan-map">
          <AmapMap :routes="solution.routes" :spots="store.planResult?.spots" :amap-key="(store.planResult?.amap_api_key) || ''" />
        </div>
        <div class="plan-schedule">
          <SchedulePanel :daily-schedules="store.planResult?.daily_schedules" :on-remove-poi="doRemovePoi" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
// ====== 状态定义 ======
import { ref, computed, watch } from 'vue'
import { usePlanStore } from '@/stores/plan'
import { usePlanAdjust } from '@/composables/usePlanAdjust'
import AmapMap from '@/components/AmapMap.vue'
import SchedulePanel from '@/components/SchedulePanel.vue'
import type { PlanResultSolution } from '@/types'

const store = usePlanStore()
const solution = computed<PlanResultSolution>(() => (store.planResult?.solution || { routes: [], total_cost: 0, total_dist: 0, wait: 0, late: 0, valid: false }) as PlanResultSolution)
const { balancing, adjusting, doBalance, doAdjustDays, doRemovePoi } = usePlanAdjust()
const newDays = ref(1)

watch(() => store.planResult?.best_days, (val) => {
  if (val) newDays.value = val
})

// 收到新规划结果时写入 localStorage 历史记录
function saveToHistory() {
  const r = store.planResult
  if (!r) return
  const key = `plan_${Date.now()}`
  const record = {
    id: key,
    city: r.city || store.city,
    hotel: store.hotelName,
    n_days: r.best_days,
    cost: r.solution?.total_cost,
    spots: store.spots.length,
    time: new Date().toLocaleString(),
  }
  const raw = localStorage.getItem('travelpal_history')
  const list = raw ? JSON.parse(raw) : []
  list.unshift(record)
  if (list.length > 10) list.length = 10
  localStorage.setItem('travelpal_history', JSON.stringify(list))
}

watch(() => store.planResult, (val) => { if (val) saveToHistory() })

// ====== 数据操作 ======
async function onAdjustDays() {
  await doAdjustDays(newDays.value)
}

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
.metric-days { gap: 6px; }
.days-input { width: 52px; text-align: center; padding: 6px 4px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
</style>
