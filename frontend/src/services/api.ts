/** API 客户端：封装 axios 实例，提供类型化的后端接口调用。 */
import axios from 'axios'
import type { components } from '@/api/types.generated'
import type { POILookupResponse, PlanRequestPayload } from '@/types'

const http = axios.create({ baseURL: '/api' })

/** POI 查询：根据城市和名称列表批量获取坐标/地址/营业时间。 */
export function postPoiLookup(city: string, names: string[]): Promise<POILookupResponse> {
  return http.post('/poi-lookup', { city, names }).then((r) => r.data)
}

// ================== 异步规划任务 ==================

/** suggest 任务完成时的完整响应（TaskDetail.result，由 OpenAPI 生成）。 */
export type SuggestResult = components['schemas']['SuggestResult']

/** 异步规划任务状态详情（由 OpenAPI 生成，status: pending/running/done/failed）。 */
export type TaskDetail = components['schemas']['TaskDetail']

/** 提交异步规划任务。suggest/plan 立即返回 task_id，前端轮询 GET /api/tasks/{id} 获取结果。 */
export function submitTask(
  type: 'suggest' | 'plan',
  data: PlanRequestPayload,
): Promise<components['schemas']['TaskSubmitResponse']> {
  return http.post(`/${type}`, data).then((r) => r.data)
}

/** 查询异步规划任务状态。 */
export function getTask(taskId: string): Promise<TaskDetail> {
  return http.get(`/tasks/${taskId}`).then((r) => r.data)
}

// ================== 历史记录（分享站） ==================

/** 历史记录列表项（摘要，由 OpenAPI 生成）。 */
export type HistorySummary = components['schemas']['HistorySummary']

/** 历史记录分页响应（由 OpenAPI 生成）。 */
export type HistoryListResponse = components['schemas']['HistoryListResponse']

/** 历史记录完整详情（由 OpenAPI 生成）。 */
export type HistoryDetail = components['schemas']['HistoryDetail']

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
  return http.get('/history', { params: { page, page_size: pageSize } }).then((r) => r.data)
}

/** 获取单条历史记录完整数据。 */
export function getHistoryDetail(id: string): Promise<HistoryDetail> {
  return http.get(`/history/${id}`).then((r) => r.data)
}

/** 保存一条历史记录（分享方案），请求体由 OpenAPI 的 HistoryCreate 约束。 */
export function postHistory(
  data: components['schemas']['HistoryCreate'],
): Promise<{ id: string }> {
  return http.post('/history', data).then((r) => r.data)
}

/** 删除一条历史记录（需 device_id 匹配）。 */
export function deleteHistory(id: string, deviceId: string): Promise<{ ok: boolean }> {
  return http.delete(`/history/${id}`, { data: { device_id: deviceId } }).then((r) => r.data)
}
