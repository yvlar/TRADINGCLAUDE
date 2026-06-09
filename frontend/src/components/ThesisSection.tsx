import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { ThesisBuilderOutput, ThesisScenario } from '../types'

// ---- Helpers visuels ----

function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' {
  const v = verdict.toUpperCase()
  if (v === 'ACHETER') return 'success'
  if (v === 'ACCUMULER') return 'success'
  if (v === 'CONSERVER') return 'warning'
  return 'danger'
}

function formatRendement(r: number): string {
  const pct = (r * 100).toFixed(0)
  return r >= 0 ? `+${pct}%` : `${pct}%`
}

function rendementColor(r: number): string {
  return r >= 0 ? 'text-bull' : 'text-bear'
}

// ---- Carte de scénario ----

interface ScenarioCardProps {
  label: 'Bull' | 'Base' | 'Bear'
  scenario: ThesisScenario
}

function ScenarioCard({ label, scenario }: ScenarioCardProps) {
  const pct = Math.round(scenario.probabilite * 100)
  const borderColor =
    label === 'Bull' ? 'border-bull/40' : label === 'Bear' ? 'border-bear/40' : 'border-neutral/40'
  const barColor =
    label === 'Bull' ? 'bg-bull' : label === 'Bear' ? 'bg-bear' : 'bg-neutral'
  const labelColor =
    label === 'Bull' ? 'text-bull' : label === 'Bear' ? 'text-bear' : 'text-neutral'

  return (
    <Card className={`border ${borderColor} bg-muted/20`} data-testid={`scenario-${label.toLowerCase()}`}>
      <CardContent className="pt-4 space-y-3">
        {/* En-tête scénario */}
        <div className="flex items-center justify-between">
          <span className={`text-sm font-bold uppercase tracking-wide ${labelColor}`}>{label}</span>
          <span className={`text-xl font-black tabular-nums ${rendementColor(scenario.rendement_cible)}`}>
            {formatRendement(scenario.rendement_cible)}
          </span>
        </div>

        {/* Barre de probabilité */}
        <div>
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>Probabilité</span>
            <span className="font-semibold tabular-nums">{pct}%</span>
          </div>
          <div className="h-2 rounded-full bg-secondary">
            <div className={`h-2 rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
          </div>
        </div>

        {/* Hypothèses clés */}
        {scenario.hypotheses.length > 0 && (
          <ul className="space-y-1">
            {scenario.hypotheses.map((h, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <span className="mt-0.5 shrink-0">•</span>
                <span>{h}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

// ---- Composant principal ----

interface ThesisSectionProps {
  output: ThesisBuilderOutput
}

export function ThesisSection({ output }: ThesisSectionProps) {
  const [open, setOpen] = useState(false)

  return (
    <Card>
      <CardHeader>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="thesis-toggle"
        >
          <CardTitle>Thèse d&apos;investissement</CardTitle>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground tabular-nums">
              Position : <span className="font-semibold text-foreground">{output.position_size_pct.toFixed(1)}%</span>
            </span>
            <Badge variant={verdictVariant(output.verdict_final)} data-testid="thesis-verdict">
              {output.verdict_final}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* 3 scénarios côte à côte */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3" data-testid="thesis-scenarios">
            <ScenarioCard label="Bull" scenario={output.scenario_bull} />
            <ScenarioCard label="Base" scenario={output.scenario_base} />
            <ScenarioCard label="Bear" scenario={output.scenario_bear} />
          </div>

          {/* Kill criteria */}
          {output.kill_criteria.length > 0 && (
            <div data-testid="thesis-kill-criteria">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Critères d&apos;invalidation (kill criteria)
              </p>
              <ul className="space-y-1">
                {output.kill_criteria.map((k, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="text-bear font-bold mt-0.5 shrink-0">✗</span>
                    <span>{k}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Devil's advocate */}
          {output.devils_advocate && (
            <div
              className="border border-warning/30 bg-warning/5 rounded-lg px-4 py-3"
              data-testid="thesis-devils-advocate"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Argument contraire principal
              </p>
              <p className="text-sm">{output.devils_advocate}</p>
            </div>
          )}

          {/* Synthèse narrative */}
          {output.synthese_narrative && (
            <div data-testid="thesis-narrative">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Thèse formelle
              </p>
              <div className="space-y-3">
                {output.synthese_narrative.split('\n\n').map((para, i) => (
                  <p key={i} className="text-sm leading-relaxed">
                    {para.trim()}
                  </p>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}
