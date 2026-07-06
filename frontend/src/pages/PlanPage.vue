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
        <div class="metric"><span class="metric-label">算法耗时</span><span class="metric-value">{{ store.planResult.algo_time.toFixed(1) }}s</span></div>
      </div>

      <div class="plan-layout">
        <div class="plan-map">
          <AmapMap :routes="solution.routes" :spots="store.planResult.spots" :amapKey="store.planResult.amap_api_key || ''" />
        </div>
        <div class="plan-schedule">
          <SchedulePanel :daily-schedules="store.planResult.daily_schedules" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
// ====== 状态定义 ======
import { computed } from 'vue'
import { usePlanStore } from '../stores/plan'
import AmapMap from '../components/AmapMap.vue'
import SchedulePanel from '../components/SchedulePanel.vue'

const store = usePlanStore()
const solution = computed(() => store.planResult.solution || {})
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
.plan-layout { display: flex; gap: 20px; }
.plan-map { flex: 2; height: 550px; }
.plan-schedule { flex: 1; min-width: 320px; }
.btn { padding: 10px 28px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; text-decoration: none; display: inline-block; }
.btn-primary { background: #1a73e8; color: #fff; }
</style>
