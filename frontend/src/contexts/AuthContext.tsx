import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { authLogin, authLogout, authMe, AuthApiError } from '../api/auth'
import type { LoginRequest, User } from '../types'

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (data: LoginRequest) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Restaure la session depuis le cookie httpOnly au montage
  useEffect(() => {
    let cancelled = false
    authMe()
      .then((u) => {
        if (!cancelled) setUser(u)
      })
      .catch(() => {
        // 401 = pas de session active → pas d'erreur à afficher
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (data: LoginRequest): Promise<void> => {
    const response = await authLogin(data)
    setUser(response.user)
  }, [])

  // Re-synchronise le profil depuis le serveur (ex. plan changé après checkout Stripe).
  // Échec (token expiré) → on garde l'état courant : un aléa réseau ne doit pas déconnecter.
  const refreshUser = useCallback(async (): Promise<void> => {
    try {
      setUser(await authMe())
    } catch {
      // état courant préservé
    }
  }, [])

  const logout = useCallback(async (): Promise<void> => {
    try {
      await authLogout()
    } catch {
      // Ignore les erreurs de logout (token déjà expiré, etc.)
    }
    setUser(null)
    // Purge totale du cache react-query au changement d'identité : une re-connexion
    // sous un autre tenant (même session SPA) ne doit jamais servir de données du
    // tenant précédent — inconditionnel, même si authLogout() a échoué.
    queryClient.clear()
    navigate('/login', { replace: true })
  }, [navigate, queryClient])

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: user !== null,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth doit être utilisé dans un AuthProvider')
  return ctx
}

export { AuthApiError }
