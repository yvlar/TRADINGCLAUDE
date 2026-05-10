import { apiClient } from './client'
import type { WatchlistEntry, WatchlistCreate, PriceStatus } from '../types'

export const getWatchlist = (): Promise<WatchlistEntry[]> =>
  apiClient.request<WatchlistEntry[]>('/watchlist')

export const addToWatchlist = (data: WatchlistCreate): Promise<WatchlistEntry> =>
  apiClient.request<WatchlistEntry>('/watchlist', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const removeFromWatchlist = (id: string): Promise<void> =>
  apiClient.requestEmpty(`/watchlist/${id}`, { method: 'DELETE' })

export const triggerWatchlistAnalysis = (id: string): Promise<{ job_id: string }> =>
  apiClient.request<{ job_id: string }>(`/watchlist/${id}/analyze`, { method: 'POST' })

export const getWatchlistPriceStatus = (id: string): Promise<PriceStatus> =>
  apiClient.request<PriceStatus>(`/watchlist/${id}/price-status`)
