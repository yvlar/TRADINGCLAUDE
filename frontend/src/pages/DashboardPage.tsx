import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader } from '../components/ui/card'
import { MetricsDashboard } from '../components/MetricsDashboard'
import { CompositeScoreHistory } from '../components/CompositeScoreHistory'
import { CompositeScoreChart } from '../components/CompositeScoreChart'
import { TickerComparisonChart } from '../components/TickerComparisonChart'
import { ConflictsList } from '../components/ConflictsList'
import { loadRecentAnalyses } from '../lib/recentAnalyses'
import { getCompositeHistory, fetchEvalDrift } from '../api/analyze'
import type { CompositeHistoryPoint, EvalDriftResult, RecentAnalysis } from '../types'

function compositeColor(label: string): string {
  if (label === 'FORT') return 'text-green-400'
  if (label === 'MODÉRÉ') return 'text-yellow-400'
  return 'text-red-400'
}

function TickerQualityCard({ analysis }: { analysis: RecentAnalysis }) {
  const [open, setOpen] = useState(false)
  const cs = analysis.composite_score

  return (
    <Card>
      <CardHeader>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid={`dashboard-ticker-${analysis.ticker}`}
        >
          <div className="flex items-center gap-3">
            <span className="font-bold tracking-tight">{analysis.ticker}</span>
            {cs && (
              <span
                data-testid="composite-score"
                className={`font-semibold tabular-nums text-sm ${compositeColor(cs.label)}`}
                title={`Skills inclus : ${cs.skills_inclus.join(', ')}`}
              >
                {cs.score.toFixed(1)}/100
                <span className="ml-1 text-xs text-muted-foreground">({cs.label})</span>
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground">
              {new Date(analysis.created_at).toLocaleDateString('fr-CA')} · {analysis.workflow}
            </span>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
              Conflits inter-skills
            </p>
            <ConflictsList conflicts={analysis.inter_skill_conflicts} />
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
              Historique composite_score
            </p>
            <CompositeScoreHistory ticker={analysis.ticker} />
          </div>
        </CardContent>
      )}
    </Card>
  )
}

function QualitySection() {
  const recent = loadRecentAnalyses()

  if (recent.length === 0) {
    return (
      <Card>
        <CardContent className="pt-5">
          <p className="text-sm text-muted-foreground" data-testid="no-recent-analyses">
            Aucune analyse récente. Lancez une analyse depuis l'onglet{' '}
            <strong>Analyse</strong> pour voir les métriques qualité ici.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3" data-testid="quality-section">
      <h3 className="text-base font-semibold">Qualité IA — analyses récentes</h3>
      {recent.map((a) => (
        <TickerQualityCard key={a.ticker} analysis={a} />
      ))}
    </div>
  )
}

function CompositeChartSection() {
  const [inputValue, setInputValue] = useState('')
  const [activeTicker, setActiveTicker] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['composite-history-chart', activeTicker],
    queryFn: () => getCompositeHistory(activeTicker!, 90),
    enabled: !!activeTicker,
  })

  function handleCharger() {
    const ticker = inputValue.trim().toUpperCase()
    if (ticker) setActiveTicker(ticker)
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-base font-semibold">Évolution composite score</h3>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCharger()}
            placeholder="Ticker (ex: BNS)"
            className="flex-1 rounded border border-input bg-background px-3 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            data-testid="chart-ticker-input"
          />
          <button
            onClick={handleCharger}
            className="rounded bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            disabled={!inputValue.trim()}
            data-testid="chart-charger-btn"
          >
            Charger
          </button>
        </div>
        {activeTicker && (
          <CompositeScoreChart
            data={data ?? []}
            isLoading={isLoading}
            isError={isError}
          />
        )}
      </CardContent>
    </Card>
  )
}

