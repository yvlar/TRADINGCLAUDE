import { extractDetailMessage } from './errorDetail'

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    // Corps `detail` brut quand le serveur renvoie un objet structuré (ex. 429 quota :
    // {message, plan, used, limit, remaining}). `undefined` pour un detail string/tableau.
    public readonly detail?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function getApiKey(): string | undefined {
  return (localStorage.getItem('api_token') ?? (import.meta.env.VITE_API_KEY as string | undefined)) || undefined
}

/** Lit le token CSRF depuis le cookie non-httpOnly (double-submit pattern). */
function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : ''
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`
  const method = (options.method ?? 'GET').toUpperCase()
  const isMutation = !['GET', 'HEAD', 'OPTIONS'].includes(method)

  // Clé API programmatique (rétrocompatibilité) — priorité sur cookie auth
  const apiKey = getApiKey()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined ?? {}),
  }

  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`
  } else if (isMutation) {
    // Cookie auth : inclure le CSRF token sur les mutations
    const csrf = getCsrfToken()
    if (csrf) headers['X-CSRF-Token'] = csrf
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (!response.ok) {
    let message = response.statusText
    let detail: unknown
    try {
      const extracted = extractDetailMessage(await response.json(), response.statusText)
      message = extracted.message
      detail = extracted.detail
    } catch { /* corps non-JSON : message reste statusText */ }
    throw new ApiError(response.status, message, detail)
  }

  return response.json() as Promise<T>
}

async function requestBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const url = `${BASE_URL}${path}`
  const apiKey = getApiKey()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined ?? {}),
  }

  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`
  } else {
    const csrf = getCsrfToken()
    if (csrf) headers['X-CSRF-Token'] = csrf
  }

  const response = await fetch(url, { ...options, headers, credentials: 'include' })

  if (!response.ok) {
    const message = response.statusText
    throw new ApiError(response.status, message)
  }

  return response.blob()
}

async function requestEmpty(path: string, options: RequestInit = {}): Promise<void> {
  const url = `${BASE_URL}${path}`
  const apiKey = getApiKey()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined ?? {}),
  }

  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`
  } else {
    const csrf = getCsrfToken()
    if (csrf) headers['X-CSRF-Token'] = csrf
  }

  const response = await fetch(url, { ...options, headers, credentials: 'include' })

  if (!response.ok) {
    let message: string
    try {
      const body = (await response.json()) as { detail?: string; error?: string }
      message = body.detail ?? body.error ?? response.statusText
    } catch {
      message = response.statusText
    }
    throw new ApiError(response.status, message)
  }
}

export const apiClient = { request, requestBlob, requestEmpty }
export { ApiError, BASE_URL }
