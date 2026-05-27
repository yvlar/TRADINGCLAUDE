import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

expect.extend(matchers)

afterEach(() => {
  cleanup()
})

// Mock fetch global : /auth/me → 401 par défaut en tests (pas de session)
// Évite que AuthProvider déclenche une vraie requête réseau vers localhost:8000
const _originalFetch = globalThis.fetch
globalThis.fetch = vi.fn(async (url: RequestInfo | URL, options?: RequestInit) => {
  const urlStr = typeof url === 'string' ? url : (url as URL).toString()
  if (urlStr.includes('/auth/me')) {
    return new Response(JSON.stringify({ detail: 'Non authentifié' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    })
  }
  if (typeof _originalFetch === 'function') {
    return _originalFetch(url, options)
  }
  return new Response(JSON.stringify({ detail: 'Not Found' }), { status: 404 })
}) as typeof fetch

// Polyfills pour Radix UI sous jsdom (hasPointerCapture manquant)
if (!window.HTMLElement.prototype.hasPointerCapture) {
  window.HTMLElement.prototype.hasPointerCapture = () => false
}
if (!window.HTMLElement.prototype.setPointerCapture) {
  window.HTMLElement.prototype.setPointerCapture = () => undefined
}
if (!window.HTMLElement.prototype.releasePointerCapture) {
  window.HTMLElement.prototype.releasePointerCapture = () => undefined
}
if (!window.HTMLElement.prototype.scrollIntoView) {
  window.HTMLElement.prototype.scrollIntoView = () => undefined
}

// Polyfill ResizeObserver pour cmdk (non disponible en jsdom)
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}
