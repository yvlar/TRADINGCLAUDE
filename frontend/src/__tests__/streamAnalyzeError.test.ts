import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { streamAnalyze } from '../api/analyze'
import { ApiError } from '../api/client'
import type { AnalyzeRequest } from '../types'

const REQUEST: AnalyzeRequest = { ticker: 'BNS.TO', ratios: null, workflow: 'value_graham' }

/** Déclenche le chemin d'erreur du générateur (la première itération lève). */
async function drainError(): Promise<unknown> {
  try {
    for await (const _ of streamAnalyze(REQUEST)) { void _ }
  } catch (e) {
    return e
  }
  throw new Error('streamAnalyze aurait dû lever')
}

describe('streamAnalyze — parsing du corps detail (délégué à extractDetailMessage)', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    globalThis.fetch = vi.fn()
  })
  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('aplatit désormais un detail tableau (422 Pydantic) au lieu de le perdre — changement S194', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: () => Promise.resolve({ detail: [{ loc: ['body', 'eps'], msg: 'doit être un nombre' }] }),
    } as Response)

    const err = await drainError()
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).status).toBe(422)
    // Avant S194 : retombait sur statusText. Désormais : message Pydantic aplati.
    expect((err as ApiError).message).toBe('eps : doit être un nombre')
  })

  it('429 quota (objet) reste inchangé : message extrait + detail brut conservé', async () => {
    const detail = { message: 'Quota atteint', plan: 'free', used: 50, limit: 50, remaining: 0 }
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: false,
      status: 429,
      statusText: 'Too Many Requests',
      json: () => Promise.resolve({ detail }),
    } as Response)

    const err = await drainError()
    expect((err as ApiError).message).toBe('Quota atteint')
    expect((err as ApiError).detail).toEqual(detail)
  })
})
