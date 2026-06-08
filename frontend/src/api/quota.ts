import { apiClient } from './client'
import type { QuotaStatus } from '../types'

/** État du quota mensuel d'analyses du tenant courant (auth-scoped, RLS serveur, lecture seule). */
export async function getQuota(): Promise<QuotaStatus> {
  return apiClient.request<QuotaStatus>('/quota')
}
