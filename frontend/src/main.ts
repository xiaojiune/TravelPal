/** 应用入口：挂载 Vue 3 实例，注册 Pinia 状态管理 + Vue Router。 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from '@/App.vue'
import router from '@/router'
import '@/style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
