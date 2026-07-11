/** 前端类型定义。API 相关类型从 openapi-typescript 生成产物导入。 */
import type { components } from '@/api/types.generated'

// ==================== API 类型（由 OpenAPI 驱动） ====================

/** 发送给后端的 PlanRequest */
export type PlanRequestPayload = components['schemas']['PlanRequest']

/** POI 查找结果 */
export type POILookupItem = components['schemas']['POILookupItem']

/** POI 查找响应 */
export type POILookupResponse = components['schemas']['POILookupResponse']

// ==================== 后端响应类型（无对应 schema，手工维护） ====================

/** 方案建议项（ca_suggest 响应） */
export interface SuggestionItem {
  n_days: number
  method: string
  cost: number
  routes: number[][]
}

/** 规划结果的 solution 子对象 */
export interface PlanResultSolution {
  routes: number[][]
  histories?: number[][]
  total_cost: number
  total_dist: number
  wait: number
  late: number
  valid: boolean
}

/** 规划结果（run_planning 响应） */
export interface PlanResult {
  type: string
  solution?: PlanResultSolution
  best_days?: number
  best_m?: string
  daily_schedules?: ScheduleItem[][]
  commentary?: string
  city?: string
  spots?: Record<string, SpotDictItem>
  cost_matrix?: number[][]
  dist_matrix?: number[][]
  amap_api_key?: string
  algo_time?: number
}

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

/** 行程项 */
export interface ScheduleItem {
  name: string
  arrival: number
  departure: number
  tw: string
  stay: number
  arrival_status: string
  departure_status: string
}

/** 聊天消息 */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/** 规划结果中的景点字典项（从后端 pipeline spots 反序列化） */
export interface SpotDictItem {
  name: string
  x: number
  y: number
  lon?: number
  lat?: number
  tw?: [number, number]
  stay?: number
  original_tw?: [number, number]
}
