import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import type { QuotaErrorDetail } from '../types'

/** True si l'erreur est un dépassement de quota (HTTP 429) renvoyé par l'API. */
export function isQuotaError(err: unknown): boolean {
  return err instanceof ApiError && err.status === 429
}

/**
 * Extrait le corps structuré d'un 429 quota, ou `null` si absent/malformé.
 * Repli propre : un vieux cache ou un 429 sans corps structuré → `null` → bandeau message seul.
 */
export function quotaDetailFromError(err: unknown): QuotaErrorDetail | null {
  if (!(err instanceof ApiError) || err.status !== 429) return null
  const d = err.detail
  if (d === null || typeof d !== 'object') return null
  const r = d as Record<string, unknown>
  if (typeof r.plan !== 'string' || typeof r.used !== 'number' || typeof r.limit !== 'number') {
    return null
  }
  return {
    message: typeof r.message === 'string' ? r.message : '',
    plan: r.plan,
    used: r.used,
    limit: r.limit,
    remaining: typeof r.remaining === 'number' ? r.remaining : Math.max(0, r.limit - r.used),
  }
}

interface QuotaBannerProps {
  message: string
  // Corps structuré du 429 — quand présent, affiche plan + borne + CTA d'upgrade.
  detail?: QuotaErrorDetail | null
  // Unité de la borne `used/limit` — « analyses » (borne mensuelle) ou « tickers » (screener).
  unit?: string
}

/** Bandeau dédié au dépassement de quota — distinct du bandeau d'erreur générique. */
export function QuotaBanner({ message, detail, unit = 'analyses' }: QuotaBannerProps) {
  return (
    <div
      data-testid="quota-banner"
      role="alert"
      className="border border-amber-500 bg-amber-500/10 text-amber-700 dark:text-amber-400 rounded-lg px-4 py-3 text-sm animate-fade-in-up"
    >
      <span className="font-semibold">Quota atteint — </span>
      {message}
      {detail && (
        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
          <span data-testid="quota-banner-borne">
            plan <span className="font-semibold uppercase">{detail.plan}</span>
            {' · '}
            {detail.used}/{detail.limit} {unit}
          </span>
          <Link
            to="/facturation"
            data-testid="quota-upgrade-link"
            className="font-semibold underline underline-offset-2 hover:text-amber-800 dark:hover:text-amber-300"
          >
            Passer à un plan supérieur →
          </Link>
        </div>
      )}
    </div>
  )
}
