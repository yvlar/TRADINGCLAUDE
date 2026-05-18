import type { AnalyzeResponse, RecentAnalysis } from '../types'

export const RECENT_ANALYSES_KEY = 'copilote_recent_analyses'

export function loadRecentAnalyses(): RecentAnalysis[] {
  try {
    const raw = localStorage.getItem(RECENT_ANALYSES_KEY)
    if (!raw) return []
    return JSON.parse(raw) as RecentAnalysis[]
  } catch {
    return []
  }
}

export function saveRecentAnalysis(result: AnalyzeResponse): void {
  const entry: RecentAnalysis = {
    ticker: result.ticker,
    composite_score: result.composite_score,
    inter_skill_conflicts: result.inter_skill_conflicts,
    workflow: result.workflow,
    created_at: result.created_at,
  }
  try {
    const prev = loadRecentAnalyses()
    const filtered = prev.filter((r) => r.ticker !== entry.ticker)
    localStorage.setItem(
      RECENT_ANALYSES_KEY,
      JSON.stringify([entry, ...filtered].slice(0, 10)),
    )
  } catch {
    // ignore localStorage errors (navigation privée, quota dépassé…)
  }
}
