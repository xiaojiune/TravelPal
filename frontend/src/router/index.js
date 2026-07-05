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
