import { apiClient, ApiError, BASE_URL } from './client'
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  CompositeHistoryPoint,
  EvalDriftResult,
  ExtractResponse,
  PerformanceResponse,
  ScreenRequest,
  ScreenResult,
  HistoryResponse,
  PagedHistoryResponse,
  SSEEvent,
} from '../types'

export async function postAnalyze(body: AnalyzeRequest): Promise<AnalyzeResponse> {
  return apiClient.request<AnalyzeResponse>('/analyze', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function postReport(body: AnalyzeRequest): Promise<Blob> {
  return apiClient.requestBlob('/report', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function postScreen(body: ScreenRequest): Promise<ScreenResult> {
  return apiClient.request<ScreenResult>('/screen', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getHistory(
  ticker?: string,
  limit = 10,
  before?: string,
  q?: string,
  fromDt?: string,
  toDt?: string,
): Promise<HistoryResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (ticker) params.set('ticker', ticker)
  if (q) params.set('q', q)
  if (before) params.set('before', before)
  if (fromDt) params.set('from_dt', fromDt)
  if (toDt) params.set('to_dt', toDt)
  return apiClient.request<HistoryResponse>(`/history?${params.toString()}`)
}

// Sprint 90 — pagination offset/limit
export interface HistoryPagedFilters {
  ticker?: string
  q?: string
  fromDt?: string
  toDt?: string
  tags?: string
}

export async function getHistoryPaged(
  filters: HistoryPagedFilters,
  page = 1,
  pageSize = 10,
): Promise<PagedHistoryResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (filters.ticker) params.set('ticker', filters.ticker)
  if (filters.q) params.set('q', filters.q)
  if (filters.fromDt) params.set('from_dt', filters.fromDt)
  if (filters.toDt) params.set('to_dt', filters.toDt)
  if (filters.tags) params.set('tags', filters.tags)
  return apiClient.request<PagedHistoryResponse>(`/history-paged?${params.toString()}`)
}

export async function getHealthz(): Promise<{ status: string; version: string }> {
  return apiClient.request('/healthz')
}

export async function getExtract(ticker: string): Promise<ExtractResponse> {
  return apiClient.request<ExtractResponse>(`/extract?ticker=${encodeURIComponent(ticker)}`)
}

export async function getPerformance(ticker: string): Promise<PerformanceResponse> {
  return apiClient.request<PerformanceResponse>(`/performance/${encodeURIComponent(ticker)}`)
}

export async function getCompositeHistory(
  ticker: string,
  limit = 90,
): Promise<CompositeHistoryPoint[]> {
  return apiClient.request<CompositeHistoryPoint[]>(
    `/composite-history/${encodeURIComponent(ticker)}?limit=${limit}`,
  )
}

export async function exportScreen(
  body: ScreenRequest,
  format: 'csv' | 'xlsx',
): Promise<Blob> {
  return apiClient.requestBlob(`/export/screen?format=${format}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function downloadTickerPdf(
  ticker: string,
  days = 90,
  analysisId?: string,
): Promise<Blob> {
  const params = new URLSearchParams({ days: String(days) })
  if (analysisId) params.set('analysis_id', analysisId)
  return apiClient.requestBlob(
    `/ticker-report/${encodeURIComponent(ticker)}?${params.toString()}`,
  )
}

export async function downloadScreenerPdf(request: ScreenRequest): Promise<Blob> {
  const tickers = request.tickers.join(',')
  const params = new URLSearchParams({ tickers, workflow: request.workflow })
  return apiClient.requestBlob(`/screener-report?${params.toString()}`)
}

export async function downloadWatchlistPdf(): Promise<Blob> {
  return apiClient.requestBlob('/watchlist/export.pdf')
}

export async function fetchEvalDrift(): Promise<EvalDriftResult[]> {
  try {
    return await apiClient.request<EvalDriftResult[]>('/telemetry/eval-drift')
  } catch {
    return []
  }
}

export async function deleteAnalysis(analysis_id: string): Promise<void> {
  await apiClient.requestEmpty(`/history/${encodeURIComponent(analysis_id)}`, {
    method: 'DELETE',
  })
}

export async function* streamAnalyze(body: AnalyzeRequest): AsyncGenerator<SSEEvent> {
  const apiKey =
    localStorage.getItem('api_token') ??
    (import.meta.env.VITE_API_KEY as string | undefined) ??
    ''

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`

  const response = await fetch(`${BASE_URL}/analyze-stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    let message = response.statusText
    try {
      const errBody = (await response.json()) as { detail?: string; error?: string }
      message = errBody.detail ?? errBody.error ?? message
    } catch { /* ignore */ }
    throw new ApiError(response.status, message)
  }

  if (!response.body) {
    throw new ApiError(500, 'Réponse SSE sans body')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEventType = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    // La dernière ligne peut être incomplète — la garder dans le buffer
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEventType = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        const raw = line.slice(6)
        try {
          const data = JSON.parse(raw) as unknown
          yield { type: currentEventType, data } as SSEEvent
        } catch {
          // ligne SSE malformée — ignorée
        }
        currentEventType = ''
      }
      // Ligne vide = séparateur d'event SSE, ignorée
    }
  }
}
