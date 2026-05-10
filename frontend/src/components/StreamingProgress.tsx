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

interface StreamingProgressProps {
  completedSkills: string[]
  activeSkill: string | null
  partialResult: Partial<AnalyzeResponse>
}

export function StreamingProgress({
  completedSkills,
  activeSkill,
  partialResult,
}: StreamingProgressProps) {
  const allVisible = activeSkill
    ? [...completedSkills, activeSkill]
    : completedSkills

  if (allVisible.length === 0) return null

  return (
    <div data-testid="streaming-progress" className="space-y-2">
      {allVisible.map((skillId) => {
        const isActive = skillId === activeSkill
        const isDone = completedSkills.includes(skillId)
        const verdict = isDone ? skillVerdict(skillId, partialResult) : undefined
        const label = SKILL_LABELS[skillId] ?? skillId

        return (
          <Card key={skillId} className={isActive ? 'border-primary/50' : ''}>
            <CardContent className="pt-3 pb-3">
              <div className="flex items-center gap-2">
                {isActive ? (
                  <span
                    data-testid={`skill-active-${skillId}`}
                    className="inline-block h-3 w-3 rounded-full bg-primary animate-pulse"
                    aria-label="En cours"
                  />
                ) : (
                  <span
                    data-testid={`skill-done-${skillId}`}
                    className="text-green-400 text-sm"
                  >
                    ✓
                  </span>
                )}
                <span className="text-sm font-medium">{label}</span>
                {verdict && (
                  <Badge variant="secondary" className="ml-auto text-xs">
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
        )
      })}
    </div>
  )
}
