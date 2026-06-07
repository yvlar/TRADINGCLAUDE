import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'
import { authMe } from '../api/auth'
import type { User } from '../types'

vi.mock('../api/auth', () => ({
  authMe: vi.fn().mockRejectedValue(new Error('401')),
  authLogin: vi.fn(),
  authLogout: vi.fn().mockResolvedValue(undefined),
}))

describe('App — shell pleine largeur', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(authMe).mockRejectedValue(new Error('401'))
  })

  it('rend le conteneur principal avec le shell fluide large', async () => {
    render(<App />)
    const main = await screen.findByTestId('app-main')
    expect(main.className).toContain('max-w-shell')
    expect(main.className).toContain('mx-auto')
    expect(main.className).not.toContain('max-w-5xl')
  })

  it('affiche le titre de l’application', async () => {
    render(<App />)
    expect(await screen.findByText('Copilote Financier IA')).toBeInTheDocument()
  })

  it('affiche le nom du tenant dans le header une fois authentifié (Sprint 169)', async () => {
    const user: User = {
      id: 'u1',
      email: 'yves@test.com',
      role: 'reader',
      tenant_id: 't1',
      tenant_name: 'Espace Démo',
      created_at: '2026-01-01T00:00:00Z',
    }
    vi.mocked(authMe).mockResolvedValue(user)

    render(<App />)
    const badge = await screen.findByTestId('tenant-badge')
    expect(badge).toHaveTextContent('Espace Démo')
  })
})
