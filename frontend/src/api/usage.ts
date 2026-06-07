import { apiClient } from './client'
import type { UsageResponse } from '../types'

/** Consommation agrégée du tenant courant sur `days` jours (auth-scoped, RLS serveur). */
export async function getUsage(days = 30): Promise<UsageResponse> {
  return apiClient.request<UsageResponse>(`/usage?days=${days}`)
}
