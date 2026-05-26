import { apiClient } from './client'
import type { MetricsResponse, SkillAnalysesResponse } from '../types'

export async function fetchMetrics(days = 30): Promise<MetricsResponse> {
  return apiClient.request<MetricsResponse>(`/metrics?days=${days}`)
}

export async function fetchSkillAnalyses(
  skill: string,
  days = 30,
): Promise<SkillAnalysesResponse> {
  const params = new URLSearchParams({ skill, days: String(days) })
  return apiClient.request<SkillAnalysesResponse>(`/metrics/skill-analyses?${params}`)
}
