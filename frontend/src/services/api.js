// ====== /api 接口封装 ======

import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

/** POI 名称→坐标批量查找 */
export function postPoiLookup(city, names) {
  return http.post('/poi-lookup', { city, names }).then(r => r.data)
}

/** 获取方案建议（引擎自动推断天数） */
export function postSuggest(data) {
  return http.post('/suggest', data).then(r => r.data)
}

/** 生成指定天数的最终规划 */
export function postPlan(data) {
  return http.post('/plan', data).then(r => r.data)
}

/** Agent 聊天（SSE 流式） */
export function postChat(message, sessionId) {
  return http.post('/chat', { message, session_id: sessionId }).then(r => r.data)
}
