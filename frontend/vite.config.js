import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Local dev  → http://localhost:8000  (backend running with: uvicorn main:app --reload)
// Docker     → http://backend:8000    (set VITE_API_TARGET=http://backend:8000 in compose)
const API_TARGET = 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth':    API_TARGET,
      '/analyse': API_TARGET,
      '/status':  API_TARGET,
      '/comments':API_TARGET,
      '/health':  API_TARGET,
    }
  }
})