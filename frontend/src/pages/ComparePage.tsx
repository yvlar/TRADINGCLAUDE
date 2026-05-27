import { useState, useRef } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { postCompare } from '../api/compare'
import { postAnalyze, streamAnalyze } from '../api/analyze'
import { ApiError } from '../api/client'
import { SkeletonTable } from '../components/ui/skeleton'
import { PageTransition } from '../components/PageTransition'
import type { CompareResponse, TickerComparison } from '../types'

type Row = {
  label: string
  key: keyof TickerComparison
}

const ROWS: Row[] = [
  { label: 'Score Graham', key: 'graham_score' },
  { label: 'Verdict Graham', key: 'graham_verdict' },
  { label: 'Verdict Buffett', key: 'buffett_verdict' },
  { label: 'Type Moat', key: 'dorsey_moat_type' },
  { label: 'Score composite', key: 'composite_score' },
  { label: 'Label composite', key: 'composite_label' },
  { label: 'Date analyse', key: 'created_at' },
]

function verdictBadgeClass(value: string | null | undefined): string {
  if (!value) return 'bg-muted text-muted-foreground'
  const v = value.toUpperCase()
  if (v === 'FORT' || v === 'COMPOUNDER' || v === 'WIDE' || v === 'ACHETER') return 'bg-green-100 text-green-800'
  if (v === 'MODERE' || v === 'NARROW' || v === 'CONSERVER') return 'bg-yellow-100 text-yellow-800'
  if (v === 'FAIBLE' || v === 'REJETER' || v === 'NONE' || v === 'EVITER') return 'bg-red-100 text-red-800'
  return 'bg-muted text-muted-foreground'
}

function formatCellValue(key: keyof TickerComparison, value: unknown): string {
  if (value === null || value === undefined) return '--'
  if (key === 'composite_score') return (value as number).toFixed(1)
  if (key === 'created_at') return (value as string).slice(0, 10)
  return String(value)
}

function isBadgeRow(key: keyof TickerComparison): boolean {
  return ['graham_verdict', 'buffett_verdict', 'dorsey_moat_type', 'composite_label'].includes(key)
}

