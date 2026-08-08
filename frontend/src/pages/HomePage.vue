<template>
  <div class="page-home">
    <h1>TravelPal</h1>
    <p class="subtitle">输入城市与景点，获取最优行程方案</p>

    <n-steps class="page-steps" size="small">
      <n-step v-for="(t, i) in steps" :key="t" :title="t" :status="stepStatus[i]" />
    </n-steps>

    <div class="cards-grid">
      <section
        v-for="card in folderCards"
        :key="card.key"
        class="form-section"
        :class="{
          'section-active': activeSection === card.key,
          'section-done': card.done,
          'card-span2': card.key === 'search',
          'card-full': card.key === 'manage',
        }"
      >
      <div class="section-head" @click="toggleSection(card.key)">
        <h3>{{ card.icon }} {{ card.title }}</h3>
        <!-- 徽标三态：warning（黄!）> done（绿✓）> 编辑中● / 等待⚪；预留 🤖（Agent 填充点）；showBadge=false 卡不渲染 -->
        <span v-if="card.showBadge && card.warning" class="state-badge badge-warn">!{{ card.warnCount ?? '' }}</span>
        <span v-else-if="card.showBadge && card.done" class="state-badge badge-done">✓</span>
        <span v-else-if="card.showBadge && activeSection === card.key" class="state-badge badge-edit">●</span>
        <span v-else-if="card.showBadge" class="state-badge badge-wait">⚪</span>
      </div>

      <Transition name="folder">
        <div v-if="activeSection === card.key" class="section-body">
        <template v-if="card.key === 'city'">
          <div class="form-row">
            <n-input v-model:value="store.city" placeholder="如：北京" />
          </div>
        </template>

        <template v-else-if="card.key === 'hotel'">
          <div class="form-row">
            <n-input v-model:value="store.hotelName" placeholder="如：北京饭店" />
          </div>
          <div class="row-actions">
            <n-button
              secondary
              size="small"
              :disabled="!canSearchHotel || loading"
              :loading="loading"
              @click="searchHotel"
            >
              🏨 搜索酒店坐标
            </n-button>
          </div>
          <div v-if="hotelMsg" class="result-row hint">{{ hotelMsg }}</div>
          <div v-if="store.hotelAddress" class="hotel-addr">{{ store.hotelAddress }}</div>
        </template>

        <template v-else-if="card.key === 'depart'">
          <div class="form-row">
            <n-input-number
              v-model:value="store.dayStart"
              :min="0"
              :max="1440"
              :show-button="false"
              :bordered="false"
              style="width: 100%"
            />
          </div>
          <div class="unit-info">0=午夜, 480=08:00，当前 {{ fmtMinutes(store.dayStart) }}</div>
        </template>

        <template v-else-if="card.key === 'search'">
          <div class="form-row">
            <n-input
              v-model:value="spotText"
              type="textarea"
              :rows="4"
              placeholder="每行一个景点&#10;故宫&#10;颐和园&#10;天坛"
            />
          </div>
          <div class="row-actions">
            <n-button
              secondary
              size="small"
              :disabled="!canSearchSpots || loading"
              :loading="loading"
              @click="searchSpots"
            >
              🔍 搜索景点坐标
            </n-button>
          </div>
          <div v-if="spotMsg" class="hint" style="white-space: pre-line">{{ spotMsg }}</div>
          <div class="added-count">
            <template v-if="store.spots.length">
              ✅ 已添加 {{ store.spots.length }} 个景点（前往「规划点管理」调整参数）
            </template>
            <template v-else>尚未添加景点</template>
          </div>
        </template>

        <template v-else-if="card.key === 'minDays'">
          <div class="form-row">
            <n-input-number
              v-model:value="store.minDays"
              :min="1"
              :show-button="false"
              :bordered="false"
              placeholder="自动"
              style="width: 100%"
            />
          </div>
          <div class="unit-info">不填则自动推断，默认 n_spots//8+1={{ minDaysHint }}</div>
        </template>

        <template v-else-if="card.key === 'manage'">
          <div v-if="showManagement" class="manage-box">
            <div class="poi-list">
              <div
                v-for="(row, i) in editRows"
                :key="i"
                class="poi-card"
                :class="{ 'poi-active': activePoiCard === i }"
                @click="togglePoi(i)"
              >
                <div class="poi-head">
                  <span class="poi-name">{{ spotEmoji(row.name) }} {{ row.name }}</span>
                  <div class="poi-head-right">
                    <span
                      v-if="poiIncompleteCount(row) === 0"
                      class="poi-state poi-state-ok"
                      title="停留与预计到达均已填写"
                      >✓</span
                    >
                    <span v-else class="poi-state poi-state-warn" title="停留或预计到达未填写"
                      >!{{ poiIncompleteCount(row) }}</span
                    >
                    <n-button text size="small" class="poi-del" @click.stop="deleteRowAt(i)">✕</n-button>
                  </div>
                </div>
                <Transition name="poi" mode="out-in">
                  <div
                    v-if="activePoiCard === i"
                    :key="'expanded'"
                    class="poi-body"
                    @click="onPoiEditClick(i, $event)"
                  >
                    <div class="poi-info-row">
                      <label>地址</label>
                      <span class="edit-divider" />
                      <span class="poi-info-text" :title="row.address">{{ row.address || '暂无地址' }}</span>
                    </div>
                    <div class="poi-info-row">
                      <label>营业时间</label>
                      <span class="edit-divider" />
                      <span class="poi-info-text">{{ formatBiz(row.twStart, row.twEnd) }}</span>
                    </div>
                    <div class="poi-edit-row">
                      <label>停留</label>
                      <span class="edit-divider" />
                      <n-input-number
                        v-if="isEditing(i, 'stay')"
                        v-model:value="row.stay"
                        :min="0"
                        size="tiny"
                        :show-button="false"
                        :bordered="false"
                        placeholder="请输入"
                        style="width: 90px"
                      />
                      <span v-else class="poi-value poi-field" @click="startEdit(i, 'stay')">
                        {{ row.stay != null ? `${row.stay} 分钟` : '未输入' }}
                      </span>
                    </div>
                    <div class="poi-edit-row">
                      <label>预计到达</label>
                      <span class="edit-divider" />
                      <n-input-number
                        v-if="isEditing(i, 'expectedArrival')"
                        v-model:value="row.expectedArrival"
                        :min="0"
                        :max="1440"
                        size="tiny"
                        :show-button="false"
                        :bordered="false"
                        placeholder="请输入"
                        style="width: 90px"
                      />
                      <span v-else class="poi-value poi-field" @click="startEdit(i, 'expectedArrival')">
                        {{ row.expectedArrival != null ? `${fmtMinutes(row.expectedArrival)}` : '未输入' }}
                      </span>
                    </div>
                    <div class="poi-unit">0=午夜, 480=08:00，当前 {{ row.expectedArrival != null ? fmtMinutes(row.expectedArrival) : fmtMinutes(store.dayStart) }}</div>
                  </div>
                  <div v-else :key="'collapsed'" class="poi-body">
                    <div class="poi-info-row">
                      <label>地址</label>
                      <span class="edit-divider" />
                      <span class="poi-info-text" :title="row.address">{{ row.address || '暂无地址' }}</span>
                    </div>
                    <div class="poi-info-row">
                      <label>营业时间</label>
                      <span class="edit-divider" />
                      <span class="poi-info-text">{{ formatBiz(row.twStart, row.twEnd) }}</span>
                    </div>
                    <div class="poi-edit-row">
                      <label>停留</label>
                      <span class="edit-divider" />
                      <span class="poi-value">{{ row.stay != null ? `${row.stay} 分钟` : '-' }}</span>
                    </div>
                    <div class="poi-edit-row">
                      <label>预计到达</label>
                      <span class="edit-divider" />
                      <span class="poi-value">{{ row.expectedArrival != null ? fmtMinutes(row.expectedArrival) : '-' }}</span>
                    </div>
                  </div>
                </Transition>
              </div>
            </div>
            <div v-if="editHint" class="hint">💡 {{ editHint }}</div>
          </div>
          <div v-else class="empty-hint">暂无规划点，先在上方搜索景点</div>
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

    </div>

    <div class="form-actions">
      <n-button
        :type="allGreen ? 'primary' : 'error'"
        size="large"
        :disabled="!allGreen || store.loading"
        :loading="store.loading"
        @click="fetchSuggest"
      >
        🚀 生成 行程
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
import { useMessage } from 'naive-ui'
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
/** 三绿判定：城市有值 / 酒店名+地址拉取成功 / 已添加景点。 */
const cityGreen = computed(() => store.city.trim().length > 0)
const hotelGreen = computed(() => store.hotelName.trim().length > 0 && store.hotelAddress.trim().length > 0)
const spotsGreen = computed(() => store.spots.length > 0)
const allGreen = computed(() => cityGreen.value && hotelGreen.value && spotsGreen.value)
const minDaysHint = computed(() => Math.max(1, Math.floor(store.spots.length / 8) + 1))

