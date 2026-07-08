/** 前端输入表单中的景点项 */
export interface SpotFormItem {
  name: string
  lon: number
  lat: number
  twStart: number
  twEnd: number
  stay: number
  address?: string
  expectedArrival?: number
}

/** 发送给后端的 PlanRequest */
export interface PlanRequestPayload {
  city: string
  hotel_name: string
  hotel_lon: number
  hotel_lat: number
  hotel_tw_start: number
  hotel_tw_end: number
  spots: {
    name: string
    lon: number
    lat: number
    tw_start: number
    tw_end: number
    stay: number
  }[]
  n_days: number | null
  mode: string
  penalty_weight: number
  early_wait_weight: number
  late_return_weight: number
}

/** POI 查找结果 */
export interface POILookupItem {
  name: string
  lon: number
  lat: number
  address: string
  tw_start: number | null
  tw_end: number | null
}

/** POI 查找响应 */
export interface POILookupResponse {
  items: POILookupItem[]
  failed: string[]
}

/** 方案建议项 */
export interface SuggestionItem {
  n_days: number
  method: string
  cost: number
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

/** 规划结果 */
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
