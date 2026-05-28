import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { BiaisCognitif, MungerOutput } from '../types'

function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' {
  const v = verdict.toUpperCase()
  if (v === 'CONFIANCE_JUSTIFIEE') return 'success'
  if (v === 'BIAIS_DETECTE') return 'warning'
  return 'danger'
}

function impactVariant(impact: string): 'success' | 'warning' | 'danger' {
  const v = impact.toUpperCase()
  if (v === 'MINEUR') return 'success'
  if (v === 'MODERE') return 'warning'
  return 'danger'
}

function BiaisCard({ biais }: { biais: BiaisCognitif }) {
  return (
    <Card className="bg-muted/30 border-border/60 p-3" data-testid="munger-biais">
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="text-sm font-medium">{biais.nom}</span>
        <Badge variant={impactVariant(biais.impact_sur_these)} className="text-xs">
          {biais.impact_sur_these}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{biais.description}</p>
    </Card>
  )
}

interface MungerSectionProps {
  output: MungerOutput
}

export function MungerSection({ output }: MungerSectionProps) {
  const [open, setOpen] = useState(false)

  return (
    <Card>
      <CardHeader>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="munger-toggle"
        >
          <CardTitle>Munger Biais Cognitifs</CardTitle>
          <div className="flex items-center gap-2">
            {output.lollapalooza_risk && (
              <Badge variant="danger" data-testid="munger-lollapalooza">
                ⚠ Lollapalooza
              </Badge>
            )}
            <Badge variant={verdictVariant(output.verdict_comportemental)} data-testid="munger-verdict">
              {output.verdict_comportemental}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Biais détectés */}
          {output.biais_detectes.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" data-testid="munger-biais-list">
              {output.biais_detectes.map((b, i) => (
                <BiaisCard key={i} biais={b} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground" data-testid="munger-no-biais">
              Aucun biais cognitif significatif détecté.
            </p>
          )}

          {/* Analyse par inversion */}
          {output.inversion_analysis && (
            <div data-testid="munger-inversion">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Inversion — qu'est-ce qui ferait échouer cette thèse ?
              </p>
              <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
                {output.inversion_analysis}
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
            <div data-testid="munger-recommendations">
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
