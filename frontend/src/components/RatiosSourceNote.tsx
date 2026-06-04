interface RatiosSourceNoteProps {
  fetchedAt: string | null | undefined
  source: string | null | undefined
  testId: string
}

// Ligne de traçabilité source+date rendue en pied de carte de skill (composant partagé Graham/earnings/valuation).
// Rien à afficher seulement si source ET date sont absentes ; sinon on montre ce qu'on a
// (honnêteté None : jamais de date factice, mais on ne perd pas la source quand la date manque).
export function RatiosSourceNote({ fetchedAt, source, testId }: RatiosSourceNoteProps) {
  if (!fetchedAt && !source) return null
  return (
    <p className="text-xs text-muted-foreground border-t border-border pt-3" data-testid={testId}>
      Source : {source ?? 'source n.d.'}
      {fetchedAt ? ` · récupéré le ${fetchedAt.slice(0, 10)}` : ''}
    </p>
  )
}
