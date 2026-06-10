import { useState } from 'react'
import { ChevronDown, Download, FileText } from 'lucide-react'
import { Card, CardContent } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import type { AnalyzeResponse, CompositeScore, GrahamCriterion } from '../types'
import { EarningsQualitySection } from './EarningsQualitySection'
import { RatiosSourceNote } from './RatiosSourceNote'
import { RatiosProvenanceNote } from './RatiosProvenanceNote'
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
import { Disclaimer } from './Disclaimer'
import { VerdictDisclaimer } from './VerdictDisclaimer'

/** Détermine le variant couleur selon un verdict textuel */
function verdictVariant(verdict: string): 'success' | 'warning' | 'danger' | 'secondary' {
  const v = verdict.toUpperCase()
  if (v === 'EXEMPLAIRE' || v === 'ACHETER' || v === 'ACHETER_FORT' || v === 'DHANDHO_FORT' || v === 'CANDIDAT_SOLIDE' || v === 'ACCUMULER' || v === 'BON') return 'success'
  if (v === 'WATCHLIST' || v === 'CONSERVER') return 'warning'
  if (v === 'PASSER' || v === 'ÉVITER' || v === 'REFUSER' || v === 'FAIBLE') return 'danger'
  return 'secondary'
}

function verdictBadge(verdict: string | undefined) {
  if (!verdict) return null
  return <Badge variant={verdictVariant(verdict)} className="text-sm px-3 py-1">{verdict}</Badge>
}

/** Barre de progression colorée */
function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = Math.round((score / max) * 100)
  const color = pct >= 70 ? 'bg-bull' : pct >= 40 ? 'bg-neutral' : 'bg-bear'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-secondary overflow-hidden">
        <div className={`h-1.5 rounded-full ${color} transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-semibold tabular-nums text-foreground">
        {score}/{max}
      </span>
    </div>
  )
}

/** Score composite grand format */
function CompositeHero({ cs }: { cs: CompositeScore }) {
  const pct = Math.round(cs.score)
  const isFort = cs.label === 'FORT'
  const isMod = cs.label === 'MODÉRÉ'
  const colorClass = isFort ? 'text-bull' : isMod ? 'text-neutral' : 'text-bear'
  const bgClass = isFort ? 'bg-bull/10 border-bull/25' : isMod ? 'bg-neutral/10 border-neutral/25' : 'bg-bear/10 border-bear/25'
  const barColor = isFort ? 'bg-bull' : isMod ? 'bg-neutral' : 'bg-bear'
  const labelDesc = isFort ? 'Opportunité solide' : isMod ? 'Potentiel modéré' : 'Signaux faibles'

  return (
    <div className={`rounded-xl border px-5 py-4 ${bgClass}`}>
      <div className="flex items-start justify-between mb-2">
        <p className="text-xs text-muted-foreground uppercase tracking-wider">Score composite</p>
        <span className={`text-xs font-semibold ${colorClass}`}>{labelDesc}</span>
      </div>
      <div className="flex items-baseline gap-2 mb-3">
        <span data-testid="composite-score" className={`text-4xl font-black tabular-nums ${colorClass}`}>
          {pct}
        </span>
        <span className="text-lg text-muted-foreground font-medium">/100</span>
      </div>
      <div className="h-2 rounded-full bg-black/20 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ${barColor}`}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Score composite : ${pct} sur 100`}
        />
      </div>
    </div>
  )
}

/** Tableau des critères Graham condensé */
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
          <TableRow
            key={c.numero}
            className={c.passe === false ? 'bg-bear/5' : c.passe === true ? 'bg-bull/3' : ''}
          >
            <TableCell className="text-muted-foreground text-xs">{c.numero}</TableCell>
            <TableCell className="text-sm">{c.nom}</TableCell>
            <TableCell className="font-mono text-xs">{c.valeur_observee}</TableCell>
            <TableCell className="font-mono text-xs text-muted-foreground">{c.seuil}</TableCell>
            <TableCell className="text-center">
              {c.passe === true ? (
                <span className="text-bull font-bold">✓</span>
              ) : (
                <span className="text-bear font-bold">✗</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

/** Wrapper section repliable */
function CollapsibleSection({
  title,
  badge,
  children,
  defaultOpen = false,
  toggleTestId,
}: {
  title: string
  badge?: React.ReactNode
  children: React.ReactNode
  defaultOpen?: boolean
  toggleTestId?: string
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <Card>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between p-5 text-left hover:bg-white/4 transition-colors rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
        aria-expanded={open}
        data-testid={toggleTestId}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-foreground">{title}</span>
          {badge}
        </div>
        <ChevronDown
          size={15}
          className={`text-muted-foreground transition-transform duration-200 shrink-0 ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <div className="border-t border-border animate-fade-in-up">
          {children}
        </div>
      )}
    </Card>
  )
}

