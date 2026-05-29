import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { lazy, Suspense } from 'react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { RouteFallback } from '../components/RouteFallback'

describe('Routage lazy — Suspense + React.lazy', () => {
  it('affiche le fallback skeleton puis monte la page lazy après résolution du chunk', async () => {
    // Import dynamique contrôlé : on garde la main sur le moment de résolution du chunk
    let resolvePage: (m: { default: () => JSX.Element }) => void = () => {}
    const pendingChunk = new Promise<{ default: () => JSX.Element }>((resolve) => {
      resolvePage = resolve
    })
    const LazyPage = lazy(() => pendingChunk)

    render(
      <MemoryRouter initialEntries={['/']}>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<LazyPage />} />
          </Routes>
        </Suspense>
      </MemoryRouter>,
    )

    // Chunk non résolu → le fallback skeleton est rendu
    expect(screen.getByTestId('route-fallback')).toBeInTheDocument()
    expect(screen.queryByTestId('lazy-page')).not.toBeInTheDocument()

    // Résolution du chunk → la page remplace le fallback
    resolvePage({ default: () => <div data-testid="lazy-page">Page chargée</div> })

    expect(await screen.findByTestId('lazy-page')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByTestId('route-fallback')).not.toBeInTheDocument()
    })
  })
})
