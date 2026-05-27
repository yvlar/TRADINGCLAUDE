import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

vi.mock('../api/auth', () => ({
  authMe: vi.fn().mockRejectedValue(new Error('401')),
  authLogin: vi.fn(),
  authLogout: vi.fn().mockResolvedValue(undefined),
}))

describe('App — shell pleine largeur', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('rend le conteneur principal avec le shell fluide large', async () => {
    render(<App />)
    const main = await screen.findByTestId('app-main')
    expect(main.className).toContain('max-w-shell')
    expect(main.className).toContain('mx-auto')
    expect(main.className).not.toContain('max-w-5xl')
  })

  it('affiche le titre de l’application', async () => {
    render(<App />)
    expect(await screen.findByText('Copilote Financier IA')).toBeInTheDocument()
  })
})
