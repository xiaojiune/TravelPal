/** 方案调整 composable：封装均衡/改天数/移除/添加景点四种操作，
 *  共享 try-catch 模板，消除 PlanPage 的重复调用代码。 */
import { ref } from 'vue'
import { AxiosError } from 'axios'
import { usePlanStore } from '@/stores/plan'
import { patchPlanAdjust, postPoiLookup } from '@/services/api'

interface AddPoiInfo {
  name: string; lon: number; lat: number
  tw_start: number; tw_end: number; stay: number
}

export function usePlanAdjust() {
  const store = usePlanStore()
  const balancing = ref(false)
  const adjusting = ref(false)
  const addingPoi = ref(false)
  const addPoiInput = ref('')
  const addPoiSearchResult = ref<AddPoiInfo | null>(null)
  const addPoiSearchFailed = ref(false)

  /** 统一调整入口：构造 patchPlanAdjust 请求体，失败时 alert 错误详情。 */
  async function doAdjust(adjustments: Record<string, unknown>, label: string) {
    const pr = store.planResult
    if (!pr) return
    try {
      const data = await patchPlanAdjust({
        spots: pr.spots,
        cost_matrix: pr.cost_matrix,
        dist_matrix: pr.dist_matrix,
        routes: pr.solution?.routes || [],
        adjustments,
      })
      store.planResult = data
    } catch (e: unknown) {
      alert(`${label}失败: ` + (e instanceof AxiosError ? (e.response?.data as { detail?: string })?.detail || e.message : (e as Error)?.message))
    }
  }

  async function searchAddPoi() {
    const name = addPoiInput.value.trim()
    if (!name || !store.city) return
    addingPoi.value = true
    addPoiSearchResult.value = null
    addPoiSearchFailed.value = false
    try {
      const data = await postPoiLookup(store.city, [name])
      if (data.items.length) {
        const item = data.items[0]
        addPoiSearchResult.value = {
          name: item.name,
          lon: item.lon, lat: item.lat,
          tw_start: item.tw_start ?? 480,
          tw_end: item.tw_end ?? 1020,
          stay: 60,
        }
      } else {
        addPoiSearchFailed.value = true
      }
    } catch {
      addPoiSearchFailed.value = true
    } finally {
      addingPoi.value = false
    }
  }

  function resetAddPoi() {
    addPoiInput.value = ''
    addPoiSearchResult.value = null
    addPoiSearchFailed.value = false
  }

  async function confirmAddPoi() {
    if (!addPoiSearchResult.value) return
    await doAdjust({ add_poi: addPoiSearchResult.value }, '添加景点')
    resetAddPoi()
  }

  /** 均衡分配：后端重新分摊各天景点数。 */
  async function doBalance() {
    balancing.value = true
    await doAdjust({ balance: true }, '均衡')
    balancing.value = false
  }

  /** 改天数：指定新天数，后端重新分群求解。 */
  async function doAdjustDays(days: number) {
    adjusting.value = true
    await doAdjust({ adjust_days: days }, '调整天数')
    adjusting.value = false
  }

  /** 移除景点：按名称移除并重新规划。用户确认后执行。 */
  async function doRemovePoi(name: string) {
    if (!confirm(`确定移除「${name}」吗？移除后将重新规划。`)) return
    await doAdjust({ remove_poi: name }, '移除景点')
  }

  return {
    balancing, adjusting, addingPoi, addPoiInput, addPoiSearchResult, addPoiSearchFailed,
    doBalance, doAdjustDays, doRemovePoi,
    searchAddPoi, confirmAddPoi, resetAddPoi,
  }
}
