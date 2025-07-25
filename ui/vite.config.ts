import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:7999',
        changeOrigin: true
      },
      '/images': {
        target: 'http://localhost:7999',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 3000,
    host: true
  }
});
