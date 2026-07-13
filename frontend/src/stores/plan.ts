/** 核心全局状态：管理输入参数、方案建议、规划结果。Pinia setup 语法。 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SpotFormItem, PlanRequestPayload, SuggestionItem, PlanResult, SpotDictItem } from '@/types'

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

  // ====== 参数确认锁 ======
  /** 用户是否已确认当前规划点参数。false 时阻止获取方案建议。 */
  const isParamsSaved = ref(false)

  // ====== 方案状态 ======
  const suggestions = ref<SuggestionItem[]>([])
  /** suggest 响应带回来的 spots 字典（含 original_tw），fast 模式构建 PlanResult 时使用。 */
  const suggestSpots = ref<Record<string, SpotDictItem>>({})
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
  /** suggest 响应中的成本矩阵，deep 模式复用。 */
  const suggestCostMatrix = ref<number[][]>([])
  /** suggest 响应中的距离矩阵。 */
  const suggestDistMatrix = ref<number[][]>([])
  /** suggest 响应中的真实路径坐标字典。 */
  const suggestPolylines = ref<Record<string, string>>({})
  /** suggest 搜索总耗时（秒）。 */
  const suggestAlgoTime = ref(0)

  // ====== 方法 ======

  /** 构建 POST /api/plan 或 /api/suggest 请求体。nDays=null 时引擎端自动推断。 */
  function buildRequest(nDays: number | null, extra?: { cost_matrix?: number[][]; dist_matrix?: number[][] }): PlanRequestPayload {
    return {
      city: city.value,
      hotel_name: hotelName.value,
      hotel_lon: hotelLon.value,
      hotel_lat: hotelLat.value,
      hotel_tw_start: hotelTwStart.value,
      hotel_tw_end: hotelTwEnd.value,
      day_start: dayStart.value,
      min_days: minDays.value ?? null,
      spots: spots.value.map(s => ({
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
      ...(extra?.cost_matrix ? { cost_matrix: extra.cost_matrix, dist_matrix: extra.dist_matrix } : {}),
    }
  }

  /** 重置全部状态至初始值。用于开始新规划或清空当前会话。 */
  function reset() {
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
    isParamsSaved.value = false
    suggestions.value = []
    suggestSpots.value = {}
    selectedNDays.value = null
    selectedMethod.value = ''
    planResult.value = null
    deepResults.value = []
    suggestCostMatrix.value = []
    suggestDistMatrix.value = []
    suggestPolylines.value = {}
    suggestAlgoTime.value = 0
    amapApiKey.value = ''
    amapSecurityCode.value = ''
  }

  return {
    city, hotelName, hotelLon, hotelLat, hotelAddress,
    hotelTwStart, hotelTwEnd, dayStart,
    spots, penaltyWeight, earlyWaitWeight, lateReturnWeight,
    minDays,
    isParamsSaved,
    suggestions, suggestSpots, selectedNDays, selectedMethod,
    planResult, deepResults, suggestCostMatrix, suggestDistMatrix, suggestPolylines, suggestAlgoTime, amapApiKey, amapSecurityCode, loading,
    buildRequest, reset,
  }
})
