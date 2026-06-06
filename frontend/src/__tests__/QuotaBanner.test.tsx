import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QuotaBanner, isQuotaError } from '../components/QuotaBanner'
import { ApiError } from '../api/client'

describe('QuotaBanner', () => {
  it('rend le message de quota avec le préfixe « Quota atteint »', () => {
    render(<QuotaBanner message="Quota mensuel atteint (plan free : 50/50 analyses)." />)
    const banner = screen.getByTestId('quota-banner')
    expect(banner).toBeInTheDocument()
    expect(banner).toHaveTextContent('Quota atteint')
    expect(banner).toHaveTextContent('plan free : 50/50')
  })

  it('porte role=alert pour l’accessibilité', () => {
    render(<QuotaBanner message="dépassement" />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
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
