import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AlertsTimelineChart } from '../components/AlertsTimelineChart'
import type { AlertEntry } from '../types'

const captured: { data?: { date: string; count: number }[] } = {}

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-container">{children}</div>
  ),
  BarChart: ({
    children,
    data,
  }: {
    children: React.ReactNode
    data: { date: string; count: number }[]
  }) => {
    captured.data = data
    return <div data-testid="recharts-bar-chart">{children}</div>
  },
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}))

const makeAlert = (id: number, created_at: string): AlertEntry => ({
  id,
  ticker: 'BNS',
  type: 'ESG_DEGRADATION',
  valeur: 1,
  seuil: 2,
  message: null,
  created_at,
})

describe('AlertsTimelineChart', () => {
  it('rend le graphique quand des alertes sont présentes', () => {
    render(<AlertsTimelineChart alerts={[makeAlert(1, '2026-05-10T12:00:00Z')]} />)
    expect(screen.getByTestId('alerts-timeline-chart')).toBeInTheDocument()
    expect(screen.getByTestId('recharts-bar-chart')).toBeInTheDocument()
  })

  it('regroupe les alertes par jour et trie par date', () => {
    render(
      <AlertsTimelineChart
        alerts={[
          makeAlert(1, '2026-05-11T09:00:00Z'),
          makeAlert(2, '2026-05-10T12:00:00Z'),
          makeAlert(3, '2026-05-10T18:00:00Z'),
        ]}
      />,
    )
    expect(captured.data).toEqual([
      { date: '2026-05-10', count: 2 },
      { date: '2026-05-11', count: 1 },
    ])
  })

  it('affiche un état vide quand aucune alerte', () => {
    render(<AlertsTimelineChart alerts={[]} />)
    expect(screen.getByTestId('alerts-timeline-empty')).toBeInTheDocument()
  })

  it('affiche un état de chargement', () => {
    render(<AlertsTimelineChart alerts={[]} isLoading />)
    expect(screen.getByTestId('alerts-timeline-loading')).toBeInTheDocument()
  })

  it('affiche un état d’erreur', () => {
    render(<AlertsTimelineChart alerts={[]} isError />)
    expect(screen.getByTestId('alerts-timeline-error')).toBeInTheDocument()
  })
})
