import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'Home', component: () => import('@/pages/HomePage.vue') },
  { path: '/suggest', name: 'Suggest', component: () => import('@/pages/SuggestPage.vue') },
  { path: '/plan', name: 'Plan', component: () => import('@/pages/PlanPage.vue') },
  { path: '/agent', name: 'Agent', component: () => import('@/pages/AgentPage.vue') },
  { path: '/history', name: 'History', component: () => import('@/pages/HistoryPage.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
