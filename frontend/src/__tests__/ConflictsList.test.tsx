import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConflictsList } from '../components/ConflictsList'

describe('ConflictsList', () => {
  it('affiche le message vide quand aucun conflit', () => {
    render(<ConflictsList conflicts={[]} />)
    expect(screen.getByTestId('conflicts-empty')).toBeInTheDocument()
    expect(screen.getByText('Aucun conflit inter-skills détecté')).toBeInTheDocument()
  })

  it("n'affiche pas le message vide si des conflits existent", () => {
    render(<ConflictsList conflicts={['Graham PASSE mais Buffett REJETER']} />)
    expect(screen.queryByTestId('conflicts-empty')).not.toBeInTheDocument()
  })

  it('affiche la liste quand des conflits existent', () => {
    const conflicts = [
      'Graham PASSE mais Buffett REJETER',
      'Marks VENDRE mais Klarman ACHETER',
    ]
    render(<ConflictsList conflicts={conflicts} />)
    expect(screen.getByTestId('conflicts-list')).toBeInTheDocument()
    expect(screen.getByText('Graham PASSE mais Buffett REJETER')).toBeInTheDocument()
    expect(screen.getByText('Marks VENDRE mais Klarman ACHETER')).toBeInTheDocument()
  })

  it('affiche un seul conflit correctement', () => {
    render(<ConflictsList conflicts={['seul conflit']} />)
    const list = screen.getByTestId('conflicts-list')
    expect(list.querySelectorAll('li')).toHaveLength(1)
  })
})
