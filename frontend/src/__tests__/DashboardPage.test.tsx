import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DashboardPage from '../pages/DashboardPage'
import { RECENT_ANALYSES_KEY } from '../lib/recentAnalyses'
import type { RecentAnalysis } from '../types'

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return {
    ...actual,
    getPerformance: vi.fn().mockResolvedValue({ ticker: 'BNS', entries: [] }),
    fetchEvalDrift: vi.fn().mockResolvedValue([]),
    getCompositeHistory: vi.fn().mockResolvedValue([]),
  }
})

// MetricsDashboard utilise le WebSocket — on le neutralise pour les tests
vi.mock('../components/MetricsDashboard', () => ({
  MetricsDashboard: () => <div data-testid="metrics-dashboard" />,
}))

vi.mock('../api/metrics', () => ({
  fetchMetrics: vi.fn().mockResolvedValue({
    period_days: 30,
    total_analyses: 0,
    total_cost_usd: 0,
    avg_cost_per_analysis: 0,
    cache_hit_ratio_avg: 0,
    top_tickers: [],
    skills_usage: {},
    skills_cost: {},
    cache_by_workflow: {},
    daily_cost: {},
  }),
  fetchSkillAnalyses: vi.fn().mockResolvedValue({
    skill: 'graham_analysis',
    period_days: 30,
    entries: [],
  }),
}))

vi.mock('../api/alerts', () => ({
  fetchAlerts: vi.fn().mockResolvedValue({ alerts: [] }),
}))

// TickerComparisonChart utilise recharts SVG non disponible en jsdom
vi.mock('../components/TickerComparisonChart', () => ({
  TickerComparisonChart: () => <div data-testid="ticker-comparison-chart-mock" />,
}))

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const _RECENT: RecentAnalysis[] = [
  {
    ticker: 'BNS',
    composite_score: {
      score: 68.5,
      label: 'MODÉRÉ',
      skills_inclus: ['graham', 'buffett'],
      skills_exclus: [],
      detail: {},
    },
    inter_skill_conflicts: [],
    workflow: 'value_graham',
    created_at: '2026-05-10T12:00:00',
  },
  {
    ticker: 'TD',
    composite_score: {
      score: 75.0,
      label: 'FORT',
      skills_inclus: ['graham', 'buffett', 'dorsey_moat'],
      skills_exclus: [],
      detail: {},
    },
    inter_skill_conflicts: ['Graham PASSE mais Buffett REJETER'],
    workflow: 'compounder_buffett',
    created_at: '2026-05-09T09:00:00',
  },
]

describe('DashboardPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('affiche le titre Dashboard', () => {
    render(<DashboardPage />, { wrapper })
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('affiche MetricsDashboard', () => {
    render(<DashboardPage />, { wrapper })
    expect(screen.getByTestId('metrics-dashboard')).toBeInTheDocument()
  })

  it('dispose les sections dans une grille responsive 12 colonnes', () => {
    render(<DashboardPage />, { wrapper })
    const grid = screen.getByTestId('dashboard-grid')
    expect(grid.className).toContain('lg:grid-cols-12')
  })

  it('affiche le message vide si aucune analyse récente', () => {
    render(<DashboardPage />, { wrapper })
    expect(screen.getByTestId('no-recent-analyses')).toBeInTheDocument()
    expect(screen.getByText(/Aucune analyse récente/)).toBeInTheDocument()
  })

  it('affiche les analyses récentes depuis localStorage', () => {
    localStorage.setItem(RECENT_ANALYSES_KEY, JSON.stringify(_RECENT))
    render(<DashboardPage />, { wrapper })

    expect(screen.queryByTestId('no-recent-analyses')).not.toBeInTheDocument()
    expect(screen.getByTestId('dashboard-ticker-BNS')).toBeInTheDocument()
    expect(screen.getByTestId('dashboard-ticker-TD')).toBeInTheDocument()
  })

  it('affiche le composite_score pour chaque ticker', () => {
    localStorage.setItem(RECENT_ANALYSES_KEY, JSON.stringify(_RECENT))
    render(<DashboardPage />, { wrapper })

    const scores = screen.getAllByTestId('composite-score')
    expect(scores).toHaveLength(2)
    expect(scores[0]).toHaveTextContent('68.5/100')
    expect(scores[0]).toHaveTextContent('(MODÉRÉ)')
    expect(scores[1]).toHaveTextContent('75.0/100')
    expect(scores[1]).toHaveTextContent('(FORT)')
  })

  it('ouvre le détail au clic sur un ticker', async () => {
    localStorage.setItem(RECENT_ANALYSES_KEY, JSON.stringify([_RECENT[0]]))
    const user = userEvent.setup()
    render(<DashboardPage />, { wrapper })

    expect(screen.queryByTestId('conflicts-empty')).not.toBeInTheDocument()

    await user.click(screen.getByTestId('dashboard-ticker-BNS'))

    await waitFor(() => {
      expect(screen.getByTestId('conflicts-empty')).toBeInTheDocument()
    })
  })

  it('affiche les conflits inter-skills dans le détail', async () => {
    localStorage.setItem(RECENT_ANALYSES_KEY, JSON.stringify([_RECENT[1]]))
    const user = userEvent.setup()
    render(<DashboardPage />, { wrapper })

    await user.click(screen.getByTestId('dashboard-ticker-TD'))

    await waitFor(() => {
      expect(screen.getByTestId('conflicts-list')).toBeInTheDocument()
      expect(screen.getByText('Graham PASSE mais Buffett REJETER')).toBeInTheDocument()
    })
  })
})

describe('ComparisonSection', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('affiche le champ de saisie et le bouton Comparer', () => {
    render(<DashboardPage />, { wrapper })
    expect(screen.getByTestId('comparison-tickers-input')).toBeInTheDocument()
    expect(screen.getByTestId('comparison-comparer-btn')).toBeInTheDocument()
  })

  it('désactive le bouton Comparer si moins de 2 tickers', () => {
    render(<DashboardPage />, { wrapper })
    expect(screen.getByTestId('comparison-comparer-btn')).toBeDisabled()
  })

  it('active le bouton Comparer si 2 tickers valides sont saisis', async () => {
    const user = userEvent.setup()
    render(<DashboardPage />, { wrapper })
    await user.type(screen.getByTestId('comparison-tickers-input'), 'BNS,TD')
    expect(screen.getByTestId('comparison-comparer-btn')).not.toBeDisabled()
  })

  it('appelle getCompositeHistory pour chaque ticker au clic', async () => {
    const { getCompositeHistory } = await import('../api/analyze')
    const mockFn = vi.mocked(getCompositeHistory)
    const user = userEvent.setup()
    render(<DashboardPage />, { wrapper })

    await user.type(screen.getByTestId('comparison-tickers-input'), 'BNS,TD')
    await user.click(screen.getByTestId('comparison-comparer-btn'))

    await waitFor(() => {
      expect(mockFn).toHaveBeenCalledWith('BNS', 90)
      expect(mockFn).toHaveBeenCalledWith('TD', 90)
    })
  })
})
