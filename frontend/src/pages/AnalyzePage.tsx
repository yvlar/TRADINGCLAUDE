import { useRef, useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { AnalyzeForm } from '../components/AnalyzeForm'
import { AnalysisResult } from '../components/AnalysisResult'
import { StreamingProgress } from '../components/StreamingProgress'
import { Badge } from '../components/ui/badge'
import { PageTransition, StaggerItem } from '../components/PageTransition'
import { QuotaBanner, isQuotaError, quotaDetailFromError } from '../components/QuotaBanner'
import { streamAnalyze, postReport, downloadTickerPdf } from '../api/analyze'
import { saveRecentAnalysis } from '../lib/recentAnalyses'
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
  esg_simplified: 'esg',
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
  const [searchParams, setSearchParams] = useSearchParams()
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [lastRequest, setLastRequest] = useState<AnalyzeRequest | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamError, setStreamError] = useState<string | null>(null)
  // Erreur de quota capturée telle quelle (ApiError) pour en dériver message + corps structuré.
  const [quotaError, setQuotaError] = useState<unknown>(null)
  const [partialResult, setPartialResult] = useState<Partial<AnalyzeResponse>>({})
  const [activeSkill, setActiveSkill] = useState<string | null>(null)
  const [plannedSkills, setPlannedSkills] = useState<string[]>([])
  const [completedSkills, setCompletedSkills] = useState<string[]>([])
  const [depuisCache, setDepuisCache] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  // Ticker pré-rempli depuis la palette de commandes (?ticker=BNS.TO)
  const prefillTicker = searchParams.get('ticker') ?? ''
  useEffect(() => {
    if (prefillTicker) setSearchParams({}, { replace: true })
  }, [prefillTicker, setSearchParams])

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
    setPlannedSkills([])
    setActiveSkill(null)
    setStreamError(null)
    setQuotaError(null)
    setDepuisCache(false)
    setLastRequest(req)
    setIsStreaming(true)

    try {
      for await (const event of streamAnalyze(req)) {
        if (event.type === 'plan') {
          setPlannedSkills(event.data.skills)
        } else if (event.type === 'skill_start') {
          setActiveSkill(event.data.skill_id)
        } else if (event.type === 'skill_result') {
          setPartialResult((prev) => applySkillResult(prev, event.data))
          setCompletedSkills((prev) => [...prev, event.data.skill_id])
          setActiveSkill(null)
        } else if (event.type === 'complete' || event.type === 'cached') {
          const finalResult = event.data as AnalyzeResponse
          setResult(finalResult)
          setDepuisCache(finalResult.depuis_cache_composite ?? false)
          saveRecentAnalysis(finalResult)
          setPartialResult({})
          setCompletedSkills([])
          setPlannedSkills([])
          setActiveSkill(null)
        } else if (event.type === 'error') {
          setStreamError(event.data.message)
        }
      }
    } catch (err) {
      if (isQuotaError(err)) {
        setQuotaError(err)
      } else {
        setStreamError(err instanceof Error ? err.message : 'Erreur de streaming')
      }
    } finally {
      setIsStreaming(false)
      setActiveSkill(null)
    }
  }

  function handleDownloadPdf() {
    if (lastRequest) pdfMutation.mutate(lastRequest)
  }

  const exportMutation = useMutation({
    mutationFn: async (res: AnalyzeResponse) => {
      const blob = await downloadTickerPdf(res.ticker, 90, res.analysis_id)
      const date = new Date().toISOString().slice(0, 10)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${res.ticker}-analyse-${date}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  // analysis_id de cache composite n'est pas une analyse persistée exportable
  const canExportAnalysis =
    !!result && !['cached', 'cached_composite'].includes(result.analysis_id)

  function handleExportAnalysis() {
    if (result) exportMutation.mutate(result)
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-bold">Analyse individuelle</h2>
            {depuisCache && (
              <Badge variant="secondary" data-testid="cache-badge">
                Score depuis cache (&lt;24h)
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            Saisissez un ticker et les ratios Graham pour lancer l'analyse multi-skills.
          </p>
        </div>

        <StaggerItem index={0}>
          <AnalyzeForm
            key={prefillTicker}
            onSubmit={handleSubmit}
            isLoading={isStreaming}
            initialTicker={prefillTicker}
          />
        </StaggerItem>

        {quotaError != null && (
          <QuotaBanner
            message={quotaError instanceof Error ? quotaError.message : 'Quota mensuel atteint'}
            detail={quotaDetailFromError(quotaError)}
          />
        )}

        {streamError && (
          <div
            data-testid="error-message"
            className="border border-destructive bg-destructive/10 text-destructive rounded-lg px-4 py-3 text-sm animate-fade-in-up"
          >
            Erreur : {streamError}
          </div>
        )}

        {isStreaming && (
          <StreamingProgress
            plannedSkills={plannedSkills}
            completedSkills={completedSkills}
            activeSkill={activeSkill}
            partialResult={partialResult}
          />
        )}

        {result && (
          <div className="animate-fade-in-up">
            <AnalysisResult
              result={result}
              onDownloadPdf={handleDownloadPdf}
              isPdfLoading={pdfMutation.isPending}
              onExportAnalysis={canExportAnalysis ? handleExportAnalysis : undefined}
              isExportLoading={exportMutation.isPending}
            />
          </div>
        )}

        {pdfMutation.isError && (
          <div className="border border-destructive bg-destructive/10 text-destructive rounded-lg px-4 py-3 text-sm">
            Erreur PDF : {(pdfMutation.error as Error).message}
          </div>
        )}
      </div>
    </PageTransition>
  )
}
