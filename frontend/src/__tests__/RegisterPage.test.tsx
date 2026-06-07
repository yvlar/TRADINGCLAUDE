import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from '../contexts/AuthContext'
import RegisterPage from '../pages/RegisterPage'

vi.mock('../api/auth', () => ({
  authMe: vi.fn().mockRejectedValue(new Error('401')),
  authRegister: vi.fn(),
  authLogin: vi.fn(),
  authLogout: vi.fn().mockResolvedValue(undefined),
}))

import * as authApi from '../api/auth'

function wrap(ui: React.ReactElement) {
  return render(
    <MemoryRouter initialEntries={['/register']}>
      <AuthProvider>
        <Routes>
          <Route path="/register" element={ui} />
          <Route path="/login" element={<div>Page login</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.mocked(authApi.authMe).mockRejectedValue(new Error('401'))
  vi.mocked(authApi.authRegister).mockReset()
})

describe('RegisterPage', () => {
  it('rend le formulaire email, mot de passe et bouton', async () => {
    wrap(<RegisterPage />)
    await waitFor(() => {
      expect(screen.getByTestId('email-input')).toBeInTheDocument()
    })
    expect(screen.getByTestId('password-input')).toBeInTheDocument()
    expect(screen.getByTestId('submit-button')).toBeInTheDocument()
  })

  it('affiche une erreur si les champs sont vides', async () => {
    wrap(<RegisterPage />)
    await waitFor(() => expect(screen.getByTestId('submit-button')).toBeInTheDocument())
    await userEvent.click(screen.getByTestId('submit-button'))
    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument()
    })
  })

  it('affiche l\'indicateur de force du mot de passe', async () => {
    wrap(<RegisterPage />)
    await waitFor(() => expect(screen.getByTestId('password-input')).toBeInTheDocument())
    await userEvent.type(screen.getByTestId('password-input'), 'abc')
    await waitFor(() => {
      expect(screen.getByTestId('password-strength')).toBeInTheDocument()
    })
  })

  it('appelle authRegister et redirige vers /login après inscription', async () => {
    vi.mocked(authApi.authRegister).mockResolvedValue({
      user: { id: 'uuid-1', email: 'new@test.com', role: 'reader', tenant_id: 'tenant-1', tenant_name: 'Acme', plan: 'free', created_at: '2026-01-01T00:00:00Z' },
      message: 'Compte créé',
    })

    wrap(<RegisterPage />)
    await waitFor(() => expect(screen.getByTestId('email-input')).toBeInTheDocument())
    await userEvent.type(screen.getByTestId('email-input'), 'new@test.com')
    await userEvent.type(screen.getByTestId('password-input'), 'MonMotDePasse123!')
    await userEvent.click(screen.getByTestId('submit-button'))

    await waitFor(() => {
      expect(authApi.authRegister).toHaveBeenCalledWith({
        email: 'new@test.com',
        password: 'MonMotDePasse123!',
      })
    })
    await waitFor(() => {
      expect(screen.getByText('Page login')).toBeInTheDocument()
    })
  })

  it('affiche une erreur si authRegister rejette', async () => {
    vi.mocked(authApi.authRegister).mockRejectedValue(new Error('Un compte avec cet email existe déjà'))

    wrap(<RegisterPage />)
    await waitFor(() => expect(screen.getByTestId('email-input')).toBeInTheDocument())
    await userEvent.type(screen.getByTestId('email-input'), 'dup@test.com')
    await userEvent.type(screen.getByTestId('password-input'), 'MonMotDePasse123!')
    await userEvent.click(screen.getByTestId('submit-button'))

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toHaveTextContent('Un compte avec cet email existe déjà')
    })
  })

  it('affiche le lien vers la page de connexion', async () => {
    wrap(<RegisterPage />)
    await waitFor(() => expect(screen.getByTestId('login-link')).toBeInTheDocument())
  })
})
