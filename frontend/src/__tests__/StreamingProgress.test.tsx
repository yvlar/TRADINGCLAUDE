import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { StreamingProgress } from '../components/StreamingProgress'

const PLANNED = [
  'graham_analysis',
  'stock_valuation_triangulation',
  'investment_thesis_builder',
]

describe('StreamingProgress', () => {
  it('utilise plannedSkills comme pipeline complet et dénominateur', () => {
    render(
      <StreamingProgress
        plannedSkills={PLANNED}
        completedSkills={['graham_analysis']}
        activeSkill="stock_valuation_triangulation"
        partialResult={{}}
      />,
    )
    // 1 terminé sur 3 planifiés (et non 1/2 comme avant le correctif)
    expect(screen.getByText('1/3')).toBeInTheDocument()
    expect(screen.getByTestId('skill-done-graham_analysis')).toBeInTheDocument()
    expect(
      screen.getByTestId('skill-active-stock_valuation_triangulation'),
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('skill-pending-investment_thesis_builder'),
    ).toBeInTheDocument()
  })

  it('replie sur les skills observés quand plannedSkills est vide', () => {
    render(
      <StreamingProgress
        plannedSkills={[]}
        completedSkills={['graham_analysis']}
        activeSkill={null}
        partialResult={{}}
      />,
    )
    expect(screen.getByText('1/1')).toBeInTheDocument()
    expect(screen.getByTestId('skill-done-graham_analysis')).toBeInTheDocument()
  })
})
