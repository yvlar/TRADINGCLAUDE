import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider, useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

vi.mock('../api/auth', () => ({
  authMe: vi.fn(),
  authLogin: vi.fn(),
  authLogout: vi.fn(),
  AuthApiError: class extends Error {},
}))

import { authMe } from '../api/auth'

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
  const { user, refreshUser } = useAuth()
  return (
    <div>
      <span data-testid="plan">{user?.plan ?? 'none'}</span>
      <button data-testid="refresh" onClick={() => void refreshUser()}>
        refresh
      </button>
    </div>
  )
}

function renderWithProvider() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    </MemoryRouter>,
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
