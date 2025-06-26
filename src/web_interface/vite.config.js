import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api/images': 'http://localhost:8001',
      '/api/verification': 'http://localhost:8002'
    }
  },
  build: {
    outDir: 'dist'
  }
})