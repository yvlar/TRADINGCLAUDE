import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { FisherOutput, FisherPoint } from '../types'

// Libellés français de la qualité de la direction (méthode scuttlebutt de Fisher)
const MANAGEMENT_LABELS: Record<string, string> = {
  EXCEPTIONNEL: 'Direction exceptionnelle',
  BON: 'Bonne direction',
  ADEQUAT: 'Direction adéquate',
  MEDIOCRE: 'Direction médiocre',
}

function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' {
  const v = verdict.toUpperCase()
  if (v === 'ACHAT_FORT' || v === 'ACHAT') return 'success'
  if (v === 'CONSERVER') return 'warning'
  return 'danger'
}

function managementVariant(quality: string): 'success' | 'warning' | 'danger' | 'secondary' {
  const v = quality.toUpperCase()
  if (v === 'EXCEPTIONNEL') return 'success'
  if (v === 'BON') return 'secondary'
  if (v === 'ADEQUAT') return 'warning'
  return 'danger'
}

// Chaque point Fisher est noté 0 (absent), 1 (partiel) ou 2 (pleinement satisfait)
function scoreColor(score: number): string {
  if (score >= 2) return 'text-bull'
  if (score === 1) return 'text-neutral'
  return 'text-bear'
}

function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = Math.round((score / max) * 100)
  const color = pct >= 70 ? 'bg-bull' : pct >= 40 ? 'bg-neutral' : 'bg-bear'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-secondary">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-semibold tabular-nums">
        {score}/{max}
      </span>
    </div>
  )
}

function PointRow({ point }: { point: FisherPoint }) {
  return (
    <div
      className="flex items-start gap-3 rounded-lg border border-border/60 bg-muted/30 p-2.5"
      data-testid="fisher-point"
    >
      <span className="text-xs font-mono text-muted-foreground mt-0.5 shrink-0">
        {point.point}.
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-snug">{point.titre}</p>
        <p className="text-xs text-muted-foreground leading-relaxed mt-0.5">{point.commentaire}</p>
      </div>
      <span className={`text-sm font-black tabular-nums shrink-0 ${scoreColor(point.score)}`}>
        {point.score}/2
      </span>
    </div>
  )
}

interface FisherSectionProps {
  output: FisherOutput
}

export function FisherSection({ output }: FisherSectionProps) {
  const [open, setOpen] = useState(false)
  const managementLabel =
    MANAGEMENT_LABELS[output.management_quality] ?? output.management_quality

  return (
    <Card>
      <CardHeader>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="fisher-toggle"
        >
          <CardTitle>Fisher Scuttlebutt</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={managementVariant(output.management_quality)} data-testid="fisher-management">
              {managementLabel}
            </Badge>
            <Badge variant={verdictVariant(output.verdict)} data-testid="fisher-verdict">
              {output.verdict}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Score Fisher global /30 */}
          <div data-testid="fisher-score">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Score Fisher (15 points)
            </p>
            <ScoreBar score={output.fisher_score} max={30} />
          </div>

          {/* Les 15 points évalués */}
          {output.points_evalues.length > 0 && (
            <div className="space-y-2" data-testid="fisher-points">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Les 15 points de Fisher
              </p>
              {output.points_evalues.map((p) => (
                <PointRow key={p.point} point={p} />
              ))}
            </div>
          )}

          {/* Résumé */}
          {output.verdict_detail && (
            <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
              {output.verdict_detail}
            </p>
          )}

          {/* Recommandations */}
          {output.recommandation_prochaine_etape.length > 0 && (
            <div data-testid="fisher-recommendations">
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
        </CardContent>
      )}
    </Card>
  )
}
