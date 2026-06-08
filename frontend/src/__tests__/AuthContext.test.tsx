import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

vi.mock('../api/auth', () => ({
  authMe: vi.fn(),
  authLogin: vi.fn(),
  authLogout: vi.fn(),
  AuthApiError: class extends Error {},
}))

import { authMe, authLogout } from '../api/auth'

function _user(plan: string): User {
  return {
    id: 'u1',
    email: 't@t.com',
    role: 'reader',
    tenant_id: 'tid',
    tenant_name: 'Espace Démo',
    plan,
    created_at: '2026-01-01T00:00:00',
  }
}

function Consumer() {
  const { user, refreshUser, logout } = useAuth()
  return (
    <div>
      <span data-testid="plan">{user?.plan ?? 'none'}</span>
      <button data-testid="refresh" onClick={() => void refreshUser()}>
        refresh
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

describe('AuthContext.refreshUser', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('re-appelle authMe et met à jour le user (plan free → pro)', async () => {
    vi.mocked(authMe).mockResolvedValueOnce(_user('free'))
    renderWithProvider()
    await waitFor(() => expect(screen.getByTestId('plan')).toHaveTextContent('free'))

    vi.mocked(authMe).mockResolvedValueOnce(_user('pro'))
    await userEvent.click(screen.getByTestId('refresh'))

    await waitFor(() => expect(screen.getByTestId('plan')).toHaveTextContent('pro'))
    // 1 appel au montage + 1 appel de refresh
    expect(authMe).toHaveBeenCalledTimes(2)
  })

  it('échec de refresh (token expiré) → garde l\'état courant sans casser', async () => {
    vi.mocked(authMe).mockResolvedValueOnce(_user('pro'))
    renderWithProvider()
    await waitFor(() => expect(screen.getByTestId('plan')).toHaveTextContent('pro'))

    vi.mocked(authMe).mockRejectedValueOnce(new Error('401'))
    await userEvent.click(screen.getByTestId('refresh'))

    // L'utilisateur reste connecté avec son plan précédent (pas de déconnexion sur aléa).
    await waitFor(() => expect(authMe).toHaveBeenCalledTimes(2))
    expect(screen.getByTestId('plan')).toHaveTextContent('pro')
  })
})

describe('AuthContext.logout — purge du cache react-query (hygiène cross-tenant)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('vide le cache au logout : une donnée pré-remplie devient inaccessible', async () => {
    vi.mocked(authMe).mockResolvedValueOnce(_user('free'))
    vi.mocked(authLogout).mockResolvedValueOnce(undefined)
    const queryClient = new QueryClient()
    // Données du tenant courant en cache (clés non scopées au tenant — la fuite à fermer).
    queryClient.setQueryData(['usage', 30], { cost_usd: 42 })
    queryClient.setQueryData(['usage-reporting'], { pending_events: 7 })

    renderWithProvider(queryClient)
    await waitFor(() => expect(screen.getByTestId('plan')).toHaveTextContent('free'))
    // Pré-condition : la donnée est bien servie avant le logout (assertion non vacue).
    expect(queryClient.getQueryData(['usage', 30])).toEqual({ cost_usd: 42 })

    await userEvent.click(screen.getByTestId('logout'))

    await waitFor(() => {
      expect(queryClient.getQueryData(['usage', 30])).toBeUndefined()
    })
    expect(queryClient.getQueryData(['usage-reporting'])).toBeUndefined()
  })

  it('cas dégradé : authLogout() rejette → le cache est quand même purgé', async () => {
    vi.mocked(authMe).mockResolvedValueOnce(_user('pro'))
    vi.mocked(authLogout).mockRejectedValueOnce(new Error('réseau'))
    const queryClient = new QueryClient()
    queryClient.setQueryData(['usage', 30], { cost_usd: 99 })

    renderWithProvider(queryClient)
    await waitFor(() => expect(screen.getByTestId('plan')).toHaveTextContent('pro'))

    await userEvent.click(screen.getByTestId('logout'))

    // La purge ne dépend pas du succès réseau du logout.
    await waitFor(() => {
      expect(queryClient.getQueryData(['usage', 30])).toBeUndefined()
    })
  })
})
