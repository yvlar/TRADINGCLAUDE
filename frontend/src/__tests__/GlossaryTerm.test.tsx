import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { GlossaryTerm } from '../components/GlossaryTerm'

function renderTerm(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('GlossaryTerm', () => {
  it('affiche le libellé par défaut du glossaire', () => {
    renderTerm(<GlossaryTerm term="pe" />)
    expect(screen.getByTestId('glossary-trigger-pe')).toHaveTextContent('P/E')
  })

  it('utilise le children comme libellé si fourni', () => {
    renderTerm(<GlossaryTerm term="rendement_dividende">Dividende</GlossaryTerm>)
    expect(screen.getByTestId('glossary-trigger-rendement_dividende')).toHaveTextContent(
      'Dividende',
    )
  })

  it('révèle la définition au clic', async () => {
    const user = userEvent.setup()
    renderTerm(<GlossaryTerm term="pe" />)

    expect(screen.queryByTestId('glossary-panel-pe')).not.toBeInTheDocument()
    await user.click(screen.getByTestId('glossary-trigger-pe'))

    const panel = screen.getByTestId('glossary-panel-pe')
    expect(panel).toBeInTheDocument()
    expect(panel).toHaveTextContent('Ratio cours/bénéfice')
  })

  it('referme la définition au second clic', async () => {
    const user = userEvent.setup()
    renderTerm(<GlossaryTerm term="pe" />)
    const trigger = screen.getByTestId('glossary-trigger-pe')

    await user.click(trigger)
    expect(screen.getByTestId('glossary-panel-pe')).toBeInTheDocument()
    await user.click(trigger)
    expect(screen.queryByTestId('glossary-panel-pe')).not.toBeInTheDocument()
  })

  it('le lien « En savoir plus » pointe vers la recherche préremplie', async () => {
    const user = userEvent.setup()
    renderTerm(<GlossaryTerm term="pe" />)
    await user.click(screen.getByTestId('glossary-trigger-pe'))

    const link = screen.getByTestId('glossary-learn-pe')
    expect(link.getAttribute('href')).toContain('/recherche?q=')
  })

  it('rend simplement le children si le terme est inconnu', () => {
    // terme volontairement absent du glossaire — teste le repli runtime (if !entry)
    renderTerm(<GlossaryTerm term="inexistant">texte brut</GlossaryTerm>)
    expect(screen.getByText('texte brut')).toBeInTheDocument()
    expect(screen.queryByTestId('glossary-trigger-inexistant')).not.toBeInTheDocument()
  })
})
