import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { CommandPalette } from '../components/CommandPalette'

// Mock cmdk : le composant Command se comporte comme des divs/inputs standard
vi.mock('cmdk', () => {
  function Command({ children, onKeyDown, shouldFilter: _sf, className }: {
    children: React.ReactNode
    onKeyDown?: React.KeyboardEventHandler
    shouldFilter?: boolean
    className?: string
  }) {
    return <div className={className} onKeyDown={onKeyDown}>{children}</div>
  }
  Command.Input = function CmdInput({ value, onValueChange, placeholder, className, 'data-testid': testId }: {
    value: string
    onValueChange: (v: string) => void
    placeholder?: string
    className?: string
    'data-testid'?: string
  }) {
    return (
      <input
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        placeholder={placeholder}
        className={className}
        data-testid={testId}
      />
    )
  }
  Command.List = function CmdList({ children, className }: { children: React.ReactNode; className?: string }) {
    return <div className={className}>{children}</div>
  }
  Command.Empty = function CmdEmpty({ children, className, 'data-testid': testId }: {
    children: React.ReactNode
    className?: string
    'data-testid'?: string
  }) {
    return <div className={className} data-testid={testId}>{children}</div>
  }
  Command.Group = function CmdGroup({ children, heading, className }: {
    children: React.ReactNode
    heading?: string
    className?: string
  }) {
    return (
      <div className={className}>
        {heading && <div>{heading}</div>}
        {children}
      </div>
    )
  }
  Command.Item = function CmdItem({ children, onSelect, className, 'data-testid': testId, value: _v }: {
    children: React.ReactNode
    onSelect?: () => void
    className?: string
    'data-testid'?: string
    value?: string
  }) {
    return (
      <div
        role="option"
        className={className}
        data-testid={testId}
        onClick={onSelect}
      >
        {children}
      </div>
    )
  }
  return { Command }
})

// Mock navigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

// Mock analyses récentes
vi.mock('../lib/recentAnalyses', () => ({
  loadRecentAnalyses: () => [
    {
      ticker: 'BNS.TO',
      composite_score: 7.2,
      workflow: 'value_graham',
      created_at: '2026-01-01',
      inter_skill_conflicts: [],
    },
  ],
}))

// Mock recherche sémantique
vi.mock('../api/search', () => ({
  fetchSemanticSearch: vi.fn().mockResolvedValue({
    rag_enabled: false,
    query: '',
    results: [],
  }),
}))

function renderPalette(open: boolean, onClose = vi.fn()) {
  return render(
    <MemoryRouter>
      <CommandPalette open={open} onClose={onClose} />
    </MemoryRouter>,
  )
}

describe('CommandPalette', () => {
  beforeEach(() => {
    mockNavigate.mockReset()
  })

  it('ne rend rien quand fermé', () => {
    renderPalette(false)
    expect(screen.queryByTestId('command-palette-overlay')).toBeNull()
  })

  it('rend la palette et le champ de saisie quand ouvert', () => {
    renderPalette(true)
    expect(screen.getByTestId('command-palette-overlay')).toBeInTheDocument()
    expect(screen.getByTestId('command-palette-input')).toBeInTheDocument()
  })

  it('affiche les pages de navigation', () => {
    renderPalette(true)
    expect(screen.getByText('Analyse')).toBeInTheDocument()
    expect(screen.getByText('Screener')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('ferme la palette en cliquant le backdrop', () => {
    const onClose = vi.fn()
    renderPalette(true, onClose)
    fireEvent.click(screen.getByTestId('command-palette-backdrop'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('affiche les analyses récentes quand la saisie est vide', () => {
    renderPalette(true)
    expect(screen.getByTestId('command-recent-BNS.TO')).toBeInTheDocument()
  })

  it('affiche le bouton Analyser et navigue vers /?ticker= en cliquant', () => {
    const onClose = vi.fn()
    renderPalette(true, onClose)
    const input = screen.getByTestId('command-palette-input')
    fireEvent.change(input, { target: { value: 'bns.to' } })
    expect(screen.getByTestId('command-analyze')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('command-analyze'))
    expect(mockNavigate).toHaveBeenCalledWith('/?ticker=BNS.TO')
    expect(onClose).toHaveBeenCalled()
  })

  it('filtre les pages selon la saisie', () => {
    renderPalette(true)
    const input = screen.getByTestId('command-palette-input')
    fireEvent.change(input, { target: { value: 'scree' } })
    expect(screen.getByText('Screener')).toBeInTheDocument()
    expect(screen.queryByText('Dashboard')).toBeNull()
  })

  it('navigue vers la page en cliquant un item de navigation', () => {
    const onClose = vi.fn()
    renderPalette(true, onClose)
    fireEvent.click(screen.getByTestId('command-nav-screener'))
    expect(mockNavigate).toHaveBeenCalledWith('/screener')
    expect(onClose).toHaveBeenCalled()
  })

  it('expose role="dialog" et aria-modal pour les lecteurs d\'écran', () => {
    renderPalette(true)
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-label')
  })

  it('place le focus sur le champ à l\'ouverture et le restaure à la fermeture', () => {
    const trigger = document.createElement('button')
    document.body.appendChild(trigger)
    trigger.focus()
    expect(document.activeElement).toBe(trigger)

    const { rerender } = render(
      <MemoryRouter>
        <CommandPalette open={true} onClose={vi.fn()} />
      </MemoryRouter>,
    )
    expect(document.activeElement).toBe(screen.getByTestId('command-palette-input'))

    rerender(
      <MemoryRouter>
        <CommandPalette open={false} onClose={vi.fn()} />
      </MemoryRouter>,
    )
    expect(document.activeElement).toBe(trigger)
    document.body.removeChild(trigger)
  })
})