/** Chips de verdicts rapides pour chaque skill présent */
function VerdictSummaryRow({ result }: { result: AnalyzeResponse }) {
  const items: { label: string; verdict?: string; score?: string }[] = []

  if (result.graham) {
    items.push({ label: 'Graham', score: `${result.graham.defensive_score}/8`, verdict: result.graham.verdict })
  }
  if (result.earnings_quality) items.push({ label: 'Qualité', verdict: result.earnings_quality.verdict })
  if (result.dorsey) items.push({ label: 'Moat', verdict: result.dorsey.moat_type })
  if (result.buffett) items.push({ label: 'Buffett', verdict: result.buffett.verdict })
  if (result.valuation) items.push({ label: 'Valorisation', verdict: result.valuation.verdict })
  if (result.lynch) items.push({ label: 'Lynch', verdict: result.lynch.verdict })
  if (result.fisher) items.push({ label: 'Fisher', verdict: result.fisher.verdict })
  if (result.klarman) items.push({ label: 'Klarman', verdict: result.klarman.verdict })
  if (result.greenblatt) items.push({ label: 'Greenblatt', verdict: result.greenblatt.verdict })
  if (result.damodaran) items.push({ label: 'Damodaran', verdict: result.damodaran.verdict })
  if (result.marks) items.push({ label: 'Marks', verdict: result.marks.recommandation_timing })
  if (result.pabrai) items.push({ label: 'Pabrai', verdict: result.pabrai.verdict })

  if (items.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5 rounded-md border border-border/50 bg-secondary/30 px-2.5 py-1.5 min-h-[2rem]">
          <span className="text-xs font-medium text-muted-foreground">{item.label}</span>
          {item.score && (
            <span className="text-xs font-bold text-foreground tabular-nums">{item.score}</span>
          )}
          {item.verdict && (
            <Badge variant={verdictVariant(item.verdict)} className="text-xs px-2 py-0.5 font-semibold">
              {item.verdict}
            </Badge>
          )}
        </div>
      ))}
    </div>
  )
}

interface AnalysisResultProps {
  result: AnalyzeResponse
  onDownloadPdf?: () => void
  isPdfLoading?: boolean
  onExportAnalysis?: () => void
  isExportLoading?: boolean
}

