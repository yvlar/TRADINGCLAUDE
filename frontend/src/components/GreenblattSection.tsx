import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { GreenblattOutput } from '../types'

function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' {
  const v = verdict.toUpperCase()
  if (v === 'TOP_DECILE' || v === 'BON') return 'success'
  if (v === 'MOYEN') return 'warning'
  return 'danger'
}

function Metric({ label, value, testid }: { label: string; value: number; testid: string }) {
  // ROC élevé = qualité ; earnings yield élevé = bon marché → plus c'est haut, plus c'est positif
  const pct = value * 100
  const color = pct >= 15 ? 'text-bull' : pct >= 7 ? 'text-neutral' : 'text-bear'
  return (
    <div data-testid={testid}>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">{label}</p>
      <span className={`text-2xl font-black tabular-nums ${color}`}>{pct.toFixed(1)}%</span>
    </div>
  )
}

interface GreenblattSectionProps {
  output: GreenblattOutput
}

export function GreenblattSection({ output }: GreenblattSectionProps) {
  const [open, setOpen] = useState(false)

  return (
    <Card>
      <CardHeader>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="greenblatt-toggle"
        >
          <CardTitle>Greenblatt Magic Formula</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={verdictVariant(output.verdict)} data-testid="greenblatt-verdict">
              {output.verdict}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* ROC + Earnings Yield — les deux piliers de la formule */}
          <div className="flex flex-wrap items-center gap-x-12 gap-y-3" data-testid="greenblatt-metrics">
            <Metric label="Rendement du capital (ROC)" value={output.roc} testid="greenblatt-roc" />
            <Metric label="Rendement des bénéfices" value={output.earnings_yield} testid="greenblatt-earnings-yield" />
          </div>

          {/* Situations spéciales */}
          {output.situations_speciales.length > 0 && (
            <div data-testid="greenblatt-situations">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Situations spéciales
              </p>
              <div className="flex flex-wrap gap-2">
                {output.situations_speciales.map((s, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">
                    {s}
                  </Badge>
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
            <div data-testid="greenblatt-recommendations">
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
