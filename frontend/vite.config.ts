import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // In dev the proxy rewrites relative API calls to the backend.
  // Override VITE_API_URL in your .env.local to point at a remote backend.
  const apiTarget = env.VITE_API_URL || 'http://localhost:8000'
  const wsTarget  = apiTarget.replace(/^https/, 'wss').replace(/^http/, 'ws')

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/analyze': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/video': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/ws': {
          target: wsTarget,
          ws: true,
          changeOrigin: true,
        },
        '/sounds': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