export function AnalysisResult({
  result,
  onDownloadPdf,
  isPdfLoading,
  onExportAnalysis,
  isExportLoading,
}: AnalysisResultProps) {
  const g = result.graham

  return (
    <div className="space-y-3">
      {/* ───── Hero : ticker + verdict + score ───── */}
      <Card>
        <CardContent className="pt-5 pb-4">
          {/* Titre + verdict + actions */}
          <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <span data-testid="result-ticker" className="text-3xl font-black tracking-tight">
                  {result.ticker}
                </span>
                {g && (
                  <span data-testid="graham-verdict">
                    {verdictBadge(g.verdict)}
                  </span>
                )}
              </div>
              {result.composite_score && (
                <p className="text-sm text-muted-foreground mt-0.5">
                  Analyse {result.workflow.replace(/_/g, ' ')}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              {onExportAnalysis && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={onExportAnalysis}
                  disabled={isExportLoading}
                  data-testid="export-analysis-pdf"
                  className="gap-1.5"
                  title="Télécharger le rapport PDF de cette analyse"
                >
                  <FileText size={13} />
                  {isExportLoading ? 'Génération…' : 'Rapport PDF'}
                </Button>
              )}
              {onDownloadPdf && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onDownloadPdf}
                  disabled={isPdfLoading}
                  className="gap-1.5"
                  title="Générer un nouveau rapport avec les ratios actuels"
                >
                  <Download size={13} />
                  {isPdfLoading ? 'Génération…' : 'Rapport'}
                </Button>
              )}
            </div>
          </div>

          {/* Score composite + Graham score */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
            {result.composite_score && (
              <CompositeHero cs={result.composite_score} />
            )}
            {g && (
              <div className="rounded-xl border border-border/60 bg-secondary/30 px-5 py-4">
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Graham</p>
                <div className="flex items-baseline gap-2 mb-2">
                  <span data-testid="graham-score" className="text-4xl font-black tabular-nums text-foreground">
                    {g.defensive_score}
                  </span>
                  <span className="text-lg text-muted-foreground">/8</span>
                  {g.marge_securite != null && (
                    <span className={`text-sm font-semibold ml-2 ${g.marge_securite >= 0 ? 'text-bull' : 'text-bear'}`}>
                      {(g.marge_securite * 100).toFixed(1)}% marge
                    </span>
                  )}
                </div>
                <ScoreBar score={g.defensive_score} max={8} />
              </div>
            )}
          </div>

          {/* Résumé des verdicts par skill */}
          <VerdictSummaryRow result={result} />

          {(g?.verdict || result.composite_score) && (
            <div className="mt-3">
              <VerdictDisclaimer />
            </div>
          )}

          {/* Métadonnées — discrètes, sans les détails techniques internes */}
          <p className="text-xs text-muted-foreground/60 mt-3">
            {result.workflow}
            {' · '}
            {new Date(result.created_at).toLocaleString('fr-CA', {
              day: 'numeric', month: 'short', year: 'numeric',
              hour: '2-digit', minute: '2-digit',
            })}
            {' · '}
            {result.skills_applied.length} framework{result.skills_applied.length > 1 ? 's' : ''}
          </p>
        </CardContent>
      </Card>

      {/* ───── Section Graham — ouverte par défaut ───── */}
      {g && (
        <CollapsibleSection
          defaultOpen
          title="Graham Analysis"
          badge={
            <span className="text-xs text-muted-foreground">
              Défensif {g.defensive_score}/8 · Entreprenant {g.enterprising_score}/5
            </span>
          }
        >
          <CardContent className="space-y-4 pt-4">
            {g.graham_number != null && (
              <p className="text-sm" data-testid="graham-number">
                Nombre de Graham :{' '}
                <span className="font-semibold">${g.graham_number.toFixed(2)}</span>
                <span className="text-muted-foreground text-xs ml-2">√(22.5 × BPA × valeur comptable)</span>
              </p>
            )}
            {g.drapeaux_rouges.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {g.drapeaux_rouges.map((d, i) => (
                  <Badge key={i} variant="danger" className="text-xs">⚠ {d}</Badge>
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
            <RatiosSourceNote
              fetchedAt={result.ratios_fetched_at}
              source={result.ratios_source}
              testId="result-ratios-source"
            />
            <RatiosProvenanceNote provenance={result.ratios_provenance} testId="result-ratios-provenance" />
          </CardContent>
        </CollapsibleSection>
      )}

      {/* ───── Autres skills — repliés par défaut ───── */}
      {/* EarningsQualitySection a son propre toggle interne (data-testid="eq-toggle") */}
      {result.earnings_quality && (
        <EarningsQualitySection
          output={result.earnings_quality}
          ratiosFetchedAt={result.earnings_ratios_fetched_at}
          ratiosSource={result.earnings_ratios_source}
        />
      )}
      {/* Toutes les sections suivantes ont leur propre toggle interne — rendu direct */}
      {result.dorsey && <DorseyMoatSection output={result.dorsey} />}
      {result.buffett && <BuffettQualitySection output={result.buffett} />}
      {result.valuation && (
        <ValuationSection
          output={result.valuation}
          ratiosFetchedAt={result.valuation_ratios_fetched_at}
          ratiosSource={result.valuation_ratios_source}
        />
      )}
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

      <Disclaimer variant="inline" />
    </div>
  )
}
