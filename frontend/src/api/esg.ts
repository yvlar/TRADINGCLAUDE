import { apiClient } from './client'
import type { EsgHistoryResponse } from '../types'

// Sprint 89 — historique des scores ESG d'un ticker
export async function fetchEsgHistory(
  ticker: string,
  limit = 100,
): Promise<EsgHistoryResponse> {
  return apiClient.request<EsgHistoryResponse>(
    `/esg-history/${encodeURIComponent(ticker)}?limit=${limit}`,
  )
}
