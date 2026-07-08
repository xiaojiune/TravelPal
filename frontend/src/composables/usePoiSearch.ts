/** POI 搜索 composable：封装高德 POI 查询 + 确认添加的逻辑，与 UI 解耦。 */
import { ref, computed } from 'vue'
import { AxiosError } from 'axios'
import { usePlanStore } from '@/stores/plan'
import { postPoiLookup } from '@/services/api'

interface PoiSearchItem {
  name: string; lon: number; lat: number; address: string
  tw_start?: number | null; tw_end?: number | null
}

interface PoiResult extends PoiSearchItem {
  checked: boolean; isHotel: boolean
}

export function usePoiSearch() {
  const store = usePlanStore()

  const spotText = ref('')
  const hotelResult = ref<PoiSearchItem | null>(null)
  const hotelFailed = ref(false)
  const spotResults = ref<PoiSearchItem[]>([])
  const spotFailed = ref<string[]>([])
  const loading = ref(false)

  const canSearchHotel = computed(() => !!store.city && store.hotelName.trim().length > 0)
  const canSearchSpots = computed(() => !!store.city && spotText.value.trim().length > 0)
  /** 是否有搜索结果（酒店或景点任一项找到），控制搜索结果表格的显隐。 */
  const hasResults = computed(() => !!hotelResult.value || spotResults.value.length > 0)

  /** 合并酒店+景点为统一列表，支持勾选状态，供搜索结果表格渲染。 */
  const allResults = computed(() => {
    const list: PoiResult[] = []
    if (hotelResult.value) list.push({ ...hotelResult.value, checked: true, isHotel: true })
    spotResults.value.forEach(item => list.push({ ...item, checked: true, isHotel: false }))
    return list
  })

  /** 搜索酒店坐标。结果存入 hotelResult，失败时设 hotelFailed。 */
  async function searchHotel() {
    loading.value = true
    hotelResult.value = null
    hotelFailed.value = false
    try {
      const data = await postPoiLookup(store.city, [store.hotelName.trim()])
      if (data.items.length) {
        hotelResult.value = data.items[0]
      } else {
        hotelFailed.value = true
      }
    } catch (e: unknown) {
      const msg = e instanceof AxiosError ? (e.response?.data as { detail?: string })?.detail || e.message : '未知错误'
      alert('搜索酒店失败: ' + msg)
    } finally {
      loading.value = false
    }
  }

  /** 批量搜索景点坐标。结果存入 spotResults，未找到的名录写入 spotFailed。 */
  async function searchSpots() {
    loading.value = true
    spotResults.value = []
    spotFailed.value = []
    try {
      const names = spotText.value.split('\n').map(s => s.trim()).filter(Boolean)
      const data = await postPoiLookup(store.city, names)
      spotResults.value = data.items.map(item => ({ ...item }))
      spotFailed.value = data.failed || []
    } catch (e: unknown) {
      const msg = e instanceof AxiosError ? (e.response?.data as { detail?: string })?.detail || e.message : '未知错误'
      alert('搜索景点失败: ' + msg)
    } finally {
      loading.value = false
    }
  }

  /**
   * 确认添加：将勾选的搜索结果写入 store。
   * 酒店写入 hotelLon/Lat/Address/TwStart/TwEnd，景点追加到 spots。
   * 已有名称的景点跳过（去重）。最后清空搜索结果。
   */
  function confirmPoi() {
    const hotel = allResults.value.find(item => item.isHotel && item.checked)
    if (hotel) {
      store.hotelLon = hotel.lon
      store.hotelLat = hotel.lat
      store.hotelAddress = hotel.address
      if (hotel.tw_start != null) store.hotelTwStart = hotel.tw_start
      if (hotel.tw_end != null) store.hotelTwEnd = hotel.tw_end
    }

    const existingNames = new Set(store.spots.map(s => s.name))
    const newSpots = allResults.value.filter(item => !item.isHotel && item.checked && !existingNames.has(item.name))
    for (const item of newSpots) {
      store.spots.push({
        name: item.name, lon: item.lon, lat: item.lat,
        twStart: item.tw_start ?? 480, twEnd: item.tw_end ?? 1020, stay: 60,
        address: item.address,
      })
    }

    // 确认后清空搜索结果，管理表格（useEditTable）自动接管
    spotText.value = ''
    hotelResult.value = null
    hotelFailed.value = false
    spotResults.value = []
    spotFailed.value = []
  }

  /** 清空搜索结果但不影响已确认的点位。用于切换输入时重置搜索面板。 */
  function clearSearchResults() {
    hotelResult.value = null
    hotelFailed.value = false
    spotResults.value = []
    spotFailed.value = []
  }

  return {
    spotText, hotelResult, hotelFailed, spotResults, spotFailed, loading,
    canSearchHotel, canSearchSpots, hasResults, allResults,
    searchHotel, searchSpots, confirmPoi, clearSearchResults,
  }
}
