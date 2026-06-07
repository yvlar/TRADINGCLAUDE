import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import type { ProxyOptions } from 'vite'

// Proxy partagé entre le dev server (`vite`) ET le preview (`vite preview`) : le preview
// sert le build de prod (assets pré-compilés, pas de compilation à la demande) et n'hérite
// PAS de `server.proxy` — sans ce partage, les appels API du E2E CI ne seraient pas relayés
// vers FastAPI :8000. Les routes à `bypass` (/admin, /compare, /screen, /watchlist) sont à la
// fois des préfixes API ET des routes SPA React Router : on laisse passer la navigation HTML
// (deep-link / refresh) vers index.html, on ne proxifie que les appels API (XHR/fetch).
const proxy: Record<string, string | ProxyOptions> = {
  '/auth': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
  '/admin': {
    target: 'http://localhost:8000',
    bypass(req) {
      if (req.headers.accept?.includes('text/html')) return '/index.html'
    },
  },
  '/annotations': 'http://localhost:8000',
  '/composite-history': 'http://localhost:8000',
  '/esg-history': 'http://localhost:8000',
  '/compare': {
    target: 'http://localhost:8000',
    bypass(req) {
      if (req.headers.accept?.includes('text/html')) return '/index.html'
    },
  },
  '/monthly-report': 'http://localhost:8000',
  '/screener-report': 'http://localhost:8000',
  '/semantic-search': 'http://localhost:8000',
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
}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy,
  },
  // Preview sert le build de prod sur :5173 avec le même proxy que le dev server. Utilisé par
  // la CI E2E : pas de compilation à la demande → la navigation Playwright ne flake plus sur le
  // budget de 10 s (la latence de compile-à-froid du dev server dépassait ce budget sous charge).
  preview: {
    port: 5173,
    proxy,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    css: true,
  },
})
