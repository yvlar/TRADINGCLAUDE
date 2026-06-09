import { useState, useEffect } from 'react'
import { ChevronDown, Zap, Settings2 } from 'lucide-react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Card, CardContent } from './ui/card'
import { WorkflowSelector } from './WorkflowSelector'
import { RatiosProvenanceNote } from './RatiosProvenanceNote'
import { getExtract } from '../api/analyze'
import { ApiError } from '../api/client'
import type { AnalyzeRequest, EarningsQualityRatios, GrahamRatios } from '../types'

interface AnalyzeFormProps {
  onSubmit: (req: AnalyzeRequest) => void
  isLoading?: boolean
  initialTicker?: string
}

type NumericRatioKey = {
  [K in keyof GrahamRatios]-?: NonNullable<GrahamRatios[K]> extends number ? K : never
}[keyof GrahamRatios]

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
  const [autoFillDone, setAutoFillDone] = useState(false)
  const [ratiosOpen, setRatiosOpen] = useState(false)

  useEffect(() => {
    function handlePrefill(e: Event) {
      const ev = e as CustomEvent<{ ticker: string; workflow: string }>
      setTicker(ev.detail.ticker.toUpperCase())
      setWorkflow(ev.detail.workflow)
      setAutoFillDone(false)
    }
    window.addEventListener('tradingclaude:prefill', handlePrefill)
    return () => window.removeEventListener('tradingclaude:prefill', handlePrefill)
  }, [])

  async function handleAutoFill() {
    if (!ticker.trim()) return
    setAutoFillLoading(true)
    setAutoFillError(null)
    setAutoFillDone(false)
    try {
      const result = await getExtract(ticker.trim().toUpperCase())
      setRatios((prev) => ({ ...prev, ...result.graham }))
      setEarningsRatios(result.earnings_quality)
      setAutoFillDone(true)
      setRatiosOpen(true)
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

  function setRatio(key: NumericRatioKey, val: string) {
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
  const earningsSourceLabel = earningsRatios
    ? `✓ chargé (${earningsRatios.ratios_source ?? 'Yahoo Finance'}${
        earningsRatios.ratios_fetched_at ? ` · ${earningsRatios.ratios_fetched_at.slice(0, 10)}` : ''
      })`
    : ''

  return (
    <form onSubmit={handleSubmit} aria-label="Formulaire d'analyse">
      <Card>
        <CardContent className="pt-5 space-y-5">
          {/* Ligne principale : ticker + auto-fill */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex flex-col gap-1.5 flex-1 min-w-0">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Symbole boursier
              </label>
              <Input
                value={ticker}
                onChange={(e) => {
                  setTicker(e.target.value.toUpperCase())
                  setAutoFillDone(false)
                }}
                placeholder="BNS"
                aria-label="Ticker"
                autoComplete="off"
                required
                className="text-base font-semibold tracking-wide h-11"
              />
            </div>

            {/* Auto-fill — CTA principal */}
            <div className="flex flex-col gap-1.5 sm:w-52">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Données automatiques
              </label>
              <Button
                type="button"
                variant={autoFillDone ? 'secondary' : 'default'}
                onClick={handleAutoFill}
                disabled={!ticker.trim() || autoFillLoading || isLoading}
                data-testid="autofill-button"
                className="h-11 gap-2"
              >
                <Zap size={15} className={autoFillLoading ? 'animate-pulse' : ''} />
                {autoFillLoading
                  ? 'Récupération…'
                  : autoFillDone
                  ? 'Données chargées ✓'
                  : 'Récupérer les données'}
              </Button>
            </div>
          </div>

          {autoFillError && (
            <p className="text-sm text-bear -mt-2" role="alert">{autoFillError}</p>
          )}

          {/* Workflow */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Stratégie d'analyse
            </label>
            <WorkflowSelector value={workflow} onChange={setWorkflow} />
          </div>

          {/* Ratios — section repliable */}
          <div className="border border-border/60 rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => setRatiosOpen((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3 text-sm text-muted-foreground hover:text-foreground hover:bg-white/3 transition-colors"
              aria-expanded={ratiosOpen}
              data-testid="ratios-section-toggle"
            >
              <span className="flex items-center gap-2">
                <Settings2 size={14} />
                <span className="font-medium">
                  Ratios financiers
                  {ratios.ratios_fetched_at && (
                    <span className="ml-2 text-xs text-bull font-normal">
                      · synchronisés {ratios.ratios_fetched_at.slice(0, 10)}
                    </span>
                  )}
                </span>
              </span>
              <ChevronDown
                size={14}
                className={`transition-transform duration-200 ${ratiosOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {ratiosOpen && (
              <div className="px-4 pb-4 pt-1 border-t border-border/40 space-y-4 animate-fade-in-up">
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
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
                    ] as [NumericRatioKey, string][]
                  ).map(([key, label]) => (
                    <div key={key} className="flex flex-col gap-1">
                      <label className="text-xs text-muted-foreground">{label}</label>
                      <Input
                        type="number"
                        step="any"
                        value={numField(ratios[key])}
                        onChange={(e) => setRatio(key, e.target.value)}
                        placeholder="—"
                        aria-label={label}
                        className="h-8 text-sm"
                      />
                      {key === 'eps_growth_total' && ratios.eps_growth_years != null && (
                        <span className="text-xs text-muted-foreground" data-testid="eps-growth-horizon">
                          sur {ratios.eps_growth_years} ans
                        </span>
                      )}
                    </div>
                  ))}
                </div>
                {ratios.ratios_fetched_at && (
                  <p className="text-xs text-muted-foreground" data-testid="ratios-source">
                    Source : {ratios.ratios_source ?? 'n.d.'} · {ratios.ratios_fetched_at.slice(0, 10)}
                  </p>
                )}
                <RatiosProvenanceNote provenance={ratios.ratios_provenance} />
              </div>
            )}
          </div>

          {/* Options supplémentaires */}
          <div className="rounded-lg border border-border/40 bg-secondary/20 px-4 py-3 space-y-2.5">
            <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium">Options d'analyse</p>

            <label
              className={`flex items-center gap-2.5 text-sm ${earningsAvailable ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}
              title={earningsAvailable ? undefined : 'Utilisez "Récupérer les données" pour activer cette option'}
              data-testid="earnings-label"
            >
              <input
                type="checkbox"
                checked={enableEarnings}
                onChange={(e) => setEnableEarnings(e.target.checked)}
                disabled={!earningsAvailable}
                className="accent-primary w-4 h-4 shrink-0"
                aria-label="Qualité bénéfices"
                data-testid="earnings-checkbox"
              />
              <span>Qualité des bénéfices</span>
              {earningsAvailable ? (
                <span className="text-xs text-bull font-medium" data-testid="earnings-source">
                  {earningsSourceLabel}
                </span>
              ) : (
                <span className="text-xs text-muted-foreground italic">(récupération automatique requise)</span>
              )}
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={enableThesis}
                onChange={(e) => {
                  setEnableThesis(e.target.checked)
                  if (!e.target.checked) setEnableMunger(false)
                }}
                className="accent-primary w-4 h-4 shrink-0"
              />
              <span>Thèse d'investissement</span>
              <span className="text-xs text-muted-foreground italic">(bull / base / bear)</span>
            </label>

            <label className={`flex items-center gap-2.5 text-sm ${!enableThesis ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}>
              <input
                type="checkbox"
                checked={enableMunger}
                disabled={!enableThesis}
                onChange={(e) => setEnableMunger(e.target.checked)}
                className="accent-primary w-4 h-4 shrink-0"
              />
              <span className={!enableThesis ? 'text-muted-foreground' : ''}>
                Analyse Munger
              </span>
              <span className="text-xs text-muted-foreground italic">(biais cognitifs — nécessite Thèse)</span>
            </label>
          </div>

          {/* Bouton principal */}
          <Button
            type="submit"
            disabled={isLoading || !ticker.trim()}
            className="w-full h-11 text-base font-semibold gap-2"
            size="lg"
          >
            {isLoading ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                Analyse en cours...
              </>
            ) : (
              'Analyser'
            )}
          </Button>
        </CardContent>
      </Card>
    </form>
  )
}
