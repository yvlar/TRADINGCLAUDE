import { apiClient } from './client'
import type { MetricsResponse } from '../types'

export async function fetchMetrics(days = 30): Promise<MetricsResponse> {
  return apiClient.request<MetricsResponse>(`/metrics?days=${days}`)
}
