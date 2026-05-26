import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SkillAnalysesDrilldown } from '../components/SkillAnalysesDrilldown'
import type { SkillAnalysesResponse } from '../types'

vi.mock('../api/metrics', () => ({
  fetchSkillAnalyses: vi.fn(),
}))

import { fetchSkillAnalyses } from '../api/metrics'

const mockFetch = vi.mocked(fetchSkillAnalyses)

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const _RESPONSE: SkillAnalysesResponse = {
  skill: 'graham_analysis',
  period_days: 30,
  entries: [
    {
      analysis_id: 'a1',
      ticker: 'BNS.TO',
      workflow_name: 'value_graham',
      cost_usd: 0.0123,
      created_at: '2026-05-25T10:00:00+00:00',
    },
    {
      analysis_id: 'a2',
      ticker: 'TD.TO',
      workflow_name: 'compounder_buffett',
      cost_usd: 0.0456,
      created_at: '2026-05-24T09:00:00+00:00',
    },
  ],
}

describe('SkillAnalysesDrilldown', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('appelle fetchSkillAnalyses avec le skill et la période', async () => {
    mockFetch.mockResolvedValue({ ..._RESPONSE, entries: [] })
    render(<SkillAnalysesDrilldown skill="graham_analysis" days={90} />, { wrapper })
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('graham_analysis', 90)
    })
  })

  it('affiche les analyses dans un tableau', async () => {
    mockFetch.mockResolvedValue(_RESPONSE)
    render(<SkillAnalysesDrilldown skill="graham_analysis" days={30} />, { wrapper })
    await waitFor(() => {
      expect(screen.getByTestId('skill-drilldown-table')).toBeInTheDocument()
    })
    expect(screen.getByTestId('skill-analysis-row-a1')).toBeInTheDocument()
    expect(screen.getByTestId('skill-analysis-row-a2')).toBeInTheDocument()
    expect(screen.getByText('BNS.TO')).toBeInTheDocument()
  })

  it('affiche un état vide quand aucune analyse', async () => {
    mockFetch.mockResolvedValue({ ..._RESPONSE, entries: [] })
    render(<SkillAnalysesDrilldown skill="graham_analysis" days={30} />, { wrapper })
    await waitFor(() => {
      expect(screen.getByTestId('skill-drilldown-empty')).toBeInTheDocument()
    })
  })

  it('affiche une erreur si l’API échoue', async () => {
    mockFetch.mockRejectedValue(new Error('boom'))
    render(<SkillAnalysesDrilldown skill="graham_analysis" days={30} />, { wrapper })
    await waitFor(() => {
      expect(screen.getByTestId('skill-drilldown-error')).toBeInTheDocument()
    })
  })

  it('appelle onClose au clic sur Fermer', async () => {
    mockFetch.mockResolvedValue({ ..._RESPONSE, entries: [] })
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(
      <SkillAnalysesDrilldown skill="graham_analysis" days={30} onClose={onClose} />,
      { wrapper },
    )
    await waitFor(() => {
      expect(screen.getByTestId('skill-drilldown-close')).toBeInTheDocument()
    })
    await user.click(screen.getByTestId('skill-drilldown-close'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
