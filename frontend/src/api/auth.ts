import type {
  AuthResponse,
  ForgotPasswordRequest,
  LoginRequest,
  RegisterRequest,
  ResetPasswordRequest,
  User,
} from '../types'
import { BASE_URL } from './client'

class AuthApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'AuthApiError'
  }
}

/** Lit le token CSRF depuis le cookie non-httpOnly (double-submit pattern). */
function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : ''
}

async function authFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`
  const method = (options.method ?? 'GET').toUpperCase()
  const isMutation = !['GET', 'HEAD', 'OPTIONS'].includes(method)

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined ?? {}),
  }

  if (isMutation) {
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
        message = (body.detail as Array<{ msg?: string; loc?: string[] }>)
          .map((e) => {
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
    throw new AuthApiError(response.status, message)
  }

  if (response.status === 204) return undefined as unknown as T
  return response.json() as Promise<T>
}

export const authRegister = (data: RegisterRequest): Promise<AuthResponse> =>
  authFetch<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const authLogin = (data: LoginRequest): Promise<AuthResponse> =>
  authFetch<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const authLogout = (): Promise<void> =>
  authFetch<void>('/auth/logout', { method: 'POST' })

export const authMe = (): Promise<User> =>
  authFetch<User>('/auth/me')

export const authRefresh = (): Promise<void> =>
  authFetch<void>('/auth/refresh', { method: 'POST' })

export const authForgotPassword = (data: ForgotPasswordRequest): Promise<void> =>
  authFetch<void>('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const authResetPassword = (data: ResetPasswordRequest): Promise<void> =>
  authFetch<void>('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export { AuthApiError }
