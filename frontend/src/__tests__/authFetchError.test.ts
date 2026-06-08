import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { authLogin, AuthApiError } from '../api/auth'

// authFetch délègue désormais le parsing du corps `detail` à extractDetailMessage (S194) :
// 4ᵉ site de l'aplatissement Pydantic réconcilié dans le helper partagé.
describe('authFetch — parsing du corps detail (délégué à extractDetailMessage)', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    globalThis.fetch = vi.fn()
  })
  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  async function loginError(): Promise<AuthApiError> {
    try {
      await authLogin({ email: 'a@b.co', password: 'x' })
    } catch (e) {
      return e as AuthApiError
    }
    throw new Error('authLogin aurait dû lever')
  }

  it('detail string (cas dominant auth) : message inchangé', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: () => Promise.resolve({ detail: 'Email ou mot de passe incorrect' }),
    } as Response)

    const err = await loginError()
    expect(err).toBeInstanceOf(AuthApiError)
    expect(err.message).toBe('Email ou mot de passe incorrect')
  })

  it('detail tableau Pydantic (422) : aplati comme sur les autres sites', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: () => Promise.resolve({ detail: [{ loc: ['body', 'email'], msg: 'format invalide' }] }),
    } as Response)

    expect((await loginError()).message).toBe('email : format invalide')
  })
})
