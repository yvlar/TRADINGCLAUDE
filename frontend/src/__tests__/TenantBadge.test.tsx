import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { TenantBadge } from '../components/TenantBadge'

describe('TenantBadge (Sprint 169)', () => {
  it('affiche le nom du tenant quand il est présent', () => {
    render(<TenantBadge tenantName="Acme Capital" />)
    const el = screen.getByTestId('tenant-badge')
    expect(el).toHaveTextContent('Espace :')
    expect(el).toHaveTextContent('Acme Capital')
  })

  it('ne rend rien quand le nom est absent (rétrocompat réponse en cache)', () => {
    const { container } = render(<TenantBadge tenantName={undefined} />)
    expect(screen.queryByTestId('tenant-badge')).toBeNull()
    expect(container).toBeEmptyDOMElement()
  })

  it('ne rend rien quand le nom est une chaîne vide', () => {
    render(<TenantBadge tenantName="" />)
    expect(screen.queryByTestId('tenant-badge')).toBeNull()
  })
})
