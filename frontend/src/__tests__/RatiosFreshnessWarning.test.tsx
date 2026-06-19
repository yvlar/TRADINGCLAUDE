import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RatiosFreshnessWarning } from '../components/RatiosFreshnessWarning'

describe('RatiosFreshnessWarning', () => {
  it('rend une bannière avec une ligne par avertissement', () => {
    render(
      <RatiosFreshnessWarning
        warnings={[
          'Ratios Graham : données vieilles de 45 j (>30 j)',
          'Ratios Valorisation : données vieilles de 120 j (>90 j) — fiabilité réduite',
        ]}
      />,
    )
    const note = screen.getByTestId('ratios-freshness-warning')
    expect(note).toHaveAttribute('role', 'note')
    expect(note).toHaveTextContent('Ratios Graham')
    expect(note).toHaveTextContent('fiabilité réduite')
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
  })

  it('ne rend rien si la liste est vide', () => {
    const { container } = render(<RatiosFreshnessWarning warnings={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('ne rend rien si warnings est null ou undefined', () => {
    const { container } = render(<RatiosFreshnessWarning warnings={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})
