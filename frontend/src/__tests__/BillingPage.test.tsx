import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import BillingPage from '../pages/BillingPage'
import { ApiError } from '../api/client'
import type { UsageResponse, User } from '../types'

vi.mock('../api/usage', () => ({ getUsage: vi.fn() }))
vi.mock('../api/billing', () => ({ createCheckout: vi.fn(), openPortal: vi.fn() }))
vi.mock('../contexts/AuthContext', () => ({ useAuth: vi.fn() }))

import { getUsage } from '../api/usage'
import { createCheckout, openPortal } from '../api/billing'
import { useAuth } from '../contexts/AuthContext'

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
    vi.mocked(getUsage).mockResolvedValue(_USAGE)
    setAuth('free')
    // Stub de window.location : la redirection CTA assigne `href` (jsdom ne navigue pas).
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...originalLocation, href: '' },
    })
  })

  afterEach(() => {
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
})
