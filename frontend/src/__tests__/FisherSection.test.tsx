import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FisherSection } from '../components/FisherSection'
import type { FisherOutput, FisherPoint } from '../types'

const POINTS: FisherPoint[] = Array.from({ length: 15 }, (_, i) => ({
  point: i + 1,
  titre: `Point Fisher ${i + 1}`,
  score: i % 3,
  commentaire: `Commentaire sur le point ${i + 1}`,
}))

const BASE_FISHER: FisherOutput = {
  ticker: 'CSU.TO',
  fisher_score: 24,
  points_evalues: POINTS,
  management_quality: 'EXCEPTIONNEL',
  verdict: 'ACHAT_FORT',
  verdict_detail: 'Direction visionnaire avec un historique de réinvestissement exceptionnel.',
  recommandation_prochaine_etape: ['Interroger d\'anciens employés', 'Analyser la R&D'],
  citations: [],
  cost_usd: 0.014,
}

describe('FisherSection', () => {
  it('affiche la qualité de direction, le verdict et reste fermé par défaut', () => {
    render(<FisherSection output={BASE_FISHER} />)
    expect(screen.getByTestId('fisher-management')).toHaveTextContent('Direction exceptionnelle')
    expect(screen.getByTestId('fisher-verdict')).toHaveTextContent('ACHAT_FORT')
    expect(screen.queryByTestId('fisher-score')).not.toBeInTheDocument()
  })

  it('ouvre la section et affiche le score Fisher /30', async () => {
    const user = userEvent.setup()
    render(<FisherSection output={BASE_FISHER} />)

    await user.click(screen.getByTestId('fisher-toggle'))

    expect(screen.getByTestId('fisher-score')).toHaveTextContent('24/30')
  })

  it('affiche les 15 points une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<FisherSection output={BASE_FISHER} />)

    await user.click(screen.getByTestId('fisher-toggle'))

    expect(screen.getAllByTestId('fisher-point')).toHaveLength(15)
    expect(screen.getByText('Point Fisher 1')).toBeInTheDocument()
  })

  it('affiche les recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<FisherSection output={BASE_FISHER} />)

    await user.click(screen.getByTestId('fisher-toggle'))

    expect(screen.getByTestId('fisher-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/anciens employés/)).toBeInTheDocument()
  })

  it('affiche le libellé FR pour chaque qualité de direction connue', () => {
    const output = { ...BASE_FISHER, management_quality: 'MEDIOCRE' }
    render(<FisherSection output={output} />)
    expect(screen.getByTestId('fisher-management')).toHaveTextContent('Direction médiocre')
  })

  it('affiche le libellé brut pour une qualité de direction inconnue', () => {
    const output = { ...BASE_FISHER, management_quality: 'INCONNU' }
    render(<FisherSection output={output} />)
    expect(screen.getByTestId('fisher-management')).toHaveTextContent('INCONNU')
  })
})
