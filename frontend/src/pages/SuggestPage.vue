<template>
  <div class="page-suggest">
    <h2>方案建议</h2>

    <div v-if="!store.suggestions.length && !store.deepResults.length" class="empty-state">
      <p>暂无方案建议，请先在首页输入规划参数。</p>
      <router-link to="/" class="btn btn-primary">返回首页</router-link>
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
          <button
            class="btn btn-mode"
            :class="{ active: mode === 'fast' }"
            @click="mode = 'fast'; deepNDays = null"
          >快速</button>
          <button
            class="btn btn-mode"
            :class="{ active: mode === 'deep' }"
            @click="mode = 'deep'; deepNDays = defaultDays"
          >深度</button>
        </div>

        <div v-if="mode === 'deep'" class="deep-form">
          <label>行程天数</label>
          <input v-model.number="deepNDays" type="number" min="1" :max="maxDayOption" placeholder="天数" />
          <span class="hint">建议 {{ defaultDays }} 天</span>
          <button class="btn btn-primary" :disabled="!deepNDays || store.loading" @click="runDeep">
            {{ store.loading ? '计算中...' : '🚀 获取规划' }}
          </button>
        </div>
        <div v-if="mode === 'fast'" class="mode-hint">
          💡 点击上方方案卡片直接查看规划结果
        </div>
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
import { usePlanStore } from '@/stores/plan'
import { postPlan } from '@/services/api'
import type { SuggestionItem, PlanResult } from '@/types'

const store = usePlanStore()
const router = useRouter()

const mode = ref<'fast' | 'deep'>('fast')
const deepNDays = ref<number | null>(null)
const deepAlgoTime = ref(0)

/** 按天数分组建议，每组内部按成本升序排列。 */
const groupedSuggestions = computed(() => {
  const seen = new Set<number>()
  const groups: { n_days: number; items: SuggestionItem[] }[] = []
  for (const s of store.suggestions) {
    if (!seen.has(s.n_days)) {
      seen.add(s.n_days)
      groups.push({
        n_days: s.n_days,
        items: store.suggestions.filter(x => x.n_days === s.n_days).sort((a, b) => a.cost - b.cost),
      })
    }
  }
  return groups.sort((a, b) => a.n_days - b.n_days)
})

const maxDayOption = computed(() => Math.max(...store.suggestions.map(s => s.n_days), 1))
const defaultDays = computed(() => {
  if (!store.suggestions.length) return 1
  return store.suggestions.reduce((a, b) => a.cost < b.cost ? a : b).n_days
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
  router.push('/plan')
}

/**
 * 深度规划：复用 suggest 阶段缓存的成本/距离矩阵，
 * 使后端 run_planning 跳过驾车 AMap API 调用。
 */
async function runDeep() {
  if (!deepNDays.value) return
  store.loading = true
  store.deepResults = []
  try {
    const req = store.buildRequest(deepNDays.value, {
      cost_matrix: store.suggestCostMatrix.length ? store.suggestCostMatrix : undefined,  // 复用成本矩阵，避免 re-fetch
      dist_matrix: store.suggestDistMatrix.length ? store.suggestDistMatrix : undefined,
    })
    req.mode = 'deep'
    const data = await postPlan(req)
    store.deepResults.push(data)
    deepAlgoTime.value = data.algo_time || 0
    deepNDays.value = null
  } catch (e: unknown) {
    alert('深度规划失败: ' + ((e as any)?.response?.data?.detail || (e as Error)?.message))
  } finally {
    store.loading = false
  }
}

function viewDeepResult(r: PlanResult) {
  store.planResult = r
  router.push('/plan')
}
</script>

<style scoped>
.page-suggest { max-width: 700px; margin: 0 auto; }
.empty-state { text-align: center; padding: 60px 0; color: #999; }
.empty-state .btn { display: inline-block; margin-top: 16px; text-decoration: none; }
.suggest-section { margin-bottom: 24px; }
.day-group { margin-bottom: 24px; }
.day-group h3 { font-size: 16px; margin-bottom: 10px; color: #333; border-left: 3px solid #1a73e8; padding-left: 10px; }
.card-list { display: flex; flex-direction: column; gap: 8px; }
.suggest-card {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 10px 16px; cursor: pointer; transition: box-shadow 0.15s;
}
.suggest-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.suggest-card.disabled { opacity: 0.5; cursor: default; }
.suggest-card.disabled:hover { box-shadow: none; }
.result-card { border-color: #1a73e8; background: #f8fbff; }
.card-body { display: flex; align-items: center; gap: 14px; }
.card-method {
  background: #e8f0fe; color: #1a73e8;
  padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;
}
.card-cost { font-size: 14px; color: #555; }
.card-meta { font-size: 12px; color: #888; }

/* ====== 操作栏 ====== */
.action-bar { margin: 20px 0; padding: 16px; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; }
.mode-toggle { display: flex; gap: 8px; margin-bottom: 12px; }
.btn-mode {
  flex: 1; padding: 8px; border: 1px solid #d0d0d0; border-radius: 6px;
  background: #f5f5f5; color: #555; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.btn-mode.active { background: #1a73e8; color: #fff; border-color: #1a73e8; }
.deep-form { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.deep-form label { font-size: 13px; color: #555; }
.deep-form input { width: 72px; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; text-align: center; }
.deep-form .hint { font-size: 12px; color: #999; }
.mode-hint { font-size: 13px; color: #888; text-align: center; padding: 4px 0; }
.algo-time { font-size: 12px; color: #999; text-align: center; padding: 2px 0; }

/* ====== 深度结果区 ====== */
.deep-section { margin-top: 20px; }
.deep-section h3 { font-size: 15px; margin-bottom: 10px; color: #1a73e8; }

.btn { padding: 6px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.15s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #1a73e8; color: #fff; }
</style>
