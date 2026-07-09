/** POI 搜索 composable：自动确认查询结果，无需用户勾选。 */
import { ref, computed } from 'vue'
import { AxiosError } from 'axios'
import { usePlanStore } from '@/stores/plan'
import { postPoiLookup } from '@/services/api'

export function usePoiSearch() {
  const store = usePlanStore()

  const spotText = ref('')
  const hotelMsg = ref('')
  const spotMsg = ref('')
  const loading = ref(false)

  const canSearchHotel = computed(() => !!store.city && store.hotelName.trim().length > 0)
  const canSearchSpots = computed(() => !!store.city && spotText.value.trim().length > 0)

  /** 搜索酒店坐标，成功则自动确认到 store。 */
  async function searchHotel() {
    loading.value = true
    hotelMsg.value = ''
    try {
      const data = await postPoiLookup(store.city, [store.hotelName.trim()])
      if (data.items.length) {
        const item = data.items[0]
        store.hotelLon = item.lon
        store.hotelLat = item.lat
        store.hotelAddress = item.address
        if (item.tw_start != null) store.hotelTwStart = item.tw_start
        if (item.tw_end != null) store.hotelTwEnd = item.tw_end
        hotelMsg.value = `✅ 已找到：${item.address}`
      } else {
        hotelMsg.value = `⚠️ ${data.failed?.[0] || '未找到该酒店'}`
      }
    } catch (e: unknown) {
      const msg = e instanceof AxiosError ? (e.response?.data as { detail?: string })?.detail || e.message : '未知错误'
      hotelMsg.value = '搜索酒店失败: ' + msg
    } finally {
      loading.value = false
    }
  }

  /** 批量搜索景点坐标，成功则自动确认到 store。 */
  async function searchSpots() {
    loading.value = true
    spotMsg.value = ''
    try {
      const names = spotText.value.split('\n').map(s => s.trim()).filter(Boolean)
      const data = await postPoiLookup(store.city, names)
      const existingNames = new Set(store.spots.map(s => s.name))
      for (const item of data.items) {
        if (!existingNames.has(item.name)) {
          store.spots.push({
            name: item.name, lon: item.lon, lat: item.lat,
            twStart: item.tw_start ?? 480, twEnd: item.tw_end ?? 1020, stay: 0,
            expectedArrival: 0, address: item.address,
          })
        }
      }
      const msgs: string[] = []
      if (data.items.length) msgs.push(`✅ 已添加 ${data.items.length} 个景点`)
      if (data.failed?.length) msgs.push(`⚠️ ${data.failed.join('；')}`)
      spotMsg.value = msgs.join('\n') || '⚠️ 未找到任何景点'
      if (data.items.length) spotText.value = ''
    } catch (e: unknown) {
      const msg = e instanceof AxiosError ? (e.response?.data as { detail?: string })?.detail || e.message : '未知错误'
      spotMsg.value = '搜索景点失败: ' + msg
    } finally {
      loading.value = false
    }
  }

  return {
    spotText, hotelMsg, spotMsg, loading,
    canSearchHotel, canSearchSpots,
    searchHotel, searchSpots,
  }
}
