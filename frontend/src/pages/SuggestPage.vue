<template>
  <div class="page-suggest">
    <h2>方案建议</h2>
    <p class="subtitle" v-if="store.suggestions.length">共 {{ store.suggestions.length }} 个方案，点击选择天数并生成规划</p>

    <div v-if="!store.suggestions.length" class="empty-state">
      <p>暂无方案建议，请先在首页输入规划参数。</p>
      <router-link to="/" class="btn btn-primary">返回首页</router-link>
    </div>

    <div v-else class="suggest-list">
      <div
        v-for="(s, i) in store.suggestions"
        :key="i"
        class="suggest-card"
        :class="{ selected: selectedIndex === i }"
        @click="select(i)"
      >
        <div class="card-method">{{ s.method }}</div>
        <div class="card-body">
          <span class="card-days">{{ s.n_days }} 天</span>
          <span class="card-cost">成本 {{ s.cost.toFixed(1) }}</span>
        </div>
      </div>
    </div>

    <div class="form-actions" v-if="store.suggestions.length">
      <div class="form-row inline">
        <label>天数</label>
        <select v-model.number="customDays">
          <option v-for="d in availableDays" :key="d" :value="d">{{ d }} 天</option>
        </select>
      </div>
      <button class="btn btn-primary" @click="generatePlan" :disabled="store.loading">
        {{ store.loading ? '规划中...' : '生成规划' }}
      </button>
    </div>
  </div>
</template>

<script setup>
// ====== 状态定义 ======
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePlanStore } from '../stores/plan'
import { postPlan } from '../services/api'

const store = usePlanStore()
const router = useRouter()

const selectedIndex = ref(0)
const customDays = ref(store.suggestions[0]?.n_days || 3)

const availableDays = computed(() => {
  const days = new Set(store.suggestions.map(s => s.n_days))
  return [...days].sort((a, b) => a - b)
})

function select(i) {
  selectedIndex.value = i
  customDays.value = store.suggestions[i].n_days
}

async function generatePlan() {
  store.loading = true
  store.selectedNDays = customDays.value
  store.selectedMethod = store.suggestions[selectedIndex.value]?.method || ''
  try {
    const data = await postPlan(store.buildRequest(customDays.value))
    store.planResult = data
    router.push('/plan')
  } catch (e) {
    alert('规划失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    store.loading = false
  }
}
</script>

<style scoped>
.page-suggest { max-width: 600px; margin: 0 auto; }
.subtitle { color: #666; margin-bottom: 20px; }
.empty-state { text-align: center; padding: 60px 0; color: #999; }
.empty-state .btn { display: inline-block; margin-top: 16px; text-decoration: none; }
.suggest-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px; }
.suggest-card {
  display: flex; align-items: center; gap: 16px;
  background: #fff; border: 2px solid #e0e0e0; border-radius: 8px;
  padding: 14px 18px; cursor: pointer; transition: border-color 0.2s;
}
.suggest-card:hover { border-color: #1a73e8; }
.suggest-card.selected { border-color: #1a73e8; background: #f0f7ff; }
.card-method {
  background: #e8f0fe; color: #1a73e8;
  padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600;
  white-space: nowrap;
}
.card-body { display: flex; gap: 20px; font-size: 14px; }
.card-days { font-weight: 600; }
.card-cost { color: #555; }
.form-actions { display: flex; align-items: center; justify-content: center; gap: 16px; }
.form-row.inline { display: flex; align-items: center; gap: 8px; }
.form-row.inline select { padding: 6px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
.btn { padding: 10px 28px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #1a73e8; color: #fff; }
</style>
