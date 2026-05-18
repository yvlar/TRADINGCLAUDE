interface ConflictsListProps {
  conflicts: string[]
}

export function ConflictsList({ conflicts }: ConflictsListProps) {
  if (conflicts.length === 0) {
    return (
      <p
        data-testid="conflicts-empty"
        className="text-xs text-muted-foreground italic"
      >
        Aucun conflit inter-skills détecté
      </p>
    )
  }

  return (
    <ul data-testid="conflicts-list" className="space-y-1">
      {conflicts.map((c, i) => (
        <li key={i} className="text-xs text-yellow-400 flex items-start gap-1">
          <span aria-hidden="true">⚠</span>
          <span>{c}</span>
        </li>
      ))}
    </ul>
  )
}
