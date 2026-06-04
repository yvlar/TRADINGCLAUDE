interface RatiosSourceNoteProps {
  fetchedAt: string | null | undefined
  source: string | null | undefined
  testId: string
}

// Ligne de traçabilité source+date rendue en pied de carte de skill (parité Graham — Sprint 139).
// Champ absent → rien affiché (honnêteté None : jamais de date factice).
export function RatiosSourceNote({ fetchedAt, source, testId }: RatiosSourceNoteProps) {
  if (!fetchedAt) return null
  return (
    <p className="text-xs text-muted-foreground border-t border-border pt-3" data-testid={testId}>
      Source : {source ?? 'source n.d.'} · récupéré le {fetchedAt.slice(0, 10)}
    </p>
  )
}
