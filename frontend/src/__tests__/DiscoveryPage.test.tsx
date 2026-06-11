import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { UIModeProvider } from '../contexts/UIModeContext'
import DiscoveryPage from '../pages/DiscoveryPage'
import * as discoveryApi from '../api/discovery'
import type { DiscoveryCategoriesResponse, DiscoveryCategoryResponse } from '../types'

vi.mock('../api/discovery', () => ({
  fetchDiscoveryCategories: vi.fn(),
  fetchDiscoveryCategory: vi.fn(),
}))

const MOCK_CATEGORIES: DiscoveryCategoriesResponse = {
  categories: [
    {
      id: 'solides_stables',
      titre: 'Solides et stables',
      emoji: '🟢',
      description: 'Des entreprises établies, rentables depuis des années.',
      niveau_risque: 'faible',
      nb_suggestions: 2,
      as_of: '2026-06-11T06:00:00+00:00',
    },
  ],
}

const MOCK_CATEGORY: DiscoveryCategoryResponse = {
  id: 'solides_stables',
  titre: 'Solides et stables',
  emoji: '🟢',
  description: 'Des entreprises établies, rentables depuis des années.',
  niveau_risque: 'faible',
  account_hint: 'Souvent avantageux en CELI.',
  as_of: '2026-06-11T06:00:00+00:00',
  suggestions: [
    {
      ticker: 'RY.TO',
      name: 'Banque Royale du Canada',
      composite_score: 78.0,
      composite_label: 'FORT',
      risk_badge: 'faible',
      why: 'Banque Royale du Canada : entreprise établie, qualité FORT (78/100).',
      dividend_yield: 0.041,
      dividend_years: 10,
      pe: 11.2,
      price: 82.4,
      account_hint: 'Souvent avantageux en CELI.',
      as_of: '2026-06-11T06:00:00+00:00',
    },
  ],
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <UIModeProvider>{children}</UIModeProvider>
      </QueryClientProvider>
    </MemoryRouter>
  )
}

describe('DiscoveryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear() // évite la fuite du mode UI entre tests
  })

  it('affiche la grille de catégories sans demander de ticker', async () => {
    vi.mocked(discoveryApi.fetchDiscoveryCategories).mockResolvedValue(MOCK_CATEGORIES)

    render(<DiscoveryPage />, { wrapper })

    expect(await screen.findByTestId('category-card-solides_stables')).toBeInTheDocument()
    expect(screen.getByText('Solides et stables')).toBeInTheDocument()
    expect(screen.getByText('Risque faible')).toBeInTheDocument()
  })

  it('charge les suggestions au clic sur une catégorie', async () => {
    const user = userEvent.setup()
    vi.mocked(discoveryApi.fetchDiscoveryCategories).mockResolvedValue(MOCK_CATEGORIES)
    vi.mocked(discoveryApi.fetchDiscoveryCategory).mockResolvedValue(MOCK_CATEGORY)

    render(<DiscoveryPage />, { wrapper })
    await user.click(await screen.findByTestId('category-card-solides_stables'))

    await waitFor(() => {
      expect(discoveryApi.fetchDiscoveryCategory).toHaveBeenCalledWith('solides_stables')
    })
    expect(await screen.findByTestId('suggestion-RY.TO')).toBeInTheDocument()
    expect(screen.getByText(/Banque Royale du Canada : entreprise établie/)).toBeInTheDocument()
    // « Dividende » est rendu via GlossaryTerm → le libellé et la valeur sont des nœuds distincts
    expect(screen.getByTestId('glossary-trigger-rendement_dividende')).toBeInTheDocument()
    expect(screen.getByText(/4\.1 % par an/)).toBeInTheDocument()
  })

  it("le bouton analyse approfondie pointe vers l'analyse préremplie", async () => {
    const user = userEvent.setup()
    vi.mocked(discoveryApi.fetchDiscoveryCategories).mockResolvedValue(MOCK_CATEGORIES)
    vi.mocked(discoveryApi.fetchDiscoveryCategory).mockResolvedValue(MOCK_CATEGORY)

    render(<DiscoveryPage />, { wrapper })
    await user.click(await screen.findByTestId('category-card-solides_stables'))

    const link = await screen.findByTestId('analyze-RY.TO')
    expect(link).toHaveAttribute('href', '/?ticker=RY.TO')
  })

  it('retour à la grille via le bouton retour', async () => {
    const user = userEvent.setup()
    vi.mocked(discoveryApi.fetchDiscoveryCategories).mockResolvedValue(MOCK_CATEGORIES)
    vi.mocked(discoveryApi.fetchDiscoveryCategory).mockResolvedValue(MOCK_CATEGORY)

    render(<DiscoveryPage />, { wrapper })
    await user.click(await screen.findByTestId('category-card-solides_stables'))
    await user.click(await screen.findByTestId('discovery-back'))

    expect(await screen.findByTestId('category-card-solides_stables')).toBeInTheDocument()
  })

  it('affiche un message si la catégorie est vide (en préparation)', async () => {
    const user = userEvent.setup()
    vi.mocked(discoveryApi.fetchDiscoveryCategories).mockResolvedValue(MOCK_CATEGORIES)
    vi.mocked(discoveryApi.fetchDiscoveryCategory).mockResolvedValue({
      ...MOCK_CATEGORY,
      suggestions: [],
      as_of: null,
    })

    render(<DiscoveryPage />, { wrapper })
    await user.click(await screen.findByTestId('category-card-solides_stables'))

    expect(await screen.findByTestId('discovery-empty')).toBeInTheDocument()
  })

  it('affiche une erreur lisible si le chargement échoue', async () => {
    vi.mocked(discoveryApi.fetchDiscoveryCategories).mockRejectedValue(new Error('500'))

    render(<DiscoveryPage />, { wrapper })

    expect(await screen.findByTestId('discovery-error')).toBeInTheDocument()
  })

  it('masque le détail technique en mode débutant (défaut)', async () => {
    const user = userEvent.setup()
    localStorage.clear() // garantit le défaut débutant
    vi.mocked(discoveryApi.fetchDiscoveryCategories).mockResolvedValue(MOCK_CATEGORIES)
    vi.mocked(discoveryApi.fetchDiscoveryCategory).mockResolvedValue(MOCK_CATEGORY)

    render(<DiscoveryPage />, { wrapper })
    await user.click(await screen.findByTestId('category-card-solides_stables'))
    await screen.findByTestId('suggestion-RY.TO')

    expect(screen.queryByTestId('suggestion-advanced-RY.TO')).not.toBeInTheDocument()
  })

  it('affiche le détail technique en mode avancé', async () => {
    const user = userEvent.setup()
    localStorage.setItem('tc_ui_mode', 'avance')
    vi.mocked(discoveryApi.fetchDiscoveryCategories).mockResolvedValue(MOCK_CATEGORIES)
    vi.mocked(discoveryApi.fetchDiscoveryCategory).mockResolvedValue(MOCK_CATEGORY)

    render(<DiscoveryPage />, { wrapper })
    await user.click(await screen.findByTestId('category-card-solides_stables'))

    expect(await screen.findByTestId('suggestion-advanced-RY.TO')).toBeInTheDocument()
    localStorage.clear()
  })
})
