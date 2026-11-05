import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发时 /api 转发到 kohakumoss-webui(127.0.0.1:8787);构建产物由它直接托管。
const proxy = { '/api': { target: 'http://127.0.0.1:8787', changeOrigin: false } }

export default defineConfig({
  plugins: [vue()],
  base: './',
  server: { host: true, proxy },
  preview: { host: true, proxy },
})
