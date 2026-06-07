import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { UsageResponse } from '../types'

vi.mock('../api/client', () => ({
  apiClient: { request: vi.fn() },
  ApiError: class ApiError extends Error {},
}))

import { apiClient } from '../api/client'
import { getUsage } from '../api/usage'
import { createCheckout, openPortal } from '../api/billing'

const _USAGE: UsageResponse = {
  period_days: 30,
  total_cost_usd: 0.03,
  total_tokens_input: 3000,
  total_tokens_output: 1500,
  by_skill: [
    { skill: 'graham_analysis', cost_usd: 0.03, tokens_input: 3000, tokens_output: 1500, events: 2 },
  ],
  daily_cost: { '2026-06-06': 0.03 },
}

describe('api/usage.ts', () => {
  beforeEach(() => vi.clearAllMocks())

  it('getUsage appelle /usage avec le défaut 30 jours et retourne la forme typée', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(_USAGE)
    const res = await getUsage()
    expect(apiClient.request).toHaveBeenCalledWith('/usage?days=30')
    expect(res.total_cost_usd).toBe(0.03)
    expect(res.by_skill[0].skill).toBe('graham_analysis')
  })

  it('getUsage transmet le paramètre days', async () => {
    vi.mocked(apiClient.request).mockResolvedValue(_USAGE)
    await getUsage(7)
    expect(apiClient.request).toHaveBeenCalledWith('/usage?days=7')
  })
})

describe('api/billing.ts', () => {
  beforeEach(() => vi.clearAllMocks())

  it('createCheckout POST /billing/checkout avec le plan et retourne checkout_url', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ checkout_url: 'https://stripe/checkout' })
    const url = await createCheckout('pro')
    expect(apiClient.request).toHaveBeenCalledWith('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan: 'pro' }),
    })
    expect(url).toBe('https://stripe/checkout')
  })

  it('openPortal POST /billing/portal et retourne portal_url', async () => {
    vi.mocked(apiClient.request).mockResolvedValue({ portal_url: 'https://stripe/portal' })
    const url = await openPortal()
    expect(apiClient.request).toHaveBeenCalledWith('/billing/portal', { method: 'POST' })
    expect(url).toBe('https://stripe/portal')
  })
})
