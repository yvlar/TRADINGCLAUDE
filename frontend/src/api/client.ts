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

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`
  const apiKey = localStorage.getItem('api_token') ?? (import.meta.env.VITE_API_KEY as string | undefined)

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {}),
  }

  if (apiKey) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${apiKey}`
  }

  const response = await fetch(url, { ...options, headers })

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

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {}),
  }

  if (apiKey) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${apiKey}`
  }

  const response = await fetch(url, { ...options, headers })

  if (!response.ok) {
    const message = response.statusText
    throw new ApiError(response.status, message)
  }

  return response.blob()
}

async function requestEmpty(path: string, options: RequestInit = {}): Promise<void> {
  const url = `${BASE_URL}${path}`
  const apiKey = localStorage.getItem('api_token') ?? (import.meta.env.VITE_API_KEY as string | undefined)

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {}),
  }

  if (apiKey) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${apiKey}`
  }

  const response = await fetch(url, { ...options, headers })

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
