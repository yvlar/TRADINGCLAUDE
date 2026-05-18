import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AdminPage from '../pages/AdminPage'
import * as adminApi from '../api/admin'
import { ApiError } from '../api/client'
import type { ApiKey } from '../types'

vi.mock('../api/admin')

const makeKey = (overrides: Partial<ApiKey> = {}): ApiKey => ({
  id: 'aaaabbbb-1111-2222-3333-ccccddddeeee',
  name: 'CI pipeline',
  role: 'user',
  created_at: '2026-05-01T10:00:00Z',
  last_used_at: null,
  is_active: true,
  ...overrides,
})

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('AdminPage', () => {
  beforeEach(() => {
    vi.mocked(adminApi.listApiKeys).mockResolvedValue([makeKey()])
    vi.mocked(adminApi.createApiKey).mockResolvedValue({ key: 'sk-test-generatedkey', id: 'new-id' })
    vi.mocked(adminApi.revokeApiKey).mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('affiche le titre "Administration"', async () => {
    wrap(<AdminPage />)
    expect(screen.getByText(/Administration/)).toBeInTheDocument()
  })

  it('affiche la liste des clés existantes avec data-testid par clé', async () => {
    wrap(<AdminPage />)
    await waitFor(() => {
      expect(
        screen.getByTestId('key-row-aaaabbbb-1111-2222-3333-ccccddddeeee'),
      ).toBeInTheDocument()
    })
    expect(screen.getByText('CI pipeline')).toBeInTheDocument()
  })

  it('formulaire création appelle createApiKey avec le nom saisi', async () => {
    wrap(<AdminPage />)
    const input = screen.getByLabelText('Nom de la clé')
    await userEvent.type(input, 'Ma clé de test')
    await userEvent.click(screen.getByText('Créer'))
    await waitFor(() => {
      expect(adminApi.createApiKey).toHaveBeenCalled()
      const firstArg = vi.mocked(adminApi.createApiKey).mock.calls[0][0]
      expect(firstArg).toEqual({ name: 'Ma clé de test', role: 'user' })
    })
  })

  it('affiche la clé générée après création (data-testid="new-key-display")', async () => {
    wrap(<AdminPage />)
    const input = screen.getByLabelText('Nom de la clé')
    await userEvent.type(input, 'Nouvelle')
    await userEvent.click(screen.getByText('Créer'))
    await waitFor(() => {
      expect(screen.getByTestId('new-key-display')).toHaveTextContent('sk-test-generatedkey')
    })
  })

  it('affiche "Accès refusé" si listApiKeys lance une ApiError 403', async () => {
    vi.mocked(adminApi.listApiKeys).mockRejectedValue(new ApiError(403, 'Forbidden'))
    wrap(<AdminPage />)
    await waitFor(() => {
      expect(
        screen.getByText(/Accès refusé — vous devez être administrateur/),
      ).toBeInTheDocument()
    })
  })

  it('clic Révoquer appelle revokeApiKey avec le bon id', async () => {
    wrap(<AdminPage />)
    const btn = await screen.findByText('Révoquer')
    await userEvent.click(btn)
    await waitFor(() => {
      expect(adminApi.revokeApiKey).toHaveBeenCalled()
      const firstArg = vi.mocked(adminApi.revokeApiKey).mock.calls[0][0]
      expect(firstArg).toBe('aaaabbbb-1111-2222-3333-ccccddddeeee')
    })
  })
})
