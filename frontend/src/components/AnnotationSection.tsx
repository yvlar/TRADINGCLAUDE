import { useState } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { TagChip } from './TagChip'
import { getAnnotation, upsertAnnotation } from '../api/annotations'
import type { Annotation } from '../types'

interface AnnotationSectionProps {
  analysisId: string
}

export function AnnotationSection({ analysisId }: AnnotationSectionProps) {
  const [open, setOpen] = useState(false)
  const [annotation, setAnnotation] = useState<Annotation | null | undefined>(undefined)
  const [note, setNote] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleToggle() {
    if (!open && annotation === undefined) {
      const existing = await getAnnotation(analysisId)
      setAnnotation(existing)
      if (existing) {
        setNote(existing.note)
        setTags(existing.tags)
      }
    }
    setOpen((prev) => !prev)
    setEditing(false)
    setError(null)
  }

  function addTag() {
    const value = tagInput.trim().toLowerCase()
    if (!value || tags.includes(value)) {
      setTagInput('')
      return
    }
    setTags((prev) => [...prev, value])
    setTagInput('')
  }

  function removeTag(tag: string) {
    setTags((prev) => prev.filter((t) => t !== tag))
  }

  async function handleSave() {
    if (!note.trim()) return
    setSaving(true)
    setError(null)
    try {
      const saved = await upsertAnnotation({ analysis_id: analysisId, note: note.trim(), tags })
      setAnnotation(saved)
      setTags(saved.tags)
      setEditing(false)
    } catch {
      setError('Erreur lors de la sauvegarde.')
    } finally {
      setSaving(false)
    }
  }

  const showEditor = open && (annotation === null || editing)
  const showNote = open && annotation !== null && annotation !== undefined && !editing

  return (
    <div className="w-full">
      <Button
        variant="ghost"
        size="sm"
        className="h-6 text-xs text-muted-foreground px-2"
        onClick={handleToggle}
        data-testid={`annotation-toggle-${analysisId}`}
      >
        {open ? '▲ Fermer notes' : annotation ? '📝 Notes' : '+ Annoter'}
      </Button>

      {open && (
        <div className="mt-2 space-y-2">
          {showNote && (
            <div className="text-sm text-muted-foreground bg-muted/40 rounded px-3 py-2 whitespace-pre-wrap">
              {annotation.note}
              {annotation.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1" data-testid={`annotation-tags-${analysisId}`}>
                  {annotation.tags.map((tag) => (
                    <TagChip key={tag} tag={tag} />
                  ))}
                </div>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="ml-2 h-5 text-xs"
                onClick={() => {
                  setNote(annotation.note)
                  setTags(annotation.tags)
                  setEditing(true)
                }}
              >
                Modifier
              </Button>
            </div>
          )}

          {showEditor && (
            <div className="space-y-1">
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Ajouter une note sur cette analyse…"
                className="w-full min-h-[60px] text-sm border rounded px-2 py-1 bg-background resize-none focus:outline-none focus:ring-1 focus:ring-ring"
                data-testid={`annotation-textarea-${analysisId}`}
              />
              <div className="flex flex-wrap items-center gap-1" data-testid={`annotation-tag-editor-${analysisId}`}>
                {tags.map((tag) => (
                  <TagChip
                    key={tag}
                    tag={tag}
                    onRemove={removeTag}
                    removeTestId={`annotation-tag-remove-${analysisId}-${tag}`}
                  />
                ))}
                <Input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      addTag()
                    }
                  }}
                  placeholder="tag…"
                  className="h-7 w-24 text-xs"
                  data-testid={`annotation-tag-input-${analysisId}`}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={addTag}
                  disabled={!tagInput.trim()}
                  data-testid={`annotation-tag-add-${analysisId}`}
                >
                  + Tag
                </Button>
              </div>
              <Button
                size="sm"
                className="h-7 text-xs"
                onClick={handleSave}
                disabled={saving || !note.trim()}
                data-testid={`annotation-save-${analysisId}`}
              >
                {saving ? 'Sauvegarde…' : 'Sauvegarder'}
              </Button>
            </div>
          )}

          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      )}
    </div>
  )
}
