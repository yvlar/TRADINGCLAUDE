import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { HelpCircle } from 'lucide-react'
import { GLOSSARY, type GlossaryKey } from '../data/glossary'
import { cn } from '@/lib/utils'

interface GlossaryTermProps {
  /** Clé du terme dans GLOSSARY. */
  term: GlossaryKey
  /** Texte affiché — par défaut le libellé du glossaire. */
  children?: React.ReactNode
  className?: string
}

/**
 * Terme cliquable qui révèle sa définition vulgarisée (popover léger, sans dépendance Radix).
 * Pilotage au clic (accessible + compatible tactile) ; fermeture sur Escape ou clic extérieur.
 * « En savoir plus » renvoie vers la recherche sémantique préremplie.
 */
export function GlossaryTerm({ term, children, className }: GlossaryTermProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLSpanElement>(null)
  const panelId = useId()
  const entry = GLOSSARY[term]

  useEffect(() => {
    if (!open) return
    function onPointerDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (!entry) return <>{children}</>

  return (
    <span ref={containerRef} className="relative inline-flex">
      <button
        type="button"
        data-testid={`glossary-trigger-${term}`}
        aria-expanded={open}
        aria-describedby={open ? panelId : undefined}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'inline-flex items-center gap-0.5 underline decoration-dotted underline-offset-2',
          'text-foreground/90 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring rounded',
          className,
        )}
      >
        {children ?? entry.label}
        <HelpCircle size={12} className="shrink-0 text-muted-foreground" aria-hidden />
      </button>

      {open && (
        <span
          id={panelId}
          role="tooltip"
          data-testid={`glossary-panel-${term}`}
          className={cn(
            'absolute left-0 top-full z-50 mt-1 w-72 rounded-lg border border-border bg-card',
            'p-3 text-left text-xs font-normal normal-case text-card-foreground shadow-lg',
          )}
        >
          <span className="block font-semibold text-foreground">{entry.label}</span>
          <span className="mt-1 block text-muted-foreground">{entry.definition}</span>
          {entry.learnQuery && (
            <Link
              to={`/recherche?q=${encodeURIComponent(entry.learnQuery)}`}
              data-testid={`glossary-learn-${term}`}
              className="mt-2 inline-block font-medium text-primary hover:underline"
            >
              En savoir plus →
            </Link>
          )}
        </span>
      )}
    </span>
  )
}
