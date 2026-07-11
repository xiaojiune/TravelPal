/** API 客户端：封装 axios 实例，提供类型化的后端接口调用。 */
import axios from 'axios'
import type { POILookupResponse, PlanRequestPayload, PlanResult, SuggestionItem, SpotDictItem } from '@/types'

const http = axios.create({ baseURL: '/api' })

/** POI 查询：根据城市和名称列表批量获取坐标/地址/营业时间。 */
export function postPoiLookup(city: string, names: string[]): Promise<POILookupResponse> {
  return http.post('/poi-lookup', { city, names }).then(r => r.data)
}

/** 获取方案建议：返回多组候选方案及高德 API key。FAST 模式可直接用 routes 渲染地图。 */
export function postSuggest(data: PlanRequestPayload): Promise<{ suggestions: SuggestionItem[]; amap_api_key?: string; spots?: Record<string, SpotDictItem> }> {
  return http.post('/suggest', data).then(r => r.data)
}

/** 执行规划：按指定天数生成完整方案（包含 routes / schedules / 地图数据）。 */
export function postPlan(data: PlanRequestPayload): Promise<PlanResult> {
  return http.post('/plan', data).then(r => r.data)
}

/** Agent 对话：使用 EventSource 或 POST 方式与 LLM 交互（mock 模式下返回固定回复）。 */
export function postChat(message: string, sessionId: string): Promise<unknown> {
  return http.post('/chat', { message, session_id: sessionId }).then(r => r.data)
}

