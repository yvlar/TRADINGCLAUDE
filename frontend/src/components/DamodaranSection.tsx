import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { DamodaranOutput } from '../types'

// Échelle de crédibilité de la narrative : POSSIBLE < PLAUSIBLE < PROBABLE (Damodaran)
const COHERENCE_LADDER = ['POSSIBLE', 'PLAUSIBLE', 'PROBABLE'] as const

const COHERENCE_LABELS: Record<string, string> = {
  POSSIBLE: 'Possible',
  PLAUSIBLE: 'Plausible',
  PROBABLE: 'Probable',
  INCOHERENT: 'Incohérent',
}

function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' {
  const v = verdict.toUpperCase()
  if (v === 'NARRATIVE_FORTE') return 'success'
  if (v === 'NARRATIVE_ACCEPTABLE') return 'warning'
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

// Affiche l'échelle possible → plausible → probable avec le niveau atteint mis en évidence
function CoherenceLadder({ level }: { level: string }) {
  const incoherent = level.toUpperCase() === 'INCOHERENT'
  const reachedIndex = COHERENCE_LADDER.indexOf(level.toUpperCase() as (typeof COHERENCE_LADDER)[number])

  return (
    <div className="flex items-center gap-2" data-testid="damodaran-ladder">
      {COHERENCE_LADDER.map((step, i) => {
        const active = !incoherent && i <= reachedIndex
        return (
          <div
            key={step}
            className={`flex-1 rounded-md border px-2 py-1.5 text-center text-xs font-semibold ${
              active ? 'border-bull/40 bg-bull/15 text-bull' : 'border-border bg-muted/30 text-muted-foreground'
            }`}
          >
            {COHERENCE_LABELS[step]}
          </div>
        )
      })}
      {incoherent && (
        <div className="flex-1 rounded-md border border-bear/40 bg-bear/15 px-2 py-1.5 text-center text-xs font-semibold text-bear">
          Incohérent
        </div>
      )}
    </div>
  )
}

interface DamodaranSectionProps {
  output: DamodaranOutput
}

export function DamodaranSection({ output }: DamodaranSectionProps) {
  const [open, setOpen] = useState(false)
  const coherenceLabel = COHERENCE_LABELS[output.test_coherence] ?? output.test_coherence

  return (
    <Card>
      <CardHeader>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="damodaran-toggle"
        >
          <CardTitle>Damodaran Narrative</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" data-testid="damodaran-coherence">
              {coherenceLabel}
            </Badge>
            <Badge variant={verdictVariant(output.verdict)} data-testid="damodaran-verdict">
              {output.verdict}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Test de cohérence story → numbers */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Test story → numbers
            </p>
            <CoherenceLadder level={output.test_coherence} />
          </div>

          {/* Solidité de la narrative + ERP implicite */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div data-testid="damodaran-strength">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Solidité de la narrative
              </p>
              <ScoreBar score={output.narrative_strength} max={10} />
            </div>
            {output.erp_implied != null && (
              <div data-testid="damodaran-erp">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                  Prime de risque implicite (ERP)
                </p>
                <span className="text-2xl font-black tabular-nums text-foreground">
                  {(output.erp_implied * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>

          {/* Divergences story vs numbers */}
          {output.divergences_detectees.length > 0 && (
            <div data-testid="damodaran-divergences">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Divergences détectées
              </p>
              <div className="flex flex-wrap gap-2">
                {output.divergences_detectees.map((d, i) => (
                  <Badge key={i} variant="danger" className="text-xs">
                    ⚠ {d}
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
            <div data-testid="damodaran-recommendations">
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