/** 分钟 → HH:MM（用于展示启程时间）。 */
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
  if (!cityGreen.value) {
    s[0] = 'process'
    return s
  }
  s[0] = 'finish'
  if (!hotelGreen.value) {
    s[1] = 'process'
    return s
  }
  s[1] = 'finish'
  if (!spotsGreen.value) {
    s[2] = 'process'
    return s
  }
  s[2] = 'finish'
  s[3] = 'process'
  return s
})

// 初始展开第一个未完成的卡片（过渡态引导）
onMounted(() => {
  activeSection.value = nextUndone()
})

// ====== 大文件夹（手风琴） ======
/** 当前展开的卡片（手风琴：一次仅一张），null 表示全部收起。 */
type CardKey = 'city' | 'hotel' | 'depart' | 'search' | 'minDays' | 'manage'
const activeSection = ref<CardKey | null>(null)

/** 六张卡片的元数据：图标/标题/完成判定/警告态/收起态摘要。
 * 徽标语义：warning（黄!，优先级最高，用于默认值未改或景点未全编辑）> done（绿✓）。
 */
const folderCards = computed(() => {
  const cityDone = cityGreen.value
  const hotelDone = hotelGreen.value
  const departDone = true
  const spotsDone = store.spots.length > 0
  // 规划点全编辑判定：所有景点行的停留与预计到达均有值
  const manageFull = editRows.value.length > 0 && editRows.value.every((r) => r.stay != null && r.expectedArrival != null)
  const manageDone = manageFull
  // 未完全编辑的景点卡数（个体相加：外层徽标只数卡片，内层看细节）
  const incompleteCount = editRows.value.filter((r) => r.stay == null || r.expectedArrival == null).length
  return [
    {
      key: 'city' as const,
      icon: '📍',
      title: '城市',
      done: cityDone,
      warning: false,
      showBadge: true,
      summary: store.city.trim() || '未设置城市',
    },
    {
      key: 'hotel' as const,
      icon: '🏨',
      title: '酒店',
      done: hotelDone,
      warning: false,
      showBadge: true,
      summary: hotelDone ? `${store.hotelName} · ${store.hotelAddress}` : '未设置酒店',
    },
    {
      key: 'depart' as const,
      icon: '⏰',
      title: '启程时间',
      done: departDone,
      warning: store.dayStart === 0, // 默认值未改 → 黄!
      showBadge: true,
      summary: store.dayStart === 0 ? '默认 08:00' : `已设 ${fmtMinutes(store.dayStart)}`,
    },
    {
      key: 'search' as const,
      icon: '🔍',
      title: '搜索',
      done: spotsDone,
      warning: false,
      showBadge: false, // 搜索框不显示状态徽标，已添加状态由下方 added-count 回执说明
      summary: spotsDone ? `已添加 ${store.spots.length} 个景点` : '尚未添加景点',
    },
    {
      key: 'minDays' as const,
      icon: '📅',
      title: '最小天数',
      done: true,
      warning: !store.minDays, // 默认自动 → 黄!
      showBadge: true,
      summary: store.minDays ? `最少 ${store.minDays} 天` : `自动（默认 ${minDaysHint.value} 天）`,
    },
    {
      key: 'manage' as const,
      icon: '🗂️',
      title: '规划点管理',
      done: manageDone,
      warning: store.spots.length > 0 && !manageDone,
      warnCount: incompleteCount,
      showBadge: true,
      summary:
        store.spots.length === 0
          ? '暂无规划点'
          : manageDone
            ? `已确认 ${store.spots.length} 个规划点`
            : `已添加 ${store.spots.length} 个景点，待补充`,
    },
  ]
})