function ComparisonSection() {
  const [inputValue, setInputValue] = useState('')
  const [activeTickers, setActiveTickers] = useState<string[]>([])
  const [tickersData, setTickersData] = useState<Map<string, CompositeHistoryPoint[]>>(new Map())
  const [isLoading, setIsLoading] = useState(false)
  const [isError, setIsError] = useState(false)

  const isValid = inputValue.split(',').filter((t) => t.trim().length > 0).length >= 2

  async function handleComparer() {
    const parsed = inputValue
      .split(',')
      .map((t) => t.trim().toUpperCase())
      .filter((t) => t.length > 0)
      .slice(0, 5)
    if (parsed.length < 2) return

    setIsLoading(true)
    setIsError(false)
    setActiveTickers(parsed)

    try {
      const results = await Promise.all(parsed.map((t) => getCompositeHistory(t, 90)))
      const newMap = new Map<string, CompositeHistoryPoint[]>()
      parsed.forEach((t, i) => newMap.set(t, results[i]))
      setTickersData(newMap)
    } catch {
      setIsError(true)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-base font-semibold">Comparaison composite score — multi-tickers</h3>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">
          Entrez 2 à 5 tickers séparés par des virgules pour comparer leur évolution.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && isValid && handleComparer()}
            placeholder="BNS,TD,RY (2-5 tickers)"
            className="flex-1 rounded border border-input bg-background px-3 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            data-testid="comparison-tickers-input"
          />
          <button
            onClick={handleComparer}
            className="rounded bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            disabled={!isValid || isLoading}
            data-testid="comparison-comparer-btn"
          >
            {isLoading ? 'Chargement…' : 'Comparer'}
          </button>
        </div>
        {activeTickers.length >= 2 && (
          <TickerComparisonChart
            tickers={activeTickers}
            tickersData={tickersData}
            isLoading={isLoading}
            isError={isError}
          />
        )}
      </CardContent>
    </Card>
  )
}

function EvalDriftSection() {
  const [results, setResults] = useState<EvalDriftResult[]>([])

  useEffect(() => {
    fetchEvalDrift().then(setResults)
  }, [])

  return (
    <Card>
      <CardHeader>
        <h3 className="text-base font-semibold" data-testid="eval-drift-title">
          Eval Drift — concordance des golden datasets
        </h3>
      </CardHeader>
      <CardContent>
        {results.length === 0 ? (
          <p className="text-sm text-muted-foreground" data-testid="eval-drift-empty">
            Aucune donnée de drift disponible.
          </p>
        ) : (
          <div className="space-y-4" data-testid="eval-drift-list">
            {results.map((r) => {
              const pct = Math.round(r.concordance_rate * 100)
              return (
                <div key={r.dataset} className="space-y-1" data-testid={`eval-drift-row-${r.dataset}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{r.dataset}</span>
                    {r.alert ? (
                      <span
                        className="rounded px-2 py-0.5 text-xs font-semibold bg-red-600 text-white"
                        data-testid={`eval-drift-badge-alert-${r.dataset}`}
                      >
                        DRIFT DÉTECTÉ
                      </span>
                    ) : (
                      <span
                        className="rounded px-2 py-0.5 text-xs font-semibold bg-green-600 text-white"
                        data-testid={`eval-drift-badge-ok-${r.dataset}`}
                      >
                        OK
                      </span>
                    )}
                  </div>
                  <div
                    className="h-2 w-full rounded bg-muted overflow-hidden"
                    aria-label={`Concordance ${pct}%`}
                  >
                    <div
                      className={`h-full rounded transition-all ${r.alert ? 'bg-red-500' : 'bg-green-500'}`}
                      style={{ width: `${pct}%` }}
                      data-testid={`eval-drift-bar-${r.dataset}`}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {r.cases_pass}/{r.cases_total} cas — {pct}% — dernier check :{' '}
                    {new Date(r.recorded_at).toLocaleString('fr-CA')}
                  </p>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold mb-1">Dashboard</h2>
        <p className="text-sm text-muted-foreground">
          Métriques live et qualité IA — composite_score, conflits inter-skills, historique.
        </p>
      </div>

      <MetricsDashboard />

      <CompositeChartSection />

      <ComparisonSection />

      <EvalDriftSection />

      <QualitySection />
    </div>
  )
}
