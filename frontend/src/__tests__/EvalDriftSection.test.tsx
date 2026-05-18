import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DashboardPage from '../pages/DashboardPage'
import type { EvalDriftResult } from '../types'

// Neutralise le WebSocket dans MetricsDashboard
vi.mock('../components/MetricsDashboard', () => ({
  MetricsDashboard: () => <div data-testid="metrics-dashboard" />,
}))

const mockFetchEvalDrift = vi.fn()

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return {
    ...actual,
    getCompositeHistory: vi.fn().mockResolvedValue([]),
    fetchEvalDrift: () => mockFetchEvalDrift(),
  }
})

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const RESULTS_OK: EvalDriftResult[] = [
  {
    dataset: 'graham',
    concordance_rate: 0.9,
    threshold: 0.85,
    alert: false,
    cases_total: 10,
    cases_pass: 9,
    recorded_at: '2026-05-14T10:00:00Z',
  },
]

const RESULTS_DRIFT: EvalDriftResult[] = [
  {
    dataset: 'earnings',
    concordance_rate: 0.7,
    threshold: 0.85,
    alert: true,
    cases_total: 10,
    cases_pass: 7,
    recorded_at: '2026-05-14T11:00:00Z',
  },
]

const RESULTS_MIXED: EvalDriftResult[] = [...RESULTS_OK, ...RESULTS_DRIFT]

describe('EvalDriftSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('affiche "Aucune donnée" quand la liste est vide', async () => {
    mockFetchEvalDrift.mockResolvedValue([])
    render(<DashboardPage />, { wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('eval-drift-empty')).toBeInTheDocument()
    })
    expect(screen.getByText(/Aucune donnée de drift disponible/)).toBeInTheDocument()
  })

  it('affiche le badge OK et la progress bar quand concordance >= seuil', async () => {
    mockFetchEvalDrift.mockResolvedValue(RESULTS_OK)
    render(<DashboardPage />, { wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('eval-drift-badge-ok-graham')).toBeInTheDocument()
    })
    expect(screen.getByTestId('eval-drift-badge-ok-graham')).toHaveTextContent('OK')
    expect(screen.getByTestId('eval-drift-bar-graham')).toHaveStyle({ width: '90%' })
    expect(screen.getByText(/9\/10 cas/)).toBeInTheDocument()
  })

  it('affiche le badge DRIFT DÉTECTÉ quand alert == true', async () => {
    mockFetchEvalDrift.mockResolvedValue(RESULTS_DRIFT)
    render(<DashboardPage />, { wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('eval-drift-badge-alert-earnings')).toBeInTheDocument()
    })
    expect(screen.getByTestId('eval-drift-badge-alert-earnings')).toHaveTextContent('DRIFT DÉTECTÉ')
    expect(screen.getByTestId('eval-drift-bar-earnings')).toHaveStyle({ width: '70%' })
    expect(screen.getByText(/7\/10 cas/)).toBeInTheDocument()
  })

  it('appelle fetchEvalDrift au montage et affiche plusieurs datasets', async () => {
    mockFetchEvalDrift.mockResolvedValue(RESULTS_MIXED)
    render(<DashboardPage />, { wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('eval-drift-list')).toBeInTheDocument()
    })

    expect(mockFetchEvalDrift).toHaveBeenCalledOnce()
    expect(screen.getByTestId('eval-drift-row-graham')).toBeInTheDocument()
    expect(screen.getByTestId('eval-drift-row-earnings')).toBeInTheDocument()
    expect(screen.getByTestId('eval-drift-badge-ok-graham')).toBeInTheDocument()
    expect(screen.getByTestId('eval-drift-badge-alert-earnings')).toBeInTheDocument()
  })

  it('affiche le titre de la section eval drift', async () => {
    mockFetchEvalDrift.mockResolvedValue([])
    render(<DashboardPage />, { wrapper })

    await waitFor(() => {
      expect(screen.getByTestId('eval-drift-title')).toBeInTheDocument()
    })
    expect(screen.getByTestId('eval-drift-title')).toHaveTextContent('Eval Drift')
  })
})
