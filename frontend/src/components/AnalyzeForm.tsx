import { useState } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { WorkflowSelector } from './WorkflowSelector'
import { getExtract } from '../api/analyze'
import { ApiError } from '../api/client'
import type { AnalyzeRequest, EarningsQualityRatios, GrahamRatios } from '../types'

interface AnalyzeFormProps {
  onSubmit: (req: AnalyzeRequest) => void
  isLoading?: boolean
  initialTicker?: string
}

const DEFAULT_RATIOS: GrahamRatios = {
  pe: 11.0,
  pb: 1.3,
  current_ratio: null,
  debt_equity: 0.45,
  eps_growth_total: 0.27,
  price: 80.0,
  book_value: 61.5,
  eps_ttm: 7.25,
  revenue_bn: 38,
  dividend_years: 190,
}

function numField(v: number | null | undefined): string {
  return v != null ? String(v) : ''
}

function parseNum(s: string): number | null {
  const v = parseFloat(s)
  return isNaN(v) ? null : v
}

export function AnalyzeForm({ onSubmit, isLoading = false, initialTicker = '' }: AnalyzeFormProps) {
  const [ticker, setTicker] = useState(initialTicker)
  const [workflow, setWorkflow] = useState('value_graham')
  const [ratios, setRatios] = useState<GrahamRatios>(DEFAULT_RATIOS)
  const [earningsRatios, setEarningsRatios] = useState<EarningsQualityRatios | null>(null)
  const [enableThesis, setEnableThesis] = useState(false)
  const [enableMunger, setEnableMunger] = useState(false)
  const [enableEarnings, setEnableEarnings] = useState(false)
  const [autoFillLoading, setAutoFillLoading] = useState(false)
  const [autoFillError, setAutoFillError] = useState<string | null>(null)

  async function handleAutoFill() {
    if (!ticker.trim()) return
    setAutoFillLoading(true)
    setAutoFillError(null)
    try {
      const result = await getExtract(ticker.trim().toUpperCase())
      setRatios((prev) => ({ ...prev, ...result.graham }))
      setEarningsRatios(result.earnings_quality)
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setAutoFillError('Ticker introuvable — vérifiez le symbole boursier')
      } else {
        setAutoFillError('Erreur de connexion — réessayez')
      }
    } finally {
      setAutoFillLoading(false)
    }
  }

  function setRatio(key: keyof GrahamRatios, val: string) {
    setRatios((prev) => ({ ...prev, [key]: parseNum(val) }))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const req: AnalyzeRequest = {
      ticker: ticker.trim().toUpperCase(),
      ratios,
      workflow,
      ...(enableThesis && { thesis_ratios: true }),
      ...(enableMunger && { munger_ratios: true }),
      ...(enableEarnings && earningsRatios !== null && { earnings_ratios: earningsRatios }),
    }
    onSubmit(req)
  }

  const earningsAvailable = earningsRatios !== null

  return (
    <form onSubmit={handleSubmit} aria-label="Formulaire d'analyse">
      <div className="flex gap-3 mb-4">
        <div className="flex flex-col gap-1 w-48">
          <label className="text-xs text-muted-foreground uppercase tracking-wide">Ticker</label>
          <div className="flex gap-2">
            <Input
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="BNS"
              aria-label="Ticker"
              autoComplete="off"
              required
              className="flex-1"
            />
            <Button
              type="button"
              variant="outline"
              onClick={handleAutoFill}
              disabled={!ticker.trim() || autoFillLoading}
              data-testid="autofill-button"
            >
              {autoFillLoading ? '...' : 'Auto-fill'}
            </Button>
          </div>
          {autoFillError && (
            <p className="text-sm text-bear" role="alert">{autoFillError}</p>
          )}
        </div>
        <div className="flex flex-col gap-1 flex-1">
          <label className="text-xs text-muted-foreground uppercase tracking-wide">Workflow</label>
          <WorkflowSelector value={workflow} onChange={setWorkflow} />
        </div>
      </div>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Ratios Graham</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {(
              [
                ['pe', 'P/E'],
                ['pb', 'P/B'],
                ['current_ratio', 'Current Ratio'],
                ['debt_equity', 'Debt/Equity'],
                ['eps_growth_total', 'Croissance EPS (totale)'],
                ['price', 'Prix ($)'],
                ['book_value', 'Valeur comptable'],
                ['eps_ttm', 'EPS TTM'],
                ['revenue_bn', 'Revenus (Md$)'],
                ['dividend_years', 'Années dividendes'],
              ] as [keyof GrahamRatios, string][]
            ).map(([key, label]) => (
              <div key={key} className="flex flex-col gap-1">
                <label className="text-xs text-muted-foreground">{label}</label>
                <Input
                  type="number"
                  step="any"
                  value={numField(ratios[key])}
                  onChange={(e) => setRatio(key, e.target.value)}
                  placeholder="null"
                  aria-label={label}
                />
                {key === 'eps_growth_total' && ratios.eps_growth_years != null && (
                  <span className="text-xs text-muted-foreground" data-testid="eps-growth-horizon">
                    sur {ratios.eps_growth_years} ans
                  </span>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Options</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <label
              className={`flex items-center gap-2 text-sm ${earningsAvailable ? 'cursor-pointer' : 'cursor-not-allowed text-muted-foreground'}`}
              title={earningsAvailable ? undefined : 'Utiliser Auto-fill pour charger les données'}
              data-testid="earnings-label"
            >
              <input
                type="checkbox"
                checked={enableEarnings}
                onChange={(e) => setEnableEarnings(e.target.checked)}
                disabled={!earningsAvailable}
                className="accent-primary w-4 h-4"
                aria-label="Qualité bénéfices"
                data-testid="earnings-checkbox"
              />
              Qualité bénéfices
              {earningsAvailable ? (
                <span className="text-xs text-bull font-medium">✓ chargé (Yahoo Finance)</span>
              ) : (
                <span className="text-xs">(Auto-fill requis)</span>
              )}
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={enableThesis}
                onChange={(e) => {
                  setEnableThesis(e.target.checked)
                  if (!e.target.checked) setEnableMunger(false)
                }}
                className="accent-primary w-4 h-4"
              />
              Thèse d'investissement
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={enableMunger}
                disabled={!enableThesis}
                onChange={(e) => setEnableMunger(e.target.checked)}
                className="accent-primary w-4 h-4"
              />
              <span className={!enableThesis ? 'text-muted-foreground' : ''}>
                Munger (nécessite Thèse)
              </span>
            </label>
          </div>
        </CardContent>
      </Card>

      <Button type="submit" disabled={isLoading} className="w-full sm:w-auto">
        {isLoading ? 'Analyse en cours...' : 'Analyser'}
      </Button>
    </form>
  )
}
