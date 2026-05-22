import { apiClient } from './client'
import type { WatchlistEntry, WatchlistCreate, PriceStatus, WatchlistEsgResponse } from '../types'

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

export const fetchWatchlistEsgScores = (): Promise<WatchlistEsgResponse> =>
  apiClient.request<WatchlistEsgResponse>('/watchlist/esg-scores')

export const patchEsgThreshold = (id: string, threshold: number): Promise<WatchlistEntry> =>
  apiClient.request<WatchlistEntry>(`/watchlist/${id}/esg-threshold`, {
    method: 'PATCH',
    body: JSON.stringify({ esg_alert_threshold: threshold }),
  })

export const patchPriceThreshold = (id: string, threshold: number): Promise<WatchlistEntry> =>
  apiClient.request<WatchlistEntry>(`/watchlist/${id}/price-threshold`, {
    method: 'PATCH',
    body: JSON.stringify({ threshold }),
  })
