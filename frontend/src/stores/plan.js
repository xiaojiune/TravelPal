import { defineStore } from 'pinia'
import { ref } from 'vue'

// ---------------------------------------------------------------------------
// 页面间共享的规划状态：首页输入 → 方案建议 → 规划结果
//
// buildRequest(nDays)       序列化 PlanRequest（可选天数）
// reset()                   清空所有状态
// ---------------------------------------------------------------------------

export const usePlanStore = defineStore('plan', () => {
  const city = ref('')
  const hotelName = ref('')
  const hotelLon = ref(0)
  const hotelLat = ref(0)
  const hotelTwStart = ref(360)
  const hotelTwEnd = ref(1440)
  const spots = ref([])
  const penaltyWeight = ref(100)
  const earlyWaitWeight = ref(0.1)
  const lateReturnWeight = ref(50)

  const suggestions = ref([])
  const selectedNDays = ref(null)
  const selectedMethod = ref('')

  const planResult = ref(null)
  const loading = ref(false)

  function buildRequest(nDays) {
    return {
      city: city.value,
      hotel_name: hotelName.value,
      hotel_lon: hotelLon.value,
      hotel_lat: hotelLat.value,
      hotel_tw_start: hotelTwStart.value,
      hotel_tw_end: hotelTwEnd.value,
      spots: spots.value.map(s => ({
        name: s.name,
        lon: Number(s.lon),
        lat: Number(s.lat),
        tw_start: Number(s.twStart),
        tw_end: Number(s.twEnd),
        stay: Number(s.stay),
      })),
      n_days: nDays,
      mode: 'fast',
      penalty_weight: penaltyWeight.value,
      early_wait_weight: earlyWaitWeight.value,
      late_return_weight: lateReturnWeight.value,
    }
  }

  function reset() {
    city.value = ''
    hotelName.value = ''
    hotelLon.value = 0
    hotelLat.value = 0
    hotelTwStart.value = 360
    hotelTwEnd.value = 1440
    spots.value = []
    suggestions.value = []
    selectedNDays.value = null
    selectedMethod.value = ''
    planResult.value = null
  }

  return {
    city, hotelName, hotelLon, hotelLat, hotelTwStart, hotelTwEnd,
    spots, penaltyWeight, earlyWaitWeight, lateReturnWeight,
    suggestions, selectedNDays, selectedMethod,
    planResult, loading,
    buildRequest, reset,
  }
})
