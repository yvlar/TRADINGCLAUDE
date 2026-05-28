import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import type { AnalyzeResponse, CompositeScore, GrahamCriterion } from '../types'
import { EarningsQualitySection } from './EarningsQualitySection'
import { ThesisSection } from './ThesisSection'
import { DorseyMoatSection } from './DorseyMoatSection'
import { BuffettQualitySection } from './BuffettQualitySection'
import { ValuationSection } from './ValuationSection'
import { LynchCategoriesSection } from './LynchCategoriesSection'
import { GreenblattSection } from './GreenblattSection'
import { MungerSection } from './MungerSection'
import { KlarmanSection } from './KlarmanSection'
import { FisherSection } from './FisherSection'
import { DamodaranSection } from './DamodaranSection'
import { MarksSection } from './MarksSection'
import { PabraiSection } from './PabraiSection'
import { CanadianTaxSection } from './CanadianTaxSection'

function verdictBadge(verdict: string | undefined) {
  if (!verdict) return null
  const v = verdict.toUpperCase()
  if (v === 'EXEMPLAIRE' || v === 'ACHETER' || v === 'ACHETER_FORT' || v === 'DHANDHO_FORT')
    return <Badge variant="success">{verdict}</Badge>
  if (v === 'CANDIDAT_SOLIDE' || v === 'ACCUMULER' || v === 'BON')
    return <Badge variant="success">{verdict}</Badge>
  if (v === 'WATCHLIST' || v === 'CONSERVER')
    return <Badge variant="warning">{verdict}</Badge>
  return <Badge variant="danger">{verdict}</Badge>
}

function CompositeBadge({ cs }: { cs: CompositeScore }) {
  const color =
    cs.label === 'FORT'
      ? 'text-bull'
      : cs.label === 'MODÉRÉ'
      ? 'text-neutral'
      : 'text-bear'
  return (
    <span
      data-testid="composite-score"
      className={`font-semibold tabular-nums text-sm ${color}`}
      title={`Skills inclus : ${cs.skills_inclus.join(', ')}`}
    >
      {cs.score.toFixed(1)}/100
      <span className="ml-1 text-xs text-muted-foreground">({cs.label})</span>
    </span>
  )
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

function CriteriaTable({ criteria }: { criteria: GrahamCriterion[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>#</TableHead>
          <TableHead>Critère</TableHead>
          <TableHead>Valeur</TableHead>
          <TableHead>Seuil</TableHead>
          <TableHead className="text-center">OK</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {criteria.map((c) => (
          <TableRow key={c.numero}>
            <TableCell className="text-muted-foreground">{c.numero}</TableCell>
            <TableCell>{c.nom}</TableCell>
            <TableCell className="font-mono text-xs">{c.valeur_observee}</TableCell>
            <TableCell className="font-mono text-xs text-muted-foreground">{c.seuil}</TableCell>
            <TableCell className="text-center">
              {c.passe === true ? (
                <span className="text-bull">✓</span>
              ) : (
                <span className="text-bear">✗</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

interface AnalysisResultProps {
  result: AnalyzeResponse
  onDownloadPdf?: () => void
  isPdfLoading?: boolean
}

export function AnalysisResult({ result, onDownloadPdf, isPdfLoading }: AnalysisResultProps) {
  const g = result.graham

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card>
        <CardContent className="pt-5">
          <div className="flex items-center gap-3 flex-wrap">
            <span data-testid="result-ticker" className="text-2xl font-black tracking-tight">{result.ticker}</span>
            {g && (
              <span data-testid="graham-score">
                <ScoreBar score={g.defensive_score} max={8} />
              </span>
            )}
            {g && <span data-testid="graham-verdict">{verdictBadge(g.verdict)}</span>}
            {result.composite_score && <CompositeBadge cs={result.composite_score} />}
            <span className="ml-auto text-xs text-muted-foreground tabular-nums">
              ${result.cost_usd.toFixed(4)} USD · {result.skills_applied.length} skill(s)
            </span>
            {onDownloadPdf && (
              <Button variant="outline" size="sm" onClick={onDownloadPdf} disabled={isPdfLoading}>
                {isPdfLoading ? 'Génération...' : '⬇ PDF'}
              </Button>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Workflow : <span className="font-medium">{result.workflow}</span> ·{' '}
            {new Date(result.created_at).toLocaleString('fr-CA')}
          </p>
        </CardContent>
      </Card>

      {/* Section Graham */}
      {g && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Graham Analysis</CardTitle>
              <span className="text-xs text-muted-foreground">
                Défensif {g.defensive_score}/8 · Entreprenant {g.enterprising_score}/5
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {g.marge_securite != null && (
              <p className="text-sm">
                Marge de sécurité :{' '}
                <span className={g.marge_securite >= 0 ? 'text-bull font-semibold' : 'text-bear font-semibold'}>
                  {(g.marge_securite * 100).toFixed(1)}%
                </span>
                {g.valeur_intrinseque_ajustee != null && (
                  <span className="text-muted-foreground ml-2">
                    (valeur ajustée : ${g.valeur_intrinseque_ajustee.toFixed(2)})
                  </span>
                )}
              </p>
            )}
            {g.drapeaux_rouges.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {g.drapeaux_rouges.map((d, i) => (
                  <Badge key={i} variant="danger" className="text-xs">
                    ⚠ {d}
                  </Badge>
                ))}
              </div>
            )}
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">Critères défensifs</p>
              <CriteriaTable criteria={g.criteria_defensif} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">Critères entrepreneuriaux</p>
              <CriteriaTable criteria={g.criteria_entreprenant} />
            </div>
            {g.verdict_detail && (
              <p className="text-sm text-muted-foreground border-t border-border pt-3">{g.verdict_detail}</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Autres skills */}
      {result.earnings_quality && (
        <EarningsQualitySection output={result.earnings_quality} />
      )}
      {result.dorsey && <DorseyMoatSection output={result.dorsey} />}
      {result.buffett && <BuffettQualitySection output={result.buffett} />}
      {result.valuation && <ValuationSection output={result.valuation} />}
      {result.lynch && <LynchCategoriesSection output={result.lynch} />}
      {result.fisher && <FisherSection output={result.fisher} />}
      {result.klarman && <KlarmanSection output={result.klarman} />}
      {result.greenblatt && <GreenblattSection output={result.greenblatt} />}
      {result.damodaran && <DamodaranSection output={result.damodaran} />}
      {result.marks && <MarksSection output={result.marks} />}
      {result.pabrai && <PabraiSection output={result.pabrai} />}
      {result.thesis && <ThesisSection output={result.thesis} />}
      {result.munger && <MungerSection output={result.munger} />}
      {result.canadian_tax && <CanadianTaxSection output={result.canadian_tax} />}
    </div>
  )
}
