import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { WatchlistTable } from '../components/WatchlistTable'
import {
  getWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  triggerWatchlistAnalysis,
} from '../api/watchlist'
import { downloadTickerPdf } from '../api/analyze'
import { ApiError } from '../api/client'
import type { WatchlistCreate } from '../types'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'

export default function WatchlistPage() {
  const queryClient = useQueryClient()
  const [ticker, setTicker] = useState('')
  const [workflow, setWorkflow] = useState('value_graham')
  const [lastJobId, setLastJobId] = useState<string | null>(null)
  const [addError, setAddError] = useState('')
  const [pdfLoadingId, setPdfLoadingId] = useState<string | null>(null)
  const [pdfMessage, setPdfMessage] = useState<string | null>(null)

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: getWatchlist,
  })

  const addMutation = useMutation({
    mutationFn: (data: WatchlistCreate) => addToWatchlist(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      setTicker('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => removeFromWatchlist(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })

  const analyzeMutation = useMutation({
    mutationFn: (id: string) => triggerWatchlistAnalysis(id),
    onSuccess: (data) => {
      setLastJobId(data.job_id)
    },
  })

  const handleDownloadPdf = async (ticker: string, id: string) => {
    setPdfLoadingId(id)
    setPdfMessage(null)
    try {
      const blob = await downloadTickerPdf(ticker)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${ticker}-rapport.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setPdfMessage(`Aucun rapport disponible pour ${ticker} (pas d'historique).`)
      } else {
        setPdfMessage('Erreur lors du téléchargement du rapport PDF.')
      }
    } finally {
      setPdfLoadingId(null)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const t = ticker.trim().toUpperCase()
    if (!t) return
    if (entries.some((e) => e.ticker === t && e.workflow === workflow)) {
      setAddError(`${t} est déjà dans la watchlist pour ce workflow`)
      return
    }
    setAddError('')
    addMutation.mutate({ ticker: t, workflow })
  }

  if (isLoading) return <p className="text-muted-foreground">Chargement...</p>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Watchlist</h1>

      <form onSubmit={handleSubmit} className="flex gap-2" aria-label="Formulaire d'ajout watchlist">
        <Input
          placeholder="Ticker (ex: BNS)"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          aria-label="Ticker"
        />
        <select
          value={workflow}
          onChange={(e) => setWorkflow(e.target.value)}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          aria-label="Workflow"
        >
          <option value="value_graham">Value Graham</option>
          <option value="compounder_buffett">Compounder Buffett</option>
          <option value="fast_grower_lynch">Fast Grower Lynch</option>
          <option value="special_situation">Situation Spéciale</option>
          <option value="distressed_pabrai">Distressed Pabrai</option>
        </select>
        <Button type="submit" disabled={addMutation.isPending}>
          {addMutation.isPending ? 'Ajout...' : 'Ajouter'}
        </Button>
      </form>

      {addError && (
        <p data-testid="watchlist-error" className="text-sm text-destructive">{addError}</p>
      )}

      {lastJobId && (
        <p className="text-sm text-muted-foreground">Analyse lancée : {lastJobId}</p>
      )}

      {entries.length === 0 ? (
        <p className="text-muted-foreground">Aucun ticker en surveillance.</p>
      ) : (
        <>
          {pdfMessage && (
            <p className="text-sm text-muted-foreground">{pdfMessage}</p>
          )}
          <WatchlistTable
            entries={entries}
            onDelete={(id) => deleteMutation.mutate(id)}
            onAnalyze={(id) => analyzeMutation.mutate(id)}
            deletingId={deleteMutation.isPending ? (deleteMutation.variables ?? null) : null}
            analyzingId={analyzeMutation.isPending ? (analyzeMutation.variables ?? null) : null}
            onDownloadPdf={handleDownloadPdf}
            pdfLoadingId={pdfLoadingId}
          />
        </>
      )}
    </div>
  )
}
