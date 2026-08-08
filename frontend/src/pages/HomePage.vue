<template>
  <div class="page-home">
    <h1>TravelPal</h1>
    <p class="subtitle">输入城市与景点，获取最优行程方案</p>

    <n-steps class="page-steps" size="small">
      <n-step v-for="(t, i) in steps" :key="t" :title="t" :status="stepStatus[i]" />
    </n-steps>

    <section class="form-section">
      <h3>城市</h3>
      <div class="form-row">
        <n-input v-model:value="store.city" placeholder="如：北京" />
      </div>
    </section>

    <section class="form-section">
      <h3>酒店</h3>
      <div class="form-row">
        <n-input v-model:value="store.hotelName" placeholder="如：北京饭店" />
        <n-button
          secondary
          :disabled="!canSearchHotel || loading"
          :loading="loading"
          @click="searchHotel"
        >
          🏨 搜索酒店坐标
        </n-button>
      </div>
      <div v-if="hotelMsg" class="result-row hint">{{ hotelMsg }}</div>
    </section>

    <section class="form-section">
      <h3>景点名称</h3>
      <div class="form-row">
        <n-input
          v-model:value="spotText"
          type="textarea"
          :rows="6"
          placeholder="每行一个景点&#10;故宫&#10;颐和园&#10;天坛"
        />
        <n-button
          secondary
          class="btn-self-start"
          :disabled="!canSearchSpots || loading"
          :loading="loading"
          @click="searchSpots"
        >
          🔍 搜索景点坐标
        </n-button>
      </div>
      <div v-if="spotMsg" class="hint" style="white-space: pre-line">{{ spotMsg }}</div>
    </section>

    <section v-if="showManagement" class="form-section">
      <h3>规划点管理</h3>
      <table class="edit-table">
        <thead>
          <tr>
            <th style="width: 40px">删除</th>
            <th>名称</th>
            <th>地址</th>
            <th>营业时间</th>
            <th style="width: 90px">停留(分)</th>
            <th style="width: 90px">预计到达</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in editRows" :key="i" :class="{ 'row-hotel': row.isHotel }">
            <td style="text-align: center"><n-checkbox v-model:checked="row.delete" /></td>
            <td>{{ row.isHotel ? '🏨 ' : '' }}{{ row.name }}</td>
            <td class="addr">{{ row.address }}</td>
            <td class="biz-hours">{{ formatBiz(row.twStart, row.twEnd) }}</td>
            <td>
              <n-input-number
                v-model:value="row.stay"
                :min="0"
                size="tiny"
                placeholder="请输入"
                style="width: 100%"
              />
            </td>
            <td>
              <n-input-number
                v-model:value="row.expectedArrival"
                :min="0"
                :max="1440"
                size="tiny"
                placeholder="请输入"
                style="width: 100%"
              />
            </td>
          </tr>
        </tbody>
      </table>
      <div class="table-actions">
        <n-button secondary size="small" @click="applyEdits">✅ 确认规划点参数</n-button>
        <n-button type="error" size="small" @click="deleteSelectedRows">🗑️ 删除选中行</n-button>
      </div>
      <div v-if="editHint" class="hint">💡 {{ editHint }}</div>
    </section>

    <section class="form-section">
      <n-collapse v-model:expanded-names="paramsExpanded">
        <n-collapse-item name="params" title="⚙️ 高级设置（算法参数）">
          <div class="form-grid-3">
            <div>
              <label>启程时间</label
              ><n-input-number
                v-model:value="store.dayStart"
                :min="0"
                :max="1440"
                placeholder="请输入"
                style="width: 100%"
              /><span class="unit-info">0=午夜, 480=08:00</span>
            </div>
            <div>
              <label>最小天数</label
              ><n-input-number
                v-model:value="store.minDays"
                :min="1"
                placeholder="自动"
                style="width: 100%"
              /><span class="unit-info">默认 n_spots//8+1={{ minDaysHint }}</span>
            </div>
            <div>
              <label>迟到惩罚</label
              ><n-input-number v-model:value="store.penaltyWeight" :step="10" style="width: 100%" />
            </div>
            <div>
              <label>等待惩罚</label
              ><n-input-number
                v-model:value="store.earlyWaitWeight"
                :step="0.1"
                style="width: 100%"
              />
            </div>
            <div>
              <label>晚归惩罚</label
              ><n-input-number
                v-model:value="store.lateReturnWeight"
                :step="10"
                style="width: 100%"
              />
            </div>
          </div>
        </n-collapse-item>
      </n-collapse>
    </section>

    <div class="form-actions">
      <n-button
        type="primary"
        size="large"
        :disabled="!canSuggest || store.loading"
        :loading="store.loading"
        @click="fetchSuggest"
      >
        🚀 生成最优行程
      </n-button>
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
import { useMessage, useDialog } from 'naive-ui'
import { usePlanStore } from '@/stores/plan'
import { submitTask } from '@/services/api'
import type { SuggestResult } from '@/services/api'
import { usePoiSearch } from '@/composables/usePoiSearch'
import { useEditTable } from '@/composables/useEditTable'
import { useTaskPolling } from '@/composables/useTaskPolling'
import { useSuggestCache } from '@/composables/useSuggestCache'

