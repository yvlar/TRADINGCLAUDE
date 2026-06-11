import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import SearchPage from '../pages/SearchPage'
import * as searchApi from '../api/search'
import type { SemanticSearchResponse } from '../types'

vi.mock('../api/search', () => ({
  fetchSemanticSearch: vi.fn(),
}))

const MOCK_RESPONSE: SemanticSearchResponse = {
  query: 'marge de securite',
  rag_enabled: true,
  results: [
    {
      source: '.claude/skills/klarman-margin-of-safety/SKILL.md',
      extrait: 'La marge de sécurité protège contre les erreurs d\'estimation.',
      score: 0.91,
    },
    {
      source: '.claude/skills/graham-stock-screening/references/marge.md',
      extrait: 'Graham exige une décote substantielle sur la valeur intrinsèque.',
      score: 0.74,
    },
  ],
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <MemoryRouter>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </MemoryRouter>
  )
}

function wrapperWithQuery(initialEntry: string) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return (
      <MemoryRouter initialEntries={[initialEntry]}>
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      </MemoryRouter>
    )
  }
}

describe('SearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le formulaire de recherche et l\'état initial', () => {
    render(<SearchPage />, { wrapper })
    expect(screen.getByTestId('search-input')).toBeInTheDocument()
    expect(screen.getByTestId('search-submit')).toBeInTheDocument()
    expect(screen.getByTestId('search-idle')).toBeInTheDocument()
  })

  it('prérem­plit et lance la recherche depuis ?q= (lien glossaire)', async () => {
    vi.mocked(searchApi.fetchSemanticSearch).mockResolvedValue(MOCK_RESPONSE)

    render(<SearchPage />, { wrapper: wrapperWithQuery('/recherche?q=ratio%20cours%20benefice') })

    await waitFor(() => {
      expect(searchApi.fetchSemanticSearch).toHaveBeenCalledWith('ratio cours benefice', 5)
    })
    expect(screen.getByTestId('search-input')).toHaveValue('ratio cours benefice')
  })

  it('appelle fetchSemanticSearch avec la requête saisie', async () => {
    const user = userEvent.setup()
    vi.mocked(searchApi.fetchSemanticSearch).mockResolvedValue(MOCK_RESPONSE)

    render(<SearchPage />, { wrapper })
    await user.type(screen.getByTestId('search-input'), 'marge de securite')
    await user.click(screen.getByTestId('search-submit'))

    await waitFor(() => {
      expect(searchApi.fetchSemanticSearch).toHaveBeenCalledWith('marge de securite', 5)
    })
  })

  it('affiche les passages retournés', async () => {
    const user = userEvent.setup()
    vi.mocked(searchApi.fetchSemanticSearch).mockResolvedValue(MOCK_RESPONSE)

    render(<SearchPage />, { wrapper })
    await user.type(screen.getByTestId('search-input'), 'marge de securite')
    await user.click(screen.getByTestId('search-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('search-results')).toBeInTheDocument()
    })
    expect(screen.getByTestId('search-result-0')).toBeInTheDocument()
    expect(screen.getByTestId('search-result-1')).toBeInTheDocument()
    expect(
      screen.getByText(/La marge de sécurité protège/),
    ).toBeInTheDocument()
  })

  it('affiche un état vide quand aucun passage', async () => {
    const user = userEvent.setup()
    vi.mocked(searchApi.fetchSemanticSearch).mockResolvedValue({
      query: 'xyz',
      rag_enabled: true,
      results: [],
    })

    render(<SearchPage />, { wrapper })
    await user.type(screen.getByTestId('search-input'), 'requete sans resultat')
    await user.click(screen.getByTestId('search-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('search-empty')).toBeInTheDocument()
    })
  })

  it('affiche un avertissement quand le RAG est désactivé', async () => {
    const user = userEvent.setup()
    vi.mocked(searchApi.fetchSemanticSearch).mockResolvedValue({
      query: 'moat',
      rag_enabled: false,
      results: [],
    })

    render(<SearchPage />, { wrapper })
    await user.type(screen.getByTestId('search-input'), 'moat economique')
    await user.click(screen.getByTestId('search-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('search-rag-disabled')).toBeInTheDocument()
    })
  })

  it('affiche un message d\'erreur si l\'API échoue', async () => {
    const user = userEvent.setup()
    vi.mocked(searchApi.fetchSemanticSearch).mockRejectedValue(new Error('boom'))

    render(<SearchPage />, { wrapper })
    await user.type(screen.getByTestId('search-input'), 'requete en erreur')
    await user.click(screen.getByTestId('search-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('search-error')).toBeInTheDocument()
    })
  })
})
