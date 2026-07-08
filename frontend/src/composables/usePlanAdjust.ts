/** 方案调整 composable：封装均衡/改天数/移除景点三种调整操作，
 *  共享 try-catch 模板，消除 PlanPage 的重复调用代码。 */
import { ref } from 'vue'
import { usePlanStore } from '@/stores/plan'
import { patchPlanAdjust } from '@/services/api'

interface Adjustments {
  balance?: boolean
  adjust_days?: number
  remove_poi?: string
}

export function usePlanAdjust() {
  const store = usePlanStore()
  const balancing = ref(false)
  const adjusting = ref(false)

  /** 统一调整入口：构造 patchPlanAdjust 请求体，失败时 alert 错误详情。 */
  async function doAdjust(adjustments: Adjustments, label: string) {
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
      alert(`${label}失败: ` + ((e as any)?.response?.data?.detail || (e as Error)?.message))
    }
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

  return { balancing, adjusting, doBalance, doAdjustDays, doRemovePoi }
}
