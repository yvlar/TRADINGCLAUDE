import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from '../App'
import { authMe } from '../api/auth'
import type { User } from '../types'

vi.mock('../api/auth', () => ({
  authMe: vi.fn().mockRejectedValue(new Error('401')),
  authLogin: vi.fn(),
  authLogout: vi.fn().mockResolvedValue(undefined),
}))

// Le header rend QuotaBadge (useQuery /quota) une fois authentifié : on neutralise le fetch.
vi.mock('../api/quota', () => ({ getQuota: vi.fn().mockRejectedValue(new Error('401')) }))

// Le QueryClientProvider vit dans main.tsx (hors de <App/>) : on le fournit ici comme en prod.
function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  )
}

describe('App — shell pleine largeur', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(authMe).mockRejectedValue(new Error('401'))
  })

  it('rend le conteneur principal avec le shell fluide large', async () => {
    renderApp()
    const main = await screen.findByTestId('app-main')
    expect(main.className).toContain('max-w-shell')
    expect(main.className).toContain('mx-auto')
    expect(main.className).not.toContain('max-w-5xl')
  })

  it('affiche le titre de l’application', async () => {
    renderApp()
    expect(await screen.findByText('Copilote Financier IA')).toBeInTheDocument()
  })

  it('affiche le nom du tenant dans le header une fois authentifié (Sprint 169)', async () => {
    const user: User = {
      id: 'u1',
      email: 'yves@test.com',
      role: 'reader',
      tenant_id: 't1',
      tenant_name: 'Espace Démo',
      plan: 'free',
      created_at: '2026-01-01T00:00:00Z',
    }
    vi.mocked(authMe).mockResolvedValue(user)

    renderApp()
    const badge = await screen.findByTestId('tenant-badge')
    expect(badge).toHaveTextContent('Espace Démo')
  })
})
