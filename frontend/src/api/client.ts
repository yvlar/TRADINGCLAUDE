const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
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
  const apiKey = localStorage.getItem('api_token') ?? (import.meta.env.VITE_API_KEY as string | undefined)

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
    let message: string
    try {
      const body = (await response.json()) as { detail?: unknown; error?: string }
      if (Array.isArray(body.detail)) {
        // Erreurs de validation Pydantic FastAPI : [{loc, msg, type}, ...]
        message = (body.detail as Array<{ msg?: string; loc?: string[] }>)
          .map(e => {
            const field = e.loc ? e.loc.slice(1).join('.') : ''
            return field ? `${field} : ${e.msg ?? 'invalide'}` : (e.msg ?? 'invalide')
          })
          .join(' | ')
      } else {
        message = (body.detail as string | undefined) ?? body.error ?? response.statusText
      }
    } catch {
      message = response.statusText
    }
    throw new ApiError(response.status, message)
  }

  return response.json() as Promise<T>
}

async function requestBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const url = `${BASE_URL}${path}`
  const apiKey = localStorage.getItem('api_token') ?? (import.meta.env.VITE_API_KEY as string | undefined)

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
  const apiKey = localStorage.getItem('api_token') ?? (import.meta.env.VITE_API_KEY as string | undefined)

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
