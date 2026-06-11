import { createContext, useCallback, useContext, useEffect, useState } from 'react'

export type UIMode = 'debutant' | 'avance'

const STORAGE_KEY = 'tc_ui_mode'

interface UIModeContextValue {
  mode: UIMode
  isBeginner: boolean
  setMode: (mode: UIMode) => void
  toggleMode: () => void
}

const UIModeContext = createContext<UIModeContextValue | null>(null)

function readInitialMode(): UIMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'avance' ? 'avance' : 'debutant'
  } catch {
    // localStorage indisponible (SSR/test isolé) → débutant par défaut
    return 'debutant'
  }
}

export function UIModeProvider({ children }: { children: React.ReactNode }) {
  // Défaut « débutant » : le profil le plus protégé prime tant qu'aucun choix n'est fait.
  const [mode, setModeState] = useState<UIMode>(readInitialMode)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, mode)
    } catch {
      // persistance best-effort — un échec ne casse pas l'UI
    }
  }, [mode])

  const setMode = useCallback((next: UIMode) => setModeState(next), [])
  const toggleMode = useCallback(
    () => setModeState((m) => (m === 'debutant' ? 'avance' : 'debutant')),
    [],
  )

  return (
    <UIModeContext.Provider
      value={{ mode, isBeginner: mode === 'debutant', setMode, toggleMode }}
    >
      {children}
    </UIModeContext.Provider>
  )
}

export function useUIMode(): UIModeContextValue {
  const ctx = useContext(UIModeContext)
  if (ctx === null) {
    throw new Error('useUIMode doit être utilisé dans un UIModeProvider')
  }
  return ctx
}
