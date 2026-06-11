import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UIModeProvider, useUIMode } from '../contexts/UIModeContext'
import { UIModeToggle } from '../components/UIModeToggle'

function Probe() {
  const { mode, isBeginner } = useUIMode()
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <span data-testid="is-beginner">{String(isBeginner)}</span>
    </div>
  )
}

describe('UIModeContext + UIModeToggle', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('démarre en mode débutant par défaut', () => {
    render(
      <UIModeProvider>
        <Probe />
      </UIModeProvider>,
    )
    expect(screen.getByTestId('mode')).toHaveTextContent('debutant')
    expect(screen.getByTestId('is-beginner')).toHaveTextContent('true')
  })

  it('la bascule alterne débutant ⇄ avancé', async () => {
    const user = userEvent.setup()
    render(
      <UIModeProvider>
        <UIModeToggle />
        <Probe />
      </UIModeProvider>,
    )
    expect(screen.getByTestId('mode')).toHaveTextContent('debutant')

    await user.click(screen.getByTestId('ui-mode-toggle'))
    expect(screen.getByTestId('mode')).toHaveTextContent('avance')

    await user.click(screen.getByTestId('ui-mode-toggle'))
    expect(screen.getByTestId('mode')).toHaveTextContent('debutant')
  })

  it('persiste le choix dans localStorage', async () => {
    const user = userEvent.setup()
    render(
      <UIModeProvider>
        <UIModeToggle />
      </UIModeProvider>,
    )
    await user.click(screen.getByTestId('ui-mode-toggle'))
    expect(localStorage.getItem('tc_ui_mode')).toBe('avance')
  })

  it('restaure le mode avancé depuis localStorage au montage', () => {
    localStorage.setItem('tc_ui_mode', 'avance')
    render(
      <UIModeProvider>
        <Probe />
      </UIModeProvider>,
    )
    expect(screen.getByTestId('mode')).toHaveTextContent('avance')
  })

  it('reflète le mode courant via aria-checked', async () => {
    const user = userEvent.setup()
    render(
      <UIModeProvider>
        <UIModeToggle />
      </UIModeProvider>,
    )
    const toggle = screen.getByTestId('ui-mode-toggle')
    expect(toggle).toHaveAttribute('aria-checked', 'false') // débutant
    await user.click(toggle)
    expect(toggle).toHaveAttribute('aria-checked', 'true') // avancé
  })
})
