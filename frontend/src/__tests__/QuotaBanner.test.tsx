import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QuotaBanner, isQuotaError, quotaDetailFromError } from '../components/QuotaBanner'
import { ApiError } from '../api/client'
import type { QuotaErrorDetail } from '../types'

const _detail: QuotaErrorDetail = {
  message: 'Quota mensuel atteint (plan free : 50/50 analyses).',
  plan: 'free',
  used: 50,
  limit: 50,
  remaining: 0,
}

function renderBanner(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('QuotaBanner', () => {
  it('rend le message de quota avec le préfixe « Quota atteint »', () => {
    renderBanner(<QuotaBanner message="Quota mensuel atteint (plan free : 50/50 analyses)." />)
    const banner = screen.getByTestId('quota-banner')
    expect(banner).toBeInTheDocument()
    expect(banner).toHaveTextContent('Quota atteint')
    expect(banner).toHaveTextContent('plan free : 50/50')
  })

  it('porte role=alert pour l’accessibilité', () => {
    renderBanner(<QuotaBanner message="dépassement" />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('avec un detail structuré : affiche plan + borne + lien vers /facturation', () => {
    renderBanner(<QuotaBanner message={_detail.message} detail={_detail} />)
    expect(screen.getByTestId('quota-banner-borne')).toHaveTextContent('plan free · 50/50 analyses')
    const link = screen.getByTestId('quota-upgrade-link')
    expect(link).toHaveAttribute('href', '/facturation')
  })

  it('unit="tickers" : la borne screener n’est pas étiquetée « analyses »', () => {
    const screenerDetail: QuotaErrorDetail = { ..._detail, used: 10, limit: 5, remaining: 0 }
    renderBanner(<QuotaBanner message="trop de tickers" detail={screenerDetail} unit="tickers" />)
    expect(screen.getByTestId('quota-banner-borne')).toHaveTextContent('plan free · 10/5 tickers')
  })

  it('cas dégradé : detail absent → message seul, aucun lien, pas de crash', () => {
    renderBanner(<QuotaBanner message="message brut" detail={null} />)
    expect(screen.getByTestId('quota-banner')).toHaveTextContent('message brut')
    expect(screen.queryByTestId('quota-upgrade-link')).not.toBeInTheDocument()
    expect(screen.queryByTestId('quota-banner-borne')).not.toBeInTheDocument()
  })
})

describe('isQuotaError', () => {
  it('reconnaît un ApiError 429 comme erreur de quota', () => {
    expect(isQuotaError(new ApiError(429, 'quota'))).toBe(true)
  })

  it('rejette les autres statuts et les erreurs non-API', () => {
    expect(isQuotaError(new ApiError(500, 'boom'))).toBe(false)
    expect(isQuotaError(new Error('générique'))).toBe(false)
    expect(isQuotaError(null)).toBe(false)
  })
})

describe('quotaDetailFromError', () => {
  it('extrait le corps structuré d’un ApiError 429', () => {
    const err = new ApiError(429, 'quota', _detail)
    expect(quotaDetailFromError(err)).toEqual(_detail)
  })

  it('déduit remaining quand le champ est absent', () => {
    const err = new ApiError(429, 'quota', { message: 'x', plan: 'free', used: 7, limit: 5 })
    expect(quotaDetailFromError(err)?.remaining).toBe(0)
  })

  it('retourne null pour un corps non structuré (string ou champs manquants)', () => {
    expect(quotaDetailFromError(new ApiError(429, 'texte brut', 'just a string'))).toBeNull()
    expect(quotaDetailFromError(new ApiError(429, 'x', { plan: 'free' }))).toBeNull()
  })

  it('retourne null pour un statut non-429 ou une erreur non-API', () => {
    expect(quotaDetailFromError(new ApiError(500, 'boom', _detail))).toBeNull()
    expect(quotaDetailFromError(new Error('générique'))).toBeNull()
  })
})
