import { createContext, useContext, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

interface AuthContextValue {
  token: string | null
  login: (key: string) => void
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem('api_token'),
  )
  const navigate = useNavigate()

  const login = useCallback((key: string) => {
    localStorage.setItem('api_token', key)
    setToken(key)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('api_token')
    setToken(null)
    navigate('/login', { replace: true })
  }, [navigate])

  return (
    <AuthContext.Provider value={{ token, login, logout, isAuthenticated: token !== null && token !== '' }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth doit être utilisé dans un AuthProvider')
  return ctx
}
