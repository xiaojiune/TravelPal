/** 路由表：页面组件懒加载 + 认证/管理守卫。
 * 一级=门户（/）、二级=工作区（/home /suggest /plan /shares）、
 * 三级=个人中心（/profile，点头像进入）/ 管理台（/admin）。Agent 已全局化（App.vue 浮动抽屉，仅二级显示），无独立路由。 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

declare module 'vue-router' {
  interface RouteMeta {
    /** 页面是否需登录。 */
    requiresAuth?: boolean
    /** 是否需超级管理员（role === 'super_admin'）。轴5：前端界面仅 super_admin 激活；普通 admin 后端可调 API。 */
    requiresAdmin?: boolean
    /** 是否使用工作区布局（导航栏+工具轨+Agent）。默认 false=门户极简布局。 */
    useWorkbench?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'Portal', component: () => import('@/pages/PortalPage.vue') },
  { path: '/home', name: 'Home', component: () => import('@/pages/HomePage.vue'), meta: { useWorkbench: true } },
  { path: '/suggest', name: 'Suggest', component: () => import('@/pages/SuggestPage.vue'), meta: { useWorkbench: true } },
  { path: '/plan', name: 'Plan', component: () => import('@/pages/PlanPage.vue'), meta: { useWorkbench: true } },
  { path: '/shares', name: 'Shares', component: () => import('@/pages/SharePage.vue'), meta: { useWorkbench: true } },
  { path: '/about', name: 'About', component: () => import('@/pages/AboutPage.vue') },
  { path: '/login', name: 'Login', component: () => import('@/pages/LoginPage.vue') },
  { path: '/register', name: 'Register', component: () => import('@/pages/RegisterPage.vue') },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/pages/ProfilePage.vue'),
    meta: { requiresAuth: true, useWorkbench: true },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/pages/AdminPage.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, useWorkbench: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 认证/管理守卫：
// - 已登录访问登录/注册页 → 工作区（/home）；
// - 需登录页未登录 → 登录页（带 redirect）；
// - 需超管页（requiresAdmin）：未登录先去登录；已登录但非 super_admin → 工作区。
router.beforeEach(async (to) => {
  const userStore = useUserStore()
  if (userStore.isLoggedIn && (to.name === 'Login' || to.name === 'Register')) {
    return { path: '/home' }
  }
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    if (!userStore.ready) await userStore.fetchMe()
    if (!userStore.isLoggedIn) return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && userStore.user?.role !== 'super_admin') {
    // 已覆盖未登录（上文已跳登录）；此处拦截已登录但非超管（普通 admin/user）
    return { path: '/home' }
  }
  return true
})

export default router
