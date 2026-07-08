import axios from 'axios'
import type { POILookupResponse, PlanRequestPayload, PlanResult, SuggestionItem } from '@/types'

const http = axios.create({ baseURL: '/api' })

export function postPoiLookup(city: string, names: string[]): Promise<POILookupResponse> {
  return http.post('/poi-lookup', { city, names }).then(r => r.data)
}

export function postSuggest(data: PlanRequestPayload): Promise<{ suggestions: SuggestionItem[] }> {
  return http.post('/suggest', data).then(r => r.data)
}

export function postPlan(data: PlanRequestPayload): Promise<PlanResult> {
  return http.post('/plan', data).then(r => r.data)
}

export function postChat(message: string, sessionId: string): Promise<unknown> {
  return http.post('/chat', { message, session_id: sessionId }).then(r => r.data)
}

export function patchPlanAdjust(data: unknown): Promise<PlanResult> {
  return http.patch('/plan/adjust', data).then(r => r.data)
}
