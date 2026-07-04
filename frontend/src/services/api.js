// /api 接口封装

import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

export function postPoiLookup(city, names) {
  return http.post('/poi-lookup', { city, names }).then(r => r.data)
}

export function postSuggest(data) {
  return http.post('/suggest', data).then(r => r.data)
}

export function postPlan(data) {
  return http.post('/plan', data).then(r => r.data)
}

export function postChat(message, sessionId) {
  return http.post('/chat', { message, session_id: sessionId }).then(r => r.data)
}