const store = usePlanStore()
const cache = useSuggestCache()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const { startPolling } = useTaskPolling()

const {
  spotText,
  hotelMsg,
  spotMsg,
  loading,
  canSearchHotel,
  canSearchSpots,
  searchHotel,
  searchSpots,
} = usePoiSearch()

// ====== 计算属性 ======
const hotelConfirmed = computed(() => store.hotelName.trim().length > 0 && store.hotelLon !== 0)
const canSuggest = computed(() => store.spots.length > 0 && hotelConfirmed.value)
const minDaysHint = computed(() => Math.max(1, Math.floor(store.spots.length / 8) + 1))

/** 分钟 → HH:MM（用于展示启程时间确认提示）。 */
function fmtMinutes(m: number): string {
  const hh = String(Math.floor(m / 60)).padStart(2, '0')
  const mm = String(m % 60).padStart(2, '0')
  return `${hh}:${mm}`
}

// ====== 步骤条 ======
/** 首页四步引导：完成置 finish、当前置 process、未到置 wait（跳过中间态直接到下一步）。 */
const steps = ['选择城市', '设置酒店', '添加景点', '生成方案']
const stepStatus = computed<('finish' | 'process' | 'wait')[]>(() => {
  const s: ('finish' | 'process' | 'wait')[] = ['wait', 'wait', 'wait', 'wait']
  if (!store.city.trim()) {
    s[0] = 'process'
    return s
  }
  s[0] = 'finish'
  if (!hotelConfirmed.value) {
    s[1] = 'process'
    return s
  }
  s[1] = 'finish'
  if (store.spots.length === 0) {
    s[2] = 'process'
    return s
  }
  s[2] = 'finish'
  s[3] = 'process'
  return s
})

/** 高级设置（算法参数）折叠面板，默认收起。 */
const paramsExpanded = ref<string[]>([])

// ====== 管理表格 ======
const { editRows, editHint, showManagement, formatBiz, deleteSelectedRows, applyEdits } =
  useEditTable()

/**
 * 获取方案建议：提交异步 suggest 任务后轮询，完成后跳转 SuggestPage。
 * buildRequest(null) 中 null 表示让引擎端自动检测天数。
 * 将响应中的 cost_matrix/dist_matrix 存入 store，
 * 供深度规划（SuggestPage）复用以跳过驾车 API。
 */
