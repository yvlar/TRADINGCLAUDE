import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { RatiosSourceNote } from './RatiosSourceNote'
import type { StockValuationOutput, ValuationMethod, SensitivityMatrix } from '../types'

// ---- Helpers visuels ----

function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' {
  const v = verdict.toUpperCase()
  if (v === 'SOUS_EVALUE') return 'success'
  if (v === 'JUSTE_VALEUR') return 'warning'
  return 'danger'
}

// Libellés français des 3 méthodes de triangulation
const METHODE_LABELS: Record<string, string> = {
  dcf: 'DCF (flux actualisés)',
  comparables: 'Multiples comparables',
  sectoriel: 'Méthode sectorielle',
}

function formatDollar(v: number | null): string {
  return v !== null ? `${v.toFixed(2)} $` : 'N/A'
}

function MethodCard({ methode }: { methode: ValuationMethod }) {
  const label = METHODE_LABELS[methode.methode] ?? methode.methode
  return (
    <Card className="bg-muted/30 border-border/60 p-3" data-testid={`valuation-methode-${methode.methode}`}>
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</span>
        <span className="text-lg font-black tabular-nums">{formatDollar(methode.valeur)}</span>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{methode.hypotheses}</p>
    </Card>
  )
}

function SensitivityTable({ matrix }: { matrix: SensitivityMatrix }) {
  return (
    <div className="overflow-x-auto" data-testid="valuation-sensitivity">
      <table className="text-xs border-collapse">
        <thead>
          <tr>
            <th className="px-2 py-1 text-left text-muted-foreground font-semibold">
              WACC \ Croissance
            </th>
            {matrix.growth_range.map((g, j) => (
              <th key={j} className="px-2 py-1 text-right text-muted-foreground font-semibold tabular-nums">
                {(g * 100).toFixed(1)}%
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.values.map((row, i) => (
            <tr key={i} className="border-t border-border/40">
              <td className="px-2 py-1 text-muted-foreground font-semibold tabular-nums">
                {(matrix.wacc_range[i] * 100).toFixed(1)}%
              </td>
              {row.map((val, j) => (
                <td key={j} className="px-2 py-1 text-right font-mono tabular-nums">
                  {val.toFixed(2)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---- Composant principal ----

interface ValuationSectionProps {
  output: StockValuationOutput
  ratiosFetchedAt?: string | null
  ratiosSource?: string | null
}

export function ValuationSection({
  output,
  ratiosFetchedAt,
  ratiosSource,
}: ValuationSectionProps) {
  const [open, setOpen] = useState(false)
  const margePct = Math.round(output.marge_securite_composite * 100)
  const margeColor = output.marge_securite_composite >= 0 ? 'text-bull' : 'text-bear'

  return (
    <Card>
      <CardHeader>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="valuation-toggle"
        >
          <CardTitle>Valorisation</CardTitle>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground tabular-nums">
              Marge :{' '}
              <span className={`font-semibold ${margeColor}`} data-testid="valuation-marge">
                {margePct >= 0 ? `+${margePct}` : margePct}%
              </span>
            </span>
            <Badge variant={verdictVariant(output.verdict)} data-testid="valuation-verdict">
              {output.verdict}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Fourchette de juste valeur */}
          <div className="grid grid-cols-3 gap-2" data-testid="valuation-fourchette">
            <div className="text-center rounded-lg bg-muted/30 border border-border/60 py-2">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Basse</p>
              <p className="text-lg font-bold tabular-nums">{formatDollar(output.fourchette_basse)}</p>
            </div>
            <div className="text-center rounded-lg bg-neutral/10 border border-neutral/40 py-2">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Centrale</p>
              <p className="text-xl font-black tabular-nums" data-testid="valuation-centrale">
                {formatDollar(output.fourchette_centrale)}
              </p>
            </div>
            <div className="text-center rounded-lg bg-muted/30 border border-border/60 py-2">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Haute</p>
              <p className="text-lg font-bold tabular-nums">{formatDollar(output.fourchette_haute)}</p>
            </div>
          </div>

          {/* Résumé */}
          {output.verdict_detail && (
            <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
              {output.verdict_detail}
            </p>
          )}

          {/* 3 méthodes de triangulation */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3" data-testid="valuation-methodes">
            {output.methodes.map((m, i) => (
              <MethodCard key={i} methode={m} />
            ))}
          </div>

          {/* Matrice de sensibilité */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Sensibilité (valeur centrale, $ / action)
            </p>
            <SensitivityTable matrix={output.matrice_sensibilite} />
          </div>

          {/* Recommandations */}
          {output.recommandation_prochaine_etape.length > 0 && (
            <div data-testid="valuation-recommendations">
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

          <RatiosSourceNote
            fetchedAt={ratiosFetchedAt}
            source={ratiosSource}
            testId="valuation-ratios-source"
          />
        </CardContent>
      )}
    </Card>
  )
}
