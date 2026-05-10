import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { WorkflowSelector } from '../components/WorkflowSelector'
import { ScreenerTable } from '../components/ScreenerTable'
import { postScreen } from '../api/analyze'
import type { ScreenResult } from '../types'

export default function ScreenerPage() {
  const [tickersRaw, setTickersRaw] = useState('BNS, TD, RY')
  const [workflow, setWorkflow] = useState('value_graham')
  const [result, setResult] = useState<ScreenResult | null>(null)

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
    screenMutation.mutate({ tickers, workflow, max_parallel: 3 })
  }

  return (
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

      {screenMutation.isError && (
        <div className="border border-destructive bg-destructive/10 text-destructive rounded-lg px-4 py-3 text-sm">
          Erreur : {(screenMutation.error as Error).message}
        </div>
      )}

      {result && (
        <ScreenerTable
          entries={result.resultats}
          workflow={result.workflow}
          durationMs={result.duration_ms}
        />
      )}
    </div>
  )
}