async function fetchSuggest() {
  if (!hotelConfirmed.value) {
    message.warning('请先搜索并确认酒店')
    return
  }
  if (store.spots.length === 0) {
    message.warning('请先添加景点')
    return
  }
  if (!store.isParamsSaved) {
    message.warning('请先在「规划点管理」中点击「确认规划点参数」')
    return
  }
  if (!store.dayStartConfirmed) {
    dialog.warning({
      title: '确认启程时间',
      content: `你未确定启程时间，当前启程时间为 ${fmtMinutes(store.dayStart)}。是否继续？`,
      positiveText: '我已知晓，继续',
      negativeText: '取消',
      onPositiveClick: () => {
        store.dayStartConfirmed = true
        fetchSuggest()
      },
    })
    return
  }
  store.suggestions = []
  store.deepResults = []
  store.planResult = null
  store.loading = true
  try {
    const { task_id } = await submitTask('suggest', store.buildRequest(null))
    const data = (await startPolling(task_id)) as unknown as SuggestResult
    store.suggestions = data.suggestions || []
    if (data.spots) cache.suggestSpots.value = data.spots
    if (data.cost_matrix) cache.suggestCostMatrix.value = data.cost_matrix // 缓存成本矩阵，deep 模式复用跳过驾车 API
    if (data.dist_matrix) cache.suggestDistMatrix.value = data.dist_matrix // 缓存距离矩阵
    if (data.algo_time) cache.suggestAlgoTime.value = data.algo_time // 搜索总耗时
    if (data.polylines) cache.suggestPolylines.value = data.polylines // 真实轨迹
    if (data.amap_api_key) store.amapApiKey = data.amap_api_key
    if (data.amap_security_code) store.amapSecurityCode = data.amap_security_code
    router.push('/suggest')
  } catch (e: unknown) {
    message.error('获取建议失败: ' + (e instanceof Error ? e.message : '未知错误'))
  } finally {
    store.loading = false
  }
}
</script>

<style scoped>
.page-home {
  max-width: 860px;
  margin: 0;
}
.subtitle {
  color: var(--tp-text-2);
  margin-bottom: 24px;
}
.page-steps {
  margin-bottom: 20px;
}
.form-section {
  background: var(--tp-bg-card);
  border: 1px solid var(--tp-card-border);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 16px;
  box-shadow: var(--tp-card-shadow);
  transition: box-shadow 0.15s, transform 0.15s;
}
.form-section:hover {
  box-shadow: var(--tp-card-shadow-hover);
  transform: translateY(-1px);
}
.form-section h3 {
  margin-bottom: 12px;
  font-size: 15px;
}
.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.form-row label {
  min-width: 80px;
  font-size: 13px;
  color: var(--tp-text-2);
}
.form-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}
.form-grid-3 > div {
  min-width: 0;
}
.form-grid-3 label {
  display: block;
  font-size: 13px;
  color: var(--tp-text-2);
  margin-bottom: 4px;
}
.form-grid-3 .unit-info {
  display: block;
  font-size: 10px;
  color: var(--tp-text-3);
  margin-top: 2px;
}
.btn-self-start {
  align-self: flex-start;
}
.addr {
  color: var(--tp-text-3);
  font-size: 12px;
}
.result-row {
  font-size: 13px;
  margin-top: 4px;
  display: flex;
  gap: 16px;
  align-items: center;
}
.hint {
  font-size: 13px;
  color: var(--tp-warning);
  margin-bottom: 12px;
}
.hint.error {
  color: var(--tp-error);
}
.form-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 12px;
}
.table-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  justify-content: flex-end;
}
.edit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  margin-bottom: 6px;
}
.edit-table th {
  text-align: left;
  padding: 4px 6px;
  border-bottom: 2px solid var(--tp-border);
  font-weight: 600;
  color: var(--tp-text-2);
  font-size: 12px;
}
.edit-table td {
  padding: 3px 4px;
  border-bottom: 1px solid var(--tp-border-light);
  vertical-align: middle;
}
.row-hotel {
  background: var(--tp-primary-soft);
}
.biz-hours {
  font-size: 11px;
  color: var(--tp-text-2);
  white-space: nowrap;
}
</style>
