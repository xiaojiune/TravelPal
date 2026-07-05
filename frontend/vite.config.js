import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strict: true, // 如果端口被占用则报错，而不是自动切换
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/Build': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
