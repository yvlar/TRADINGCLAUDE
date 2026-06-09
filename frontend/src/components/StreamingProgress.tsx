import { Badge } from './ui/badge'
import type { AnalyzeResponse, SkillOutput, GrahamAnalysisOutput } from '../types'

const SKILL_LABELS: Record<string, string> = {
  graham_analysis: 'Graham',
  earnings_quality: 'Qualité bénéfices',
  dorsey_moat: 'Dorsey Moat',
  buffett_quality: 'Buffett',
  stock_valuation_triangulation: 'Valorisation',
  investment_thesis_builder: 'Thèse',
  munger_mental_models: 'Munger',
  canadian_tax_considerations: 'Fiscalité CA',
  lynch_categories: 'Lynch',
  fisher_scuttlebutt: 'Fisher',
  klarman_margin: 'Klarman',
  greenblatt_magic_formula: 'Greenblatt',
  damodaran_narrative: 'Damodaran',
  marks_cycles_risk: 'Marks',
  pabrai_dhandho: 'Pabrai',
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
  if (v.includes('PASS') || v.includes('FORT') || v.includes('FAVORABLE') || v.includes('BON') || v.includes('ACHETER')) return 'success'
  if (v.includes('FAIL') || v.includes('FAIBLE') || v.includes('DÉFAVORABLE') || v.includes('ÉVITER')) return 'danger'
  if (v.includes('NEUTRE') || v.includes('MODÉRÉ') || v.includes('PARTIEL') || v.includes('WATCHLIST')) return 'warning'
  return 'secondary'
}

interface StreamingProgressProps {
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
  const fallback = activeSkill ? [...completedSkills, activeSkill] : completedSkills
  const order = plannedSkills.length > 0 ? plannedSkills : fallback

  const total = order.length
  const done = completedSkills.length

  if (order.length === 0) return null

  const progressPct = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <div data-testid="streaming-progress" className="space-y-3">
      {/* Barre de progression principale */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1 rounded-full bg-secondary overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progressPct}%` }}
            role="progressbar"
            aria-valuenow={progressPct}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
        <span className="text-xs text-muted-foreground tabular-nums shrink-0 font-medium">
          {done}/{total}
        </span>
      </div>

      {/* Steps en ligne — chips compacts */}
      <div className="flex flex-wrap gap-2">
        {order.map((skillId, index) => {
          const isActive = skillId === activeSkill
          const isDone = completedSkills.includes(skillId)
          const isPending = !isActive && !isDone
          const verdict = isDone ? skillVerdict(skillId, partialResult) : undefined
          const label = SKILL_LABELS[skillId] ?? skillId
          const delay = Math.min(index * 30, 250)

          return (
            <div
              key={skillId}
              className="animate-fade-in-up"
              style={{ animationDelay: `${delay}ms` }}
            >
              <div
                className={`
                  flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border transition-all duration-200
                  ${isActive
                    ? 'border-primary/50 bg-primary/10 text-primary'
                    : isDone
                    ? 'border-bull/30 bg-bull/8 text-foreground'
                    : 'border-border/40 bg-secondary/30 text-muted-foreground'
                  }
                `}
              >
                {/* Indicateur d'état */}
                {isActive ? (
                  <span
                    data-testid={`skill-active-${skillId}`}
                    className="relative flex h-2 w-2 shrink-0"
                    aria-label="En cours"
                  >
                    <span className="absolute inline-flex h-full w-full rounded-full bg-primary opacity-75 animate-ping" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                  </span>
                ) : isDone ? (
                  <span
                    data-testid={`skill-done-${skillId}`}
                    className="text-bull text-xs shrink-0 font-bold"
                  >
                    ✓
                  </span>
                ) : (
                  <span
                    data-testid={`skill-pending-${skillId}`}
                    className="h-2 w-2 shrink-0 rounded-full border border-muted-foreground/30"
                    aria-label="En attente"
                  />
                )}

                <span>{label}</span>

                {verdict && (
                  <Badge
                    variant={verdictVariant(verdict)}
                    className="text-[10px] px-1.5 py-0 h-4 ml-0.5"
                  >
                    {verdict}
                  </Badge>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Message en cours */}
      {activeSkill && (
        <p className="text-xs text-muted-foreground animate-pulse">
          Analyse en cours : <span className="font-medium text-foreground">{SKILL_LABELS[activeSkill] ?? activeSkill}</span>…
        </p>
      )}
    </div>
  )
}
