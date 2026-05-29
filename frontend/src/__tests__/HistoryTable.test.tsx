import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HistoryTable } from '../components/HistoryTable'
import type { HistoryEntry } from '../types'

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
    created_at: '2026-05-10T12:00:00+00:00',
    tags,
  }
}

describe('HistoryTable — chips de tags (Sprint 125)', () => {
  it('rend les chips en lecture seule quand l\'entrée porte des tags', () => {
    render(
      <HistoryTable
        entries={[makeEntry('id-1', ['value', 'growth'])]}
        hasMore={false}
        onLoadMore={() => {}}
      />,
    )
    const chips = screen.getByTestId('history-tags-id-1')
    expect(chips).toHaveTextContent('value')
    expect(chips).toHaveTextContent('growth')
  })

  it('n\'affiche aucun conteneur de chips si l\'entrée n\'a pas de tags', () => {
    render(
      <HistoryTable
        entries={[makeEntry('id-2', [])]}
        hasMore={false}
        onLoadMore={() => {}}
      />,
    )
    expect(screen.queryByTestId('history-tags-id-2')).not.toBeInTheDocument()
  })
})
