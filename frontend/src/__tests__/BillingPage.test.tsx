import { StrictMode } from 'react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import BillingPage, { MAX_POLL_ATTEMPTS, POLL_INTERVAL_MS } from '../pages/BillingPage'
import { ApiError } from '../api/client'
import type { UsageReporting, UsageResponse, User } from '../types'

vi.mock('../api/usage', () => ({ getUsage: vi.fn(), getUsageReporting: vi.fn() }))
vi.mock('../api/billing', () => ({ createCheckout: vi.fn(), openPortal: vi.fn() }))
vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }))

// useSearchParams mocké : on contrôle `?status` et on observe le nettoyage du param.
const mockSetSearchParams = vi.fn()
let mockSearchParams = new URLSearchParams()
vi.mock('react-router-dom', () => ({
  useSearchParams: () => [mockSearchParams, mockSetSearchParams] as const,
}))

import { getUsage, getUsageReporting } from '../api/usage'
import { createCheckout, openPortal } from '../api/billing'
import { useAuth } from '../contexts/AuthContext'

const mockRefreshUser = vi.fn()

const _USAGE: UsageResponse = {
  period_days: 30,
  total_cost_usd: 0.1234,
  total_tokens_input: 3000,
  total_tokens_output: 1500,
  by_skill: [
    { skill: 'graham_analysis', cost_usd: 0.08, tokens_input: 2000, tokens_output: 1000, events: 2 },
    { skill: 'buffett_quality', cost_usd: 0.0434, tokens_input: 1000, tokens_output: 500, events: 1 },
  ],
  daily_cost: { '2026-06-06': 0.1234 },
}

const _REPORTING: UsageReporting = {
  reported_through: '2026-06-01T12:00:00Z',
  pending_events: 7,
}

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

