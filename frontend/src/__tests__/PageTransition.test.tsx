import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PageTransition, StaggerItem } from '../components/PageTransition'

describe('PageTransition', () => {
  it('rend ses enfants', () => {
    render(
      <PageTransition>
        <p>Contenu de la page</p>
      </PageTransition>,
    )
    expect(screen.getByText('Contenu de la page')).toBeInTheDocument()
  })

  it('applique la classe animate-fade-in-up', () => {
    const { container } = render(
      <PageTransition>
        <span>test</span>
      </PageTransition>,
    )
    expect((container.firstChild as HTMLElement).className).toContain('animate-fade-in-up')
  })

  it('accepte une className supplémentaire', () => {
    const { container } = render(
      <PageTransition className="space-y-6">
        <span>test</span>
      </PageTransition>,
    )
    expect((container.firstChild as HTMLElement).className).toContain('space-y-6')
  })
})

describe('StaggerItem', () => {
  it('rend ses enfants', () => {
    render(
      <StaggerItem index={0}>
        <p>Item en cascade</p>
      </StaggerItem>,
    )
    expect(screen.getByText('Item en cascade')).toBeInTheDocument()
  })

  it('applique animate-fade-in-up', () => {
    const { container } = render(
      <StaggerItem index={1}>
        <span>test</span>
      </StaggerItem>,
    )
    expect((container.firstChild as HTMLElement).className).toContain('animate-fade-in-up')
  })

  it('applique un délai croissant selon l\'index', () => {
    const { container: c0 } = render(<StaggerItem index={0}><span /></StaggerItem>)
    const { container: c3 } = render(<StaggerItem index={3}><span /></StaggerItem>)
    const delay0 = (c0.firstChild as HTMLElement).style.animationDelay
    const delay3 = (c3.firstChild as HTMLElement).style.animationDelay
    const ms0 = parseInt(delay0)
    const ms3 = parseInt(delay3)
    expect(ms3).toBeGreaterThan(ms0)
  })

  it('plafonne le délai à 400 ms', () => {
    const { container } = render(<StaggerItem index={999}><span /></StaggerItem>)
    const delay = (container.firstChild as HTMLElement).style.animationDelay
    expect(parseInt(delay)).toBeLessThanOrEqual(400)
  })
})
