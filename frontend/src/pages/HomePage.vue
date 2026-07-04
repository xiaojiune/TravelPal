<template>
  <div class="page-home">
    <h1>旅行伴侣</h1>
    <p class="subtitle">输入城市与景点，获取最优行程方案</p>

    <section class="form-section">
      <h3>城市与酒店</h3>
      <div class="form-row">
        <label>城市</label>
        <input v-model="store.city" placeholder="如：北京" />
      </div>
      <div class="form-row">
        <label>酒店名称</label>
        <input v-model="store.hotelName" placeholder="如：北京饭店" />
      </div>
      <div class="form-row cols-3">
        <div><label>经度</label><input v-model.number="store.hotelLon" type="number" step="0.0001" /></div>
        <div><label>纬度</label><input v-model.number="store.hotelLat" type="number" step="0.0001" /></div>
        <div><label>出发/返回时间窗</label><span class="hint">{{ store.hotelTwStart }}–{{ store.hotelTwEnd }}</span></div>
      </div>
      <div class="form-row cols-2">
        <div><label>最早出发 (分钟)</label><input v-model.number="store.hotelTwStart" type="number" min="0" max="1440" /></div>
        <div><label>最晚返回 (分钟)</label><input v-model.number="store.hotelTwEnd" type="number" min="0" max="1440" /></div>
      </div>
    </section>

    <section class="form-section">
      <h3>景点列表</h3>
      <table class="spot-table" v-if="store.spots.length">
        <thead>
          <tr>
            <th>名称</th>
            <th>经度</th>
            <th>纬度</th>
            <th>开始</th>
            <th>关闭</th>
            <th>停留</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(spot, i) in store.spots" :key="i">
            <td><input v-model="spot.name" /></td>
            <td><input v-model.number="spot.lon" type="number" step="0.0001" /></td>
            <td><input v-model.number="spot.lat" type="number" step="0.0001" /></td>
            <td><input v-model.number="spot.twStart" type="number" min="0" max="1440" /></td>
            <td><input v-model.number="spot.twEnd" type="number" min="0" max="1440" /></td>
            <td><input v-model.number="spot.stay" type="number" min="0" /> 分</td>
            <td><button class="btn-sm btn-danger" @click="removeSpot(i)">✕</button></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-hint">请添加至少一个景点</p>
      <button class="btn btn-secondary" @click="addSpot">+ 添加景点</button>
    </section>

    <details class="form-section">
      <summary><h3 style="display:inline">算法参数</h3></summary>
      <div class="form-row cols-3">
        <div><label>迟到惩罚</label><input v-model.number="store.penaltyWeight" type="number" step="10" /></div>
        <div><label>等待惩罚</label><input v-model.number="store.earlyWaitWeight" type="number" step="0.1" /></div>
        <div><label>晚归惩罚</label><input v-model.number="store.lateReturnWeight" type="number" step="10" /></div>
      </div>
    </details>

    <div class="form-actions">
      <button class="btn btn-primary" @click="fetchSuggest" :disabled="store.loading || !valid">
        {{ store.loading ? '计算中...' : '获取方案建议' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePlanStore } from '../stores/plan'
import { postSuggest } from '../services/api'

const store = usePlanStore()
const router = useRouter()

const valid = computed(() => store.city && store.hotelName && store.spots.length > 0)

function addSpot() {
  store.spots.push({ name: '', lon: 0, lat: 0, twStart: 480, twEnd: 1020, stay: 60 })
}

function removeSpot(i) {
  store.spots.splice(i, 1)
}

async function fetchSuggest() {
  store.loading = true
  try {
    const data = await postSuggest(store.buildRequest(null))
    store.suggestions = data.suggestions || []
    router.push('/suggest')
  } catch (e) {
    alert('获取建议失败: ' + e.message)
  } finally {
    store.loading = false
  }
}
</script>

<style scoped>
.page-home { max-width: 800px; margin: 0 auto; }
.subtitle { color: #666; margin-bottom: 24px; }
.form-section { background: #fff; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; border: 1px solid #e0e0e0; }
.form-section h3 { margin-bottom: 12px; font-size: 15px; }
.form-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.form-row label { min-width: 80px; font-size: 13px; color: #555; }
.form-row input { flex: 1; padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; }
.form-row input:focus { outline: none; border-color: #1a73e8; }
.cols-3 > div { flex: 1; }
.cols-2 > div { flex: 1; }
.hint { color: #888; font-size: 13px; padding: 6px 0; }
.spot-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 12px; }
.spot-table th { text-align: left; padding: 6px 4px; border-bottom: 2px solid #e0e0e0; font-weight: 600; color: #555; }
.spot-table td { padding: 4px; }
.spot-table input { width: 100%; padding: 4px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 12px; }
.empty-hint { color: #999; font-size: 13px; margin-bottom: 12px; }
.form-actions { text-align: center; margin-top: 20px; }
.btn { padding: 10px 28px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; transition: opacity 0.2s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #1a73e8; color: #fff; }
.btn-secondary { background: #f0f0f0; color: #333; font-size: 13px; padding: 6px 14px; }
.btn-sm { border: none; cursor: pointer; font-size: 12px; padding: 2px 6px; border-radius: 3px; }
.btn-danger { background: #e74c3c; color: #fff; }
</style>
