/** 规划点管理表格 composable：维护编辑行数据，提供确认/删除操作，与 store 数据解耦。 */
import { ref, computed, watch, nextTick } from 'vue'
import { usePlanStore } from '@/stores/plan'
import { fmtRange } from '@/utils/time'

interface EditRow {
  name: string
  address: string
  lon: number
  lat: number
  twStart: number
  twEnd: number
  stay: number | null
  expectedArrival: number | null
  delete: boolean
}

export function useEditTable() {
  const store = usePlanStore()
  const editRows = ref<EditRow[]>([])
  const editHint = ref('')
  let _rebuilding = false // 重建中标志，阻止 editRows watch 触发解锁
  let _saving = false // 保存中标志，阻止 store watch 重建

  rebuildEditRows() // 组件初始化时从 store 重建，确保跨页面导航后数据不为空

  /** 已有确认景点时展示管理表格（酒店信息由酒店卡独立管理，不进入表格）。 */
  const showManagement = computed(() => store.spots.length > 0)

  /** 从 store 重建编辑行，与源数据解耦。用户确认前所有修改不影响 store。 */
  function rebuildEditRows() {
    _rebuilding = true
    const rows: EditRow[] = store.spots.map((s) => ({
      name: s.name,
      address: s.address || '',
      lon: s.lon,
      lat: s.lat,
      twStart: s.twStart,
      twEnd: s.twEnd,
      stay: s.stay || null,
      expectedArrival: s.expectedArrival || null,
      delete: false,
    }))
    editRows.value = rows
    nextTick(() => {
      _rebuilding = false
    })
  }

  /** store 数据变化 → 解锁参数锁（applyEdits 自发的写入除外）+ 重建表格。 */
  watch(
    [() => store.spots, () => store.hotelName, () => store.hotelLon, () => store.hotelAddress],
    () => {
      if (!_saving) {
        store.isParamsSaved = false
        editHint.value = ''
      }
      rebuildEditRows()
    },
    { deep: true, flush: 'sync' },
  )

  /** 用户编辑表格单元格时自动解锁，必须再次确认才能获取方案。 */
  watch(
    editRows,
    () => {
      if (!_rebuilding) {
        store.isParamsSaved = false
        editHint.value = ''
      }
    },
    { deep: true },
  )

  /** 将分钟数转换为 HH:MM 格式，用于表格显示营业时间列。 */
  function formatBiz(start: number, end: number) {
    return fmtRange(start, end)
  }

  /** 删除勾选行。全部为景点行（酒店不在表格中），直接移除并回写 store。 */
  function deleteSelectedRows() {
    const remaining = editRows.value.filter((r) => !r.delete)
    if (remaining.length === editRows.value.length) {
      editHint.value = '没有选中要删除的行'
      return
    }
    store.spots = remaining
      .map((r) => ({
        name: r.name,
        lon: r.lon,
        lat: r.lat,
        twStart: r.twStart,
        twEnd: r.twEnd,
        stay: r.stay ?? 0,
        expectedArrival: r.expectedArrival ?? 0,
        address: r.address,
      }))
    editHint.value = ''
  }

  /** 单删一行（景点卡右上角 ✕）：标记该行删除后复用批量删除逻辑。 */
  function deleteRowAt(index: number) {
    if (index >= 0 && index < editRows.value.length) {
      editRows.value[index].delete = true
    }
    deleteSelectedRows()
  }

  /** 将编辑行数据回写 store（时间窗/停留/预计到达）。watch 自动重建表格。 */
  function applyEdits() {
    if (editRows.value.length === 0) {
      editHint.value = '请先搜索并添加景点'
      return
    }
    _saving = true
    store.isParamsSaved = true
    store.spots = editRows.value.map((r) => ({
      name: r.name,
      lon: r.lon,
      lat: r.lat,
      twStart: r.twStart,
      twEnd: r.twEnd,
      stay: r.stay ?? 0,
      expectedArrival: r.expectedArrival ?? 0,
      address: r.address,
    }))
    _saving = false
    editHint.value = '参数已保存'
  }

  return {
    editRows,
    editHint,
    showManagement,
    rebuildEditRows,
    formatBiz,
    deleteSelectedRows,
    deleteRowAt,
    applyEdits,
  }
}
