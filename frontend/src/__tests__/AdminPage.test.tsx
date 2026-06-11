import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AdminPage from '../pages/AdminPage'
import * as adminApi from '../api/admin'
import { ApiError } from '../api/client'
import type { ApiKey, AuditLogEntry, TenantAdminEntry } from '../types'

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

const makeAudit = (overrides: Partial<AuditLogEntry> = {}): AuditLogEntry => ({
  id: '11110000-0000-0000-0000-000000000001',
  tenant_id: 'deadbeef-1111-2222-3333-444455556666',
  user_id: null,
  action: 'watchlist.add',
  cible_type: 'watchlist',
  cible_id: 'BNS.TO',
  metadata: {},
  created_at: '2026-06-01T12:00:00Z',
  ...overrides,
})

const makeTenant = (overrides: Partial<TenantAdminEntry> = {}): TenantAdminEntry => ({
  id: 'tttt0000-0000-0000-0000-000000000001',
  name: 'Acme',
  slug: 'acme',
  plan: 'pro',
  stripe_customer_id: 'cus_abc123def456',
  created_at: '2026-05-15T09:00:00Z',
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
    vi.mocked(adminApi.getAuditLog).mockResolvedValue([])
    vi.mocked(adminApi.listTenants).mockResolvedValue([])
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

  describe('Journal d\'audit', () => {
    it('rend une ligne par entrée d\'audit mockée', async () => {
      vi.mocked(adminApi.getAuditLog).mockResolvedValue([
        makeAudit({ id: 'audit-1', action: 'api_key.create', cible_type: 'api_key' }),
        makeAudit({ id: 'audit-2', action: 'watchlist.add', cible_type: 'watchlist' }),
      ])
      wrap(<AdminPage />)
      await waitFor(() => {
        expect(screen.getByTestId('audit-log-table')).toBeInTheDocument()
      })
      expect(screen.getByTestId('audit-row-audit-1')).toBeInTheDocument()
      expect(screen.getByTestId('audit-row-audit-2')).toBeInTheDocument()
    })

    it('filtre par action réduit les lignes affichées', async () => {
      vi.mocked(adminApi.getAuditLog).mockResolvedValue([
        makeAudit({ id: 'audit-1', action: 'api_key.create', cible_type: 'api_key' }),
        makeAudit({ id: 'audit-2', action: 'watchlist.add', cible_type: 'watchlist' }),
      ])
      wrap(<AdminPage />)
      await screen.findByTestId('audit-row-audit-1')

      await userEvent.selectOptions(
        screen.getByTestId('audit-filter-action'),
        'api_key.create',
      )

      expect(screen.getByTestId('audit-row-audit-1')).toBeInTheDocument()
      expect(screen.queryByTestId('audit-row-audit-2')).not.toBeInTheDocument()
    })

    it('combine les filtres action ET type de cible (aucune correspondance → no-match)', async () => {
      vi.mocked(adminApi.getAuditLog).mockResolvedValue([
        makeAudit({ id: 'audit-1', action: 'api_key.create', cible_type: 'api_key' }),
        makeAudit({ id: 'audit-2', action: 'watchlist.add', cible_type: 'watchlist' }),
      ])
      wrap(<AdminPage />)
      await screen.findByTestId('audit-row-audit-1')

      // action de audit-1 + type de cible de audit-2 → combinaison sans correspondance
      await userEvent.selectOptions(screen.getByTestId('audit-filter-action'), 'api_key.create')
      await userEvent.selectOptions(screen.getByTestId('audit-filter-cible-type'), 'watchlist')

      expect(screen.queryByTestId('audit-row-audit-1')).not.toBeInTheDocument()
      expect(screen.queryByTestId('audit-row-audit-2')).not.toBeInTheDocument()
      expect(screen.getByTestId('audit-log-no-match')).toBeInTheDocument()
    })

    it('affiche le squelette pendant le chargement', () => {
      vi.mocked(adminApi.getAuditLog).mockReturnValue(new Promise<AuditLogEntry[]>(() => {}))
      wrap(<AdminPage />)
      expect(screen.getByTestId('audit-log-loading')).toBeInTheDocument()
    })

    it('affiche un message d\'erreur si getAuditLog échoue', async () => {
      vi.mocked(adminApi.getAuditLog).mockRejectedValue(new Error('Panne audit'))
      wrap(<AdminPage />)
      await waitFor(() => {
        expect(screen.getByTestId('audit-log-error')).toHaveTextContent('Panne audit')
      })
    })

    it('affiche un message neutre quand la liste est vide', async () => {
      vi.mocked(adminApi.getAuditLog).mockResolvedValue([])
      wrap(<AdminPage />)
      await waitFor(() => {
        expect(screen.getByTestId('audit-log-empty')).toBeInTheDocument()
      })
      expect(screen.queryByTestId('audit-log-table')).not.toBeInTheDocument()
    })
  })

  describe('Tenants', () => {
    it('rend une ligne par tenant mocké avec customer Stripe tronqué', async () => {
      vi.mocked(adminApi.listTenants).mockResolvedValue([
        makeTenant({ id: 'tenant-1', name: 'Acme', stripe_customer_id: 'cus_abc123def456ghi' }),
        makeTenant({ id: 'tenant-2', name: 'Globex', plan: 'free', stripe_customer_id: null }),
      ])
      wrap(<AdminPage />)
      await waitFor(() => {
        expect(screen.getByTestId('admin-tenants-table')).toBeInTheDocument()
      })
      expect(screen.getByTestId('admin-tenants-row-tenant-1')).toBeInTheDocument()
      expect(screen.getByTestId('admin-tenants-row-tenant-2')).toBeInTheDocument()
      expect(screen.getByText('cus_abc123def4…')).toBeInTheDocument()
      // tenant sans abonnement → tiret
      expect(screen.getByTestId('admin-tenants-row-tenant-2')).toHaveTextContent('—')
    })

    it('affiche le squelette pendant le chargement', () => {
      vi.mocked(adminApi.listTenants).mockReturnValue(new Promise<TenantAdminEntry[]>(() => {}))
      wrap(<AdminPage />)
      expect(screen.getByTestId('admin-tenants-loading')).toBeInTheDocument()
    })

    it('affiche un message d\'erreur si listTenants échoue', async () => {
      vi.mocked(adminApi.listTenants).mockRejectedValue(new Error('Panne tenants'))
      wrap(<AdminPage />)
      await waitFor(() => {
        expect(screen.getByTestId('admin-tenants-error')).toHaveTextContent('Panne tenants')
      })
    })

    it('affiche "Accès refusé" si listTenants lance une ApiError 403', async () => {
      vi.mocked(adminApi.listTenants).mockRejectedValue(new ApiError(403, 'Forbidden'))
      wrap(<AdminPage />)
      await waitFor(() => {
        expect(screen.getByTestId('admin-tenants-error')).toHaveTextContent('Accès refusé')
      })
    })

    it('affiche un message neutre quand la liste est vide', async () => {
      vi.mocked(adminApi.listTenants).mockResolvedValue([])
      wrap(<AdminPage />)
      await waitFor(() => {
        expect(screen.getByTestId('admin-tenants-empty')).toBeInTheDocument()
      })
      expect(screen.queryByTestId('admin-tenants-table')).not.toBeInTheDocument()
    })
  })
})
