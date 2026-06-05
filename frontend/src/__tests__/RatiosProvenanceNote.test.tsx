import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RatiosProvenanceNote, ratiosEnRepli } from '../components/RatiosProvenanceNote'

describe('ratiosEnRepli — logique signal-only partagée', () => {
  it('ne retient que les ratios dont la clé effective diffère de la clé primaire', () => {
    const repli = ratiosEnRepli({ pb: 'priceToBookRatio', debt_equity: 'debtToEquity' })
    expect(repli).toEqual([['pb', 'priceToBookRatio']])
  })

  it('retourne [] pour une provenance null ou undefined', () => {
    expect(ratiosEnRepli(null)).toEqual([])
    expect(ratiosEnRepli(undefined)).toEqual([])
  })

  it('retourne [] quand toutes les clés sont primaires (aucun repli)', () => {
    expect(
      ratiosEnRepli({ pb: 'priceToBook', debt_equity: 'debtToEquity', book_value: 'bookValue' }),
    ).toEqual([])
  })

  it('ignore les clés non instrumentées (hors pb/debt_equity/book_value)', () => {
    expect(ratiosEnRepli({ pe: 'forwardPE' })).toEqual([])
  })
})

describe('RatiosProvenanceNote — composant partagé (Sprint 150)', () => {
  it('rend un badge « <ratio> via <clé> (repli) » pour chaque ratio en repli', () => {
    render(<RatiosProvenanceNote provenance={{ book_value: 'bookValuePerShare' }} />)
    const note = screen.getByTestId('ratios-provenance')
    expect(note).toHaveTextContent('Valeur comptable')
    expect(note).toHaveTextContent('bookValuePerShare')
    expect(note).toHaveTextContent('(repli)')
  })

  it('ne rend rien (null) quand il n’y a aucun repli', () => {
    const { container } = render(<RatiosProvenanceNote provenance={{ pb: 'priceToBook' }} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('respecte le testId fourni (placement sur l’analyse rendue)', () => {
    render(
      <RatiosProvenanceNote
        provenance={{ pb: 'priceToBookRatio' }}
        testId="result-ratios-provenance"
      />,
    )
    expect(screen.getByTestId('result-ratios-provenance')).toBeInTheDocument()
    expect(screen.queryByTestId('ratios-provenance')).not.toBeInTheDocument()
  })
})
