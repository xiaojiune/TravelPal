/** 核心全局状态：管理输入参数、方案建议、规划结果、Agent 对话。Pinia setup 语法。 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useSuggestCache } from '@/composables/useSuggestCache'
import type {
  SpotFormItem,
  PlanRequestPayload,
  SuggestionItem,
  PlanResult,
  PoiItem,
  ChatMessage as ChatMessageType,
} from '@/types'

/** 单次工具查询结果（供左侧查询面板分节展示）。 */
export interface QueryResult {
  tool: string
  result: unknown
  city?: string
}

/** 判定工具是否为 POI 查询（其结果数组可加入待选栏）。 */
export function isPoiQuery(tool: string): boolean {
  return tool === 'poi_lookup'
}

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
  }

  // ====== Agent 待选栏状态（全局共享，面板与左侧静态栏共用） ======
  /** 工具查询结果暂存列表（含工具名/结果/城市，供左侧查询面板分节展示）。 */
  const queryResults = ref<QueryResult[]>([])

  /** 对话中暂存的 POI 待选列表（由 poi 型查询结果派生，供加入首页表单）。 */
  const pendingPois = computed(() =>
    queryResults.value.filter((q) => isPoiQuery(q.tool)).flatMap((q) => q.result as PoiItem[]),
  )

  /** 接收 Agent 工具查询结果：入队 queryResults；并尝试自动填充城市（仅一次）。 */
  function addQueryResult(tool: string, result: unknown, cityFromTool?: string) {
    queryResults.value.push({ tool, result, city: cityFromTool })
    // 城市基于工具参数自动填充一次（store.city 空才填）
    if (cityFromTool && !city.value) {
      city.value = cityFromTool
    }
  }

  /** 从待选栏移除指定 POI（从 queryResults 中剔除对应条目）。 */
  function removePendingPoi(poi: PoiItem) {
    const idx = queryResults.value.findIndex((q) => {
      const arr = q.result as PoiItem[]
      return Array.isArray(arr) && arr.some((p) => p.name === poi.name)
    })
    if (idx !== -1) queryResults.value.splice(idx, 1)
  }

  // ====== Agent 对话状态（上提 store，面板 v-if 卸载后会话仍保留） ======
  /** 对话消息列表（user/assistant/tool 富卡片形态）。 */
  const chatMessages = ref<ChatMessageType[]>([])

  /** 是否处于 SSE 流式响应中（驱动输入禁用/发送按钮 loading）。 */
  const chatLoading = ref(false)

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
    removePendingPoi(poi)
  }

  /** 一键将全部待选 POI 加入首页表单（addPoiToForm 会逐个 splice，需遍历副本）。 */
  function addAllPendingPois() {
    const all = pendingPois.value.slice()
    for (const poi of all) addPoiToForm(poi)
  }

  // ====== 历史记录与 Agent 状态 ======
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
    spots.value = []
    minDays.value = null
    historyRecordId.value = null
    historyRequestParams.value = null
    suggestions.value = []
    selectedNDays.value = null
    selectedMethod.value = ''
    planResult.value = null
    deepResults.value = []
    amapApiKey.value = ''
    amapSecurityCode.value = ''
    queryResults.value = []
    chatMessages.value = []
    chatLoading.value = false
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
    spots,
    penaltyWeight,
    earlyWaitWeight,
    lateReturnWeight,
    minDays,
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
    queryResults,
    chatMessages,
    chatLoading,
    addQueryResult,
    removePendingPoi,
    addPoiToForm,
    addAllPendingPois,
    buildRequest,
    reset,
    addHotel,
    addSpot,
  }
})
