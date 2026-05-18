import { useState, useCallback } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { HistoryTable } from '../components/HistoryTable'
import { getHistory, downloadTickerPdf } from '../api/analyze'
import { apiClient, ApiError } from '../api/client'
import type { HistoryEntry } from '../types'

interface SearchState {
  ticker: string
  q: string
}

export default function HistoryPage() {
  const [ticker, setTicker] = useState('')
  const [searchQ, setSearchQ] = useState('')
  const [submitted, setSubmitted] = useState<SearchState | null>(null)
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [nextBefore, setNextBefore] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfMessage, setPdfMessage] = useState<string | null>(null)

  const historyQuery = useQuery({
    queryKey: ['history', submitted?.ticker, submitted?.q],
    queryFn: async () => {
      if (!submitted) return null
      const res = await getHistory(
        submitted.ticker || undefined,
        15,
        undefined,
        submitted.q || undefined,
      )
      setEntries(res.entries)
      setNextBefore(res.next_before)
      return res
    },
    enabled: submitted !== null,
  })

  const loadMoreMutation = useMutation({
    mutationFn: () =>
      getHistory(
        submitted?.ticker || undefined,
        15,
        nextBefore ?? undefined,
        submitted?.q || undefined,
      ),
    onSuccess: (res) => {
      setEntries((prev) => [...prev, ...res.entries])
      setNextBefore(res.next_before)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const t = ticker.trim().toUpperCase()
    const q = searchQ.trim()
    if (!t && !q) return
    setEntries([])
    setNextBefore(null)
    // force re-fetch même si les valeurs sont identiques
    setSubmitted((prev) =>
      prev?.ticker === t && prev?.q === q ? { ticker: t + ' ', q } : { ticker: t, q },
    )
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
        setPdfMessage('Erreur lors du téléchargement du rapport PDF.')
      }
    } finally {
      setPdfLoading(false)
    }
  }

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
            placeholder="ACHAT, value_graham…"
            className="w-52"
            aria-label="Recherche"
            data-testid="history-search-input"
          />
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

      {pdfMessage && (
        <p className="text-sm text-muted-foreground">{pdfMessage}</p>
      )}

      {isSearchMode && entries.length > 0 && (
        <p className="text-xs text-muted-foreground" data-testid="search-cross-ticker-notice">
          Résultats cross-ticker pour « {submitted?.q} »
        </p>
      )}

      {historyQuery.isError && (
        <div className="border border-destructive bg-destructive/10 text-destructive rounded-lg px-4 py-3 text-sm">
          Erreur : {(historyQuery.error as Error).message}
        </div>
      )}

      {entries.length > 0 && (
        <HistoryTable
          entries={entries}
          hasMore={nextBefore !== null}
          onLoadMore={() => loadMoreMutation.mutate()}
          isLoading={loadMoreMutation.isPending}
          onDownloadPdf={handleDownloadPdf}
        />
      )}

      {historyQuery.isFetched && entries.length === 0 && (
        <p className="text-muted-foreground text-sm" data-testid="history-empty">
          Aucun résultat trouvé.
        </p>
      )}
    </div>
  )
}
