import { apiClient } from './client'
import type { DiscoveryCategoriesResponse, DiscoveryCategoryResponse } from '../types'

/** Grille de cartes de la page Découvrir — métadonnées + compteur par catégorie. */
export async function fetchDiscoveryCategories(): Promise<DiscoveryCategoriesResponse> {
  return apiClient.request<DiscoveryCategoriesResponse>('/discovery/categories')
}

/** Suggestions précalculées d'une catégorie (lecture seule, instantané). */
export async function fetchDiscoveryCategory(
  categoryId: string,
): Promise<DiscoveryCategoryResponse> {
  return apiClient.request<DiscoveryCategoryResponse>(
    `/discovery/${encodeURIComponent(categoryId)}`,
  )
}
