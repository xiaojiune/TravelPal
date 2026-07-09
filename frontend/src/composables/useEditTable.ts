/** 规划点管理表格 composable：维护编辑行数据，提供确认/删除操作，与 store 数据解耦。 */
import { ref, computed, watch } from 'vue'
import { usePlanStore } from '@/stores/plan'

interface EditRow {
  isHotel: boolean; name: string; address: string
  lon: number; lat: number
  twStart: number; twEnd: number; stay: number
  expectedArrival: number; delete: boolean
}

export function useEditTable() {
  const store = usePlanStore()
  const editRows = ref<EditRow[]>([])
  const editHint = ref('')

  /** 已有确认点位时展示管理表格。 */
  const showManagement = computed(() => !!(store.hotelName || store.spots.length > 0))

  /** 从 store 重建编辑行，与源数据解耦。用户确认前所有修改不影响 store。 */
  function rebuildEditRows() {
    const rows: EditRow[] = []
    if (store.hotelName && store.hotelLon) {
      rows.push({
        isHotel: true, name: store.hotelName, address: store.hotelAddress,
        lon: store.hotelLon, lat: store.hotelLat,
        twStart: store.hotelTwStart, twEnd: store.hotelTwEnd,
        stay: 0, expectedArrival: store.hotelTwStart, delete: false,
      })
    }
    store.spots.forEach(s => {
      rows.push({
        isHotel: false, name: s.name, address: s.address || '',
        lon: s.lon, lat: s.lat,
        twStart: s.twStart, twEnd: s.twEnd,
        stay: s.stay, expectedArrival: s.expectedArrival ?? s.twStart, delete: false,
      })
    })
    editRows.value = rows
  }

  watch([() => store.spots, () => store.hotelName, () => store.hotelLon], rebuildEditRows, { deep: true })

  /** 将分钟数转换为 HH:MM 格式，用于表格显示营业时间列。 */
  function formatBiz(start: number, end: number) {
    const s = `${Math.floor(start / 60)}:${String(start % 60).padStart(2, '0')}`
    const e = `${Math.floor(end / 60)}:${String(end % 60).padStart(2, '0')}`
    return `${s}-${e}`
  }

  /** 删除勾选行。酒店行被删则清空 store 酒店信息；景点行直接移除。 */
  function deleteSelectedRows() {
    const remaining = editRows.value.filter(r => !r.delete)
    if (remaining.length === editRows.value.length) {
      editHint.value = '没有选中要删除的行'
      return
    }
    const hotelRow = remaining.find(r => r.isHotel)
    if (!hotelRow) {
      store.hotelName = ''
      store.hotelLon = 0
      store.hotelLat = 0
      store.hotelAddress = ''
    }
    store.spots = remaining.filter(r => !r.isHotel).map(r => ({
      name: r.name, lon: r.lon, lat: r.lat,
      twStart: r.twStart, twEnd: r.twEnd, stay: r.stay,
      expectedArrival: r.expectedArrival,
      address: r.address,
    }))
    editHint.value = ''
    rebuildEditRows()
  }

  /** 将编辑行数据回写 store（时间窗/停留/预计到达），触发重建。 */
  function applyEdits() {
    const hotelRow = editRows.value.find(r => r.isHotel)
    if (hotelRow) {
      store.hotelTwStart = hotelRow.twStart
      store.hotelTwEnd = hotelRow.twEnd
    }
    store.spots = editRows.value.filter(r => !r.isHotel).map(r => ({
      name: r.name, lon: r.lon, lat: r.lat,
      twStart: r.twStart, twEnd: r.twEnd, stay: r.stay,
      expectedArrival: r.expectedArrival,
      address: r.address,
    }))
    editHint.value = '参数已保存'
    setTimeout(() => { editHint.value = '' }, 2000)
    rebuildEditRows()
  }

  return { editRows, editHint, showManagement, rebuildEditRows, formatBiz, deleteSelectedRows, applyEdits }
}
