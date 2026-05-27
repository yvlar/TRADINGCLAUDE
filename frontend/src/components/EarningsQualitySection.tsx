import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type {
  EarningsQualityOutput,
  FScoreCriterion,
  CScoreSignal,
  MScoreDetail,
  ZScoreDetail,
  SloanDetail,
} from '../types'

// ---- Helpers visuels ----

function verdictColor(verdict: string): string {
  const v = verdict.toUpperCase()
  if (v === 'AUCUN_SIGNAL') return 'success'
  if (v === 'ATTENTION') return 'warning'
  if (v === 'WATCHLIST') return 'warning'
  return 'danger'
}

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct >= 80 ? 'bg-bull' : pct >= 60 ? 'bg-neutral' : 'bg-bear'
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-1.5 rounded-full bg-secondary">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground tabular-nums">{pct}%</span>
    </div>
  )
}

// ---- Sous-composants des cadres analytiques ----

function FScoreCard({ fscore }: { fscore: { criteria: FScoreCriterion[]; f_score: number; interpretation: string } }) {
  const score = fscore.f_score
  const color = score >= 7 ? 'text-bull' : score >= 4 ? 'text-neutral' : 'text-bear'
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Piotroski F-Score</span>
        <span className={`text-xl font-black tabular-nums ${color}`} data-testid="fscore-value">{score}/9</span>
      </div>
      <p className="text-xs text-muted-foreground italic">{fscore.interpretation}</p>
      <div className="space-y-1">
        {fscore.criteria.map((c, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span className={c.passe ? 'text-bull font-bold mt-0.5' : 'text-bear font-bold mt-0.5'}>
              {c.passe ? '✓' : '✗'}
            </span>
            <div>
              <span className="font-medium">{c.nom}</span>
              {c.detail && (
                <span className="text-muted-foreground ml-1">— {c.detail}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CScoreCard({ cscore }: { cscore: { signaux: CScoreSignal[]; c_score: number; interpretation: string } }) {
  const score = cscore.c_score
  // C-Score élevé = mauvais (signaux de manipulation)
  const color = score <= 1 ? 'text-bull' : score <= 3 ? 'text-neutral' : 'text-bear'
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Montier C-Score</span>
        <span className={`text-xl font-black tabular-nums ${color}`} data-testid="cscore-value">{score}/6</span>
      </div>
      <p className="text-xs text-muted-foreground italic">{cscore.interpretation}</p>
      <div className="space-y-1">
        {cscore.signaux.map((s, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span className={s.present ? 'text-bear font-bold mt-0.5' : 'text-bull font-bold mt-0.5'}>
              {s.present ? '⚠' : '✓'}
            </span>
            <div>
              <span className="font-medium">{s.nom}</span>
              {s.detail && (
                <span className="text-muted-foreground ml-1">— {s.detail}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function MScoreCard({ mscore }: { mscore: MScoreDetail }) {
  const score = mscore.m_score
  // M-Score > -1.78 = suspicion de manipulation
  const color =
    score === null
      ? 'text-muted-foreground'
      : score > -1.78
      ? 'text-bear'
      : 'text-bull'
  const ratios: { label: string; value: number | null }[] = [
    { label: 'DSRI', value: mscore.dsri },
    { label: 'GMI', value: mscore.gmi },
    { label: 'AQI', value: mscore.aqi },
    { label: 'SGI', value: mscore.sgi },
    { label: 'DEPI', value: mscore.depi },
    { label: 'SGAI', value: mscore.sgai },
    { label: 'TATA', value: mscore.tata },
    { label: 'LVGI', value: mscore.lvgi },
  ].filter((r) => r.value !== null)
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Beneish M-Score</span>
        <span className={`text-xl font-black tabular-nums ${color}`} data-testid="mscore-value">
          {score !== null ? score.toFixed(2) : 'N/A'}
        </span>
      </div>
      <p className="text-xs text-muted-foreground italic">{mscore.interpretation}</p>
      {ratios.length > 0 && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          {ratios.map((r) => (
            <div key={r.label} className="flex justify-between text-xs">
              <span className="text-muted-foreground">{r.label}</span>
              <span className="font-mono tabular-nums">{r.value!.toFixed(3)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ZScoreCard({ zscore }: { zscore: ZScoreDetail }) {
  const score = zscore.z_score
  const color =
    score === null
      ? 'text-muted-foreground'
      : score >= 2.99
      ? 'text-bull'
      : score >= 1.81
      ? 'text-neutral'
      : 'text-bear'
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Altman Z-Score
          <span className="ml-1 font-normal normal-case">({zscore.variante})</span>
        </span>
        <span className={`text-xl font-black tabular-nums ${color}`} data-testid="zscore-value">
          {score !== null ? score.toFixed(2) : 'N/A'}
        </span>
      </div>
      <p className="text-xs text-muted-foreground italic">{zscore.interpretation}</p>
    </div>
  )
}

function SloanCard({ sloan }: { sloan: SloanDetail }) {
  const ratio = sloan.accrual_ratio
  // Sloan accrual ratio : idéalement proche de 0 ; élevé = earnings de mauvaise qualité
  const color =
    ratio === null
      ? 'text-muted-foreground'
      : Math.abs(ratio) <= 0.05
      ? 'text-bull'
      : Math.abs(ratio) <= 0.1
      ? 'text-neutral'
      : 'text-bear'
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Sloan Accruals</span>
        <span className={`text-xl font-black tabular-nums ${color}`} data-testid="sloan-value">
          {ratio !== null ? (ratio * 100).toFixed(1) + '%' : 'N/A'}
        </span>
      </div>
      <p className="text-xs text-muted-foreground italic">{sloan.interpretation}</p>
    </div>
  )
}

// ---- Composant principal ----

interface EarningsQualitySectionProps {
  output: EarningsQualityOutput
}

export function EarningsQualitySection({ output }: EarningsQualitySectionProps) {
  const [open, setOpen] = useState(false)

  return (
    <Card>
      <CardHeader>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="eq-toggle"
        >
          <CardTitle>Earnings Quality</CardTitle>
          <div className="flex items-center gap-3">
            <ConfidenceBar score={output.confidence_score} />
            <Badge variant={verdictColor(output.verdict) as 'success' | 'warning' | 'danger'}>
              {output.verdict}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Résumé */}
          {output.verdict_detail && (
            <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
              {output.verdict_detail}
            </p>
          )}

          {/* Red flags */}
          {output.drapeaux_rouges.length > 0 && (
            <div className="flex flex-wrap gap-2" data-testid="eq-red-flags">
              {output.drapeaux_rouges.map((d, i) => (
                <Badge key={i} variant="danger" className="text-xs">⚠ {d}</Badge>
              ))}
            </div>
          )}

          {/* 5 cadres analytiques */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card className="bg-muted/30 border-border/60 p-4">
              <FScoreCard fscore={output.f_score} />
            </Card>
            <Card className="bg-muted/30 border-border/60 p-4">
              <CScoreCard cscore={output.c_score} />
            </Card>
            <Card className="bg-muted/30 border-border/60 p-4">
              <MScoreCard mscore={output.m_score} />
            </Card>
            <Card className="bg-muted/30 border-border/60 p-4">
              <ZScoreCard zscore={output.z_score} />
            </Card>
            <Card className="bg-muted/30 border-border/60 p-4 lg:col-span-2">
              <SloanCard sloan={output.sloan} />
            </Card>
          </div>

          {/* Recommandations */}
          {output.recommandation_prochaine_etape.length > 0 && (
            <div data-testid="eq-recommendations">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Prochaines étapes
              </p>
              <ul className="space-y-1">
                {output.recommandation_prochaine_etape.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="text-muted-foreground mt-1">→</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Note financière */}
          {output.is_financial && (
            <p className="text-xs text-muted-foreground italic border border-border/40 rounded px-3 py-2">
              Institution financière — M-Score et Z-Score peuvent être inapplicables (bilan atypique).
            </p>
          )}
        </CardContent>
      )}
    </Card>
  )
}
