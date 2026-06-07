import { ApiError } from '../api/client'

/** True si l'erreur est un dépassement de quota (HTTP 429) renvoyé par l'API. */
export function isQuotaError(err: unknown): boolean {
  return err instanceof ApiError && err.status === 429
}

interface QuotaBannerProps {
  message: string
}

/** Bandeau dédié au dépassement de quota — distinct du bandeau d'erreur générique. */
export function QuotaBanner({ message }: QuotaBannerProps) {
  return (
    <div
      data-testid="quota-banner"
      role="alert"
      className="border border-amber-500 bg-amber-500/10 text-amber-700 dark:text-amber-400 rounded-lg px-4 py-3 text-sm animate-fade-in-up"
    >
      <span className="font-semibold">Quota atteint — </span>
      {message}
    </div>
  )
}
