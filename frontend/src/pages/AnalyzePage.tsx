import { useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { AnalyzeForm } from '../components/AnalyzeForm'
import { AnalysisResult } from '../components/AnalysisResult'
import { StreamingProgress } from '../components/StreamingProgress'
import { streamAnalyze, postReport } from '../api/analyze'
import type { AnalyzeRequest, AnalyzeResponse, SSESkillResult } from '../types'

/** Mappe skill_id → champ de AnalyzeResponse. */
const SKILL_FIELD: Record<string, keyof AnalyzeResponse> = {
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

function applySkillResult(
  prev: Partial<AnalyzeResponse>,
  event: SSESkillResult,
): Partial<AnalyzeResponse> {
  const field = SKILL_FIELD[event.skill_id]
  if (!field) return prev
  return { ...prev, [field]: event.result }
}

export default function AnalyzePage() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [lastRequest, setLastRequest] = useState<AnalyzeRequest | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamError, setStreamError] = useState<string | null>(null)
  const [partialResult, setPartialResult] = useState<Partial<AnalyzeResponse>>({})
  const [activeSkill, setActiveSkill] = useState<string | null>(null)
  const [completedSkills, setCompletedSkills] = useState<string[]>([])
  const abortRef = useRef<AbortController | null>(null)

  const pdfMutation = useMutation({
    mutationFn: async (req: AnalyzeRequest) => {
      const blob = await postReport(req)
      const ticker = req.ticker
      const date = new Date().toISOString().slice(0, 7)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${ticker}-${date}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  async function handleSubmit(req: AnalyzeRequest) {
    abortRef.current?.abort()
    setResult(null)
    setPartialResult({})
    setCompletedSkills([])
    setActiveSkill(null)
    setStreamError(null)
    setLastRequest(req)
    setIsStreaming(true)

    try {
      for await (const event of streamAnalyze(req)) {
        if (event.type === 'skill_start') {
          setActiveSkill(event.data.skill_id)
        } else if (event.type === 'skill_result') {
          setPartialResult((prev) => applySkillResult(prev, event.data))
          setCompletedSkills((prev) => [...prev, event.data.skill_id])
          setActiveSkill(null)
        } else if (event.type === 'complete' || event.type === 'cached') {
          setResult(event.data as AnalyzeResponse)
          setPartialResult({})
          setCompletedSkills([])
          setActiveSkill(null)
        } else if (event.type === 'error') {
          setStreamError(event.data.message)
        }
      }
    } catch (err) {
      setStreamError(err instanceof Error ? err.message : 'Erreur de streaming')
    } finally {
      setIsStreaming(false)
      setActiveSkill(null)
    }
  }

  function handleDownloadPdf() {
    if (lastRequest) pdfMutation.mutate(lastRequest)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold mb-1">Analyse individuelle</h2>
        <p className="text-sm text-muted-foreground">
          Saisissez un ticker et les ratios Graham pour lancer l'analyse multi-skills.
        </p>
      </div>

      <AnalyzeForm onSubmit={handleSubmit} isLoading={isStreaming} />

      {streamError && (
        <div
          data-testid="error-message"
          className="border border-destructive bg-destructive/10 text-destructive rounded-lg px-4 py-3 text-sm"
        >
          Erreur : {streamError}
        </div>
      )}

      {isStreaming && (
        <StreamingProgress
          completedSkills={completedSkills}
          activeSkill={activeSkill}
          partialResult={partialResult}
        />
      )}

      {result && (
        <AnalysisResult
          result={result}
          onDownloadPdf={handleDownloadPdf}
          isPdfLoading={pdfMutation.isPending}
        />
      )}

      {pdfMutation.isError && (
        <div className="border border-destructive bg-destructive/10 text-destructive rounded-lg px-4 py-3 text-sm">
          Erreur PDF : {(pdfMutation.error as Error).message}
        </div>
      )}
    </div>
  )
}
