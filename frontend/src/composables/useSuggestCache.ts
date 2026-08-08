/**
 * suggest 响应缓存：HomePage 写入、SuggestPage 消费的跨页临时数据。
 *
 * 从 plan store 独立出来（ADR-011 #2）：这五项是「首页 fetchSuggest → 建议页
 * 复用」的页面间临时数据，不属于全局规划状态，放 store 表面膨胀。
 * 模块级 ref 即单例，多个页面共享同一份数据，无需各自初始化。
 */
import { ref } from 'vue'
import type { SpotDictItem } from '@/types'

/** suggest 响应带回来的 spots 字典（含 original_tw），fast 模式构建 PlanResult 时使用。 */
const suggestSpots = ref<Record<string, SpotDictItem>>({})
/** suggest 响应中的成本矩阵，deep 模式复用（跳过驾车 API）。 */
const suggestCostMatrix = ref<number[][]>([])
/** suggest 响应中的距离矩阵。 */
const suggestDistMatrix = ref<number[][]>([])
/** suggest 响应中的真实路径坐标字典。 */
const suggestPolylines = ref<Record<string, string>>({})
/** suggest 搜索总耗时（秒）。 */
const suggestAlgoTime = ref(0)

/** 清空全部 suggest 缓存（新规划开始时调用）。 */
function clear() {
  suggestSpots.value = {}
  suggestCostMatrix.value = []
  suggestDistMatrix.value = []
  suggestPolylines.value = {}
  suggestAlgoTime.value = 0
}

/** 返回共享缓存（模块级单例，跨页面读写同一份数据）。 */
export function useSuggestCache() {
  return {
    suggestSpots,
    suggestCostMatrix,
    suggestDistMatrix,
    suggestPolylines,
    suggestAlgoTime,
    clear,
  }
}
