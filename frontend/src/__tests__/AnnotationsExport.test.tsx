import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HistoryPage from '../pages/HistoryPage'
import * as annotationsApi from '../api/annotations'

vi.mock('../api/annotations', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/annotations')>()
  return {
    ...actual,
    downloadAnnotationsCsv: vi.fn(),
    downloadAnnotationsXlsx: vi.fn(),
  }
})

vi.mock('../api/analyze', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/analyze')>()
  return { ...actual, getHistory: vi.fn(), downloadTickerPdf: vi.fn() }
})

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('AnnotationsExport — boutons dans HistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.URL.createObjectURL = vi.fn().mockReturnValue('blob:test')
    global.URL.revokeObjectURL = vi.fn()
  })

  it('affiche le bouton "Exporter CSV"', () => {
    render(<HistoryPage />, { wrapper })
    expect(screen.getByTestId('export-annotations-csv-btn')).toBeInTheDocument()
  })

  it('affiche le bouton "Exporter Excel"', () => {
    render(<HistoryPage />, { wrapper })
    expect(screen.getByTestId('export-annotations-xlsx-btn')).toBeInTheDocument()
  })

  it('clic CSV appelle downloadAnnotationsCsv', async () => {
    const user = userEvent.setup()
    vi.mocked(annotationsApi.downloadAnnotationsCsv).mockResolvedValue(new Blob(['ticker,note']))
    render(<HistoryPage />, { wrapper })

    await user.click(screen.getByTestId('export-annotations-csv-btn'))

    expect(annotationsApi.downloadAnnotationsCsv).toHaveBeenCalledOnce()
  })

  it('clic Excel appelle downloadAnnotationsXlsx', async () => {
    const user = userEvent.setup()
    vi.mocked(annotationsApi.downloadAnnotationsXlsx).mockResolvedValue(new Blob(['xlsx-data']))
    render(<HistoryPage />, { wrapper })

    await user.click(screen.getByTestId('export-annotations-xlsx-btn'))

    expect(annotationsApi.downloadAnnotationsXlsx).toHaveBeenCalledOnce()
  })

  it("erreur API CSV affiche message d'erreur", async () => {
    const user = userEvent.setup()
    vi.mocked(annotationsApi.downloadAnnotationsCsv).mockRejectedValue(new Error('Network error'))
    render(<HistoryPage />, { wrapper })

    await user.click(screen.getByTestId('export-annotations-csv-btn'))

    expect(await screen.findByTestId('export-annotations-error')).toBeInTheDocument()
  })
})
