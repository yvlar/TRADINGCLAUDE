import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { QuotaBadge } from '../components/QuotaBadge'
import { getQuota } from '../api/quota'
import type { QuotaStatus } from '../types'

vi.mock('../api/quota', () => ({ getQuota: vi.fn() }))

const _STATUS: QuotaStatus = {
  plan: 'free',
  used: 12,
  limit: 50,
  remaining: 38,
  reset_at: '2026-07-01T00:00:00Z',
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('QuotaBadge (Sprint 184)', () => {
  beforeEach(() => {
    vi.mocked(getQuota).mockReset()
  })

  it('affiche le plan et le quota restant depuis la donnée', async () => {
    vi.mocked(getQuota).mockResolvedValue(_STATUS)
    render(<QuotaBadge tenantId="t1" />, { wrapper })

    const badge = await screen.findByTestId('quota-badge')
    expect(badge).toHaveTextContent('FREE')
    expect(badge).toHaveTextContent('38 analyses restantes')
  })

  it('ne fetch rien et ne rend rien si non authentifié (tenant absent)', async () => {
    render(<QuotaBadge tenantId={undefined} />, { wrapper })

    expect(screen.queryByTestId('quota-badge')).toBeNull()
    expect(getQuota).not.toHaveBeenCalled()
  })

  it('reste masqué et ne casse pas le header si le fetch échoue', async () => {
    vi.mocked(getQuota).mockRejectedValue(new Error('boom'))
    const { container } = render(<QuotaBadge tenantId="t1" />, { wrapper })

    await waitFor(() => expect(getQuota).toHaveBeenCalled())
    expect(screen.queryByTestId('quota-badge')).toBeNull()
    expect(container).toBeEmptyDOMElement()
  })

  it('affiche le plan sans compteur quand le restant est inconnu (fail-open)', async () => {
    vi.mocked(getQuota).mockResolvedValue({
      ..._STATUS,
      plan: 'unknown',
      limit: null,
      remaining: null,
    })
    render(<QuotaBadge tenantId="t1" />, { wrapper })

    const badge = await screen.findByTestId('quota-badge')
    expect(badge).toHaveTextContent('UNKNOWN')
    expect(screen.queryByTestId('quota-remaining')).toBeNull()
  })
})
