/** 路由表：4 个页面组件，所有路由使用懒加载（动态 import）。首页 /suggest /plan /history；Agent 已全局化（App.vue 浮动抽屉），无独立路由。 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'Home', component: () => import('@/pages/HomePage.vue') },
  { path: '/suggest', name: 'Suggest', component: () => import('@/pages/SuggestPage.vue') },
  { path: '/plan', name: 'Plan', component: () => import('@/pages/PlanPage.vue') },
  { path: '/history', name: 'History', component: () => import('@/pages/HistoryPage.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
