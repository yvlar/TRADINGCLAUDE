import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { WorkflowSelector } from '../components/WorkflowSelector'
import { ScreenerTable } from '../components/ScreenerTable'
import { Disclaimer } from '../components/Disclaimer'
import { SkeletonTable } from '../components/ui/skeleton'
import { PageTransition } from '../components/PageTransition'
import { QuotaBanner, isQuotaError } from '../components/QuotaBanner'
import { postScreen, exportScreen, downloadScreenerPdf } from '../api/analyze'
import type { ScreenRequest, ScreenResult } from '../types'

export default function ScreenerPage() {
  const [tickersRaw, setTickersRaw] = useState('BNS, TD, RY')
  const [workflow, setWorkflow] = useState('value_graham')
  const [result, setResult] = useState<ScreenResult | null>(null)
  const [lastRequest, setLastRequest] = useState<ScreenRequest | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)

  const screenMutation = useMutation({
    mutationFn: postScreen,
    onSuccess: (data) => setResult(data),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const tickers = tickersRaw
      .split(/[,\n]/)
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean)
    if (tickers.length === 0) return
    const req: ScreenRequest = { tickers, workflow, max_parallel: 3 }
    setLastRequest(req)
    screenMutation.mutate(req)
  }

  async function handleExport(format: 'csv' | 'xlsx') {
    if (!lastRequest) return
    try {
      const blob = await exportScreen(lastRequest, format)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `screener.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(`Erreur export : ${(e as Error).message}`)
    }
  }

  async function handleExportPdf() {
    if (!lastRequest) return
    setPdfLoading(true)
    try {
      const blob = await downloadScreenerPdf(lastRequest)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `screener-${lastRequest.workflow}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(`Erreur export PDF : ${(e as Error).message}`)
    } finally {
      setPdfLoading(false)
    }
  }

  return (
    <PageTransition>
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold mb-1">Screener multi-tickers</h2>
        <p className="text-sm text-muted-foreground">
          Analysez plusieurs tickers en parallèle. L'extraction automatique Yahoo Finance est
          utilisée si aucun ratio n'est fourni.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>Tickers à analyser</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground uppercase tracking-wide">
                Tickers (séparés par virgule ou retour à la ligne, max 20)
              </label>
              <textarea
                value={tickersRaw}
                onChange={(e) => setTickersRaw(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono resize-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                placeholder="BNS, TD, RY"
                aria-label="Tickers"
              />
            </div>

            <div className="flex flex-col gap-1 max-w-xs">
              <label className="text-xs text-muted-foreground uppercase tracking-wide">
                Workflow
              </label>
              <WorkflowSelector value={workflow} onChange={setWorkflow} />
            </div>

            <Button type="submit" disabled={screenMutation.isPending}>
              {screenMutation.isPending ? 'Screener en cours...' : 'Lancer le screener'}
            </Button>
          </CardContent>
        </Card>
      </form>

      {screenMutation.isError &&
        (isQuotaError(screenMutation.error) ? (
          <QuotaBanner message={(screenMutation.error as Error).message} />
        ) : (
          <div className="border border-destructive bg-destructive/10 text-destructive rounded-lg px-4 py-3 text-sm">
            Erreur : {(screenMutation.error as Error).message}
          </div>
        ))}

      {screenMutation.isPending && (
        <SkeletonTable rows={5} cols={7} />
      )}

      {result && (
        <>
          <div className="flex gap-3">
            <Button
              variant="outline"
              size="sm"
              data-testid="export-csv"
              onClick={() => void handleExport('csv')}
            >
              Exporter CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              data-testid="export-xlsx"
              onClick={() => void handleExport('xlsx')}
            >
              Exporter Excel
            </Button>
            <Button
              variant="outline"
              size="sm"
              data-testid="export-pdf"
              disabled={pdfLoading}
              onClick={() => void handleExportPdf()}
            >
              {pdfLoading ? 'Génération PDF...' : 'Exporter PDF'}
            </Button>
          </div>
          <ScreenerTable
            entries={result.resultats}
            workflow={result.workflow}
            durationMs={result.duration_ms}
          />
          <Disclaimer variant="inline" />
        </>
      )}
    </div>
    </PageTransition>
  )
}
