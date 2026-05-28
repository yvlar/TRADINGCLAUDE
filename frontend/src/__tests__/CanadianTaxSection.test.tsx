import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CanadianTaxSection } from '../components/CanadianTaxSection'
import type { CanadianTaxOutput } from '../types'

const BASE_TAX: CanadianTaxOutput = {
  ticker: 'BNS.TO',
  compte_recommande: 'CELI',
  justification_fiscale: 'Dividendes canadiens éligibles déjà avantageux ; croissance libre d\'impôt au CELI.',
  impact_retenue_us: null,
  strategie_smith_manoeuvre: false,
  taux_inclusion_gain_capital: 0.5,
  recommandation_prochaine_etape: ['Vérifier l\'espace CELI disponible', 'Documenter le PBR'],
  citations: [],
  cost_usd: 0.008,
}

describe('CanadianTaxSection', () => {
  it('affiche le compte recommandé et reste fermé par défaut', () => {
    render(<CanadianTaxSection output={BASE_TAX} />)
    expect(screen.getByTestId('tax-compte')).toHaveTextContent('CELI (TFSA)')
    expect(screen.queryByTestId('tax-inclusion')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche le taux d\'inclusion du gain en capital', async () => {
    const user = userEvent.setup()
    render(<CanadianTaxSection output={BASE_TAX} />)

    await user.click(screen.getByTestId('tax-toggle'))

    expect(screen.getByTestId('tax-inclusion')).toHaveTextContent('50%')
  })

  it('affiche la justification fiscale une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<CanadianTaxSection output={BASE_TAX} />)

    await user.click(screen.getByTestId('tax-toggle'))

    expect(screen.getByTestId('tax-justification')).toBeInTheDocument()
    expect(screen.getByText(/croissance libre d'impôt/)).toBeInTheDocument()
  })

  it('affiche la retenue US et le badge Smith Manœuvre quand applicables', async () => {
    const user = userEvent.setup()
    const output = {
      ...BASE_TAX,
      compte_recommande: 'REER',
      impact_retenue_us: 'Retenue 15 % récupérable au REER via la convention Canada-US.',
      strategie_smith_manoeuvre: true,
    }
    render(<CanadianTaxSection output={output} />)

    await user.click(screen.getByTestId('tax-toggle'))

    expect(screen.getByTestId('tax-compte')).toHaveTextContent('REER (RRSP)')
    expect(screen.getByTestId('tax-retenue-us')).toHaveTextContent(/15 %/)
    expect(screen.getByTestId('tax-smith')).toBeInTheDocument()
  })

  it('masque la retenue US et le badge Smith quand absents', async () => {
    const user = userEvent.setup()
    render(<CanadianTaxSection output={BASE_TAX} />)

    await user.click(screen.getByTestId('tax-toggle'))

    expect(screen.queryByTestId('tax-retenue-us')).not.toBeInTheDocument()
    expect(screen.queryByTestId('tax-smith')).not.toBeInTheDocument()
  })

  it('affiche le libellé brut pour un compte inconnu', () => {
    const output = { ...BASE_TAX, compte_recommande: 'INCONNU' }
    render(<CanadianTaxSection output={output} />)
    expect(screen.getByTestId('tax-compte')).toHaveTextContent('INCONNU')
  })
})
