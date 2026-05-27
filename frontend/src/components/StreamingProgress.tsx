import { Card, CardContent } from './ui/card'
import { Badge } from './ui/badge'
import type { AnalyzeResponse, SkillOutput, GrahamAnalysisOutput } from '../types'

const SKILL_LABELS: Record<string, string> = {
  graham_analysis: 'Graham Analysis',
  earnings_quality: 'Earnings Quality',
  dorsey_moat: 'Dorsey Moat',
  buffett_quality: 'Buffett Quality',
  stock_valuation_triangulation: 'Valorisation',
  investment_thesis_builder: "Thèse d'investissement",
  munger_mental_models: 'Munger Biais Cognitifs',
  canadian_tax_considerations: 'Fiscalité CA/QC',
  lynch_categories: 'Lynch Categories',
  fisher_scuttlebutt: 'Fisher Scuttlebutt',
  klarman_margin: 'Klarman Marge Sécurité',
  greenblatt_magic_formula: 'Greenblatt Magic Formula',
  damodaran_narrative: 'Damodaran Narrative',
  marks_cycles_risk: 'Marks Cycles',
  pabrai_dhandho: 'Pabrai Dhandho',
}

function skillVerdict(skillId: string, partial: Partial<AnalyzeResponse>): string | undefined {
  const fieldMap: Record<string, keyof AnalyzeResponse> = {
    graham_analysis: 'graham',
    earnings_quality: 'earnings_quality',
    dorsey_moat: 'dorsey',
    buffett_quality: 'buffett',
    stock_valuation_triangulation: 'valuation',
    investment_thesis_builder: 'thesis',
    munger_mental_models: 'munger',
    canadian_tax_considerations: 'canadian_tax',
    lynch_categories: 'lynch',
    fisher_scuttlebutt: 'fisher',
    klarman_margin: 'klarman',
    greenblatt_magic_formula: 'greenblatt',
    damodaran_narrative: 'damodaran',
    marks_cycles_risk: 'marks',
    pabrai_dhandho: 'pabrai',
  }
  const field = fieldMap[skillId]
  if (!field) return undefined
  const output = partial[field] as (SkillOutput & GrahamAnalysisOutput) | null | undefined
  return output?.verdict
}

function verdictVariant(verdict: string): 'success' | 'danger' | 'warning' | 'secondary' {
  const v = verdict.toUpperCase()
  if (v.includes('PASS') || v.includes('FORT') || v.includes('FAVORABLE')) return 'success'
  if (v.includes('FAIL') || v.includes('FAIBLE') || v.includes('DÉFAVORABLE')) return 'danger'
  if (v.includes('NEUTRE') || v.includes('MODÉRÉ') || v.includes('PARTIEL')) return 'warning'
  return 'secondary'
}

interface StreamingProgressProps {
  /** Skills planifiés (event `plan`) — détermine le pipeline complet et le dénominateur. */
  plannedSkills?: string[]
  completedSkills: string[]
  activeSkill: string | null
  partialResult: Partial<AnalyzeResponse>
}

export function StreamingProgress({
  plannedSkills = [],
  completedSkills,
  activeSkill,
  partialResult,
}: StreamingProgressProps) {
  // Pipeline ordonné : liste planifiée si disponible, sinon repli sur ce qui a été observé.
  const fallback = activeSkill ? [...completedSkills, activeSkill] : completedSkills
  const order = plannedSkills.length > 0 ? plannedSkills : fallback

  const total = order.length
  const done = completedSkills.length

  if (order.length === 0) return null

  const progressPct = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <div data-testid="streaming-progress" className="space-y-2">
      {/* barre de progression globale */}
      <div className="flex items-center gap-3 mb-3">
        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className="text-xs text-muted-foreground tabular-nums shrink-0">
          {done}/{total}
        </span>
      </div>

      {order.map((skillId, index) => {
        const isActive = skillId === activeSkill
        const isDone = completedSkills.includes(skillId)
        const isPending = !isActive && !isDone
        const verdict = isDone ? skillVerdict(skillId, partialResult) : undefined
        const label = SKILL_LABELS[skillId] ?? skillId
        const delay = Math.min(index * 40, 300)

        return (
          <div
            key={skillId}
            className="animate-fade-in-up"
            style={{ animationDelay: `${delay}ms` }}
          >
            <Card className={isActive ? 'border-primary/60' : isPending ? 'opacity-60' : ''}>
              <CardContent className="pt-3 pb-3">
                <div className="flex items-center gap-2">
                  {isActive ? (
                    <span
                      data-testid={`skill-active-${skillId}`}
                      className="relative flex h-3 w-3 shrink-0"
                      aria-label="En cours"
                    >
                      <span className="absolute inline-flex h-full w-full rounded-full bg-primary opacity-75 animate-ping" />
                      <span className="relative inline-flex h-3 w-3 rounded-full bg-primary" />
                    </span>
                  ) : isDone ? (
                    <span
                      data-testid={`skill-done-${skillId}`}
                      className="text-bull text-sm shrink-0"
                    >
                      ✓
                    </span>
                  ) : (
                    <span
                      data-testid={`skill-pending-${skillId}`}
                      className="h-3 w-3 shrink-0 rounded-full border border-muted-foreground/40"
                      aria-label="En attente"
                    />
                  )}
                  <span className={`text-sm font-medium ${isPending ? 'text-muted-foreground' : ''}`}>
                    {label}
                  </span>
                  {verdict && (
                    <Badge
                      variant={verdictVariant(verdict)}
                      className="ml-auto text-xs"
                    >
                      {verdict}
                    </Badge>
                  )}
                  {isActive && (
                    <span className="ml-auto text-xs text-muted-foreground animate-pulse">
                      En cours…
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )
      })}
    </div>
  )
}
