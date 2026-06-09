import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { MarksOutput } from '../types'

// Libellés français des positions du pendule de sentiment (Howard Marks)
const POSITION_LABELS: Record<string, string> = {
  PESSIMISME_EXCESSIF: 'Pessimisme excessif',
  PESSIMISME: 'Pessimisme',
  NEUTRE: 'Neutre',
  OPTIMISME: 'Optimisme',
  EUPHORIE: 'Euphorie',
}

function timingVariant(timing: string): 'success' | 'warning' | 'danger' {
  const v = timing.toUpperCase()
  if (v === 'ACHETER_AGRESSIF' || v === 'ACHETER_PRUDEMMENT') return 'success'
  if (v === 'ATTENDRE') return 'warning'
  return 'danger'
}

// Logique contrariante : pendule négatif = pessimisme = opportunité ; positif = euphorie = risque
function penduleColor(score: number): string {
  if (score < 0) return 'text-bull'
  if (score > 0) return 'text-bear'
  return 'text-neutral'
}

// Jauge horizontale du pendule de -5 (pessimisme) à +5 (euphorie)
function PenduleGauge({ score }: { score: number }) {
  const pct = ((score + 5) / 10) * 100
  return (
    <div data-testid="marks-pendule">
      <div className="flex justify-between text-xs text-muted-foreground mb-1">
        <span>Pessimisme −5</span>
        <span>Euphorie +5</span>
      </div>
      <div className="relative h-2 rounded-full bg-gradient-to-r from-bull/40 via-neutral/40 to-bear/40">
        <div
          className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-foreground"
          style={{ left: `${pct}%` }}
        />
      </div>
      <div className="mt-2 text-center">
        <span className={`text-2xl font-black tabular-nums ${penduleColor(score)}`}>
          {score > 0 ? `+${score}` : score}
        </span>
      </div>
    </div>
  )
}

interface MarksSectionProps {
  output: MarksOutput
}

export function MarksSection({ output }: MarksSectionProps) {
  const [open, setOpen] = useState(false)
  const positionLabel = POSITION_LABELS[output.position_cycle] ?? output.position_cycle

  return (
    <Card>
      <CardHeader>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="marks-toggle"
        >
          <CardTitle>Marks Cycles</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" data-testid="marks-position">
              {positionLabel}
            </Badge>
            <Badge variant={timingVariant(output.recommandation_timing)} data-testid="marks-timing">
              {output.recommandation_timing}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Pendule de sentiment */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Pendule de sentiment
            </p>
            <PenduleGauge score={output.pendule_score} />
          </div>

          {/* Second-level thinking */}
          {output.second_level_insight && (
            <div data-testid="marks-insight">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Second-level thinking
              </p>
              <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
                {output.second_level_insight}
              </p>
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
            <div data-testid="marks-recommendations">
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
