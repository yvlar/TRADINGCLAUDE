import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { authLogin, authLogout, authMe, AuthApiError } from '../api/auth'
import type { LoginRequest, User } from '../types'

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (data: LoginRequest) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()

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

  const logout = useCallback(async (): Promise<void> => {
    try {
      await authLogout()
    } catch {
      // Ignore les erreurs de logout (token déjà expiré, etc.)
    }
    setUser(null)
    navigate('/login', { replace: true })
  }, [navigate])

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: user !== null,
        isLoading,
        login,
        logout,
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
