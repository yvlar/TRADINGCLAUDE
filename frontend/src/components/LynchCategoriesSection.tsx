import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { LynchCategoriesOutput } from '../types'

// Libellés français des 6 catégories de Lynch (One Up on Wall Street)
const CATEGORIE_LABELS: Record<string, string> = {
  SLOW_GROWER: 'Croissance lente',
  STALWART: 'Pilier',
  FAST_GROWER: 'Croissance rapide',
  CYCLICAL: 'Cyclique',
  TURNAROUND: 'Redressement',
  ASSET_PLAY: "Jeu d'actifs",
}

function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' {
  const v = verdict.toUpperCase()
  if (v === 'EXCELLENT' || v === 'BON') return 'success'
  if (v === 'MOYEN') return 'warning'
  return 'danger'
}

// PEG < 1 = bon marché vs croissance ; 1-2 = correct ; > 2 = cher
function pegColor(peg: number | null): string {
  if (peg == null) return 'text-muted-foreground'
  if (peg < 1) return 'text-bull'
  if (peg <= 2) return 'text-neutral'
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

interface LynchCategoriesSectionProps {
  output: LynchCategoriesOutput
}

export function LynchCategoriesSection({ output }: LynchCategoriesSectionProps) {
  const [open, setOpen] = useState(false)
  const categorieLabel = CATEGORIE_LABELS[output.categorie] ?? output.categorie

  return (
    <Card data-testid="lynch-category">
      <CardHeader>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="lynch-toggle"
        >
          <CardTitle>Lynch Categories</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" data-testid="lynch-categorie">
              {categorieLabel}
            </Badge>
            <Badge variant={verdictVariant(output.verdict)} data-testid="lynch-verdict">
              {output.verdict}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* PEG + tenbagger */}
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <div data-testid="lynch-peg">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Ratio PEG
              </p>
              <span className={`text-2xl font-black tabular-nums ${pegColor(output.peg_ratio)}`}>
                {output.peg_ratio != null ? output.peg_ratio.toFixed(2) : 'N/A'}
              </span>
            </div>
            {output.tenbagger_potential && (
              <Badge variant="success" data-testid="lynch-tenbagger">
                ★ Tenbagger potentiel
              </Badge>
            )}
          </div>

          {/* Score de qualité de croissance */}
          <div data-testid="lynch-score">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Qualité de croissance
            </p>
            <ScoreBar score={output.score_croissance} max={5} />
          </div>

          {/* Résumé */}
          {output.verdict_detail && (
            <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
              {output.verdict_detail}
            </p>
          )}

          {/* Recommandations */}
          {output.recommandation_prochaine_etape.length > 0 && (
            <div data-testid="lynch-recommendations">
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
