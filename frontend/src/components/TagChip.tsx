interface TagChipProps {
  tag: string
  onRemove?: (tag: string) => void
  removeTestId?: string
}

export function TagChip({ tag, onRemove, removeTestId }: TagChipProps) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary text-xs px-2 py-0.5">
      {tag}
      {onRemove && (
        <button
          type="button"
          onClick={() => onRemove(tag)}
          aria-label={`Retirer ${tag}`}
          data-testid={removeTestId}
          className="text-primary/70 hover:text-primary"
        >
          ×
        </button>
      )}
    </span>
  )
}
