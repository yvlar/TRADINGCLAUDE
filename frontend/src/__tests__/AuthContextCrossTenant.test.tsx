import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '../contexts/AuthContext'
import type { AuthResponse, User } from '../types'

vi.mock('../api/auth', () => ({
  authMe: vi.fn(),
  authLogin: vi.fn(),
  authLogout: vi.fn(),
  AuthApiError: class extends Error {},
}))

import { authMe, authLogin, authLogout } from '../api/auth'

// Deux locataires distincts : la bascule A → B doit changer l'identité sans fuite de cache.
function _user(tenantId: string, plan: string): User {
  return {
    id: `u-${tenantId}`,
    email: `${tenantId}@t.com`,
    role: 'reader',
    tenant_id: tenantId,
    tenant_name: `Espace ${tenantId}`,
    plan,
    created_at: '2026-01-01T00:00:00',
  }
}

function _authResponse(user: User): AuthResponse {
  return { user, message: 'ok' }
}

function Consumer() {
  const { user, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="tenant">{user?.tenant_id ?? 'none'}</span>
      <span data-testid="plan">{user?.plan ?? 'none'}</span>
      <button
        data-testid="login"
        onClick={() => void login({ email: 'x@y.com', password: 'pw' })}
      >
        login
      </button>
      <button data-testid="logout" onClick={() => void logout()}>
        logout
      </button>
    </div>
  )
}

function renderWithProvider(queryClient = new QueryClient()) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <Consumer />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AuthContext — flux re-connexion cross-tenant (login A → logout → login B)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('aucune donnée du tenant A ne survit à la bascule vers B, et user reflète B', async () => {
    // Pas de session au montage : on démarre déconnecté avant le login A.
    vi.mocked(authMe).mockRejectedValueOnce(new Error('401'))
    vi.mocked(authLogin)
      .mockResolvedValueOnce(_authResponse(_user('tenant-a', 'free')))
      .mockResolvedValueOnce(_authResponse(_user('tenant-b', 'pro')))
    vi.mocked(authLogout).mockResolvedValueOnce(undefined)
    const queryClient = new QueryClient()

    renderWithProvider(queryClient)
    await waitFor(() => expect(screen.getByTestId('tenant')).toHaveTextContent('none'))

    // (a) login tenant A
    await userEvent.click(screen.getByTestId('login'))
    await waitFor(() => expect(screen.getByTestId('tenant')).toHaveTextContent('tenant-a'))

    // (b) données « de A » en cache sous des clés NON scopées au tenant (la fuite à fermer).
    queryClient.setQueryData(['usage', 30], { cost_usd: 111 })
    queryClient.setQueryData(['usage-reporting'], { pending_events: 9 })
    // Pré-condition non vacue : la donnée de A est bien servie avant la bascule.
    expect(queryClient.getQueryData(['usage', 30])).toEqual({ cost_usd: 111 })

    // (c) logout (purge le cache react-query)
    await userEvent.click(screen.getByTestId('logout'))
    await waitFor(() => expect(screen.getByTestId('tenant')).toHaveTextContent('none'))

    // (d) login tenant B dans le même onglet, sans rechargement de page
    await userEvent.click(screen.getByTestId('login'))
    await waitFor(() => expect(screen.getByTestId('tenant')).toHaveTextContent('tenant-b'))

    // (e) aucune donnée de A ne survit (clés → undefined) et user = B
    // Échouerait si queryClient.clear() était retiré du logout : la donnée de A
    // pré-remplie en (b) survivrait à la bascule → ce test verrouille le FLUX, pas l'appel.
    expect(queryClient.getQueryData(['usage', 30])).toBeUndefined()
    expect(queryClient.getQueryData(['usage-reporting'])).toBeUndefined()
    expect(screen.getByTestId('plan')).toHaveTextContent('pro')
  })
})
