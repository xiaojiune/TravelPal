/** 路由表：页面组件懒加载 + 认证守卫骨架。首页 /suggest /plan /shares /about /login /register；Agent 已全局化（App.vue 浮动抽屉），无独立路由。 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

declare module 'vue-router' {
  interface RouteMeta {
    /** 页面是否需登录（供轴5 admin 等使用；现阶段无强制页面，访客零门槛）。 */
    requiresAuth?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'Home', component: () => import('@/pages/HomePage.vue') },
  { path: '/suggest', name: 'Suggest', component: () => import('@/pages/SuggestPage.vue') },
  { path: '/plan', name: 'Plan', component: () => import('@/pages/PlanPage.vue') },
  { path: '/shares', name: 'Shares', component: () => import('@/pages/SharePage.vue') },
  { path: '/about', name: 'About', component: () => import('@/pages/AboutPage.vue') },
  { path: '/login', name: 'Login', component: () => import('@/pages/LoginPage.vue') },
  { path: '/register', name: 'Register', component: () => import('@/pages/RegisterPage.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 认证守卫：已登录访问登录/注册页 → 首页；需登录页未登录 → 登录页（带 redirect）。
// 现阶段没有 meta.requiresAuth 页面，此守卫为骨架，供轴5 admin 等页使用。
router.beforeEach(async (to) => {
  const userStore = useUserStore()
  if (userStore.isLoggedIn && (to.name === 'Login' || to.name === 'Register')) {
    return { path: '/' }
  }
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    if (!userStore.ready) await userStore.fetchMe()
    if (!userStore.isLoggedIn) return { name: 'Login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
