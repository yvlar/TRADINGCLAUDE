import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { DorseyMoatOutput, MoatSource } from '../types'

// ---- Helpers visuels ----

function moatVariant(moatType: string): 'success' | 'warning' | 'danger' {
  const v = moatType.toUpperCase()
  if (v === 'WIDE') return 'success'
  if (v === 'NARROW') return 'warning'
  return 'danger'
}

function durabilityColor(durability: string): string {
  const v = durability.toUpperCase()
  if (v === 'FORTE') return 'text-bull'
  if (v === 'MODÉRÉE') return 'text-neutral'
  return 'text-bear'
}

function intensiteVariant(intensite: string): 'success' | 'warning' | 'danger' | 'secondary' {
  const v = intensite.toUpperCase()
  if (v === 'FORTE') return 'success'
  if (v === 'MODÉRÉE') return 'warning'
  if (v === 'FAIBLE') return 'danger'
  return 'secondary'
}

// Libellés français des 5 sources d'avantage concurrentiel de Dorsey
const SOURCE_LABELS: Record<string, string> = {
  intangibles: 'Actifs intangibles',
  switching_costs: 'Coûts de transfert',
  network_effects: 'Effets de réseau',
  cost_advantages: 'Avantages de coûts',
  efficient_scale: 'Échelle efficiente',
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

function SourceCard({ source }: { source: MoatSource }) {
  const label = SOURCE_LABELS[source.source] ?? source.source
  return (
    <Card className="bg-muted/30 border-border/60 p-3" data-testid={`moat-source-${source.source}`}>
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2">
          <span className={source.present ? 'text-bull font-bold' : 'text-bear font-bold'}>
            {source.present ? '✓' : '✗'}
          </span>
          <span className="text-sm font-medium">{label}</span>
        </div>
        <Badge variant={intensiteVariant(source.intensite)} className="text-xs">
          {source.intensite}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{source.justification}</p>
    </Card>
  )
}

// ---- Composant principal ----

interface DorseyMoatSectionProps {
  output: DorseyMoatOutput
}

export function DorseyMoatSection({ output }: DorseyMoatSectionProps) {
  const [open, setOpen] = useState(false)

  return (
    <Card>
      <CardHeader>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="dorsey-toggle"
        >
          <CardTitle>Dorsey Moat</CardTitle>
          <div className="flex items-center gap-3">
            <ConfidenceBar score={output.confidence_score} />
            <Badge variant={moatVariant(output.moat_type)} data-testid="dorsey-moat-type">
              {output.moat_type}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Durabilité du ROIC */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Durabilité du ROIC
            </span>
            <span className={`font-bold ${durabilityColor(output.roic_durability)}`} data-testid="dorsey-durability">
              {output.roic_durability}
            </span>
          </div>

          {/* Résumé */}
          {output.verdict_detail && (
            <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
              {output.verdict_detail}
            </p>
          )}

          {/* 5 sources d'avantage concurrentiel */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" data-testid="dorsey-sources">
            {output.sources_identifiees.map((s, i) => (
              <SourceCard key={i} source={s} />
            ))}
          </div>

          {/* Red flags */}
          {output.drapeaux_rouges.length > 0 && (
            <div className="flex flex-wrap gap-2" data-testid="dorsey-red-flags">
              {output.drapeaux_rouges.map((d, i) => (
                <Badge key={i} variant="danger" className="text-xs">⚠ {d}</Badge>
              ))}
            </div>
          )}

          {/* Recommandations */}
          {output.recommandation_prochaine_etape.length > 0 && (
            <div data-testid="dorsey-recommendations">
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
