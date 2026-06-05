// Ratios Graham instrumentés (Sprint 140) : clé yfinance primaire attendue par ratio.
// Un repli réel = clé effective de ratios_provenance ≠ cette clé primaire (signal-only).
const RATIO_PRIMARY_KEYS: Record<string, string> = {
  pb: 'priceToBook',
  debt_equity: 'debtToEquity',
  book_value: 'bookValue',
}

const RATIO_LABELS: Record<string, string> = {
  pb: 'P/B',
  debt_equity: 'Dette/Capitaux',
  book_value: 'Valeur comptable',
}

// Ne retient que les ratios dont la provenance révèle un repli (clé effective ≠ clé primaire).
// Provenance null/absente ou clés toutes primaires → liste vide (aucun bruit affiché).
export function ratiosEnRepli(
  provenance: Record<string, string> | null | undefined,
): [string, string][] {
  if (!provenance) return []
  return Object.entries(provenance).filter(
    ([name, key]) => RATIO_PRIMARY_KEYS[name] !== undefined && key !== RATIO_PRIMARY_KEYS[name],
  )
}

interface RatiosProvenanceNoteProps {
  provenance: Record<string, string> | null | undefined
  testId?: string
  className?: string
}

// Badges signal-only « <ratio> via <clé> (repli) », rendus seulement quand la clé yfinance
// effective diffère de la clé primaire attendue. Rien sinon (aucun bruit). Composant partagé
// par AnalyzeForm (après auto-fill) et AnalysisResult (analyse rendue/rechargée — Sprint 150).
export function RatiosProvenanceNote({
  provenance,
  testId = 'ratios-provenance',
  className = 'mt-2',
}: RatiosProvenanceNoteProps) {
  const repli = ratiosEnRepli(provenance)
  if (repli.length === 0) return null
  return (
    <div className={`flex flex-wrap gap-2 ${className}`} data-testid={testId}>
      {repli.map(([name, key]) => (
        <span
          key={name}
          className="text-xs text-muted-foreground border border-border rounded px-2 py-0.5"
          title={`Clé yfinance de repli — la clé primaire « ${RATIO_PRIMARY_KEYS[name]} » était absente de la source`}
        >
          {RATIO_LABELS[name] ?? name} via <code>{key}</code> (repli)
        </span>
      ))}
    </div>
  )
}
