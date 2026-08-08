/** 核心全局状态：管理输入参数、方案建议、规划结果。Pinia setup 语法。 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useSuggestCache } from '@/composables/useSuggestCache'
import type {
  SpotFormItem,
  PlanRequestPayload,
  SuggestionItem,
  PlanResult,
  PoiItem,
} from '@/types'

export const usePlanStore = defineStore('plan', () => {
  // ====== 输入状态 ======
  const city = ref('')
  const hotelName = ref('')
  const hotelLon = ref(0)
  const hotelLat = ref(0)
  const hotelAddress = ref('')
  const hotelTwStart = ref(0)
  const hotelTwEnd = ref(1440)
  const dayStart = ref(0)
  /** 用户是否已确认启程时间（默认 0=午夜合法，确认后本会话不再提示，改值需重新确认）。 */
  const dayStartConfirmed = ref(false)
  watch(dayStart, () => {
    dayStartConfirmed.value = false
  })
  const spots = ref<SpotFormItem[]>([])
  const penaltyWeight = ref(100)
  const earlyWaitWeight = ref(0.1)
  const lateReturnWeight = ref(50)
  const minDays = ref<number | null>(null)

  /** 从 Agent 页面添加一个酒店到输入表单。 */
  function addHotel(poi: SpotFormItem) {
    hotelName.value = poi.name
    hotelLon.value = poi.lon
    hotelLat.value = poi.lat
    hotelAddress.value = poi.address ?? ''
    hotelTwStart.value = poi.twStart ?? 0
    hotelTwEnd.value = poi.twEnd ?? 1440
    isParamsSaved.value = false
  }

  /** 从 Agent 页面添加一个景点到输入列表（重复名称去重）。 */
  function addSpot(poi: SpotFormItem) {
    if (spots.value.some((s) => s.name === poi.name)) return
    spots.value.push({
      name: poi.name,
      lon: poi.lon,
      lat: poi.lat,
      twStart: poi.twStart ?? 480,
      twEnd: poi.twEnd ?? 1020,
      stay: poi.stay ?? 0,
      address: poi.address,
    })
    isParamsSaved.value = false
  }

  // ====== Agent 待选栏状态（全局共享，面板与左侧静态栏共用） ======
  /** 对话中查询到的 POI 暂存列表（去重，供加入首页表单）。 */
  const pendingPois = ref<PoiItem[]>([])

  /** 接收 Agent 工具查询结果，去重后加入待选栏。 */
  function addPendingPoi(poi: PoiItem) {
    if (!poi.name) return
    if (!pendingPois.value.some((p) => p.name === poi.name)) {
      pendingPois.value.push(poi)
    }
  }

  /** 从待选栏移除指定下标项（不做其他操作）。 */
  function removePendingPoi(index: number) {
    pendingPois.value.splice(index, 1)
  }

  /** 将待选 POI 添加到首页输入列表，然后从待选栏移除。 */
  function addPoiToForm(poi: PoiItem) {
    if (!poi.name || poi.lon == null || poi.lat == null) return
    const base: SpotFormItem = {
      name: poi.name,
      lon: poi.lon,
      lat: poi.lat,
      twStart: poi.tw_start ?? 480,
      twEnd: poi.tw_end ?? 1020,
      stay: 0,
      address: poi.address,
    }
    if (poi.poi_type === 'hotel') {
      addHotel(base)
    } else {
      addSpot(base)
    }
    const idx = pendingPois.value.findIndex((p) => p.name === poi.name)
    if (idx !== -1) pendingPois.value.splice(idx, 1)
  }

  /** 一键将全部待选 POI 加入首页表单（addPoiToForm 会逐个 splice，需遍历副本）。 */
  function addAllPendingPois() {
    const all = pendingPois.value.slice()
    for (const poi of all) addPoiToForm(poi)
  }

  // ====== 参数确认锁 ======
  /** 用户是否已确认当前规划点参数。false 时阻止获取方案建议。 */
  const isParamsSaved = ref(false)
  /** 从历史记录加载的记录 ID，非空时 PlanPage 应禁用「分享此方案」。 */
  const historyRecordId = ref<string | null>(null)
  /** 从历史记录加载的原始请求参数，用于 PlanPage 展示。 */
  const historyRequestParams = ref<Record<string, unknown> | null>(null)

  // ====== 方案状态 ======
  const suggestions = ref<SuggestionItem[]>([])
  const selectedNDays = ref<number | null>(null)
  const selectedMethod = ref('')

  // ====== 结果状态 ======
  const planResult = ref<PlanResult | null>(null)
  /** 深度模式生成的规划结果卡片列表（首页传来新参数时不清除）。 */
  const deepResults = ref<PlanResult[]>([])
  const amapApiKey = ref('')
  const loading = ref(false)
  /** 高德 JS API 安全密钥 */
  const amapSecurityCode = ref('')

  // ====== 方法 ======

  /** 构建 POST /api/plan 或 /api/suggest 请求体。nDays=null 时引擎端自动推断。 */
  function buildRequest(
    nDays: number | null,
    extra?: { cost_matrix?: number[][]; dist_matrix?: number[][] },
  ): PlanRequestPayload {
    return {
      city: city.value,
      hotel_name: hotelName.value,
      hotel_lon: hotelLon.value,
      hotel_lat: hotelLat.value,
      hotel_tw_start: hotelTwStart.value,
      hotel_tw_end: hotelTwEnd.value,
      day_start: dayStart.value,
      min_days: minDays.value ?? null,
      spots: spots.value.map((s) => ({
        name: s.name,
        lon: Number(s.lon),
        lat: Number(s.lat),
        tw_start: Number(s.twStart),
        tw_end: Number(s.twEnd),
        stay: Number(s.stay),
        expected_arrival: Number(s.expectedArrival ?? s.twStart),
      })),
      n_days: nDays,
      mode: 'fast',
      penalty_weight: penaltyWeight.value,
      early_wait_weight: earlyWaitWeight.value,
      late_return_weight: lateReturnWeight.value,
      ...(extra?.cost_matrix
        ? { cost_matrix: extra.cost_matrix, dist_matrix: extra.dist_matrix }
        : {}),
    }
  }

  /** 重置全部状态至初始值。用于开始新规划或清空当前会话。 */
  function reset() {
    useSuggestCache().clear()
    city.value = ''
    hotelName.value = ''
    hotelLon.value = 0
    hotelLat.value = 0
    hotelAddress.value = ''
    hotelTwStart.value = 0
    hotelTwEnd.value = 1440
    dayStart.value = 0
    dayStartConfirmed.value = false
    spots.value = []
    minDays.value = null
    isParamsSaved.value = false
    historyRecordId.value = null
    historyRequestParams.value = null
    suggestions.value = []
    selectedNDays.value = null
    selectedMethod.value = ''
    planResult.value = null
    deepResults.value = []
    amapApiKey.value = ''
    amapSecurityCode.value = ''
    pendingPois.value = []
    loading.value = false
    penaltyWeight.value = 100
    earlyWaitWeight.value = 0.1
    lateReturnWeight.value = 50
  }

  return {
    city,
    hotelName,
    hotelLon,
    hotelLat,
    hotelAddress,
    hotelTwStart,
    hotelTwEnd,
    dayStart,
    dayStartConfirmed,
    spots,
    penaltyWeight,
    earlyWaitWeight,
    lateReturnWeight,
    minDays,
    isParamsSaved,
    historyRecordId,
    historyRequestParams,
    suggestions,
    selectedNDays,
    selectedMethod,
    planResult,
    deepResults,
    amapApiKey,
    amapSecurityCode,
    loading,
    pendingPois,
    addPendingPoi,
    removePendingPoi,
    addPoiToForm,
    addAllPendingPois,
    buildRequest,
    reset,
    addHotel,
    addSpot,
  }
})
