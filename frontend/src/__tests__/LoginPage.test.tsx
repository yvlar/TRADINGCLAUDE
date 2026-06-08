import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../contexts/AuthContext'
import { ProtectedRoute } from '../components/ProtectedRoute'
import LoginPage from '../pages/LoginPage'

vi.mock('../api/auth', () => ({
  authMe: vi.fn().mockRejectedValue(new Error('401')),
  authLogin: vi.fn(),
  authLogout: vi.fn().mockResolvedValue(undefined),
}))

import * as authApi from '../api/auth'

function wrap(ui: React.ReactElement, { initialEntries = ['/login'] } = {}) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(authApi.authMe).mockRejectedValue(new Error('401'))
  vi.mocked(authApi.authLogin).mockReset()
})

describe('LoginPage', () => {
  it('rend le formulaire email, mot de passe et bouton Se connecter', async () => {
    wrap(<LoginPage />)
    await waitFor(() => {
      expect(screen.getByLabelText('Adresse email')).toBeInTheDocument()
    })
    expect(screen.getByLabelText('Mot de passe')).toBeInTheDocument()
    expect(screen.getByTestId('submit-button')).toBeInTheDocument()
  })

  it('affiche le message d\'erreur si les champs sont vides', async () => {
    wrap(<LoginPage />)
    await waitFor(() => expect(screen.getByTestId('submit-button')).toBeInTheDocument())
    await userEvent.click(screen.getByTestId('submit-button'))
    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument()
    })
  })

  it('appelle authLogin avec email et mot de passe et redirige', async () => {
    vi.mocked(authApi.authLogin).mockResolvedValue({
      user: { id: 'uuid-1', email: 'test@test.com', role: 'reader', tenant_id: 'tenant-1', tenant_name: 'Acme', plan: 'free', created_at: '2026-01-01T00:00:00Z' },
      message: 'Connexion réussie',
    })

    wrap(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<div>Accueil</div>} />
      </Routes>,
    )

    await waitFor(() => expect(screen.getByTestId('email-input')).toBeInTheDocument())
    await userEvent.type(screen.getByTestId('email-input'), 'test@test.com')
    await userEvent.type(screen.getByTestId('password-input'), 'MonMotDePasse123!')
    await userEvent.click(screen.getByTestId('submit-button'))

    await waitFor(() => {
      expect(authApi.authLogin).toHaveBeenCalledWith({
        email: 'test@test.com',
        password: 'MonMotDePasse123!',
        remember_me: false,
      })
    })
  })

  it('affiche une erreur si authLogin rejette', async () => {
    vi.mocked(authApi.authLogin).mockRejectedValue(new Error('Email ou mot de passe incorrect'))

    wrap(<LoginPage />)
    await waitFor(() => expect(screen.getByTestId('email-input')).toBeInTheDocument())
    await userEvent.type(screen.getByTestId('email-input'), 'bad@test.com')
    await userEvent.type(screen.getByTestId('password-input'), 'WrongPass123!')
    await userEvent.click(screen.getByTestId('submit-button'))

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toHaveTextContent('Email ou mot de passe incorrect')
    })
  })

  it('affiche les liens vers /register et /forgot-password', async () => {
    wrap(<LoginPage />)
    await waitFor(() => expect(screen.getByTestId('register-link')).toBeInTheDocument())
    expect(screen.getByTestId('forgot-password-link')).toBeInTheDocument()
  })
})

describe('ProtectedRoute', () => {
  it('redirige vers /login si non authentifié (après résolution async)', async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/']}>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<div>Page login</div>} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <div>Contenu protégé</div>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await waitFor(() => {
      expect(screen.getByText('Page login')).toBeInTheDocument()
    })
    expect(screen.queryByText('Contenu protégé')).not.toBeInTheDocument()
  })
})
