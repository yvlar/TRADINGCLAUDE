import { apiClient } from './client'
import type { AlertsResponse } from '../types'

export async function fetchAlerts(limit = 50): Promise<AlertsResponse> {
  return apiClient.request<AlertsResponse>(`/alerts?limit=${limit}`)
}