export default function ComparePage() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CompareResponse | null>(null)
  const [analyzingTickers, setAnalyzingTickers] = useState<Set<string>>(new Set())
  const [tickerErrors, setTickerErrors] = useState<Record<string, string>>({})
  const [streamingEnabled, setStreamingEnabled] = useState(false)
  const [tickerStreamSkill, setTickerStreamSkill] = useState<Record<string, string>>({})
  const errorTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  const handleAnalyze = async (ticker: string) => {
    if (!result) return

    setAnalyzingTickers((prev) => new Set([...prev, ticker]))
    if (errorTimers.current[ticker]) clearTimeout(errorTimers.current[ticker])
    setTickerErrors((prev) => { const n = { ...prev }; delete n[ticker]; return n })

    try {
      if (streamingEnabled) {
        const streamPromise = (async () => {
          for await (const event of streamAnalyze({ ticker, ratios: null, workflow: 'value_graham' })) {
            if (event.type === 'skill_start') {
              setTickerStreamSkill((prev) => ({ ...prev, [ticker]: event.data.skill_id }))
            } else if (event.type === 'skill_result') {
              setTickerStreamSkill((prev) => ({ ...prev, [ticker]: event.data.skill_id }))
            } else if (event.type === 'error') {
              throw new Error(event.data.message)
            }
          }
        })()
        await Promise.race([
          streamPromise,
          new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error('Délai dépassé (60s)')), 60_000),
          ),
        ])
      } else {
        await Promise.race([
          postAnalyze({ ticker, ratios: null, workflow: 'value_graham' }),
          new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error('Délai dépassé (60s)')), 60_000),
          ),
        ])
      }
      setTickerStreamSkill((prev) => { const n = { ...prev }; delete n[ticker]; return n })
      const refreshed = await postCompare(result.tickers)
      setResult(refreshed)
    } catch (e) {
      let msg = "Erreur lors de l'analyse."
      if (e instanceof ApiError) msg = e.message
      else if (e instanceof Error) msg = e.message
      setTickerErrors((prev) => ({ ...prev, [ticker]: msg }))
      setTickerStreamSkill((prev) => { const n = { ...prev }; delete n[ticker]; return n })
      errorTimers.current[ticker] = setTimeout(() => {
        setTickerErrors((prev) => { const n = { ...prev }; delete n[ticker]; return n })
      }, 5_000)
    } finally {
      setAnalyzingTickers((prev) => {
        const n = new Set(prev)
        n.delete(ticker)
        return n
      })
    }
  }

  const handleSubmit = async () => {
    setError(null)
    const tickers = input
      .split(',')
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean)

    if (tickers.length < 2) {
      setError('Entrez au moins 2 tickers séparés par des virgules.')
      return
    }
    if (tickers.length > 5) {
      setError('Maximum 5 tickers par comparaison.')
      return
    }

    setLoading(true)
    try {
      const data = await postCompare(tickers)
      setResult(data)
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message)
      } else {
        setError('Erreur lors de la comparaison.')
      }
    } finally {
      setLoading(false)
    }
  }

  const bestScoreIndex = result
    ? result.comparisons.reduce(
        (best, c, i) => {
          const score = c.composite_score
          if (score === null) return best
          if (best.index === -1 || score > best.score) return { index: i, score }
          return best
        },
        { index: -1, score: -Infinity },
      ).index
    : -1

  return (
    <PageTransition>
    <div className="space-y-6">
      <h2 className="text-xl font-bold">Comparaison de tickers</h2>

      <div className="flex gap-2 items-center flex-wrap">
        <Input
          data-testid="compare-ticker-input"
          placeholder="Ex : BNS.TO, TD.TO, RY.TO"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="max-w-sm"
          onKeyDown={(e) => { if (e.key === 'Enter') void handleSubmit() }}
        />
        <Button
          data-testid="compare-submit-btn"
          onClick={() => void handleSubmit()}
          disabled={loading}
        >
          {loading ? 'Chargement…' : 'Comparer'}
        </Button>
        <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            data-testid="streaming-toggle"
            checked={streamingEnabled}
            onChange={(e) => setStreamingEnabled(e.target.checked)}
            className="h-4 w-4 accent-primary"
          />
          Streaming en direct
        </label>
      </div>

      {error && (
        <p className="text-sm text-destructive" data-testid="compare-error">{error}</p>
      )}

      {loading && <SkeletonTable rows={7} cols={4} />}

      {result && (
        <div className="overflow-x-auto">
          <table
            data-testid="compare-table"
            className="w-full border-collapse text-sm"
          >
            <thead>
              <tr>
                <th className="text-left p-2 border-b border-border font-semibold w-40">Métrique</th>
                {result.comparisons.map((c, i) => (
                  <th
                    key={c.ticker}
                    className={`text-center p-2 border-b border-border font-semibold ${
                      i === bestScoreIndex ? 'bg-yellow-50' : ''
                    }`}
                    data-testid={`compare-col-${c.ticker}`}
                  >
                    {c.ticker}
                    {c.analysis_id === null && (
                      <div className="mt-1 space-y-1">
                        <Button
                          data-testid={`analyze-btn-${c.ticker}`}
                          size="sm"
                          variant="outline"
                          className="text-xs h-6 px-2 font-normal"
                          disabled={analyzingTickers.has(c.ticker)}
                          onClick={() => void handleAnalyze(c.ticker)}
                        >
                          {analyzingTickers.has(c.ticker) ? 'Analyse…' : 'Analyser'}
                        </Button>
                        {analyzingTickers.has(c.ticker) && streamingEnabled && tickerStreamSkill[c.ticker] && (
                          <span
                            data-testid={`stream-skill-${c.ticker}`}
                            className="text-xs text-muted-foreground truncate max-w-[120px] block"
                          >
                            {tickerStreamSkill[c.ticker]}
                          </span>
                        )}
                        {tickerErrors[c.ticker] && (
                          <p
                            data-testid={`analyze-error-${c.ticker}`}
                            className="text-xs text-red-600 font-normal"
                          >
                            {tickerErrors[c.ticker]}
                          </p>
                        )}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.key} className="border-b border-border last:border-0">
                  <td className="p-2 text-muted-foreground font-medium">{row.label}</td>
                  {result.comparisons.map((c, i) => {
                    const val = c[row.key]
                    const formatted = formatCellValue(row.key, val)
                    const isHighlighted = row.key === 'composite_score' && i === bestScoreIndex
                    return (
                      <td
                        key={c.ticker}
                        className={`text-center p-2 ${isHighlighted ? 'bg-yellow-100 font-semibold' : ''}`}
                        data-testid={`compare-cell-${row.key}-${c.ticker}`}
                      >
                        {isBadgeRow(row.key) && val !== null ? (
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${verdictBadgeClass(val as string)}`}
                          >
                            {formatted}
                          </span>
                        ) : (
                          formatted
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
    </PageTransition>
  )
}
