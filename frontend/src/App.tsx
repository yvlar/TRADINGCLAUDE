import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import AnalyzePage from './pages/AnalyzePage'
import ScreenerPage from './pages/ScreenerPage'
import HistoryPage from './pages/HistoryPage'
import DashboardPage from './pages/DashboardPage'
import WatchlistPage from './pages/WatchlistPage'
import LoginPage from './pages/LoginPage'
import { Button } from './components/ui/button'

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
          isActive
            ? 'text-foreground border-primary'
            : 'text-muted-foreground border-transparent hover:text-foreground'
        }`
      }
    >
      {label}
    </NavLink>
  )
}

function AppShell() {
  const { isAuthenticated, logout } = useAuth()

  return (
    <>
      <header className="bg-card border-b border-border px-6 py-3 flex items-center gap-4 sticky top-0 z-50">
        <h1 className="text-lg font-bold tracking-tight">Copilote Financier IA</h1>
        {isAuthenticated && (
          <nav className="flex items-end gap-1 ml-4">
            <NavItem to="/" label="Analyse" />
            <NavItem to="/screener" label="Screener" />
            <NavItem to="/historique" label="Historique" />
            <NavItem to="/dashboard" label="Dashboard" />
            <NavItem to="/watchlist" label="Watchlist" />
          </nav>
        )}
        {isAuthenticated && (
          <Button variant="ghost" className="ml-auto text-sm" onClick={logout}>
            Déconnexion
          </Button>
        )}
      </header>
      <main className="max-w-5xl mx-auto px-6 py-6">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AnalyzePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/screener"
            element={
              <ProtectedRoute>
                <ScreenerPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/historique"
            element={
              <ProtectedRoute>
                <HistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/watchlist"
            element={
              <ProtectedRoute>
                <WatchlistPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </BrowserRouter>
  )
}
