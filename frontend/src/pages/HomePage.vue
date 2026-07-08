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
      <div v-if="hotelResult" class="result-row">
        <span class="coord">{{ hotelResult.lon.toFixed(4) }}, {{ hotelResult.lat.toFixed(4) }}</span>
        <span class="addr">{{ hotelResult.address }}</span>
      </div>
      <div v-else-if="hotelFailed" class="hint error">⚠️ 未找到该酒店</div>
    </section>

    <section class="form-section">
      <h3>景点名称</h3>
      <div class="form-row">
        <textarea v-model="spotText" rows="6" placeholder="每行一个景点&#10;故宫&#10;颐和园&#10;天坛" />
        <button class="btn btn-outline btn-self-start" :disabled="!canSearchSpots || loading" @click="searchSpots">
          {{ loading ? '搜索中...' : '🔍 搜索景点坐标' }}
        </button>
      </div>
    </section>

    <section v-if="hasResults" class="form-section">
      <h3>搜索结果（勾选要添加的点）</h3>
      <table class="poi-table">
        <thead>
          <tr>
            <th style="width:40px">✓</th>
            <th>类型</th>
            <th>名称</th>
            <th>经度</th>
            <th>纬度</th>
            <th>地址</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, i) in allResults" :key="i">
            <td style="text-align:center"><input v-model="item.checked" type="checkbox" /></td>
            <td>{{ item.isHotel ? '🏨酒店' : '📍景点' }}</td>
            <td>{{ item.name }}</td>
            <td>{{ item.lon?.toFixed(4) }}</td>
            <td>{{ item.lat?.toFixed(4) }}</td>
            <td class="addr">{{ item.address }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="spotFailed.length" class="hint">⚠️ 未找到：{{ spotFailed.join('、') }}</div>
      <div class="form-actions">
        <button class="btn btn-primary" @click="confirmPoi">✅ 确认添加选中的点</button>
      </div>
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
            <th style="width:72px">开始</th>
            <th style="width:72px">关闭</th>
            <th style="width:72px">停留</th>
            <th style="width:72px">预计到达</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in editRows" :key="i" :class="{ 'row-hotel': row.isHotel }">
            <td style="text-align:center"><input v-model="row.delete" type="checkbox" /></td>
            <td>{{ row.isHotel ? '🏨 ' : '' }}{{ row.name }}</td>
            <td class="addr">{{ row.address }}</td>
            <td class="biz-hours">{{ formatBiz(row.twStart, row.twEnd) }}</td>
            <td><input v-model.number="row.twStart" type="number" min="0" max="1440" class="num-input" /></td>
            <td><input v-model.number="row.twEnd" type="number" min="0" max="1440" class="num-input" /></td>
            <td><input v-model.number="row.stay" type="number" min="0" class="num-input" /></td>
            <td><input v-model.number="row.expectedArrival" type="number" min="0" max="1440" class="num-input" /></td>
          </tr>
        </tbody>
      </table>
      <div class="table-actions">
        <button class="btn btn-outline btn-sm" @click="applyEdits">✅ 确认规划点参数</button>
        <button class="btn btn-danger btn-sm" @click="deleteSelectedRows">🗑️ 删除选中行</button>
      </div>
      <div v-if="editHint" class="hint">💡 {{ editHint }}</div>
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
      <button class="btn btn-primary btn-lg" :disabled="!canSuggest" @click="fetchSuggest">
        {{ store.loading ? '计算中...' : '🚀 获取方案建议' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
// ====== 状态定义 ======
// 时间相关字段单位：分钟，取值 0-1440，对应 00:00-24:00
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import { postSuggest } from '@/services/api'
import { usePoiSearch } from '@/composables/usePoiSearch'
import type { SpotFormItem } from '@/types'

const store = usePlanStore()
const router = useRouter()

const {
  spotText, hotelResult, hotelFailed, spotResults, spotFailed, loading,
  canSearchHotel, canSearchSpots, hasResults, allResults,
  searchHotel, searchSpots, confirmPoi, clearSearchResults,
} = usePoiSearch()

// ====== 管理表格状态 ======
interface EditRow {
  isHotel: boolean; name: string; address: string
  lon: number; lat: number
  twStart: number; twEnd: number; stay: number; expectedArrival: number; delete: boolean
}

const editRows = ref<EditRow[]>([])
const editHint = ref('')

// ====== 计算属性 ======
// 管理表格显隐逻辑：搜索结果展示时隐藏，已有已确认点位时展示。避免表格和搜索结果同时出现。
const showManagement = computed(() => {
  if (hasResults.value) return false
  if (store.spots.length > 0) return true
  if (store.hotelName && store.hotelLon) return true
  return false
})
const canSuggest = computed(() => store.spots.length > 0)

// ====== 编辑表格构建 ======
// 构建编辑态行数据：与 store 源数据解耦，用户点击确认后再统一回写，避免中途修改污染全局状态
function rebuildEditRows() {
  const rows = []
  if (store.hotelName && store.hotelLon) {
    rows.push({
      isHotel: true, name: store.hotelName, address: store.hotelAddress,
      lon: store.hotelLon, lat: store.hotelLat,
      twStart: store.hotelTwStart, twEnd: store.hotelTwEnd,
      stay: 0, expectedArrival: store.hotelTwStart, delete: false,
    })
  }
  store.spots.forEach(s => {
    rows.push({
      isHotel: false, name: s.name, address: s.address,
      lon: s.lon, lat: s.lat,
      twStart: s.twStart, twEnd: s.twEnd,
      stay: s.stay, expectedArrival: s.expectedArrival ?? s.twStart, delete: false,
    })
  })
  editRows.value = rows
}

watch([() => store.spots, () => store.hotelName, () => store.hotelLon], rebuildEditRows, { deep: true })

function formatBiz(start: number, end: number) {
  const s = `${Math.floor(start / 60)}:${String(start % 60).padStart(2, '0')}`
  const e = `${Math.floor(end / 60)}:${String(end % 60).padStart(2, '0')}`
  return `${s}-${e}`
}

// ====== 编辑表格操作 ======
function deleteSelectedRows() {
  const remaining = editRows.value.filter(r => !r.delete)
  if (remaining.length === editRows.value.length) {
    editHint.value = '没有选中要删除的行'
    return
  }
  const hotelRow = remaining.find(r => r.isHotel)
  if (!hotelRow) {
    store.hotelName = ''
    store.hotelLon = 0
    store.hotelLat = 0
    store.hotelAddress = ''
  }
  store.spots = remaining.filter(r => !r.isHotel).map(r => ({
    name: r.name, lon: r.lon, lat: r.lat,
    twStart: r.twStart, twEnd: r.twEnd, stay: r.stay,
    address: r.address,
  }))
  editHint.value = ''
  rebuildEditRows()
}

function applyEdits() {
  const hotelRow = editRows.value.find(r => r.isHotel)
  if (hotelRow) {
    store.hotelTwStart = hotelRow.twStart
    store.hotelTwEnd = hotelRow.twEnd
  }
  store.spots = editRows.value.filter(r => !r.isHotel).map(r => ({
    name: r.name, lon: r.lon, lat: r.lat,
    twStart: r.twStart, twEnd: r.twEnd, stay: r.stay,
    address: r.address,
  }))
  editHint.value = '参数已保存'
  setTimeout(() => { editHint.value = '' }, 2000)
  rebuildEditRows()
}

// 获取方案建议：buildRequest(null) 中 null 表示自动检测天数（由引擎端 ca_suggest 自动推断）
async function fetchSuggest() {
  store.loading = true
  try {
    const data = await postSuggest(store.buildRequest(null))
    store.suggestions = data.suggestions || []
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
.cols-3 > div { flex: 1; }
textarea { flex: 1; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; resize: vertical; box-sizing: border-box; min-height: 120px; }
textarea:focus { outline: none; border-color: #1a73e8; }
.btn-self-start { align-self: flex-start; }
.poi-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 12px; }
.poi-table th { text-align: left; padding: 6px 8px; border-bottom: 2px solid #e0e0e0; font-weight: 600; color: #555; }
.poi-table td { padding: 6px 8px; border-bottom: 1px solid #f0f0f0; }
.addr { color: #888; font-size: 12px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.coord { font-family: monospace; color: #333; }
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
