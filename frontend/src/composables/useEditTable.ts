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
  let _rebuilding = false // 重建中标志，阻止 editRows watch 触发回写
  let _saving = false // 保存中标志，阻止 store watch 重建
  let _hintTimer: ReturnType<typeof setTimeout> | null = null // 自动保存提示定时器

  rebuildEditRows() // 组件初始化时从 store 重建，确保跨页面导航后数据不为空

  /** 已有确认景点时展示管理表格（酒店信息由酒店卡独立管理，不进入表格）。 */
  const showManagement = computed(() => store.spots.length > 0)

  /** 从 store 重建编辑行，与源数据解耦。单行编辑即时回写 store。 */
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

  /** 短暂提示「已自动保存」，2s 后清除（可被后续 hint 覆盖）。 */
  function flashSaved() {
    editHint.value = '✅ 已自动保存'
    if (_hintTimer) clearTimeout(_hintTimer)
    _hintTimer = setTimeout(() => {
      if (editHint.value === '✅ 已自动保存') editHint.value = ''
    }, 2000)
  }

  /** store 数据变化（外部添加/删除景点）→ 重建表格。 */
  watch(
    [() => store.spots, () => store.hotelName, () => store.hotelLon, () => store.hotelAddress],
    () => {
      if (!_saving) {
        rebuildEditRows()
      }
    },
    { deep: true, flush: 'sync' },
  )

  /** 单行编辑即时回写：用户在编辑行改 stay/expectedArrival 时，逐行比对差异写回 store。 */
  watch(
    editRows,
    (newRows, oldRows) => {
      if (_rebuilding) return
      if (!oldRows) return
      _saving = true
      let changed = false
      newRows.forEach((r, i) => {
        const prev = oldRows[i]
        if (!prev) return
        const prevStay = prev.stay ?? null
        const prevArr = prev.expectedArrival ?? null
        const curStay = r.stay ?? null
        const curArr = r.expectedArrival ?? null
        if (prevStay !== curStay || prevArr !== curArr) {
          const s = store.spots[i]
          if (!s) return
          store.spots[i] = {
            ...s,
            stay: r.stay ?? 0,
            expectedArrival: r.expectedArrival ?? 0,
          }
          changed = true
        }
      })
      _saving = false
      if (changed) flashSaved()
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

  return {
    editRows,
    editHint,
    showManagement,
    rebuildEditRows,
    formatBiz,
    deleteSelectedRows,
    deleteRowAt,
  }
}
