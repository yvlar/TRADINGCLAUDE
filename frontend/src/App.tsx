import { useState, useEffect, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { RouteFallback } from './components/RouteFallback'
import { Button } from './components/ui/button'
import { CommandPalette } from './components/CommandPalette'
import { Disclaimer } from './components/Disclaimer'
import { TenantBadge } from './components/TenantBadge'
import { QuotaBadge } from './components/QuotaBadge'
// Imports dynamiques par page : chaque page (et recharts, embarqué par Dashboard/Esg/
// Watchlist/Compare) forme un chunk séparé, exclu du bundle d'entrée (Sprint 123).
const AnalyzePage = lazy(() => import('./pages/AnalyzePage'))
const ScreenerPage = lazy(() => import('./pages/ScreenerPage'))
const HistoryPage = lazy(() => import('./pages/HistoryPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const WatchlistPage = lazy(() => import('./pages/WatchlistPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const AlertsPage = lazy(() => import('./pages/AlertsPage'))
const ComparePage = lazy(() => import('./pages/ComparePage'))
const EsgPage = lazy(() => import('./pages/EsgPage'))
const SearchPage = lazy(() => import('./pages/SearchPage'))
const BillingPage = lazy(() => import('./pages/BillingPage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'))

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `relative px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors duration-150 ${
          isActive
            ? 'text-foreground border-primary'
            : 'text-muted-foreground border-transparent hover:text-foreground hover:border-primary/30'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {label}
          {isActive && (
            <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-primary animate-scale-in" />
          )}
        </>
      )}
    </NavLink>
  )
}

function AppShell() {
  const { isAuthenticated, logout, user } = useAuth()
  const [paletteOpen, setPaletteOpen] = useState(false)

  // Raccourci global Ctrl+K / ⌘K pour ouvrir/fermer la palette
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <>
      <header className="bg-card border-b border-border sticky top-0 z-50">
        <div className="max-w-shell mx-auto w-full px-6 py-3 flex items-center gap-4">
          <h1 className="text-lg font-bold tracking-tight">Copilote Financier IA</h1>
          {isAuthenticated && (
            <nav className="flex items-end gap-1 ml-4">
              <NavItem to="/" label="Analyse" />
              <NavItem to="/screener" label="Screener" />
              <NavItem to="/historique" label="Historique" />
              <NavItem to="/dashboard" label="Dashboard" />
              <NavItem to="/watchlist" label="Watchlist" />
              <NavItem to="/compare" label="Comparer" />
              <NavItem to="/esg" label="ESG" />
              <NavItem to="/recherche" label="Recherche" />
              <NavItem to="/alerts" label="Alertes" />
              <NavItem to="/facturation" label="Facturation" />
              <NavItem to="/admin" label="Admin" />
            </nav>
          )}
          {isAuthenticated && (
            <>
              <button
                type="button"
                onClick={() => setPaletteOpen(true)}
                className="ml-auto flex items-center gap-2 rounded-md border border-border bg-muted/50 px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                data-testid="command-palette-trigger"
                aria-label="Ouvrir la palette de commandes"
              >
                <span className="hidden md:inline">Rechercher…</span>
                <kbd className="flex items-center gap-0.5 rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px]">
                  <span>Ctrl</span>
                  <span>K</span>
                </kbd>
              </button>
              <TenantBadge tenantName={user?.tenant_name} />
              <QuotaBadge tenantId={user?.tenant_id} />
              <Button variant="ghost" className="text-sm" onClick={logout}>
                Déconnexion
              </Button>
            </>
          )}
        </div>
      </header>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <main data-testid="app-main" className="max-w-shell mx-auto w-full px-6 py-6">
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
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
            <Route
              path="/compare"
              element={
                <ProtectedRoute>
                  <ComparePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/esg"
              element={
                <ProtectedRoute>
                  <EsgPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recherche"
              element={
                <ProtectedRoute>
                  <SearchPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/alerts"
              element={
                <ProtectedRoute>
                  <AlertsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/facturation"
              element={
                <ProtectedRoute>
                  <BillingPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute>
                  <AdminPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </Suspense>
      </main>
      <footer className="border-t border-border mt-8">
        <div className="max-w-shell mx-auto w-full px-6 py-4">
          <Disclaimer variant="footer" />
        </div>
      </footer>
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
