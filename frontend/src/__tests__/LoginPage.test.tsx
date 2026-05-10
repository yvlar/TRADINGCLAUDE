import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider, useAuth } from '../contexts/AuthContext'
import { ProtectedRoute } from '../components/ProtectedRoute'
import LoginPage from '../pages/LoginPage'

function wrap(ui: React.ReactElement, { initialEntries = ['/login'] } = {}) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>{ui}</AuthProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  localStorage.clear()
})

describe('LoginPage', () => {
  it('rend le formulaire avec input Clé API et bouton Se connecter', () => {
    wrap(<LoginPage />)
    expect(screen.getByLabelText('Clé API')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Se connecter' })).toBeInTheDocument()
  })

  it('stocke le token dans localStorage après soumission valide', async () => {
    wrap(<Routes><Route path="/login" element={<LoginPage />} /><Route path="/" element={<div>Accueil</div>} /></Routes>)
    const input = screen.getByLabelText('Clé API')
    await userEvent.type(input, 'ma-cle-secrete')
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }))
    await waitFor(() => {
      expect(localStorage.getItem('api_token')).toBe('ma-cle-secrete')
    })
  })

  it('affiche le message d\'erreur si la clé est vide', async () => {
    wrap(<LoginPage />)
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }))
    await waitFor(() => {
      expect(screen.getByText('La clé API est requise')).toBeInTheDocument()
    })
  })
})

describe('ProtectedRoute', () => {
  it('redirige vers /login si non authentifié', () => {
    render(
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
      </MemoryRouter>,
    )
    expect(screen.getByText('Page login')).toBeInTheDocument()
    expect(screen.queryByText('Contenu protégé')).not.toBeInTheDocument()
  })
})

describe('useAuth logout', () => {
  it('efface le token localStorage après logout', async () => {
    localStorage.setItem('api_token', 'token-existant')

    function LogoutButton() {
      const { logout } = useAuth()
      return <button onClick={logout}>Déconnexion</button>
    }

    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<LogoutButton />} />
            <Route path="/login" element={<div>Login</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Déconnexion' }))
    await waitFor(() => {
      expect(localStorage.getItem('api_token')).toBeNull()
    })
  })
})
