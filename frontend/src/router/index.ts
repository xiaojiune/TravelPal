/** 路由表：页面组件懒加载 + 认证/管理守卫。首页 /suggest /plan /shares /about /login /register /admin；Agent 已全局化（App.vue 浮动抽屉），无独立路由。 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

declare module 'vue-router' {
  interface RouteMeta {
    /** 页面是否需登录。 */
    requiresAuth?: boolean
    /** 是否需超级管理员（role === 'super_admin'）。轴5：前端界面仅 super_admin 激活；普通 admin 后端可调 API。 */
    requiresAdmin?: boolean
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
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/pages/AdminPage.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 认证/管理守卫：
// - 已登录访问登录/注册页 → 首页；
// - 需登录页未登录 → 登录页（带 redirect）；
// - 需超管页（requiresAdmin）：未登录先去登录；已登录但非 super_admin → 回首页。
router.beforeEach(async (to) => {
  const userStore = useUserStore()
  if (userStore.isLoggedIn && (to.name === 'Login' || to.name === 'Register')) {
    return { path: '/' }
  }
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    if (!userStore.ready) await userStore.fetchMe()
    if (!userStore.isLoggedIn) return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && userStore.user?.role !== 'super_admin') {
    // 已覆盖未登录（上文已跳登录）；此处拦截已登录但非超管（普通 admin/user）
    return { path: '/' }
  }
  return true
})

export default router
