/** API 客户端：封装 axios 实例，提供类型化的后端接口调用。 */
import axios from 'axios'
import type { POILookupResponse, PlanRequestPayload, PlanResult, SuggestionItem } from '@/types'

const http = axios.create({ baseURL: '/api' })

/** POI 查询：根据城市和名称列表批量获取坐标/地址/营业时间。 */
export function postPoiLookup(city: string, names: string[]): Promise<POILookupResponse> {
  return http.post('/poi-lookup', { city, names }).then(r => r.data)
}

/** 获取方案建议：返回多组不同天数的候选方案（ca_suggest 结果）。 */
export function postSuggest(data: PlanRequestPayload): Promise<{ suggestions: SuggestionItem[] }> {
  return http.post('/suggest', data).then(r => r.data)
}

/** 执行规划：按指定天数生成完整方案（包含 routes / schedules / Cesium 数据）。 */
export function postPlan(data: PlanRequestPayload): Promise<PlanResult> {
  return http.post('/plan', data).then(r => r.data)
}

/** Agent 对话：使用 EventSource 或 POST 方式与 LLM 交互（mock 模式下返回固定回复）。 */
export function postChat(message: string, sessionId: string): Promise<unknown> {
  return http.post('/chat', { message, session_id: sessionId }).then(r => r.data)
}

/** 方案调整：均衡天数 / 调整天数 / 移除景点，后端重新求解后返回新方案。 */
export function patchPlanAdjust(data: unknown): Promise<PlanResult> {
  return http.patch('/plan/adjust', data).then(r => r.data)
}
