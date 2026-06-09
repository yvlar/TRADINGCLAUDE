import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { DhandhoPrincipe, PabraiOutput } from '../types'

function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' {
  const v = verdict.toUpperCase()
  if (v === 'DHANDHO_FORT') return 'success'
  if (v === 'DHANDHO_MOYEN') return 'warning'
  return 'danger'
}

// Asymétrie = upside / |downside| : > 3 très favorable, 1-3 correct, < 1 défavorable
function asymetrieColor(ratio: number): string {
  if (ratio >= 3) return 'text-bull'
  if (ratio >= 1) return 'text-neutral'
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

function PrincipeRow({ principe }: { principe: DhandhoPrincipe }) {
  return (
    <div
      className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-muted/30 p-2.5"
      data-testid="pabrai-principe"
    >
      <span className={`mt-0.5 shrink-0 ${principe.satisfait ? 'text-bull' : 'text-bear'}`}>
        {principe.satisfait ? '✓' : '✗'}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-snug">{principe.nom}</p>
        <p className="text-xs text-muted-foreground leading-relaxed mt-0.5">{principe.commentaire}</p>
      </div>
    </div>
  )
}

interface PabraiSectionProps {
  output: PabraiOutput
}

export function PabraiSection({ output }: PabraiSectionProps) {
  const [open, setOpen] = useState(false)

  return (
    <Card>
      <CardHeader>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="pabrai-toggle"
        >
          <CardTitle>Pabrai Dhandho</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={verdictVariant(output.verdict)} data-testid="pabrai-verdict">
              {output.verdict}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Asymétrie + Kelly fractionnel */}
          <div className="flex flex-wrap items-center gap-x-12 gap-y-3" data-testid="pabrai-metrics">
            <div data-testid="pabrai-asymetrie">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Asymétrie (upside / downside)
              </p>
              <span className={`text-2xl font-black tabular-nums ${asymetrieColor(output.asymetrie)}`}>
                {output.asymetrie.toFixed(1)}×
              </span>
            </div>
            <div data-testid="pabrai-kelly">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Kelly fractionnel
              </p>
              <span className="text-2xl font-black tabular-nums text-foreground">
                {output.kelly_fractionnel != null
                  ? `${(output.kelly_fractionnel * 100).toFixed(1)}%`
                  : 'N/A'}
              </span>
            </div>
          </div>

          {/* Heads I win, tails I don't lose much */}
          <div data-testid="pabrai-score">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Heads I win — principes satisfaits
            </p>
            <ScoreBar score={output.heads_i_win_score} max={9} />
          </div>

          {/* Les 9 principes Dhandho */}
          {output.principes_dhandho.length > 0 && (
            <div className="space-y-2" data-testid="pabrai-principes">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Les 9 principes Dhandho
              </p>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
                {output.principes_dhandho.map((p, i) => (
                  <PrincipeRow key={i} principe={p} />
                ))}
              </div>
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
            <div data-testid="pabrai-recommendations">
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
