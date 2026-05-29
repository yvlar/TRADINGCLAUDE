import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RouteFallback } from '../components/RouteFallback'

describe('RouteFallback — squelette de chargement de route', () => {
  it('se rend sans erreur avec le conteneur status', () => {
    render(<RouteFallback />)
    const fallback = screen.getByTestId('route-fallback')
    expect(fallback).toBeInTheDocument()
    expect(fallback).toHaveAttribute('aria-busy', 'true')
  })

  it('respecte la largeur du shell (max-w-shell)', () => {
    render(<RouteFallback />)
    expect(screen.getByTestId('route-fallback').className).toContain('max-w-shell')
  })
})
