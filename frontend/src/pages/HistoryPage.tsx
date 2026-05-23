import { useState, useCallback, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { HistoryTable } from '../components/HistoryTable'
import { getHistoryPaged, downloadTickerPdf, deleteAnalysis } from '../api/analyze'
import { downloadAnnotationsCsv, downloadAnnotationsXlsx } from '../api/annotations'
import { apiClient, ApiError } from '../api/client'

interface SearchState {
  ticker: string
  q: string
  fromDt: string
  toDt: string
}

export default function HistoryPage() {
  const [ticker, setTicker] = useState('')
  const [searchQ, setSearchQ] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [dateError, setDateError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState<SearchState | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfMessage, setPdfMessage] = useState<string | null>(null)
  const [csvLoading, setCsvLoading] = useState(false)
  const [xlsxLoading, setXlsxLoading] = useState(false)
  const [exportMessage, setExportMessage] = useState<string | null>(null)
  const [deletedIds, setDeletedIds] = useState<Set<string>>(new Set())
  const [deleteMessage, setDeleteMessage] = useState<string | null>(null)

  const historyQuery = useQuery({
    queryKey: ['history-paged', submitted?.ticker, submitted?.q, submitted?.fromDt, submitted?.toDt, currentPage, pageSize],
    queryFn: async () => {
      if (!submitted) return null
      return await getHistoryPaged(
        {
          ticker: submitted.ticker || undefined,
          q: submitted.q || undefined,
          fromDt: submitted.fromDt || undefined,
          toDt: submitted.toDt || undefined,
        },
        currentPage,
        pageSize,
      )
    },
    enabled: submitted !== null,
  })

  const entries = (historyQuery.data?.entries ?? []).filter(
    (e) => !deletedIds.has(e.analysis_id),
  )
  const totalPages = historyQuery.data?.total_pages ?? 1
  const totalCount = historyQuery.data?.total_count ?? 0

  // Reset page=1 quand filtre change (Sprint 90)
  useEffect(() => {
    setCurrentPage(1)
  }, [submitted, pageSize])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const t = ticker.trim().toUpperCase()
    const q = searchQ.trim()
    if (!t && !q) return

    if (fromDate && toDate && fromDate > toDate) {
      setDateError('La date "Du" doit etre anterieure ou egale a la date "Au".')
      return
    }
    setDateError(null)
    setSubmitted({ ticker: t, q, fromDt: fromDate, toDt: toDate })
  }

  const handleDownloadTickerPdf = async () => {
    if (!submitted?.ticker) return
    setPdfLoading(true)
    setPdfMessage(null)
    try {
      const blob = await downloadTickerPdf(submitted.ticker)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${submitted.ticker}-rapport.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setPdfMessage(`Aucun rapport disponible pour ${submitted.ticker} (pas d'historique).`)
      } else {
        setPdfMessage('Erreur lors du telechargement du rapport PDF.')
      }
    } finally {
      setPdfLoading(false)
    }
  }

  const handleExportCsv = async () => {
    setCsvLoading(true)
    setExportMessage(null)
    try {
      const blob = await downloadAnnotationsCsv()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'annotations.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setExportMessage('Erreur lors de l\'export CSV des annotations.')
    } finally {
      setCsvLoading(false)
    }
  }

  const handleExportXlsx = async () => {
    setXlsxLoading(true)
    setExportMessage(null)
    try {
      const blob = await downloadAnnotationsXlsx()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'annotations.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setExportMessage('Erreur lors de l\'export Excel des annotations.')
    } finally {
      setXlsxLoading(false)
    }
  }

  const handleDeleteAnalysis = useCallback(async (analysisId: string) => {
    if (!window.confirm('Supprimer cette analyse ? Cette action est irréversible.')) return
    try {
      await deleteAnalysis(analysisId)
      setDeletedIds((prev) => new Set([...prev, analysisId]))
      setDeleteMessage('Analyse supprimée.')
    } catch {
      setDeleteMessage('Erreur lors de la suppression.')
    } finally {
      setTimeout(() => setDeleteMessage(null), 3000)
    }
  }, [])

  const handleDownloadPdf = useCallback(async (analysisId: string, ticker: string) => {
    try {
      const blob = await apiClient.requestBlob(`/report/${analysisId}`)
      const date = new Date().toISOString().slice(0, 7)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${ticker}-${date}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(`Erreur PDF : ${(e as Error).message}`)
    }
  }, [])

  const isSearchMode = !!(submitted?.q && !submitted?.ticker)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold mb-1">Historique des analyses</h2>
        <p className="text-sm text-muted-foreground">
          Recherchez par ticker ou par terme (verdict, workflow).
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-wrap gap-3 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wide">Ticker</label>
          <Input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="BNS"
            className="w-28"
            aria-label="Ticker"
            data-testid="history-ticker-input"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wide">Recherche</label>
          <Input
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            placeholder="ACHAT, value_graham..."
            className="w-52"
            aria-label="Recherche"
            data-testid="history-search-input"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wide">Du</label>
          <Input
            type="date"
            value={fromDate}
            onChange={(e) => { setFromDate(e.target.value); setDateError(null) }}
            className="w-36"
            aria-label="Date debut"
            data-testid="history-from-date"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wide">Au</label>
          <Input
            type="date"
            value={toDate}
            onChange={(e) => { setToDate(e.target.value); setDateError(null) }}
            className="w-36"
            aria-label="Date fin"
            data-testid="history-to-date"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wide">Page size</label>
          <select
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            aria-label="Taille de page"
            data-testid="history-page-size"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>
        <Button
          type="submit"
          disabled={historyQuery.isFetching || (!ticker.trim() && !searchQ.trim())}
          data-testid="history-search-btn"
        >
          {historyQuery.isFetching ? 'Chargement...' : 'Chercher'}
        </Button>
        {submitted?.ticker?.trim() && (
          <Button
            type="button"
            variant="outline"
            disabled={pdfLoading}
            onClick={handleDownloadTickerPdf}
          >
            {pdfLoading ? 'Téléchargement...' : 'Télécharger PDF'}
          </Button>
        )}
      </form>

      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={csvLoading}
          onClick={handleExportCsv}
          data-testid="export-annotations-csv-btn"
        >
          {csvLoading ? 'Export...' : 'Exporter CSV'}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={xlsxLoading}
          onClick={handleExportXlsx}
          data-testid="export-annotations-xlsx-btn"
        >
          {xlsxLoading ? 'Export...' : 'Exporter Excel'}
        </Button>
      </div>

      {dateError && (
        <p className="text-sm text-destructive" data-testid="history-date-error">{dateError}</p>
      )}

      {exportMessage && (
        <p className="text-sm text-destructive" data-testid="export-annotations-error">{exportMessage}</p>
      )}

      {pdfMessage && (
        <p className="text-sm text-muted-foreground">{pdfMessage}</p>
      )}

      {deleteMessage && (
        <p className="text-sm text-muted-foreground" data-testid="delete-analysis-message">{deleteMessage}</p>
      )}

      {isSearchMode && entries.length > 0 && (
        <p className="text-xs text-muted-foreground" data-testid="search-cross-ticker-notice">
          Resultats cross-ticker pour &laquo; {submitted?.q} &raquo;
        </p>
      )}

      {historyQuery.isError && (
        <div className="border border-destructive bg-destructive/10 text-destructive rounded-lg px-4 py-3 text-sm">
          Erreur : {(historyQuery.error as Error).message}
        </div>
      )}

      {entries.length > 0 && (
        <>
          <HistoryTable
            entries={entries}
            hasMore={false}
            onLoadMore={() => { /* pagination geree par boutons */ }}
            isLoading={historyQuery.isFetching}
            onDownloadPdf={handleDownloadPdf}
            onDeleteAnalysis={handleDeleteAnalysis}
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {totalCount} analyses au total
            </span>
            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="outline"
                disabled={currentPage <= 1 || historyQuery.isFetching}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                data-testid="history-pagination-prev"
              >
                Precedent
              </Button>
              <span className="text-sm" data-testid="history-page-label">
                Page {currentPage} sur {totalPages}
              </span>
              <Button
                type="button"
                variant="outline"
                disabled={currentPage >= totalPages || historyQuery.isFetching}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                data-testid="history-pagination-next"
              >
                Suivant
              </Button>
            </div>
          </div>
        </>
      )}

      {historyQuery.isFetched && entries.length === 0 && (
        <p className="text-muted-foreground text-sm" data-testid="history-empty">
          Aucun resultat trouve.
        </p>
      )}
    </div>
  )
}
