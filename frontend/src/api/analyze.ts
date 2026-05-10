import { apiClient, ApiError, BASE_URL } from './client'
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ExtractResponse,
  ScreenRequest,
  ScreenResult,
  HistoryResponse,
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
  ticker: string,
  limit = 10,
  before?: string,
): Promise<HistoryResponse> {
  const params = new URLSearchParams({ ticker, limit: String(limit) })
  if (before) params.set('before', before)
  return apiClient.request<HistoryResponse>(`/history?${params.toString()}`)
}

export async function getHealthz(): Promise<{ status: string; version: string }> {
  return apiClient.request('/healthz')
}

export async function getExtract(ticker: string): Promise<ExtractResponse> {
  return apiClient.request<ExtractResponse>(`/extract?ticker=${encodeURIComponent(ticker)}`)
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
