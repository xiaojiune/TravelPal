/** 核心全局状态：管理输入参数、方案建议、规划结果。Pinia setup 语法。 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SpotFormItem, PlanRequestPayload, SuggestionItem, PlanResult } from '@/types'

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

  // ====== 参数确认锁 ======
  /** 用户是否已确认当前规划点参数。false 时阻止获取方案建议。 */
  const isParamsSaved = ref(false)

  // ====== 方案状态 ======
  const suggestions = ref<SuggestionItem[]>([])
  const selectedNDays = ref<number | null>(null)
  const selectedMethod = ref('')

  // ====== 结果状态 ======
  const planResult = ref<PlanResult | null>(null)
  const loading = ref(false)

  // ====== 方法 ======

  /** 构建 POST /api/plan 或 /api/suggest 请求体。nDays=null 时引擎端自动推断。 */
  function buildRequest(nDays: number | null): PlanRequestPayload {
    return {
      city: city.value,
      hotel_name: hotelName.value,
      hotel_lon: hotelLon.value,
      hotel_lat: hotelLat.value,
      hotel_tw_start: hotelTwStart.value,
      hotel_tw_end: hotelTwEnd.value,
      day_start: dayStart.value,
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
    isParamsSaved.value = false
    suggestions.value = []
    selectedNDays.value = null
    selectedMethod.value = ''
    planResult.value = null
  }

  return {
    city, hotelName, hotelLon, hotelLat, hotelAddress,
    hotelTwStart, hotelTwEnd, dayStart,
    spots, penaltyWeight, earlyWaitWeight, lateReturnWeight,
    isParamsSaved, suggestions, selectedNDays, selectedMethod,
    planResult, loading,
    buildRequest, reset,
  }
})
