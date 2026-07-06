/**
 * 路由配置：首页（输入） → 方案建议（选择） → 规划结果（查看）
 * SuggestPage 和 PlanPage 使用懒加载。
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../pages/HomePage.vue'),
  },
  {
    path: '/suggest',
    name: 'Suggest',
    component: () => import('../pages/SuggestPage.vue'),
  },
  {
    path: '/plan',
    name: 'Plan',
    component: () => import('../pages/PlanPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
