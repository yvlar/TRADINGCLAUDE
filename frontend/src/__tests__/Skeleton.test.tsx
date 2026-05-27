import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  Skeleton,
  SkeletonRow,
  SkeletonCard,
  SkeletonCardGrid,
  SkeletonChart,
  SkeletonTable,
} from '../components/ui/skeleton'

describe('Skeleton', () => {
  it('rend un élément aria-hidden avec la classe shimmer', () => {
    const { container } = render(<Skeleton />)
    const el = container.firstChild as HTMLElement
    expect(el.getAttribute('aria-hidden')).toBe('true')
    expect(el.className).toContain('skeleton-shimmer')
  })

  it('accepte une className supplémentaire', () => {
    const { container } = render(<Skeleton className="h-4 w-20" />)
    const el = container.firstChild as HTMLElement
    expect(el.className).toContain('h-4')
    expect(el.className).toContain('w-20')
  })
})

describe('SkeletonRow', () => {
  it('rend le nombre de colonnes par défaut (5)', () => {
    const { container } = render(
      <table><tbody><SkeletonRow /></tbody></table>,
    )
    const cells = container.querySelectorAll('td')
    expect(cells).toHaveLength(5)
  })

  it('rend le nombre de colonnes spécifié', () => {
    const { container } = render(
      <table><tbody><SkeletonRow cols={3} /></tbody></table>,
    )
    expect(container.querySelectorAll('td')).toHaveLength(3)
  })
})

describe('SkeletonCard', () => {
  it('rend trois rectangles shimmer', () => {
    const { container } = render(<SkeletonCard />)
    const shimmers = container.querySelectorAll('[aria-hidden="true"]')
    expect(shimmers.length).toBeGreaterThanOrEqual(3)
  })
})

describe('SkeletonCardGrid', () => {
  it('rend le nombre de cartes par défaut (4)', () => {
    const { container } = render(<SkeletonCardGrid />)
    // Chaque carte contient ≥3 shimmers — vérifie qu'il y a du contenu
    const grid = container.firstChild as HTMLElement
    expect(grid.children).toHaveLength(4)
  })

  it('rend le nombre de cartes spécifié', () => {
    const { container } = render(<SkeletonCardGrid count={2} />)
    const grid = container.firstChild as HTMLElement
    expect(grid.children).toHaveLength(2)
  })
})

describe('SkeletonChart', () => {
  it('rend un graphique squelette', () => {
    const { container } = render(<SkeletonChart />)
    expect(container.firstChild).toBeTruthy()
  })
})

describe('SkeletonTable', () => {
  it('rend 6 lignes × 5 colonnes par défaut', () => {
    const { container } = render(<SkeletonTable />)
    const rows = container.querySelectorAll('tr')
    expect(rows).toHaveLength(6)
    const cells = container.querySelectorAll('td')
    expect(cells).toHaveLength(30) // 6×5
  })

  it('rend les dimensions spécifiées', () => {
    const { container } = render(<SkeletonTable rows={3} cols={4} />)
    expect(container.querySelectorAll('tr')).toHaveLength(3)
    expect(container.querySelectorAll('td')).toHaveLength(12)
  })
})
