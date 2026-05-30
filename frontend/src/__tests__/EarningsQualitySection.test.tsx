import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EarningsQualitySection } from '../components/EarningsQualitySection'
import type { EarningsQualityOutput } from '../types'

const BASE_EQ: EarningsQualityOutput = {
  ticker: 'BNS.TO',
  is_financial: false,
  m_score: {
    dsri: 1.05,
    gmi: 0.98,
    aqi: 1.01,
    sgi: 1.03,
    depi: 0.97,
    sgai: null,
    tata: -0.02,
    lvgi: 1.01,
    m_score: -2.45,
    interpretation: 'Faible risque de manipulation (< -1.78)',
  },
  z_score: {
    variante: 'Altman Z-Score classique',
    x1: 0.215,
    x2: 0.342,
    x3: 0.118,
    x4: 1.874,
    x5: 0.456,
    z_score: 3.15,
    interpretation: 'Zone sûre (> 2.99)',
  },
  f_score: {
    criteria: [
      { nom: 'ROA positif', passe: true, detail: 'ROA = 0.012' },
      { nom: 'CFO positif', passe: true, detail: 'CFO > 0' },
      { nom: 'Variation ROA', passe: true, detail: '+0.002' },
      { nom: 'Accruals', passe: true, detail: 'CFO > ROA' },
      { nom: 'Levier financier', passe: false, detail: 'Légère hausse' },
      { nom: 'Liquidité courante', passe: true, detail: 'CR 1.12 → 1.18' },
      { nom: 'Actions émises', passe: true, detail: 'Aucune dilution' },
      { nom: 'Marge brute', passe: true, detail: '+0.4 pp' },
      { nom: 'Rotation actifs', passe: false, detail: 'Stable' },
    ],
    f_score: 7,
    interpretation: 'Qualité élevée (7+/9)',
  },
  c_score: {
    signaux: [
      { nom: 'Hausse A/R sur ventes', present: false, detail: 'Ratio stable' },
      { nom: 'Hausse stocks sur ventes', present: false, detail: 'Inventaire stable' },
      { nom: 'Hausse autres courants sur ventes', present: false, detail: 'Stable' },
      { nom: 'Baisse D&A sur PPE brut', present: false, detail: 'D&A stable' },
      { nom: 'Hausse G&A sur ventes', present: true, detail: 'Légère hausse des frais généraux' },
      { nom: 'Hausse taux impôt effectif', present: false, detail: 'Stable' },
    ],
    c_score: 1,
    interpretation: 'Faible risque de manipulation (1/6)',
  },
  sloan: {
    accrual_ratio: -0.032,
    interpretation: 'Accruals négatifs — bons earnings cash',
  },
  drapeaux_rouges: ['Ratio levier en légère hausse'],
  verdict: 'ATTENTION',
  verdict_detail: 'Un signal mineur détecté sur le levier financier.',
  confidence_score: 1.0,
  recommandation_prochaine_etape: [
    'Surveiller évolution du levier sur 2 trimestres',
    'Comparer avec pairs sectoriels',
  ],
  citations: [],
  cost_usd: 0.012,
}

describe('EarningsQualitySection', () => {
  it('affiche le verdict et le toggle fermé par défaut', () => {
    render(<EarningsQualitySection output={BASE_EQ} />)
    expect(screen.getByText('ATTENTION')).toBeInTheDocument()
    expect(screen.queryByTestId('eq-red-flags')).not.toBeInTheDocument()
  })

  it('ouvre la section au clic et affiche F-Score et C-Score', async () => {
    const user = userEvent.setup()
    render(<EarningsQualitySection output={BASE_EQ} />)

    await user.click(screen.getByTestId('eq-toggle'))

    expect(screen.getByTestId('fscore-value')).toHaveTextContent('7/9')
    expect(screen.getByTestId('cscore-value')).toHaveTextContent('1/6')
  })

  it('affiche le M-Score et le Z-Score une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<EarningsQualitySection output={BASE_EQ} />)

    await user.click(screen.getByTestId('eq-toggle'))

    expect(screen.getByTestId('mscore-value')).toHaveTextContent('-2.45')
    expect(screen.getByTestId('zscore-value')).toHaveTextContent('3.15')
  })

  it('affiche les drapeaux rouges une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<EarningsQualitySection output={BASE_EQ} />)

    await user.click(screen.getByTestId('eq-toggle'))

    expect(screen.getByTestId('eq-red-flags')).toBeInTheDocument()
    expect(screen.getByText(/Ratio levier/)).toBeInTheDocument()
  })

  it('affiche les recommandations une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<EarningsQualitySection output={BASE_EQ} />)

    await user.click(screen.getByTestId('eq-toggle'))

    expect(screen.getByTestId('eq-recommendations')).toBeInTheDocument()
    expect(screen.getByText(/Surveiller évolution/)).toBeInTheDocument()
  })

  it('affiche N/A pour M-Score null', async () => {
    const user = userEvent.setup()
    const output = {
      ...BASE_EQ,
      m_score: { ...BASE_EQ.m_score, m_score: null },
    }
    render(<EarningsQualitySection output={output} />)

    await user.click(screen.getByTestId('eq-toggle'))

    expect(screen.getByTestId('mscore-value')).toHaveTextContent('N/A')
  })

  it('affiche les termes X1-X5 du Z-Score une fois ouvert', async () => {
    const user = userEvent.setup()
    render(<EarningsQualitySection output={BASE_EQ} />)

    await user.click(screen.getByTestId('eq-toggle'))

    const termes = screen.getByTestId('zscore-termes')
    expect(termes).toBeInTheDocument()
    for (const label of ['X1', 'X2', 'X3', 'X4', 'X5']) {
      expect(termes).toHaveTextContent(label)
    }
    expect(termes).toHaveTextContent('0.215')
    expect(termes).toHaveTextContent('1.874')
  })

  it('omet la grille X1-X5 quand tous les termes sont null (banque) mais garde score et interprétation', async () => {
    const user = userEvent.setup()
    const output = {
      ...BASE_EQ,
      is_financial: true,
      z_score: {
        ...BASE_EQ.z_score,
        x1: null,
        x2: null,
        x3: null,
        x4: null,
        x5: null,
      },
    }
    render(<EarningsQualitySection output={output} />)

    await user.click(screen.getByTestId('eq-toggle'))

    expect(screen.queryByTestId('zscore-termes')).not.toBeInTheDocument()
    expect(screen.getByTestId('zscore-value')).toHaveTextContent('3.15')
    expect(screen.getByText('Zone sûre (> 2.99)')).toBeInTheDocument()
  })
})
