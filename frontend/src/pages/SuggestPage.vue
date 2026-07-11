<template>
  <div class="page-suggest">
    <h2>方案建议</h2>

    <div v-if="!store.suggestions.length" class="empty-state">
      <p>暂无方案建议，请先在首页输入规划参数。</p>
      <router-link to="/" class="btn btn-primary">返回首页</router-link>
    </div>

    <div v-else>
      <div v-for="group in groupedSuggestions" :key="group.n_days" class="day-group">
        <h3>{{ group.n_days }} 日游</h3>
        <div class="card-list">
          <div
            v-for="(s, i) in group.items"
            :key="i"
            class="suggest-card"
          >
            <div class="card-body">
              <span class="card-method">{{ s.method }}</span>
              <span class="card-cost">成本 {{ s.cost.toFixed(1) }}</span>
            </div>
            <div class="card-actions">
              <button
                class="btn btn-sm btn-outline"
                :class="{ active: selectedNDays === s.n_days && selectedMethod === s.method && mode === 'fast' }"
                :disabled="store.loading"
                @click="generateFast(s)"
              >快速</button>
              <button
                class="btn btn-sm btn-primary"
                :class="{ active: selectedNDays === s.n_days && selectedMethod === s.method && mode === 'deep' }"
                :disabled="store.loading"
                @click="generateDeep(s)"
              >深度</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 方案建议页：树形分组展示，快速/深度双模式入口。 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import { postPlan } from '@/services/api'
import type { SuggestionItem, PlanResult, SpotDictItem } from '@/types'

const store = usePlanStore()
const router = useRouter()

const mode = ref<'fast' | 'deep'>('fast')
const selectedNDays = ref<number | null>(null)
const selectedMethod = ref('')

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

function buildPlanResultFromSuggestion(s: SuggestionItem): PlanResult {
  const spots: Record<string, SpotDictItem> = {
    '0': {
      name: store.hotelName,
      x: store.hotelLon, y: store.hotelLat,
      tw: [store.hotelTwStart, store.hotelTwEnd],
      stay: 0,
    },
  }
  store.spots.forEach((sp, i) => {
    spots[String(i + 1)] = {
      name: sp.name,
      x: sp.lon, y: sp.lat,
      tw: [sp.twStart, sp.twEnd],
      stay: sp.stay,
    }
  })
  return {
    type: 'suggest',
    solution: {
      routes: s.routes,
      total_cost: s.cost,
      total_dist: 0, wait: 0, late: 0, valid: true,
    },
    best_days: s.n_days,
    best_m: s.method,
    spots,
    amap_api_key: store.amapApiKey,
  }
}

async function generateFast(s: SuggestionItem) {
  mode.value = 'fast'
  selectedNDays.value = s.n_days
  selectedMethod.value = s.method
  store.selectedNDays = s.n_days
  store.selectedMethod = s.method
  store.planResult = buildPlanResultFromSuggestion(s)
  router.push('/plan')
}

async function generateDeep(s: SuggestionItem) {
  mode.value = 'deep'
  selectedNDays.value = s.n_days
  selectedMethod.value = s.method
  store.loading = true
  store.planResult = null
  store.selectedNDays = s.n_days
  store.selectedMethod = s.method
  try {
    const data = await postPlan(store.buildRequest(s.n_days))
    store.planResult = data
    router.push('/plan')
  } catch (e: unknown) {
    alert('规划失败: ' + ((e as any)?.response?.data?.detail || (e as Error)?.message))
  } finally {
    store.loading = false
  }
}
</script>

<style scoped>
.page-suggest { max-width: 700px; margin: 0 auto; }
.empty-state { text-align: center; padding: 60px 0; color: #999; }
.empty-state .btn { display: inline-block; margin-top: 16px; text-decoration: none; }
.day-group { margin-bottom: 24px; }
.day-group h3 { font-size: 16px; margin-bottom: 10px; color: #333; border-left: 3px solid #1a73e8; padding-left: 10px; }
.card-list { display: flex; flex-direction: column; gap: 8px; }
.suggest-card {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 10px 16px; transition: box-shadow 0.15s;
}
.suggest-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.card-body { display: flex; align-items: center; gap: 14px; }
.card-method {
  background: #e8f0fe; color: #1a73e8;
  padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;
}
.card-cost { font-size: 14px; color: #555; }
.card-actions { display: flex; gap: 6px; }
.btn { padding: 6px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.15s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm { padding: 4px 12px; font-size: 11px; }
.btn-primary { background: #1a73e8; color: #fff; }
.btn-outline { background: #fff; color: #1a73e8; border: 1px solid #1a73e8; }
.btn-outline.active { background: #e8f0fe; }
.btn-primary.active { background: #1557b0; }
</style>
