import { apiClient } from './client'
import type { UsageReporting, UsageResponse } from '../types'

/** Consommation agrégée du tenant courant sur `days` jours (auth-scoped, RLS serveur). */
export async function getUsage(days = 30): Promise<UsageResponse> {
  return apiClient.request<UsageResponse>(`/usage?days=${days}`)
}

/** État du report d'usage vers Stripe : curseur + événements en attente (auth-scoped). */
export async function getUsageReporting(): Promise<UsageReporting> {
  return apiClient.request<UsageReporting>('/usage/reporting')
}
