import { Skeleton } from './ui/skeleton'

/** Squelette affiché pendant le chargement du chunk d'une page (code-splitting React.lazy). */
export function RouteFallback() {
  return (
    <div
      className="max-w-shell mx-auto w-full space-y-6"
      data-testid="route-fallback"
      role="status"
      aria-busy="true"
      aria-live="polite"
    >
      <span className="sr-only">Chargement de la page…</span>
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  )
}
