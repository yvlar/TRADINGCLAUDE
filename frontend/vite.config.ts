import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/admin': 'http://localhost:8000',
      '/annotations': 'http://localhost:8000',
      '/composite-history': 'http://localhost:8000',
      '/esg-history': 'http://localhost:8000',
      '/compare': 'http://localhost:8000',
      '/monthly-report': 'http://localhost:8000',
      '/screener-report': 'http://localhost:8000',
      '/ticker-report': 'http://localhost:8000',
      '/backtest': 'http://localhost:8000',
      '/evals': 'http://localhost:8000',
      '/performance': 'http://localhost:8000',
      '/analyze': 'http://localhost:8000',
      '/screen': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html'
        },
      },
      '/history': 'http://localhost:8000',
      '/report': 'http://localhost:8000',
      '/telemetry': 'http://localhost:8000',
      '/metrics': 'http://localhost:8000',
      '/extract': 'http://localhost:8000',
      '/jobs': 'http://localhost:8000',
      '/healthz': 'http://localhost:8000',
      '/cache': 'http://localhost:8000',
      '/watchlist': {
        target: 'http://localhost:8000',
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html'
        },
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    css: true,
  },
})
