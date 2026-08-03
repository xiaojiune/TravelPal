/** API 客户端：封装 axios 实例，提供类型化的后端接口调用。 */
import axios from 'axios'
import type { POILookupResponse, PlanRequestPayload, SuggestionItem, SpotDictItem } from '@/types'

const http = axios.create({ baseURL: '/api' })

/** POI 查询：根据城市和名称列表批量获取坐标/地址/营业时间。 */
export function postPoiLookup(city: string, names: string[]): Promise<POILookupResponse> {
  return http.post('/poi-lookup', { city, names }).then(r => r.data)
}

// ================== 异步规划任务 ==================


/** suggest 任务完成时的完整响应（原 POST /api/suggest 同步返回体）。 */
export interface SuggestResult {
  suggestions: SuggestionItem[]
  algo_time?: number
  amap_api_key?: string
  amap_security_code?: string
  spots?: Record<string, SpotDictItem>
  cost_matrix?: number[][]
  dist_matrix?: number[][]
  polylines?: Record<string, string>
  message?: string
}

/** 异步规划任务状态详情（status: pending/running/done/failed，result 仅 done 时存在）。 */
export interface TaskDetail {
  task_id: string
  task_type: string
  status: string
  result?: Record<string, unknown> | null
  error?: string | null
}

/** 提交异步规划任务。suggest/plan 立即返回 task_id，前端轮询 GET /api/tasks/{id} 获取结果。 */
export function submitTask(type: 'suggest' | 'plan', data: PlanRequestPayload): Promise<{ task_id: string }> {
  return http.post(`/${type}`, data).then(r => r.data)
}

/** 查询异步规划任务状态。 */
export function getTask(taskId: string): Promise<TaskDetail> {
  return http.get(`/tasks/${taskId}`).then(r => r.data)
}

/** Agent 对话：使用 EventSource 或 POST 方式与 LLM 交互（mock 模式下返回固定回复）。 */
export function postChat(message: string, sessionId: string): Promise<unknown> {
  return http.post('/chat', { message, session_id: sessionId }).then(r => r.data)
}


// ================== 历史记录（分享站） ==================


/** 历史记录列表项（摘要） */
export interface HistorySummary {
  id: string
  city: string
  hotel?: string
  n_days: number
  cost?: number
  spot_count?: number
  note?: string
  created_at: string
}

/** 历史记录分页响应 */
export interface HistoryListResponse {
  items: HistorySummary[]
  total: number
  page: number
  page_size: number
}

/** 历史记录完整详情 */
export interface HistoryDetail {
  id: string
  city: string
  hotel?: string
  n_days: number
  cost?: number
  spot_count?: number
  note?: string
  plan_result: Record<string, unknown>
  request_params?: Record<string, unknown>
  created_at: string
}

/** 获取设备 ID：首次访问时生成匿名随机标识，存入 localStorage。 */
export function getDeviceId(): string {
  const key = 'travelpal_device_id'
  let id = localStorage.getItem(key)
  if (!id) {
    id = 'dev_' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36)
    localStorage.setItem(key, id)
  }
  return id
}

/** 获取历史记录列表（分页）。 */
export function getHistoryList(page = 1, pageSize = 20): Promise<HistoryListResponse> {
  return http.get('/history', { params: { page, page_size: pageSize } }).then(r => r.data)
}

/** 获取单条历史记录完整数据。 */
export function getHistoryDetail(id: string): Promise<HistoryDetail> {
  return http.get(`/history/${id}`).then(r => r.data)
}

/** 保存一条历史记录（分享方案）。 */
export function postHistory(data: {
  device_id?: string
  note?: string
  city: string
  hotel?: string
  n_days: number
  cost?: number
  spot_count?: number
  plan_result: Record<string, unknown>
  request_params?: Record<string, unknown>
}): Promise<{ id: string }> {
  return http.post('/history', data).then(r => r.data)
}

/** 删除一条历史记录（需 device_id 匹配）。 */
export function deleteHistory(id: string, deviceId: string): Promise<{ ok: boolean }> {
  return http.delete(`/history/${id}`, { data: { device_id: deviceId } }).then(r => r.data)
}

