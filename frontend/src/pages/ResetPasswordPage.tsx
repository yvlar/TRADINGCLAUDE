import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { authResetPassword } from '../api/auth'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') ?? ''

  const [newPassword, setNewPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!token) setError('Lien de réinitialisation invalide ou manquant.')
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newPassword) {
      setError('Le nouveau mot de passe est requis')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await authResetPassword({ token, new_password: newPassword })
      setSuccess(true)
      setTimeout(() => navigate('/login', { replace: true }), 2000)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur lors de la réinitialisation'
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="flex items-center justify-center min-h-[70vh]">
        <div className="w-full max-w-sm space-y-4 text-center">
          <h1 className="text-2xl font-bold tracking-tight">Mot de passe réinitialisé</h1>
          <p className="text-sm text-muted-foreground">
            Votre mot de passe a été mis à jour. Redirection vers la connexion…
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[70vh]">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-bold tracking-tight">Nouveau mot de passe</h1>
          <p className="text-sm text-muted-foreground">
            Choisissez un mot de passe fort (min. 12 caractères).
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="relative">
            <Input
              type={showPassword ? 'text' : 'password'}
              aria-label="Nouveau mot de passe"
              placeholder="Nouveau mot de passe"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={submitting || !token}
              data-testid="new-password-input"
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

          {error && (
            <p className="text-sm text-destructive" role="alert" data-testid="error-message">
              {error}
            </p>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={submitting || !token}
            data-testid="submit-button"
          >
            {submitting ? 'Réinitialisation…' : 'Réinitialiser le mot de passe'}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          <Link to="/login" className="text-primary hover:underline">
            Retour à la connexion
          </Link>
        </p>
      </div>
    </div>
  )
}
