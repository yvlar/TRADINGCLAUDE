import { useState, useCallback } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { HistoryTable } from '../components/HistoryTable'
import { getHistory } from '../api/analyze'
import { apiClient } from '../api/client'
import type { HistoryEntry } from '../types'

export default function HistoryPage() {
  const [ticker, setTicker] = useState('')
  const [submittedTicker, setSubmittedTicker] = useState('')
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [nextBefore, setNextBefore] = useState<string | null>(null)

  const historyQuery = useQuery({
    queryKey: ['history', submittedTicker],
    queryFn: async () => {
      const res = await getHistory(submittedTicker || 'ALL', 15)
      setEntries(res.entries)
      setNextBefore(res.next_before)
      return res
    },
    enabled: submittedTicker !== '',
  })

  const loadMoreMutation = useMutation({
    mutationFn: () => getHistory(submittedTicker, 15, nextBefore ?? undefined),
    onSuccess: (res) => {
      setEntries((prev) => [...prev, ...res.entries])
      setNextBefore(res.next_before)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const t = ticker.trim().toUpperCase() || 'ALL'
    setEntries([])
    setNextBefore(null)
    setSubmittedTicker(t === submittedTicker ? t + ' ' : t)
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

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold mb-1">Historique des analyses</h2>
        <p className="text-sm text-muted-foreground">
          Retrouvez toutes les analyses passées par ticker.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wide">Ticker</label>
          <Input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="BNS"
            className="w-32"
            aria-label="Ticker"
          />
        </div>
        <Button type="submit" disabled={historyQuery.isFetching}>
          {historyQuery.isFetching ? 'Chargement...' : 'Charger'}
        </Button>
      </form>

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
        <p className="text-muted-foreground text-sm">Aucun historique pour ce ticker.</p>
      )}
    </div>
  )
}
