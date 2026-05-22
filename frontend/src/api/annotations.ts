import { apiClient } from './client'
import type { Annotation, AnnotationCreate } from '../types'

export async function getAnnotation(analysisId: string): Promise<Annotation | null> {
  try {
    return await apiClient.request<Annotation>(`/annotations/${encodeURIComponent(analysisId)}`)
  } catch {
    return null
  }
}

export async function upsertAnnotation(data: AnnotationCreate): Promise<Annotation> {
  return apiClient.request<Annotation>('/annotations', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function downloadAnnotationsCsv(): Promise<Blob> {
  return apiClient.requestBlob('/annotations/export.csv')
}

export async function downloadAnnotationsXlsx(): Promise<Blob> {
  return apiClient.requestBlob('/annotations/export.xlsx')
}
