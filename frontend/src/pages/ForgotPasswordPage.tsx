import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authForgotPassword } from '../api/auth'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) {
      setError('Email requis')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await authForgotPassword({ email: email.trim() })
      setSubmitted(true)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur lors de l'envoi"
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="flex items-center justify-center min-h-[70vh]">
        <div className="w-full max-w-sm space-y-4 text-center">
          <h1 className="text-2xl font-bold tracking-tight">Email envoyé</h1>
          <p className="text-sm text-muted-foreground">
            Si un compte existe pour <strong>{email}</strong>, vous recevrez un lien de
            réinitialisation valable 1 heure.
          </p>
          <Link to="/login" className="text-primary hover:underline text-sm">
            Retour à la connexion
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[70vh]">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-bold tracking-tight">Mot de passe oublié</h1>
          <p className="text-sm text-muted-foreground">
            Entrez votre email pour recevoir un lien de réinitialisation.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
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
            {submitting ? 'Envoi en cours…' : 'Envoyer le lien'}
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
