<template>
  <div class="page-suggest">
    <h2>方案建议</h2>

    <div v-if="!store.suggestions.length && !store.deepResults.length" class="empty-state">
      <p>暂无方案建议，请先在首页输入规划参数。</p>
      <n-button type="primary" @click="router.push('/')">返回首页</n-button>
    </div>

    <template v-else>
      <!-- ====== 上区：方案建议卡片 ====== -->
      <div v-if="store.suggestions.length" class="suggest-section">
        <div v-for="group in groupedSuggestions" :key="group.n_days" class="day-group">
          <h3>{{ group.n_days }} 日游</h3>
          <div class="card-list">
            <div
              v-for="(s, i) in group.items"
              :key="i"
              class="suggest-card"
              :class="{ disabled: mode === 'deep' }"
              @click="onCardClick(s)"
            >
              <div class="card-body">
                <span class="card-method">{{ s.method }}</span>
                <span class="card-cost">成本 {{ s.cost.toFixed(1) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ====== 模式切换 + 深度操作区 ====== -->
      <div class="action-bar">
        <div class="mode-toggle">
          <n-radio-group v-model:value="mode" @update:value="onModeChange">
            <n-radio-button value="fast">快速</n-radio-button>
            <n-radio-button value="deep">深度</n-radio-button>
          </n-radio-group>
        </div>

        <div v-if="mode === 'deep'" class="deep-form">
          <label>行程天数</label>
          <n-input-number
            v-model:value="deepNDays"
            :min="1"
            :max="maxDayOption"
            placeholder="天数"
            style="width: 130px"
          />
          <span class="hint">建议 {{ defaultDays }} 天</span>
          <n-button type="primary" :loading="store.loading" :disabled="!deepNDays" @click="runDeep">
            🚀 获取规划
          </n-button>
        </div>
        <div v-if="mode === 'fast'" class="mode-hint">💡 点击上方方案卡片直接查看规划结果</div>
        <div v-if="mode === 'fast' && store.suggestAlgoTime" class="algo-time">
          ⏱ 搜索耗时 {{ store.suggestAlgoTime.toFixed(3) }}s
        </div>
        <div v-if="mode === 'deep' && deepAlgoTime" class="algo-time">
          ⏱ 深度规划耗时 {{ deepAlgoTime.toFixed(3) }}s
        </div>
      </div>

      <!-- ====== 下区：深度结果卡片 ====== -->
      <div v-if="store.deepResults.length" class="deep-section">
        <h3>深度规划结果</h3>
        <div class="card-list">
          <div
            v-for="(r, i) in store.deepResults"
            :key="i"
            class="suggest-card result-card"
            @click="viewDeepResult(r)"
          >
            <div class="card-body">
              <span class="card-method">VNS({{ r.best_m }})</span>
              <span class="card-cost">成本 {{ r.solution?.total_cost?.toFixed(1) }}</span>
              <span class="card-meta">{{ r.best_days }} 天</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/** 方案建议页：快速/深度双模式入口。快速点击卡片直达，深度生成结果卡片后点击跳转。 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { usePlanStore } from '@/stores/plan'
import { submitTask } from '@/services/api'
import { useTaskPolling } from '@/composables/useTaskPolling'
import type { SuggestionItem, PlanResult } from '@/types'

const store = usePlanStore()
const router = useRouter()
const message = useMessage()

const { startPolling } = useTaskPolling()

const mode = ref<'fast' | 'deep'>('fast')
const deepNDays = ref<number | null>(null)
const deepAlgoTime = ref(0)

/** 模式切换：切到快速清空天数，切到深度预填建议天数。 */
function onModeChange(value: string | number) {
  mode.value = value as 'fast' | 'deep'
  if (mode.value === 'fast') deepNDays.value = null
  else deepNDays.value = defaultDays.value
}

/** 按天数分组建议，每组内部按成本升序排列。 */
const groupedSuggestions = computed(() => {
  const seen = new Set<number>()
  const groups: { n_days: number; items: SuggestionItem[] }[] = []
  for (const s of store.suggestions) {
    if (!seen.has(s.n_days)) {
      seen.add(s.n_days)
      groups.push({
        n_days: s.n_days,
        items: store.suggestions
          .filter((x) => x.n_days === s.n_days)
          .sort((a, b) => a.cost - b.cost),
      })
    }
  }
  return groups.sort((a, b) => a.n_days - b.n_days)
})

const maxDayOption = computed(() => Math.max(...store.suggestions.map((s) => s.n_days), 1))
const defaultDays = computed(() => {
  if (!store.suggestions.length) return 1
  return store.suggestions.reduce((a, b) => (a.cost < b.cost ? a : b)).n_days
})

/**
 * 从建议项构造完整 PlanResult，直接使用 suggest 响应的 daily_schedules、spots 和 polylines。
 * 不调 plan/ 接口，避免重复计算。
 */
function buildPlanResultFromSuggestion(s: SuggestionItem): PlanResult {
  return {
    type: 'solution',
    solution: {
      routes: s.routes,
      total_cost: s.cost,
      total_dist: s.total_dist,
      wait: s.wait,
      late: s.late,
      valid: true,
    },
    best_days: s.n_days,
    best_m: s.method,
    spots: store.suggestSpots,
    daily_schedules: s.daily_schedules || [],
    amap_api_key: store.amapApiKey,
    amap_security_code: store.amapSecurityCode,
    algo_time: store.suggestAlgoTime,
    polylines: Object.keys(store.suggestPolylines).length ? store.suggestPolylines : undefined,
  }
}

function onCardClick(s: SuggestionItem) {
  if (mode.value === 'deep') return
  store.planResult = buildPlanResultFromSuggestion(s)
  store.historyRecordId = null
  store.historyRequestParams = null
  router.push('/plan')
}

/**
 * 深度规划：复用 suggest 阶段缓存的成本/距离矩阵，
 * 使后端 run_planning 跳过驾车 AMap API 调用。
 * 提交异步 plan 任务后轮询，完成后追加到深度结果卡片。
 */
async function runDeep() {
  if (!deepNDays.value) return
  store.loading = true
  store.deepResults = []
  try {
    const req = store.buildRequest(deepNDays.value, {
      cost_matrix: store.suggestCostMatrix.length ? store.suggestCostMatrix : undefined, // 复用成本矩阵，避免 re-fetch
      dist_matrix: store.suggestDistMatrix.length ? store.suggestDistMatrix : undefined,
    })
    req.mode = 'deep'
    const { task_id } = await submitTask('plan', req)
    const data = (await startPolling(task_id)) as unknown as PlanResult
    // 深度模式复用 suggest 阶段缓存的真实路径坐标（后端因跳过驾车 API 返回空 polylines）
    if (Object.keys(store.suggestPolylines).length) data.polylines = store.suggestPolylines
    store.deepResults.push(data)
    deepAlgoTime.value = data.algo_time || 0
    deepNDays.value = null
  } catch (e: unknown) {
    message.error('深度规划失败: ' + ((e as any)?.response?.data?.detail || (e as Error)?.message))
  } finally {
    store.loading = false
  }
}

function viewDeepResult(r: PlanResult) {
  store.planResult = r
  store.historyRecordId = null
  store.historyRequestParams = null
  router.push('/plan')
}
</script>

<style scoped>
.page-suggest {
  max-width: 700px;
  margin: 0;
}
.empty-state {
  text-align: center;
  padding: 60px 0;
  color: var(--tp-text-3);
}
.empty-state .btn {
  display: inline-block;
  margin-top: 16px;
  text-decoration: none;
}
.suggest-section {
  margin-bottom: 24px;
}
.day-group {
  margin-bottom: 24px;
}
.day-group h3 {
  font-size: 16px;
  margin-bottom: 10px;
  color: var(--tp-text);
  border-left: 3px solid var(--tp-primary);
  padding-left: 10px;
}
.card-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.suggest-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--tp-bg-card);
  border: 1px solid var(--tp-card-border);
  border-radius: 8px;
  padding: 10px 16px;
  cursor: pointer;
  box-shadow: var(--tp-card-shadow);
  transition: box-shadow 0.15s, transform 0.15s;
}
.suggest-card:hover {
  box-shadow: var(--tp-card-shadow-hover);
  transform: translateY(-1px);
}
.suggest-card.disabled {
  opacity: 0.5;
  cursor: default;
}
.suggest-card.disabled:hover {
  box-shadow: none;
  transform: none;
}
.result-card {
  border-color: var(--tp-primary);
  background: var(--tp-primary-soft);
}
.card-body {
  display: flex;
  align-items: center;
  gap: 14px;
}
.card-method {
  background: var(--tp-primary-soft);
  color: var(--tp-primary);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.card-cost {
  font-size: 14px;
  color: var(--tp-text-2);
}
.card-meta {
  font-size: 12px;
  color: var(--tp-text-3);
}

/* ====== 操作栏 ====== */
.action-bar {
  margin: 20px 0;
  padding: 16px;
  background: var(--tp-surface);
  border: 1px solid var(--tp-border);
  border-radius: 8px;
}
.mode-toggle {
  display: flex;
  margin-bottom: 12px;
}
.deep-form {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.deep-form label {
  font-size: 13px;
  color: var(--tp-text-2);
}
.deep-form .hint {
  font-size: 12px;
  color: var(--tp-text-3);
}
.mode-hint {
  font-size: 13px;
  color: var(--tp-text-3);
  text-align: center;
  padding: 4px 0;
}
.algo-time {
  font-size: 12px;
  color: var(--tp-text-3);
  text-align: center;
  padding: 2px 0;
}

/* ====== 深度结果区 ====== */
.deep-section {
  margin-top: 20px;
}
.deep-section h3 {
  font-size: 15px;
  margin-bottom: 10px;
  color: var(--tp-primary);
}
</style>
