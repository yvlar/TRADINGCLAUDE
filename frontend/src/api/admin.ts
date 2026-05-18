import { apiClient } from './client'
import type { ApiKey, ApiKeyCreate } from '../types'

export const listApiKeys = (): Promise<ApiKey[]> =>
  apiClient.request<ApiKey[]>('/admin/keys')

export const createApiKey = (body: ApiKeyCreate): Promise<{ key: string; id: string }> =>
  apiClient.request<{ key: string; id: string }>('/admin/keys', {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const revokeApiKey = (id: string): Promise<void> =>
  apiClient.requestEmpty(`/admin/keys/${id}`, { method: 'DELETE' })
