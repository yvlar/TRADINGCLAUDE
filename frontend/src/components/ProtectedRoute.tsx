import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function ProtectedRoute({ children }: { children: React.ReactNode }): React.ReactElement | null {
  const { isAuthenticated, isLoading } = useAuth()

  // Attendre la vérification du cookie avant de rediriger
  if (isLoading) return <></>

  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}
