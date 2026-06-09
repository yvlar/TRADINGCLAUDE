import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '../contexts/AuthContext'
import BillingPage from '../pages/BillingPage'
import type { AuthResponse, UsageReporting, UsageResponse, User } from '../types'

// On monte la VRAIE chaîne AuthProvider → BillingPage (pas un useAuth mocké) pour que `logout`
// exécute réellement `queryClient.clear()` (S190) : c'est ce flux qu'on verrouille au niveau
// page. Seuls les appels réseau sous-jacents sont mockés.
vi.mock('../api/auth', () => ({
  authMe: vi.fn(),
  authLogin: vi.fn(),
  authLogout: vi.fn(),
  AuthApiError: class extends Error {},
}))
vi.mock('../api/usage', () => ({ getUsage: vi.fn(), getUsageReporting: vi.fn() }))
vi.mock('../api/billing', () => ({ createCheckout: vi.fn(), openPortal: vi.fn() }))

import { authMe, authLogin, authLogout } from '../api/auth'
import { getUsage, getUsageReporting } from '../api/usage'

// Deux locataires distincts : la bascule A (free) → B (pro) doit refléter B et ne laisser
// survivre aucune donnée mise en cache sous A.
function _user(tenantId: string, plan: string): User {
  return {
    id: `u-${tenantId}`,
    email: `${tenantId}@t.com`,
    role: 'reader',
    tenant_id: tenantId,
    tenant_name: `Espace ${tenantId}`,
    plan,
    created_at: '2026-01-01T00:00:00',
  }
}

function _authResponse(user: User): AuthResponse {
  return { user, message: 'ok' }
}

// Conso « de A » VALIDE (BillingPage la rend après pré-remplissage) et distincte (total 1.2345)
// pour prouver qu'elle est affichée avant la bascule puis disparaît de la vue de B.
const _USAGE_A: UsageResponse = {
  period_days: 30,
  total_cost_usd: 1.2345,
  total_tokens_input: 9000,
  total_tokens_output: 4000,
  by_skill: [
    { skill: 'graham_analysis', cost_usd: 1.2345, tokens_input: 9000, tokens_output: 4000, events: 3 },
  ],
  daily_cost: { '2026-06-01': 1.2345 },
}

const _REPORTING_A: UsageReporting = {
  reported_through: '2026-06-01T12:00:00Z',
  pending_events: 99,
}

// Harness : expose login/logout du VRAI contexte + un témoin de tenant pour séquencer le flux,
// et rend BillingPage pour observer la bascule du CTA au niveau page.
function Harness() {
  const { user, login, logout } = useAuth()
  return (
    <>
      <span data-testid="current-tenant">{user?.tenant_id ?? 'none'}</span>
      <button data-testid="do-login" onClick={() => void login({ email: 'x@y.com', password: 'pw' })}>
        login
      </button>
      <button data-testid="do-logout" onClick={() => void logout()}>
        logout
      </button>
      <BillingPage />
    </>
  )
}

function renderPage(queryClient: QueryClient) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <Harness />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('BillingPage — bascule CTA cross-tenant (login A free → logout → login B pro)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // /usage et /usage/reporting ne résolvent jamais : BillingPage reste en chargement et ne
    // re-peuple PAS le cache de lui-même → les clés purgées restent `undefined` de façon
    // déterministe (idiome BillingPage.test.tsx pour le skeleton).
    vi.mocked(getUsage).mockReturnValue(new Promise<UsageResponse>(() => {}))
    vi.mocked(getUsageReporting).mockReturnValue(new Promise<UsageReporting>(() => {}))
    // Pas de session au montage → user=null avant le login A ; rejet persistant (aucun refresh
    // dans ce flux sans `?status`, mais robuste si l'un survenait).
    vi.mocked(authMe).mockRejectedValue(new Error('401'))
    vi.mocked(authLogout).mockResolvedValue(undefined)
  })

  it('le CTA reflète le plan pro de B et aucune conso/donnée de A ne survit à la bascule', async () => {
    vi.mocked(authLogin)
      .mockResolvedValueOnce(_authResponse(_user('tenant-a', 'free')))
      .mockResolvedValueOnce(_authResponse(_user('tenant-b', 'pro')))
    // QueryClient PARTAGÉ provider↔assertions (même instance) : sinon le test ne verrouille pas
    // le flux réel de purge.
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    renderPage(queryClient)
    await waitFor(() => expect(screen.getByTestId('current-tenant')).toHaveTextContent('none'))

    // (a) login tenant A (free) → CTA checkout
    await userEvent.click(screen.getByTestId('do-login'))
    await waitFor(() => expect(screen.getByTestId('current-tenant')).toHaveTextContent('tenant-a'))
    expect(screen.getByTestId('billing-checkout-btn')).toBeInTheDocument()

    // (b) conso « de A » en cache sous des clés NON scopées au tenant (la fuite à fermer)
    queryClient.setQueryData(['usage', 30], _USAGE_A)
    queryClient.setQueryData(['usage-reporting'], _REPORTING_A)
    // Pré-condition non vacue : la donnée de A est en cache ET affichée sur la page avant bascule.
    expect(queryClient.getQueryData(['usage', 30])).toEqual(_USAGE_A)
    expect(queryClient.getQueryData(['usage-reporting'])).toEqual(_REPORTING_A)
    await waitFor(() => expect(screen.getByTestId('billing-total-cost')).toHaveTextContent('$1.2345'))

    // (c) logout (purge le cache react-query via queryClient.clear())
    await userEvent.click(screen.getByTestId('do-logout'))
    await waitFor(() => expect(screen.getByTestId('current-tenant')).toHaveTextContent('none'))

    // (d) login tenant B (pro) dans le même onglet, sans rechargement de page
    await userEvent.click(screen.getByTestId('do-login'))
    await waitFor(() => expect(screen.getByTestId('current-tenant')).toHaveTextContent('tenant-b'))

    // (e) le CTA bascule sur le plan de B (portail, pas checkout), badge PRO — sans rechargement :
    // même arbre monté, le CTA flippe depuis l'état du contexte, aucun remount/reload.
    expect(screen.getByTestId('billing-portal-btn')).toBeInTheDocument()
    expect(screen.queryByTestId('billing-checkout-btn')).not.toBeInTheDocument()
    expect(screen.getByTestId('billing-plan-badge')).toHaveTextContent('PRO')

    // (f) aucune donnée de A ne survit : clés purgées → `undefined` (le re-fetch de BillingPage ne
    // résout jamais). Échouerait si `queryClient.clear()` était retiré du logout (la conso de A
    // pré-remplie en (b) survivrait → assertions `undefined` rouges).
    expect(queryClient.getQueryData(['usage', 30])).toBeUndefined()
    expect(queryClient.getQueryData(['usage-reporting'])).toBeUndefined()

    // (g) la page n'affiche plus la conso de l'ancien tenant : re-fetch en cours → skeleton.
    expect(screen.queryByTestId('billing-total-cost')).not.toBeInTheDocument()
    expect(screen.getByTestId('billing-usage-loading')).toBeInTheDocument()
  })
})