/** 点击卡片头：同卡收起、异卡切换（手风琴）。 */
function toggleSection(key: CardKey) {
  activeSection.value = activeSection.value === key ? null : key
}

/** 找到下一个未完成的卡片 key（用于初始展开引导），无则 null。 */
function nextUndone(): CardKey | null {
  for (const card of folderCards.value) {
    if (!card.done) return card.key
  }
  return null
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
const { editRows, editHint, showManagement, formatBiz, deleteRowAt } = useEditTable()

/** 当前展开的景点卡索引（手风琴：一次仅一张），null 表示全部收起。 */
const activePoiCard = ref<number | null>(null)

/** 展开态中正在编辑的字段（点击状态行才出输入框），null 表示均显示状态文案。 */
const activeEditField = ref<{ row: number; field: 'stay' | 'expectedArrival' } | null>(null)

/** 点击景点卡头：同卡收起、异卡切换（手风琴）。 */
function togglePoi(i: number) {
  activePoiCard.value = activePoiCard.value === i ? null : i
}

/** 单个景点未填字段数（停留/预计到达各算一个，0~2），驱动小卡 ✓ / !N 状态标识。 */
function poiIncompleteCount(row: { stay: number | null; expectedArrival: number | null }): number {
  return (row.stay == null ? 1 : 0) + (row.expectedArrival == null ? 1 : 0)
}

/** 判断某字段当前是否处于编辑态。 */
function isEditing(i: number, field: 'stay' | 'expectedArrival'): boolean {
  const f = activeEditField.value
  return f !== null && f.row === i && f.field === field
}

/** 点击状态行：进入字段编辑态（出输入框）。 */
function startEdit(i: number, field: 'stay' | 'expectedArrival') {
  activeEditField.value = { row: i, field }
}

/** 点击编辑区：仅展开态拦截冒泡（点输入框不折叠），收起态放行以触发整卡展开。 */
function onPoiEditClick(i: number, e: MouseEvent) {
  if (activePoiCard.value === i) e.stopPropagation()
}

/**
 * 获取方案建议：提交异步 suggest 任务后轮询，完成后跳转 SuggestPage。
 * buildRequest(null) 中 null 表示让引擎端自动检测天数。
 * 将响应中的 cost_matrix/dist_matrix 存入 store，
 * 供深度规划（SuggestPage）复用以跳过驾车 API。
 */
async function fetchSuggest() {
  if (!hotelGreen.value) {
    message.warning('请先搜索并确认酒店')
    return
  }
  if (store.spots.length === 0) {
    message.warning('请先添加景点')
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
  transition: box-shadow 0.15s, transform 0.15s, border-color 0.2s;
}
.cards-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  align-items: stretch;
}
.cards-grid .form-section {
  margin-bottom: 0;
  min-width: 0;
}
.cards-grid .card-span2 {
  grid-column: span 2;
}
.cards-grid .card-full {
  grid-column: 1 / -1;
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
.badge-warn {
  color: var(--tp-warning);
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
  overflow: hidden;
}
.summary-text {
  font-size: 13px;
  color: var(--tp-text-2);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.added-count {
  font-size: 13px;
  color: var(--tp-text-2);
  margin-top: 8px;
}
.poi-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.poi-card {
  border: 1px solid var(--tp-border);
  border-radius: 8px;
  padding: 0;
  background: var(--tp-surface);
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.poi-card:hover {
  border-color: var(--tp-info);
}
.poi-card.poi-active {
  border-color: var(--tp-info);
}
.poi-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
  border-bottom: 1px solid var(--tp-border-light);
}
.poi-card.poi-active .poi-name {
  color: var(--tp-info);
}
.poi-name {
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.poi-head-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.poi-state {
  font-size: 12px;
  line-height: 1;
  margin-right: 2px;
}
.poi-state-ok {
  color: var(--tp-success);
}
.poi-state-warn {
  color: var(--tp-warning);
}
.poi-del {
  color: var(--tp-text-3);
}
.poi-del:hover {
  color: var(--tp-error);
}
.poi-body {
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.poi-info-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.poi-info-row label {
  font-size: 12px;
  color: var(--tp-text-2);
  white-space: nowrap;
}
.poi-info-text {
  font-size: 12px;
  color: var(--tp-text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hotel-addr {
  font-size: 12px;
  color: var(--tp-text-2);
  margin-top: 6px;
  white-space: normal;
  overflow-wrap: break-word;
}
.poi-unit {
  font-size: 10px;
  color: var(--tp-text-3);
  margin-top: 2px;
}
.poi-edit-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.poi-edit-row label {
  font-size: 12px;
  color: var(--tp-text-2);
  white-space: nowrap;
}
.edit-divider {
  width: 1px;
  height: 12px;
  background: var(--tp-border);
  flex-shrink: 0;
}
.poi-value {
  font-size: 13px;
  color: var(--tp-text);
  min-width: 40px;
}
.poi-field {
  cursor: pointer;
}
.poi-field:hover {
  color: var(--tp-primary);
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
.poi-enter-active,
.poi-leave-active {
  transition: opacity 0.18s, transform 0.18s;
}
.poi-enter-from,
.poi-leave-to {
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
.unit-info {
  display: block;
  font-size: 10px;
  color: var(--tp-text-3);
  margin-top: 2px;
}
.row-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 6px;
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
/* 生成按钮三绿未就绪：disabled + error 色覆盖，让未通过态真实可见 */
.form-actions .n-button--error.n-button--disabled {
  background-color: var(--tp-error) !important;
  color: #fff !important;
  opacity: 0.55;
}
</style>
