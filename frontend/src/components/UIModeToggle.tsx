import { GraduationCap, Wrench } from 'lucide-react'
import { useUIMode } from '../contexts/UIModeContext'
import { cn } from '@/lib/utils'

/** Bascule Débutant ⇄ Avancé — pilote la profondeur d'information affichée dans l'app. */
export function UIModeToggle() {
  const { mode, toggleMode } = useUIMode()
  const isBeginner = mode === 'debutant'

  return (
    <button
      type="button"
      onClick={toggleMode}
      data-testid="ui-mode-toggle"
      role="switch"
      aria-checked={!isBeginner}
      aria-label={`Mode ${isBeginner ? 'Débutant' : 'Avancé'} — cliquer pour basculer`}
      title={
        isBeginner
          ? 'Mode Débutant — explications simples. Cliquer pour passer en Avancé.'
          : 'Mode Avancé — détails techniques. Cliquer pour revenir en Débutant.'
      }
      className={cn(
        'flex items-center gap-1.5 rounded-md border border-border/60 bg-background/50 px-2.5 py-1.5',
        'text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors',
      )}
    >
      {isBeginner ? (
        <>
          <GraduationCap size={13} aria-hidden />
          <span className="hidden sm:inline">Débutant</span>
        </>
      ) : (
        <>
          <Wrench size={13} aria-hidden />
          <span className="hidden sm:inline">Avancé</span>
        </>
      )}
    </button>
  )
}
