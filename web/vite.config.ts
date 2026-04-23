import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  const rootDir = path.resolve(__dirname, '..')
  const env = loadEnv(mode, rootDir, '')
  const backendPort = env.VITE_BACKEND_PORT || '8005'

  return {
    plugins: [vue()],
    server: {
      port: parseInt(env.VITE_PORT || '5188'),
      proxy: {
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  }
})
