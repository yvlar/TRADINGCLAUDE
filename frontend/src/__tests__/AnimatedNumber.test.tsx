import { describe, expect, it } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { AnimatedNumber } from '../components/ui/animated-number'

describe('AnimatedNumber', () => {
  it('affiche la valeur initiale', () => {
    render(<AnimatedNumber value={42} />)
    // La valeur initiale est affichée (pas encore animée)
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('applique la className fournie', () => {
    const { container } = render(
      <AnimatedNumber value={10} className="text-green-400" />,
    )
    expect((container.firstChild as HTMLElement).className).toContain('text-green-400')
  })

  it('utilise le formatter pour afficher la valeur', () => {
    render(
      <AnimatedNumber
        value={0.75}
        formatter={(n) => `${(n * 100).toFixed(0)}%`}
        duration={0}
      />,
    )
    // Avec duration=0 l'animation se complète immédiatement
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('rend un span', () => {
    const { container } = render(<AnimatedNumber value={100} />)
    expect(container.firstChild?.nodeName).toBe('SPAN')
  })

  it('affiche tabular-nums pour l\'alignement des chiffres', () => {
    const { container } = render(<AnimatedNumber value={1234} />)
    expect((container.firstChild as HTMLElement).className).toContain('tabular-nums')
  })
})
