import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { authRegister } from '../api/auth'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'

/** Retourne un niveau de force entre 0 et 4 pour l'indicateur visuel. */
function passwordStrength(pwd: string): number {
  if (pwd.length === 0) return 0
  let score = 0
  if (pwd.length >= 8) score++
  if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score++
  if (/\d/.test(pwd)) score++
  if (/[^A-Za-z0-9]/.test(pwd) && pwd.length >= 12) score++
  return score
}

const STRENGTH_LABELS = ['', 'Faible', 'Moyen', 'Bien', 'Fort']
const STRENGTH_COLORS = [
  '',
  'bg-destructive',
  'bg-neutral',
  'bg-primary',
  'bg-bull',
]

export default function RegisterPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const strength = passwordStrength(password)

  useEffect(() => {
    if (!isLoading && isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, isLoading, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password) {
      setError('Email et mot de passe requis')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await authRegister({ email: email.trim(), password })
      // Après inscription, le cookie de session est posé → rediriger vers login
      navigate('/login', { replace: true, state: { registered: true } })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur lors de l'inscription"
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-[70vh]">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-bold tracking-tight">Créer un compte</h1>
          <p className="text-sm text-muted-foreground">
            Accédez à 18 frameworks d'analyse — Graham, Buffett, ESG et plus encore
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-1">
            <Input
              type="email"
              aria-label="Adresse email"
              placeholder="votre@email.com"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
              data-testid="email-input"
            />
          </div>

          <div className="space-y-2">
            <div className="relative">
              <Input
                type={showPassword ? 'text' : 'password'}
                aria-label="Mot de passe"
                placeholder="Mot de passe (min. 12 caractères)"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
                data-testid="password-input"
              />
              <button
                type="button"
                aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground text-xs hover:text-foreground"
                onClick={() => setShowPassword((v) => !v)}
                tabIndex={-1}
              >
                {showPassword ? 'Masquer' : 'Afficher'}
              </button>
            </div>

            {/* Indicateur de force du mot de passe — 4 niveaux */}
            {password.length > 0 && (
              <div aria-live="polite" data-testid="password-strength">
                <div className="flex gap-1 mb-1">
                  {[1, 2, 3, 4].map((level) => (
                    <div
                      key={level}
                      className={`h-1.5 flex-1 rounded-full transition-colors ${
                        strength >= level ? STRENGTH_COLORS[strength] : 'bg-muted'
                      }`}
                    />
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  Force : <span className="font-medium">{STRENGTH_LABELS[strength]}</span>
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Requis : 12 caractères, majuscule, minuscule, chiffre, caractère spécial
                </p>
              </div>
            )}
          </div>

          {error && (
            <p className="text-sm text-destructive" role="alert" data-testid="error-message">
              {error}
            </p>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={submitting}
            data-testid="submit-button"
          >
            {submitting ? 'Création en cours…' : 'Créer mon compte'}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          Déjà un compte ?{' '}
          <Link to="/login" className="text-primary hover:underline" data-testid="login-link">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  )
}
