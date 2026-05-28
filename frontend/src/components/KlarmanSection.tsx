import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { KlarmanOutput } from '../types'

// Libellés français des types de situation qualifiés par Klarman
const SITUATION_LABELS: Record<string, string> = {
  NET_NET: 'Net-net',
  ACTIFS_CACHES: 'Actifs cachés',
  DISTRESSED: 'En détresse',
  SPECIAL_SITUATION: 'Situation spéciale',
  VALEUR_CLASSIQUE: 'Valeur classique',
}

function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' | 'secondary' {
  const v = verdict.toUpperCase()
  if (v === 'OPPORTUNITE_FORTE') return 'success'
  if (v === 'OPPORTUNITE_MODEREE') return 'warning'
  if (v === 'ATTENDRE') return 'secondary'
  return 'danger'
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

interface KlarmanSectionProps {
  output: KlarmanOutput
}

export function KlarmanSection({ output }: KlarmanSectionProps) {
  const [open, setOpen] = useState(false)
  const situationLabel = SITUATION_LABELS[output.situation_type_qualifie] ?? output.situation_type_qualifie

  return (
    <Card>
      <CardHeader>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="klarman-toggle"
        >
          <CardTitle>Klarman Marge Sécurité</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" data-testid="klarman-situation">
              {situationLabel}
            </Badge>
            <Badge variant={verdictVariant(output.verdict)} data-testid="klarman-verdict">
              {output.verdict}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Décote vs valeur intrinsèque */}
          {output.discount_to_intrinsic != null && (
            <div data-testid="klarman-discount">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Décote vs valeur intrinsèque
              </p>
              <span
                className={`text-2xl font-black tabular-nums ${
                  output.discount_to_intrinsic >= 0 ? 'text-bull' : 'text-bear'
                }`}
              >
                {(output.discount_to_intrinsic * 100).toFixed(1)}%
              </span>
            </div>
          )}

          {/* Scores 0-10 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div data-testid="klarman-marge-score">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Marge de sécurité
              </p>
              <ScoreBar score={output.marge_securite_score} max={10} />
            </div>
            <div data-testid="klarman-preservation-score">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Préservation du capital
              </p>
              <ScoreBar score={output.preservation_capital_score} max={10} />
            </div>
          </div>

          {/* Résumé */}
          {output.verdict_detail && (
            <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
              {output.verdict_detail}
            </p>
          )}

          {/* Recommandations */}
          {output.recommandation_prochaine_etape.length > 0 && (
            <div data-testid="klarman-recommendations">
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
