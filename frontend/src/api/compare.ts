import { apiClient } from './client'
import type { CompareResponse } from '../types'

export async function postCompare(tickers: string[]): Promise<CompareResponse> {
  return apiClient.request<CompareResponse>('/compare', {
    method: 'POST',
    body: JSON.stringify({ tickers }),
  })
}
