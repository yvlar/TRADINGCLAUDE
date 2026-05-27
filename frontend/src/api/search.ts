import { apiClient } from './client'
import type { SemanticSearchResponse } from '../types'

export async function fetchSemanticSearch(
  query: string,
  k = 5,
): Promise<SemanticSearchResponse> {
  return apiClient.request<SemanticSearchResponse>(
    `/semantic-search?q=${encodeURIComponent(query)}&k=${k}`,
  )
}
