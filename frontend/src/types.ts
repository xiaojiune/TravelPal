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

/** suggest 任务完成时的完整响应（TaskDetail.result，由 OpenAPI 生成）。 */
export type SuggestResult = components['schemas']['SuggestResult']

/** 异步规划任务状态详情（由 OpenAPI 生成，status: pending/running/done/failed）。 */
export type TaskDetail = components['schemas']['TaskDetail']

/** 方案分享列表项（摘要，由 OpenAPI 生成）。 */
export type ShareSummary = components['schemas']['ShareSummary']

/** 方案分享分页响应（由 OpenAPI 生成）。 */
export type ShareListResponse = components['schemas']['ShareListResponse']

/** 方案分享完整详情（由 OpenAPI 生成）。 */
export type ShareDetail = components['schemas']['ShareDetail']

/** 当前登录用户（由 OpenAPI 生成；id/role/email/nickname/is_active）。 */
export type UserOut = components['schemas']['UserOut']

// ==================== 管理员操作台（轴5） ====================

/** 管理人员：用户列表项（由 OpenAPI 生成）。 */
export type AdminUser = components['schemas']['AdminUser']

/** 管理人员：异步任务列表项（由 OpenAPI 生成）。 */
export type AdminTask = components['schemas']['AdminTask']

/** 管理人员：用户反馈列表项（由 OpenAPI 生成）。 */
export type AdminFeedback = components['schemas']['AdminFeedback']

/** 用户列表分页响应（由 OpenAPI 生成）。 */
export type AdminUsersResponse = components['schemas']['AdminUsersResponse']

/** 任务列表分页响应（由 OpenAPI 生成）。 */
export type AdminTasksResponse = components['schemas']['AdminTasksResponse']

/** 反馈列表分页响应（由 OpenAPI 生成）。 */
export type AdminFeedbackResponse = components['schemas']['AdminFeedbackResponse']

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

/** 聊天消息（tool 形态承载工具结果原始数据，供 ToolResultCard 判别渲染） */
export interface ChatMessage {
  role: 'user' | 'assistant' | 'tool'
  content: string
  time?: string
  data?: unknown
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
