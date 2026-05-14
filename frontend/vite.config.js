import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig(({ mode }) => {
  const envPath = path.resolve(__dirname, '..')

  const env = loadEnv(mode, envPath, '')

  const API_TARGET =
    env.VITE_API_TARGET || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      allowedHosts: true,

      proxy: {
        '/auth': API_TARGET,
        '/analyse': API_TARGET,
        '/status': API_TARGET,
        '/comments': API_TARGET,
        '/health': API_TARGET,
      },
    },
  }
})