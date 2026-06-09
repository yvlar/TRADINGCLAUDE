import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import type { CanadianTaxOutput } from '../types'

// Libellés français des comptes canadiens (sigle EN entre parenthèses)
const COMPTE_LABELS: Record<string, string> = {
  CELI: 'CELI (TFSA)',
  REER: 'REER (RRSP)',
  CELIAPP: 'CELIAPP (FHSA)',
  NON_ENREGISTRE: 'Non enregistré',
}

// Les comptes enregistrés mettent l'investissement à l'abri de l'impôt → mis en avant
function compteVariant(compte: string): 'success' | 'secondary' {
  return compte.toUpperCase() === 'NON_ENREGISTRE' ? 'secondary' : 'success'
}

interface CanadianTaxSectionProps {
  output: CanadianTaxOutput
}

export function CanadianTaxSection({ output }: CanadianTaxSectionProps) {
  const [open, setOpen] = useState(false)
  const compteLabel = COMPTE_LABELS[output.compte_recommande] ?? output.compte_recommande

  return (
    <Card>
      <CardHeader>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center justify-between w-full text-left"
          aria-expanded={open}
          data-testid="tax-toggle"
        >
          <CardTitle>Fiscalité CA/QC</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={compteVariant(output.compte_recommande)} data-testid="tax-compte">
              {compteLabel}
            </Badge>
            <span className="text-muted-foreground text-xs">{open ? '▲' : '▼'}</span>
          </div>
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-6">
          {/* Justification de l'allocation par compte */}
          {output.justification_fiscale && (
            <div data-testid="tax-justification">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                Justification fiscale
              </p>
              <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
                {output.justification_fiscale}
              </p>
            </div>
          )}

          {/* Paramètres fiscaux clés */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div data-testid="tax-inclusion">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Inclusion gain en capital
              </p>
              <span className="text-2xl font-black tabular-nums text-foreground">
                {(output.taux_inclusion_gain_capital * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex flex-col gap-2">
              {output.strategie_smith_manoeuvre && (
                <Badge variant="warning" data-testid="tax-smith" className="w-fit">
                  Smith Manœuvre applicable
                </Badge>
              )}
            </div>
          </div>

          {/* Retenue à la source US */}
          {output.impact_retenue_us && (
            <div data-testid="tax-retenue-us">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Retenue à la source US
              </p>
              <p className="text-sm text-muted-foreground">{output.impact_retenue_us}</p>
            </div>
          )}

          {/* Recommandations */}
          {output.recommandation_prochaine_etape.length > 0 && (
            <div data-testid="tax-recommendations">
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
