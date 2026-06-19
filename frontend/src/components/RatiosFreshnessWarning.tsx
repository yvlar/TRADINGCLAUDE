interface RatiosFreshnessWarningProps {
  warnings: string[] | null | undefined
}

// Bannière d'avertissement quand les ratios d'entrée sont périmés (> 30 j) — une ligne par famille.
// Rien à afficher si la liste est vide ou absente (honnêteté None : pas de faux positif quand la date manque).
export function RatiosFreshnessWarning({ warnings }: RatiosFreshnessWarningProps) {
  if (!warnings || warnings.length === 0) return null
  return (
    <div
      role="note"
      data-testid="ratios-freshness-warning"
      className="border border-amber-500 bg-amber-500/10 text-amber-700 dark:text-amber-400 rounded-lg px-4 py-3 text-sm"
    >
      <p className="font-medium flex items-center gap-1.5">
        <span aria-hidden="true">⚠</span>
        Fraîcheur des données
      </p>
      <ul className="mt-1 list-disc pl-5 space-y-0.5">
        {warnings.map((message, i) => (
          <li key={i}>{message}</li>
        ))}
      </ul>
    </div>
  )
}
