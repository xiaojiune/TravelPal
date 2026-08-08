/** 前端类型定义。API 相关类型从 openapi-typescript 生成产物导入。 */
import type { components } from '@/api/types.generated'

// ==================== API 类型（由 OpenAPI 驱动） ====================

/** 发送给后端的 PlanRequest（cost_matrix/dist_matrix 已由后端 schema 覆盖，不再重复扩展） */
export type PlanRequestPayload = components['schemas']['PlanRequest']

/** POI 查找响应 */
export type POILookupResponse = components['schemas']['POILookupResponse']

// ==================== 后端响应类型（由 OpenAPI 驱动） ====================
// 由 backend/api/schemas.py 的 Pydantic 响应模型生成；改后端 schema 后执行
// make gen-api 自动同步，禁止手工改动。

/** 方案建议项（SuggestResult.suggestions 元素） */
export type SuggestionItem = components['schemas']['SuggestionItem']

/** 规划结果的 solution 子对象 */
export type PlanResultSolution = components['schemas']['PlanSolution']

/** 规划结果（plan 任务 result） */
export type PlanResult = components['schemas']['PlanResult']

/** 行程项（stay 为展示字符串，如 "180 min" 或 "-"） */
export type ScheduleItem = components['schemas']['ScheduleItem']

/** 规划结果中的景点字典项（result.spots 值） */
export type SpotDictItem = components['schemas']['SpotDictItem']

// ==================== 纯前端类型（不与后端 schema 对应） ====================

/** 前端输入表单中的景点项 */
export interface SpotFormItem {
  name: string
  lon: number
  lat: number
  twStart: number
  twEnd: number
  stay: number
  expectedArrival?: number
  address?: string
}

/** 聊天消息 */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  time?: string
}

/** Agent 对话查询到的 POI（待选栏暂存项，tool_result 事件载荷） */
export interface PoiItem {
  name?: string
  lon?: number
  lat?: number
  address?: string
  tw_start?: number
  tw_end?: number
  poi_type?: string
}
