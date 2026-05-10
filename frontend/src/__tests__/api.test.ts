import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ApiError, BASE_URL } from '../api/client'

describe('api/client.ts', () => {
  describe('BASE_URL', () => {
    it('est une chaîne', () => {
      expect(typeof BASE_URL).toBe('string')
    })
  })

  describe('ApiError', () => {
    it('expose le status HTTP', () => {
      const err = new ApiError(404, 'Not Found')
      expect(err.status).toBe(404)
      expect(err.message).toBe('Not Found')
      expect(err.name).toBe('ApiError')
    })

    it('est une instance d\'Error', () => {
      const err = new ApiError(500, 'Internal Server Error')
      expect(err).toBeInstanceOf(Error)
    })
  })

  describe('request', () => {
    const originalFetch = globalThis.fetch

    beforeEach(() => {
      globalThis.fetch = vi.fn()
    })

    afterEach(() => {
      globalThis.fetch = originalFetch
    })

    it('appelle fetch avec la bonne URL', async () => {
      const mockFetch = vi.mocked(globalThis.fetch)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'ok' }),
      } as Response)

      const { apiClient } = await import('../api/client')
      await apiClient.request('/healthz')

      expect(mockFetch).toHaveBeenCalledOnce()
      const [url] = mockFetch.mock.calls[0]
      expect(String(url)).toContain('/healthz')
    })

    it('définit Content-Type: application/json', async () => {
      const mockFetch = vi.mocked(globalThis.fetch)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response)

      const { apiClient } = await import('../api/client')
      await apiClient.request('/analyze', { method: 'POST', body: '{}' })

      const [, options] = mockFetch.mock.calls[0]
      const headers = options?.headers as Record<string, string>
      expect(headers['Content-Type']).toBe('application/json')
    })

    it('lève ApiError sur réponse non-ok', async () => {
      const mockFetch = vi.mocked(globalThis.fetch)
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        json: () => Promise.resolve({ detail: 'Ratios invalides' }),
      } as Response)

      const { apiClient } = await import('../api/client')
      await expect(apiClient.request('/analyze', { method: 'POST' })).rejects.toThrow(ApiError)
    })
  })
})
