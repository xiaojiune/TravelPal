<template>
  <div class="page-home">
    <h1>旅行伴侣</h1>
    <p class="subtitle">输入城市与景点，获取最优行程方案</p>

    <section class="form-section">
      <h3>城市</h3>
      <div class="form-row">
        <input v-model="store.city" placeholder="如：北京" />
      </div>
    </section>

    <section class="form-section">
      <h3>酒店</h3>
      <div class="form-row">
        <input v-model="store.hotelName" placeholder="如：北京饭店" />
        <button class="btn btn-outline" :disabled="!canSearchHotel || loading" @click="searchHotel">
          {{ loading ? '搜索中...' : '🏨 搜索酒店坐标' }}
        </button>
      </div>
      <div v-if="hotelMsg" class="result-row hint">{{ hotelMsg }}</div>
    </section>

    <section class="form-section">
      <h3>景点名称</h3>
      <div class="form-row">
        <textarea v-model="spotText" rows="6" placeholder="每行一个景点&#10;故宫&#10;颐和园&#10;天坛" />
        <button class="btn btn-outline btn-self-start" :disabled="!canSearchSpots || loading" @click="searchSpots">
          {{ loading ? '搜索中...' : '🔍 搜索景点坐标' }}
        </button>
      </div>
      <div v-if="spotMsg" class="hint" style="white-space:pre-line">{{ spotMsg }}</div>
    </section>

    <section v-if="showManagement" class="form-section">
      <h3>规划点管理</h3>
      <table class="edit-table">
        <thead>
          <tr>
            <th style="width:40px">删除</th>
            <th>名称</th>
            <th>地址</th>
            <th>营业时间</th>
            <th style="width:72px">停留(分)</th>
            <th style="width:72px">预计到达</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in editRows" :key="i" :class="{ 'row-hotel': row.isHotel }">
            <td style="text-align:center"><input v-model="row.delete" type="checkbox" /></td>
            <td>{{ row.isHotel ? '🏨 ' : '' }}{{ row.name }}</td>
            <td class="addr">{{ row.address }}</td>
            <td class="biz-hours">{{ formatBiz(row.twStart, row.twEnd) }}</td>
            <td><input :value="row.stay || ''" @input="row.stay = Number(($event.target as HTMLInputElement).value) || 0" type="number" min="0" placeholder="请输入" class="num-input" /></td>
            <td><input :value="row.expectedArrival || ''" @input="row.expectedArrival = Number(($event.target as HTMLInputElement).value) || 0" type="number" min="0" max="1440" placeholder="请输入" class="num-input" /></td>
          </tr>
        </tbody>
      </table>
      <div class="table-actions">
        <button class="btn btn-outline btn-sm" @click="applyEdits">✅ 确认规划点参数</button>
        <button class="btn btn-danger btn-sm" @click="deleteSelectedRows">🗑️ 删除选中行</button>
      </div>
      <div v-if="editHint" class="hint">💡 {{ editHint }}</div>
    </section>

    <section class="form-section">
      <h3>算法参数</h3>
      <div class="form-grid-3">
        <div><label>启程时间</label><input :value="store.dayStart || ''" @input="store.dayStart = Number(($event.target as HTMLInputElement).value) || 0" type="number" min="0" max="1440" placeholder="请输入" /><span class="unit-info">0=午夜, 480=08:00</span></div>
        <div><label>最小天数</label><input :value="store.minDays ?? ''" @input="store.minDays = Number(($event.target as HTMLInputElement).value) || null" type="number" min="1" placeholder="自动" /><span class="unit-info">n_spots//8+1={{ minDaysHint }}</span></div>
        <div><label>迟到惩罚</label><input v-model.number="store.penaltyWeight" type="number" step="10" /></div>
        <div><label>等待惩罚</label><input v-model.number="store.earlyWaitWeight" type="number" step="0.1" /></div>
        <div><label>晚归惩罚</label><input v-model.number="store.lateReturnWeight" type="number" step="10" /></div>
      </div>
      <div v-if="dayStartMsg" class="hint error">{{ dayStartMsg }}</div>
    </section>

    <div class="form-actions">
      <button class="btn btn-primary btn-lg" :disabled="!canSuggest" @click="fetchSuggest">
        {{ store.loading ? '计算中...' : '🚀 获取方案建议' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 首页：城市/酒店/景点输入 → POI 搜索确认 → 管理表格编辑 → 获取方案建议。
 * 通过 usePoiSearch + useEditTable 两个 composable 拆分交互逻辑。
 */
defineOptions({ name: 'HomePage' })
// ====== 状态定义 ======
// 时间相关字段单位：分钟，取值 0-1440，对应 00:00-24:00
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import { postSuggest } from '@/services/api'
import { usePoiSearch } from '@/composables/usePoiSearch'
import { useEditTable } from '@/composables/useEditTable'

const store = usePlanStore()
const router = useRouter()

const {
  spotText, hotelMsg, spotMsg, loading,
  canSearchHotel, canSearchSpots,
  searchHotel, searchSpots,
} = usePoiSearch()

// ====== 计算属性 ======
const hotelConfirmed = computed(() => store.hotelName.trim().length > 0 && store.hotelLon !== 0)
const canSuggest = computed(() => store.spots.length > 0 && hotelConfirmed.value)
const minDaysHint = computed(() => Math.max(1, Math.floor(store.spots.length / 8) + 1))
const dayStartMsg = ref('')

// ====== 管理表格 ======
const { editRows, editHint, showManagement, formatBiz, deleteSelectedRows, applyEdits } = useEditTable()

/**
 * 获取方案建议：调 /api/suggest 后跳转 SuggestPage。
 * buildRequest(null) 中 null 表示让引擎端自动检测天数。
 */
async function fetchSuggest() {
  if (!hotelConfirmed.value) {
    alert('请先搜索并确认酒店')
    return
  }
  if (store.spots.length === 0) {
    alert('请先添加景点')
    return
  }
  if (!store.isParamsSaved) {
    alert('请先在「规划点管理」中点击「确认规划点参数」')
    return
  }
  if (!store.dayStart) {
    dayStartMsg.value = '请输入启程时间'
    return
  }
  dayStartMsg.value = ''
  store.suggestions = []
  store.deepResults = []
  store.planResult = null
  store.loading = true
  try {
    const data = await postSuggest(store.buildRequest(null))
    store.suggestions = data.suggestions || []
    if (data.spots) store.suggestSpots = data.spots
    if (data.amap_api_key) store.amapApiKey = data.amap_api_key
    router.push('/suggest')
  } catch (e: unknown) {
    alert('获取建议失败: ' + ((e as any)?.response?.data?.detail || (e as Error)?.message))
  } finally {
    store.loading = false
  }
}
</script>

<style scoped>
.page-home { max-width: 860px; margin: 0 auto; }
.subtitle { color: #666; margin-bottom: 24px; }
.form-section { background: #fff; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; border: 1px solid #e0e0e0; }
.form-section h3 { margin-bottom: 12px; font-size: 15px; }
.form-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.form-row label { min-width: 80px; font-size: 13px; color: #555; }
.form-row input { flex: 1; padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; }
.form-row input:focus { outline: none; border-color: #1a73e8; }
.form-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.form-grid-3 > div { min-width: 0; }
.form-grid-3 .unit-info { display: block; font-size: 10px; color: #999; margin-top: 2px; }
textarea { flex: 1; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; resize: vertical; box-sizing: border-box; min-height: 120px; }
textarea:focus { outline: none; border-color: #1a73e8; }
.btn-self-start { align-self: flex-start; }
.addr { color: #888; font-size: 12px; }
.result-row { font-size: 13px; margin-top: 4px; display: flex; gap: 16px; align-items: center; }
.hint { font-size: 13px; color: #e67e22; margin-bottom: 12px; }
.hint.error { color: #e74c3c; }
.form-actions { display: flex; justify-content: center; gap: 12px; margin-top: 12px; }
.table-actions { display: flex; gap: 8px; margin-top: 10px; justify-content: flex-end; }
.edit-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 6px; }
.edit-table th { text-align: left; padding: 4px 6px; border-bottom: 2px solid #e0e0e0; font-weight: 600; color: #555; font-size: 12px; }
.edit-table td { padding: 3px 4px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
.row-hotel { background: #f8f9ff; }
.num-input { width: 100%; padding: 3px 4px; border: 1px solid #ddd; border-radius: 3px; font-size: 12px; text-align: center; box-sizing: border-box; }
.num-input:focus { outline: none; border-color: #1a73e8; }
.biz-hours { font-size: 11px; color: #666; white-space: nowrap; }
.btn { padding: 8px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: opacity 0.2s; white-space: nowrap; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm { padding: 5px 14px; font-size: 12px; }
.btn-primary { background: #1a73e8; color: #fff; }
.btn-outline { background: #fff; color: #1a73e8; border: 1px solid #1a73e8; }
.btn-danger { background: #e74c3c; color: #fff; border: 1px solid #c0392b; }
.btn-lg { padding: 12px 36px; font-size: 16px; }
</style>