function setAuth(plan: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: _user(plan),
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: mockRefreshUser,
  })
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('BillingPage', () => {
  const originalLocation = window.location

  beforeEach(() => {
    vi.clearAllMocks()
    mockSearchParams = new URLSearchParams()
    vi.mocked(getUsage).mockResolvedValue(_USAGE)
    vi.mocked(getUsageReporting).mockResolvedValue(_REPORTING)
    setAuth('free')
    // Stub de window.location : la redirection CTA assigne `href` (jsdom ne navigue pas) ;
    // `reload` espionné pour prouver la bascule du CTA SANS rechargement de page.
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...originalLocation, href: '', reload: vi.fn() },
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    })
  })

  it('affiche le titre Facturation', () => {
    render(<BillingPage />, { wrapper })
    expect(screen.getByText('Facturation')).toBeInTheDocument()
  })

  it('plan free → badge FREE et CTA « Passer à Pro »', () => {
    setAuth('free')
    render(<BillingPage />, { wrapper })
    expect(screen.getByTestId('billing-plan-badge')).toHaveTextContent('FREE')
    expect(screen.getByTestId('billing-checkout-btn')).toHaveTextContent('Passer à Pro')
    expect(screen.queryByTestId('billing-portal-btn')).not.toBeInTheDocument()
  })

  it('plan pro → badge PRO et CTA « Gérer l\'abonnement »', () => {
    setAuth('pro')
    render(<BillingPage />, { wrapper })
    expect(screen.getByTestId('billing-plan-badge')).toHaveTextContent('PRO')
    expect(screen.getByTestId('billing-portal-btn')).toHaveTextContent("Gérer l'abonnement")
    expect(screen.queryByTestId('billing-checkout-btn')).not.toBeInTheDocument()
  })

  it('affiche le squelette de chargement pendant la requête /usage', () => {
    vi.mocked(getUsage).mockReturnValue(new Promise<UsageResponse>(() => {}))
    render(<BillingPage />, { wrapper })
    expect(screen.getByTestId('billing-usage-loading')).toBeInTheDocument()
  })

  it('affiche le total et la ventilation par skill (preuve d\'acceptation)', async () => {
    render(<BillingPage />, { wrapper })
    await waitFor(() => {
      expect(screen.getByTestId('billing-total-cost')).toHaveTextContent('$0.1234')
    })
    // SkillCostPieChart rendu avec la ventilation by_skill (2 skills → graphique non vide)
    expect(screen.getByTestId('skill-cost-chart')).toBeInTheDocument()
  })

  it('affiche un message d\'erreur si /usage échoue', async () => {
    vi.mocked(getUsage).mockRejectedValue(new ApiError(500, 'boom'))
    render(<BillingPage />, { wrapper })
    await waitFor(() => {
      expect(screen.getByTestId('billing-usage-error')).toBeInTheDocument()
    })
  })

  it('clic « Passer à Pro » appelle createCheckout(pro)', async () => {
    vi.mocked(createCheckout).mockResolvedValue('https://stripe/checkout')
    const u = userEvent.setup()
    render(<BillingPage />, { wrapper })
    await u.click(screen.getByTestId('billing-checkout-btn'))
    await waitFor(() => expect(createCheckout).toHaveBeenCalledWith('pro'))
  })

  it('clic « Gérer l\'abonnement » appelle openPortal', async () => {
    setAuth('pro')
    vi.mocked(openPortal).mockResolvedValue('https://stripe/portal')
    const u = userEvent.setup()
    render(<BillingPage />, { wrapper })
    await u.click(screen.getByTestId('billing-portal-btn'))
    await waitFor(() => expect(openPortal).toHaveBeenCalledOnce())
  })

  it('facturation désactivée (503) → message sans casser la page', async () => {
    vi.mocked(createCheckout).mockRejectedValue(new ApiError(503, 'off'))
    const u = userEvent.setup()
    render(<BillingPage />, { wrapper })
    await u.click(screen.getByTestId('billing-checkout-btn'))
    await waitFor(() => {
      expect(screen.getByTestId('billing-action-error')).toHaveTextContent('Facturation indisponible')
    })
    // La page reste montée (titre toujours présent).
    expect(screen.getByText('Facturation')).toBeInTheDocument()
  })

  it('?status=success → bandeau de succès, refreshUser appelé une fois (garde StrictMode)', async () => {
    mockSearchParams = new URLSearchParams('status=success')
    // StrictMode double-invoque l'effet en dev : le garde-fou useRef doit garantir un seul refreshUser.
    render(
      <StrictMode>
        <BillingPage />
      </StrictMode>,
      { wrapper },
    )
    await waitFor(() => {
      expect(screen.getByTestId('billing-success-banner')).toBeInTheDocument()
    })
    expect(mockRefreshUser).toHaveBeenCalledOnce()
    expect(mockSetSearchParams).toHaveBeenCalledWith({}, { replace: true })
    expect(screen.queryByTestId('billing-cancel-banner')).not.toBeInTheDocument()
  })

  it('?status=cancel → message d\'annulation, refreshUser NON appelé', async () => {
    mockSearchParams = new URLSearchParams('status=cancel')
    render(<BillingPage />, { wrapper })
    await waitFor(() => {
      expect(screen.getByTestId('billing-cancel-banner')).toBeInTheDocument()
    })
    expect(mockRefreshUser).not.toHaveBeenCalled()
    expect(mockSetSearchParams).toHaveBeenCalledWith({}, { replace: true })
    expect(screen.queryByTestId('billing-success-banner')).not.toBeInTheDocument()
  })

  it('sans ?status → aucun bandeau, refreshUser non appelé, param non touché', () => {
    render(<BillingPage />, { wrapper })
    expect(screen.queryByTestId('billing-success-banner')).not.toBeInTheDocument()
    expect(screen.queryByTestId('billing-cancel-banner')).not.toBeInTheDocument()
    expect(mockRefreshUser).not.toHaveBeenCalled()
    expect(mockSetSearchParams).not.toHaveBeenCalled()
  })

  it('section « à l\'usage » : affiche les unités en attente et la date de report (preuve d\'acceptation)', async () => {
    render(<BillingPage />, { wrapper })
    await waitFor(() => {
      expect(screen.getByTestId('billing-usage-reporting')).toBeInTheDocument()
    })
    expect(screen.getByTestId('billing-reporting-pending')).toHaveTextContent('7')
    // reported_through formaté en fr-CA (YYYY-MM-DD) — preuve : K rapportées jusqu'au <date>.
    expect(screen.getByTestId('billing-reporting-through')).toHaveTextContent('2026-06-01')
  })

  it('section « à l\'usage » sans report (reported_through null) → libellé neutre', async () => {
    vi.mocked(getUsageReporting).mockResolvedValue({ reported_through: null, pending_events: 42 })
    render(<BillingPage />, { wrapper })
    await waitFor(() => {
      expect(screen.getByTestId('billing-reporting-pending')).toHaveTextContent('42')
    })
    expect(screen.getByTestId('billing-reporting-through')).toHaveTextContent('Aucun report')
  })

  it('section « à l\'usage » : squelette pendant le chargement', () => {
    vi.mocked(getUsageReporting).mockReturnValue(new Promise<UsageReporting>(() => {}))
    render(<BillingPage />, { wrapper })
    expect(screen.getByTestId('billing-reporting-loading')).toBeInTheDocument()
  })

  it('section « à l\'usage » : message neutre si la requête échoue (sans casser la page)', async () => {
    vi.mocked(getUsageReporting).mockRejectedValue(new ApiError(503, 'off'))
    render(<BillingPage />, { wrapper })
    await waitFor(() => {
      expect(screen.getByTestId('billing-reporting-error')).toBeInTheDocument()
    })
    expect(screen.getByText('Facturation')).toBeInTheDocument()
  })

  it('après refresh renvoyant plan pro, le CTA bascule checkout → portail', async () => {
    // Au montage : plan free → CTA checkout. Le retour de checkout déclenche refreshUser ;
    // on simule le plan re-synchronisé en faisant repointer useAuth sur plan='pro'.
    mockSearchParams = new URLSearchParams('status=success')
    const { rerender } = render(<BillingPage />, { wrapper })
    expect(screen.getByTestId('billing-checkout-btn')).toBeInTheDocument()
    await waitFor(() => expect(mockRefreshUser).toHaveBeenCalledOnce())

    setAuth('pro')
    rerender(<BillingPage />)
    expect(screen.getByTestId('billing-portal-btn')).toBeInTheDocument()
    expect(screen.queryByTestId('billing-checkout-btn')).not.toBeInTheDocument()
  })

  it('?status=success → polling resync le plan ; le CTA bascule checkout→portail sans reload, puis s\'arrête (preuve d\'acceptation)', async () => {
    vi.useFakeTimers()
    mockSearchParams = new URLSearchParams('status=success')
    setAuth('free')
    const { rerender } = render(<BillingPage />, { wrapper })

    // Refresh ponctuel du retour de checkout (effet existant).
    expect(mockRefreshUser).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('billing-checkout-btn')).toBeInTheDocument()

    // 1ᵉʳ tick de polling : le plan est toujours free → re-sync.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    })
    expect(mockRefreshUser).toHaveBeenCalledTimes(2)

    // Le webhook a synchronisé `tenants.plan` → useAuth repointe sur 'pro' (changement RÉEL).
    setAuth('pro')
    rerender(<BillingPage />)
    expect(screen.getByTestId('billing-portal-btn')).toBeInTheDocument()
    expect(screen.queryByTestId('billing-checkout-btn')).not.toBeInTheDocument()

    // Le polling s'est arrêté : des ticks supplémentaires ne re-synchronisent plus.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 5)
    })
    expect(mockRefreshUser).toHaveBeenCalledTimes(2)
    expect(window.location.reload).not.toHaveBeenCalled()
  })

  it('?status=success mais plan jamais synchronisé → polling borné (s\'arrête au plafond, pas de boucle infinie)', async () => {
    vi.useFakeTimers()
    mockSearchParams = new URLSearchParams('status=success')
    setAuth('free')
    render(<BillingPage />, { wrapper })
    expect(mockRefreshUser).toHaveBeenCalledTimes(1) // refresh ponctuel

    // Bien au-delà du plafond (MAX_POLL_ATTEMPTS × intervalle).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * (MAX_POLL_ATTEMPTS + 20))
    })
    // 1 (ponctuel) + MAX_POLL_ATTEMPTS (plafond) — jamais davantage.
    const cappedCalls = 1 + MAX_POLL_ATTEMPTS
    expect(mockRefreshUser).toHaveBeenCalledTimes(cappedCalls)

    // Prouve la borne : un nouveau lot de temps ne déclenche plus aucun refresh.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 20)
    })
    expect(mockRefreshUser).toHaveBeenCalledTimes(cappedCalls)
  })

  it('?status=success → le polling est nettoyé au démontage (plus de resync après unmount)', async () => {
    vi.useFakeTimers()
    mockSearchParams = new URLSearchParams('status=success')
    setAuth('free')
    const { unmount } = render(<BillingPage />, { wrapper })
    expect(mockRefreshUser).toHaveBeenCalledTimes(1)

    unmount()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * (MAX_POLL_ATTEMPTS + 1))
    })
    expect(mockRefreshUser).toHaveBeenCalledTimes(1) // aucun tick après démontage
  })

  it('sans ?status=success → aucun polling (refreshUser jamais appelé même après plusieurs intervalles)', async () => {
    vi.useFakeTimers()
    // mockSearchParams reste vide (réinitialisé en beforeEach).
    setAuth('free')
    render(<BillingPage />, { wrapper })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * (MAX_POLL_ATTEMPTS + 1))
    })
    expect(mockRefreshUser).not.toHaveBeenCalled()
  })
})
