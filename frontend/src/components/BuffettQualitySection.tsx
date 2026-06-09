import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { BuffettQualityOutput, BuffettFiltre } from '../types'

// ---- Helpers visuels ----

function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' {
  const v = verdict.toUpperCase()
  if (v === 'COMPOUNDER') return 'success'
  if (v === 'QUALITE_CORRECTE') return 'warning'
  return 'danger'
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

function FiltreRow({ filtre, index }: { filtre: BuffettFiltre; index: number }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-border/40 last:border-0" data-testid={`buffett-filtre-${index}`}>
      <span className={filtre.passe ? 'text-bull font-bold mt-0.5' : 'text-bear font-bold mt-0.5'}>
        {filtre.passe ? '✓' : '✗'}
      </span>
      <div className="flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium">
            {index + 1}. {filtre.filtre}
          </span>
          <span className="text-xs text-muted-foreground tabular-nums shrink-0">{filtre.score}/1</span>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed mt-0.5">{filtre.justification}</p>
      </div>
    </div>
  )
}

// ---- Composant principal ----

interface BuffettQualitySectionProps {
  output: BuffettQualityOutput
}

export function BuffettQualitySection({ output }: BuffettQualitySectionProps) {
  const [open, setOpen] = useState(false)
  const qualityColor =
    output.quality_score >= 3 ? 'text-bull' : output.quality_score >= 2 ? 'text-neutral' : 'text-bear'

  return (
    <Card>
      <CardHeader>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="buffett-toggle"
        >
          <CardTitle>Buffett Quality</CardTitle>
          <div className="flex items-center gap-3">
            <span className={`text-xl font-black tabular-nums ${qualityColor}`} data-testid="buffett-quality-score">
              {output.quality_score}/4
            </span>
            <ConfidenceBar score={output.confidence_score} />
            <Badge variant={verdictVariant(output.verdict)} data-testid="buffett-verdict">
              {output.verdict}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Owner earnings — métrique signature de Buffett */}
          <div
            className="flex items-center justify-between border border-border/60 bg-muted/30 rounded-lg px-4 py-3"
            data-testid="buffett-owner-earnings"
          >
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Owner earnings</p>
              <p className="text-[11px] text-muted-foreground">Flux normalisé par action</p>
            </div>
            <span className="text-2xl font-black tabular-nums">
              {output.owner_earnings !== null ? `${output.owner_earnings.toFixed(2)} $` : 'N/A'}
            </span>
          </div>

          {/* Résumé */}
          {output.verdict_detail && (
            <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
              {output.verdict_detail}
            </p>
          )}

          {/* 4 filtres séquentiels */}
          <div data-testid="buffett-filtres">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
              Les 4 filtres
            </p>
            <div>
              {output.filtres.map((f, i) => (
                <FiltreRow key={i} filtre={f} index={i} />
              ))}
            </div>
          </div>

          {/* Red flags */}
          {output.drapeaux_rouges.length > 0 && (
            <div className="flex flex-wrap gap-2" data-testid="buffett-red-flags">
              {output.drapeaux_rouges.map((d, i) => (
                <Badge key={i} variant="danger" className="text-xs">⚠ {d}</Badge>
              ))}
            </div>
          )}

          {/* Recommandations */}
          {output.recommandation_prochaine_etape.length > 0 && (
            <div data-testid="buffett-recommendations">
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
