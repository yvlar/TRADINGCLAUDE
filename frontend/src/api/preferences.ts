import { apiClient } from './client'
import type { ScreenerPreferences } from '../types'

/** Préférences Screener serveur, ou null si non authentifié / réseau KO (fallback localStorage). */
export async function getScreenerPreferences(): Promise<ScreenerPreferences | null> {
  try {
    return await apiClient.request<ScreenerPreferences>('/preferences/screener')
  } catch {
    return null
  }
}

/** Persiste le tri + les filtres ; renvoie l'état persisté, ou null en cas d'échec (best-effort). */
export async function putScreenerPreferences(
  prefs: ScreenerPreferences,
): Promise<ScreenerPreferences | null> {
  try {
    return await apiClient.request<ScreenerPreferences>('/preferences/screener', {
      method: 'PUT',
      body: JSON.stringify(prefs),
    })
  } catch {
    return null
  }
}
