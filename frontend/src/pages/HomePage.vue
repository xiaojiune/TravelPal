<template>
  <div class="page-home">
    <h1>TravelPal</h1>
    <p class="subtitle">输入城市与景点，获取最优行程方案</p>

    <n-steps class="page-steps" size="small">
      <n-step v-for="(t, i) in steps" :key="t" :title="t" :status="stepStatus[i]" />
    </n-steps>

    <section
      v-for="card in folderCards"
      :key="card.key"
      class="form-section"
      :class="{ 'section-active': activeSection === card.key, 'section-done': card.done }"
    >
      <div class="section-head" @click="toggleSection(card.key)">
        <h3>{{ card.icon }} {{ card.title }}</h3>
        <span v-if="card.done" class="state-badge badge-done">✓</span>
        <span v-else-if="activeSection === card.key" class="state-badge badge-edit">●</span>
        <span v-else class="state-badge badge-wait">⚪</span>
      </div>

      <Transition name="folder">
        <div v-if="activeSection === card.key" class="section-body">
        <template v-if="card.key === 'city'">
          <div class="form-row">
            <n-input v-model:value="store.city" placeholder="如：北京" @keyup.enter="confirmCity" />
          </div>
          <div class="body-actions">
            <n-button size="small" type="primary" @click="confirmCity">✓ 确定城市</n-button>
          </div>
        </template>

        <template v-else-if="card.key === 'hotel'">
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
          <div class="body-actions">
            <n-button size="small" type="primary" :disabled="!hotelConfirmed" @click="confirmHotel">
              ✓ 确认酒店
            </n-button>
          </div>
        </template>

        <template v-else-if="card.key === 'spots'">
          <div class="form-row">
            <n-input
              v-model:value="spotText"
              type="textarea"
              :rows="4"
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
          <div v-if="store.spots.length" class="spot-grid">
            <div v-for="s in store.spots" :key="s.name" class="spot-tile">
              <span class="spot-emoji">{{ spotEmoji(s.name) }}</span>
              <span class="spot-name">{{ s.name }}</span>
            </div>
          </div>
          <div v-else class="empty-hint">尚未添加景点</div>
        </template>

        <template v-else-if="card.key === 'manage'">
          <div v-if="showManagement" class="manage-box">
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
          </div>
          <div v-else class="empty-hint">暂无规划点，先在上方添加景点</div>
        </template>
        </div>
      </Transition>

      <div v-if="activeSection !== card.key" class="section-summary">
        <span class="summary-text">{{ card.summary }}</span>
        <n-button size="small" quaternary @click="toggleSection(card.key)">
          ✏️ {{ card.done ? '编辑' : '补充' }}
        </n-button>
      </div>
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
import { onMounted } from 'vue'
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

// ====== 大文件夹（手风琴） ======
/** 当前展开的卡片（手风琴：一次仅一张），null 表示全部收起。 */
const activeSection = ref<'city' | 'hotel' | 'spots' | 'manage' | null>(null)

/** 四张卡片的元数据：图标/标题/完成判定/收起态摘要。 */
const folderCards = computed(() => {
  const cityDone = store.city.trim().length > 0
  const hotelDone = hotelConfirmed.value
  const spotsDone = store.spots.length > 0
  const manageDone = showManagement.value
  return [
    {
      key: 'city' as const,
      icon: '📍',
      title: '城市',
      done: cityDone,
      summary: store.city.trim() || '未设置城市',
    },
    {
      key: 'hotel' as const,
      icon: '🏨',
      title: '酒店',
      done: hotelDone,
      summary: hotelDone ? store.hotelName : '未设置酒店',
    },
    {
      key: 'spots' as const,
      icon: '🏞️',
      title: '景点',
      done: spotsDone,
      summary: spotsDone ? `已添加 ${store.spots.length} 个景点` : '尚未添加景点',
    },
    {
      key: 'manage' as const,
      icon: '🗂️',
      title: '规划点管理',
      done: manageDone,
      summary: manageDone ? `已确认 ${store.spots.length} 个规划点` : '暂无规划点',
    },
  ]
})

/** 点击卡片头：同卡收起、异卡切换（手风琴）。 */
function toggleSection(key: 'city' | 'hotel' | 'spots' | 'manage') {
  activeSection.value = activeSection.value === key ? null : key
}

/** 找到下一个未完成的卡片 key（用于确认后自动推进），无则 null。 */
function nextUndone(): 'city' | 'hotel' | 'spots' | 'manage' | null {
  for (const card of folderCards.value) {
    if (!card.done) return card.key
  }
  return null
}

/** 城市确认：非空后收起本卡并推进到下一未完成。 */
function confirmCity() {
  if (!store.city.trim()) {
    message.warning('请先输入城市')
    return
  }
  activeSection.value = nextUndone()
}

/** 酒店确认：已确认坐标后收起并推进。 */
function confirmHotel() {
  if (!hotelConfirmed.value) {
    message.warning('请先搜索并确认酒店坐标')
    return
  }
  activeSection.value = nextUndone()
}

/** 景点名称 → emoji（关键词归类，兜底 🏛️）。 */
function spotEmoji(name: string): string {
  if (/山|峰|岭|石林/.test(name)) return '⛰️'
  if (/海|岛|滩|湖|江|河|泉|湾|池|瀑布/.test(name)) return '🌊'
  if (/公园|园|森林/.test(name)) return '🌳'
  if (/寺|庙|祠|塔/.test(name)) return '🏯'
  if (/馆|博物馆|科技馆/.test(name)) return '🏛️'
  if (/街|巷|广场|城/.test(name)) return '🏘️'
  if (/塔|楼|塔楼/.test(name)) return '🗼'
  return '🏛️'
}

// 初始展开第一个未完成的卡片（过渡态引导）
onMounted(() => {
  activeSection.value = nextUndone()
})

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
  font-size: 15px;
}
.section-head {
  border-bottom: 1px solid var(--tp-border-light);
  padding-bottom: 10px;
  margin-bottom: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}
.form-section {
  transition: box-shadow 0.15s, transform 0.15s, border-color 0.2s;
}
.section-active {
  border-color: var(--tp-primary);
}
.section-done {
  border-color: var(--tp-success);
}
.state-badge {
  font-size: 12px;
  line-height: 1;
}
.badge-done {
  color: var(--tp-success);
}
.badge-edit {
  color: var(--tp-primary);
}
.badge-wait {
  color: var(--tp-text-3);
}
.section-body {
  padding-bottom: 2px;
}
.body-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
.section-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 0;
}
.summary-text {
  font-size: 13px;
  color: var(--tp-text-2);
}
.spot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
  margin-top: 8px;
}
.spot-tile {
  background: var(--tp-primary-soft);
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.spot-emoji {
  font-size: 16px;
  flex-shrink: 0;
}
.spot-name {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.empty-hint {
  font-size: 13px;
  color: var(--tp-text-3);
  padding: 8px 0;
}
.folder-enter-active,
.folder-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.folder-enter-from,
.folder-leave-to {
  opacity: 0;
  transform: translateY(-4px);
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
