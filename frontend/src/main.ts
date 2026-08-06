/** 应用入口：挂载 Vue 3 实例，注册 Pinia 状态管理 + Vue Router。
 * 前端架构详解见 docs/structure/frontend.md（docs 目录导航见根 ARCHITECTURE.md）。
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from '@/App.vue'
import router from '@/router'
import { applyThemeVars } from '@/theme'
import '@/style.css'

// 挂载前注入品牌色 CSS 变量（--tp-*），避免首帧 FOUC（ADR-009 §4）
applyThemeVars()

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
