import { useEffect, useState, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { Command } from 'cmdk'
import { Search, ArrowRight, Clock, BookOpen, ArrowUpRight } from 'lucide-react'
import { loadRecentAnalyses } from '../lib/recentAnalyses'
import { fetchSemanticSearch } from '../api/search'
import type { SemanticSearchResult } from '../types'

const NAV_ITEMS = [
  { label: 'Analyse', path: '/' },
  { label: 'Screener', path: '/screener' },
  { label: 'Historique', path: '/historique' },
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Watchlist', path: '/watchlist' },
  { label: 'Comparer', path: '/compare' },
  { label: 'ESG', path: '/esg' },
  { label: 'Recherche sémantique', path: '/recherche' },
  { label: 'Alertes', path: '/alerts' },
  { label: 'Admin', path: '/admin' },
]

const ITEM_CLASS =
  'relative flex cursor-default select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground hover:bg-accent hover:text-accent-foreground transition-colors'

const GROUP_CLASS =
  'overflow-hidden p-1 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground'

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [ragResults, setRagResults] = useState<SemanticSearchResult[]>([])
  const [ragLoading, setRagLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const dialogRef = useRef<HTMLDivElement>(null)

  // Réinitialiser l'état à chaque ouverture/fermeture
  useEffect(() => {
    if (!open) {
      setQuery('')
      setRagResults([])
      setRagLoading(false)
    }
  }, [open])

  // Focus management : focus initial sur le champ à l'ouverture, restauration sur
  // l'élément déclencheur à la fermeture (mémorisé via document.activeElement).
  useEffect(() => {
    if (!open) return
    const trigger = document.activeElement as HTMLElement | null
    dialogRef.current?.querySelector<HTMLElement>('input')?.focus()
    return () => {
      trigger?.focus?.()
    }
  }, [open])

  // Recherche RAG avec debounce 400 ms
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (query.length < 3) {
      setRagResults([])
      return
    }
    debounceRef.current = setTimeout(async () => {
      setRagLoading(true)
      try {
        const res = await fetchSemanticSearch(query, 3)
        setRagResults(res.rag_enabled ? res.results : [])
      } catch {
        setRagResults([])
      } finally {
        setRagLoading(false)
      }
    }, 400)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query])

  const handleNavigate = useCallback(
    (path: string) => {
      navigate(path)
      onClose()
    },
    [navigate, onClose],
  )

  const handleAnalyze = useCallback(
    (ticker: string) => {
      navigate(`/?ticker=${encodeURIComponent(ticker.trim().toUpperCase())}`)
      onClose()
    },
    [navigate, onClose],
  )

  // Piège le focus dans le dialogue : Tab/Shift+Tab boucle entre les éléments
  // focusables ; Escape ferme. Conserve le comportement clavier existant.
  const handleDialogKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      onClose()
      return
    }
    if (e.key !== 'Tab') return
    const focusables = dialogRef.current?.querySelectorAll<HTMLElement>(
      'a[href], button, input, textarea, select, [tabindex]:not([tabindex="-1"])',
    )
    if (!focusables || focusables.length === 0) return
    const first = focusables[0]
    const last = focusables[focusables.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }

  if (!open) return null

  const trimmed = query.trim()
  const upper = trimmed.toUpperCase()
  const recentAnalyses = loadRecentAnalyses()
  const filteredNav = NAV_ITEMS.filter(
    (item) => !trimmed || item.label.toLowerCase().includes(trimmed.toLowerCase()),
  )

  return createPortal(
    <div className="fixed inset-0 z-50" data-testid="command-palette-overlay">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        aria-hidden="true"
        onClick={onClose}
        data-testid="command-palette-backdrop"
      />

      {/* Fenêtre */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Palette de commandes"
        onKeyDown={handleDialogKeyDown}
        className="fixed left-1/2 top-[18%] -translate-x-1/2 w-full max-w-xl px-4"
      >
        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-2xl ring-1 ring-black/5">
          <Command shouldFilter={false} className="w-full">
            {/* Champ de recherche */}
            <div className="flex items-center border-b border-border px-3">
              <Search
                className="mr-2 h-4 w-4 shrink-0 text-muted-foreground"
                aria-hidden="true"
              />
              <Command.Input
                placeholder="Chercher une page, un ticker, un concept…"
                value={query}
                onValueChange={setQuery}
                className="flex h-12 w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground"
                data-testid="command-palette-input"
              />
              <kbd className="hidden sm:flex items-center rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                ESC
              </kbd>
            </div>

            <Command.List className="max-h-80 overflow-y-auto overflow-x-hidden p-1">
              <Command.Empty
                className="py-6 text-center text-sm text-muted-foreground"
                data-testid="command-palette-empty"
              >
                {ragLoading ? 'Recherche en cours…' : 'Aucun résultat.'}
              </Command.Empty>

              {/* Actions rapides quand une saisie est présente */}
              {trimmed.length > 0 && (
                <Command.Group heading="Actions rapides" className={GROUP_CLASS}>
                  <Command.Item
                    value={`analyser-${upper}`}
                    onSelect={() => handleAnalyze(trimmed)}
                    className={ITEM_CLASS}
                    data-testid="command-analyze"
                  >
                    <Search className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
                    <span>
                      Analyser <strong>{upper}</strong>
                    </span>
                  </Command.Item>
                  <Command.Item
                    value={`comparer-${upper}`}
                    onSelect={() => handleNavigate('/compare')}
                    className={ITEM_CLASS}
                    data-testid="command-compare"
                  >
                    <ArrowUpRight className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
                    <span>Comparer</span>
                  </Command.Item>
                </Command.Group>
              )}

              {/* Analyses récentes (palette vide) */}
              {!trimmed && recentAnalyses.length > 0 && (
                <Command.Group heading="Analyses récentes" className={GROUP_CLASS}>
                  {recentAnalyses.slice(0, 5).map((r) => (
                    <Command.Item
                      key={r.ticker}
                      value={`recent-${r.ticker}`}
                      onSelect={() => handleAnalyze(r.ticker)}
                      className={ITEM_CLASS}
                      data-testid={`command-recent-${r.ticker}`}
                    >
                      <Clock
                        className="h-4 w-4 text-muted-foreground shrink-0"
                        aria-hidden="true"
                      />
                      <span className="font-medium">{r.ticker}</span>
                      {r.composite_score?.score != null && (
                        <span className="ml-auto text-xs text-muted-foreground tabular-nums">
                          Score {r.composite_score.score.toFixed(1)}
                        </span>
                      )}
                    </Command.Item>
                  ))}
                </Command.Group>
              )}

              {/* Navigation entre pages */}
              {filteredNav.length > 0 && (
                <Command.Group heading="Pages" className={GROUP_CLASS}>
                  {filteredNav.map((item) => (
                    <Command.Item
                      key={item.path}
                      value={`nav-${item.path}`}
                      onSelect={() => handleNavigate(item.path)}
                      className={ITEM_CLASS}
                      data-testid={`command-nav-${item.path.replace(/\//g, '') || 'home'}`}
                    >
                      <ArrowRight
                        className="h-4 w-4 text-muted-foreground shrink-0"
                        aria-hidden="true"
                      />
                      {item.label}
                    </Command.Item>
                  ))}
                </Command.Group>
              )}

              {/* Résultats RAG */}
              {ragResults.length > 0 && (
                <Command.Group heading="Base de connaissances" className={GROUP_CLASS}>
                  {ragResults.map((result, i) => (
                    <Command.Item
                      key={i}
                      value={`rag-${i}`}
                      onSelect={() => {
                        navigate(`/recherche?q=${encodeURIComponent(query)}`)
                        onClose()
                      }}
                      className={ITEM_CLASS}
                      data-testid={`command-rag-${i}`}
                    >
                      <BookOpen
                        className="h-4 w-4 text-muted-foreground shrink-0"
                        aria-hidden="true"
                      />
                      <div className="min-w-0">
                        <div className="truncate text-xs text-muted-foreground">
                          {result.source.split('/').pop()}
                        </div>
                        <div className="truncate">{result.extrait.slice(0, 80)}</div>
                      </div>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
            </Command.List>
          </Command>
        </div>

        {/* Légende raccourcis */}
        <p className="mt-2 text-center text-xs text-muted-foreground select-none">
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono">↵</kbd>{' '}
          sélectionner ·{' '}
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono">↑↓</kbd>{' '}
          naviguer ·{' '}
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono">ESC</kbd>{' '}
          fermer
        </p>
      </div>
    </div>,
    document.body,
  )
}
