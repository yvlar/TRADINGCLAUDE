import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HistoryTable } from '../components/HistoryTable'
import type { HistoryEntry } from '../types'

// AnnotationSection (rendu dans chaque ligne) appelle l'API au toggle uniquement.
vi.mock('../api/annotations')

function makeEntry(id: string, tags: string[]): HistoryEntry {
  return {
    analysis_id: id,
    ticker: 'BNS',
    workflow: 'value_graham',
    skills_applied: ['graham_analysis'],
    cost_usd: 0.004,
    defensive_score: 7,
    graham_verdict: 'CANDIDAT_SOLIDE',
    earnings_verdict: null,
    tags,
    created_at: '2026-05-10T12:00:00+00:00',
  }
}

describe('HistoryTable — chips de tags', () => {
  it('rend les tags en lecture seule pour une entrée', () => {
    render(
      <HistoryTable
        entries={[makeEntry('aaa', ['value', 'growth'])]}
        hasMore={false}
        onLoadMore={() => {}}
      />,
    )
    const container = screen.getByTestId('history-tags-aaa')
    expect(container).toBeInTheDocument()
    expect(screen.getByText('value')).toBeInTheDocument()
    expect(screen.getByText('growth')).toBeInTheDocument()
  })

  it("n'affiche pas de conteneur de tags quand l'entrée n'en a pas", () => {
    render(
      <HistoryTable
        entries={[makeEntry('bbb', [])]}
        hasMore={false}
        onLoadMore={() => {}}
      />,
    )
    expect(screen.queryByTestId('history-tags-bbb')).not.toBeInTheDocument()
  })
})
