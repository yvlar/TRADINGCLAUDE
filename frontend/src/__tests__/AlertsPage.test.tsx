import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AlertsPage from '../pages/AlertsPage'
import * as alertsApi from '../api/alerts'
import type { AlertsResponse } from '../types'

vi.mock('../api/alerts', () => ({
  fetchAlerts: vi.fn(),
}))

function makeAlert(overrides: Partial<AlertsResponse['alerts'][0]> = {}): AlertsResponse['alerts'][0] {
  return {
    id: 1,
    ticker: 'BNS',
    type: 'ESG_DEGRADATION',
    valeur: 3.5,
    seuil: 5.0,
    message: 'Score ESG dégradé',
    created_at: '2026-05-23T10:00:00+00:00',
    ...overrides,
  }
}

function renderAlertsPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AlertsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AlertsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le message vide quand la liste est vide', async () => {
    vi.mocked(alertsApi.fetchAlerts).mockResolvedValue({ alerts: [] })

    renderAlertsPage()
    const empty = await screen.findByTestId('alerts-empty')
    expect(empty).toHaveTextContent('Aucune alerte enregistrée.')
  })

  it('affiche le tableau avec 2 alertes', async () => {
    vi.mocked(alertsApi.fetchAlerts).mockResolvedValue({
      alerts: [
        makeAlert({ id: 1, ticker: 'BNS', type: 'ESG_DEGRADATION' }),
        makeAlert({ id: 2, ticker: 'TD', type: 'SCREENER_FORT', valeur: 75.0, seuil: 70.0 }),
      ],
    })

    renderAlertsPage()
    await screen.findByTestId('alerts-table')

    expect(screen.getByTestId('alert-row-1')).toBeInTheDocument()
    expect(screen.getByTestId('alert-row-2')).toBeInTheDocument()
  })

  it('affiche le bon badge de type colore pour ESG_DEGRADATION', async () => {
    vi.mocked(alertsApi.fetchAlerts).mockResolvedValue({
      alerts: [makeAlert({ id: 3, type: 'ESG_DEGRADATION' })],
    })

    renderAlertsPage()
    const badge = await screen.findByTestId('alert-type-badge-3')
    expect(badge).toHaveTextContent('ESG_DEGRADATION')
  })

  it('affiche le spinner de chargement', async () => {
    vi.mocked(alertsApi.fetchAlerts).mockImplementation(
      () => new Promise(() => {}),
    )

    renderAlertsPage()
    expect(await screen.findByTestId('alerts-spinner')).toBeInTheDocument()
  })

  it('affiche un message d erreur si l API echoue', async () => {
    vi.mocked(alertsApi.fetchAlerts).mockRejectedValue(new Error('Erreur réseau'))

    renderAlertsPage()
    const err = await screen.findByTestId('alerts-error')
    expect(err).toHaveTextContent('Impossible de charger les alertes.')
  })
})
