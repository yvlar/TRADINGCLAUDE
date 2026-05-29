import { useState } from 'react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { getAnnotation, upsertAnnotation } from '../api/annotations'
import type { Annotation } from '../types'

interface AnnotationSectionProps {
  analysisId: string
}

function normalizeTag(raw: string): string {
  return raw.trim().toLowerCase().slice(0, 40)
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
    const cleaned = normalizeTag(tagInput)
    if (cleaned && !tags.includes(cleaned)) {
      setTags((prev) => [...prev, cleaned])
    }
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
            <div className="text-sm text-muted-foreground bg-muted/40 rounded px-3 py-2 space-y-2">
              <div className="whitespace-pre-wrap">
                {annotation.note}
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
              {annotation.tags.length > 0 && (
                <div className="flex flex-wrap gap-1" data-testid={`annotation-tags-${analysisId}`}>
                  {annotation.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          )}

          {showEditor && (
            <div className="space-y-2">
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Ajouter une note sur cette analyse…"
                className="w-full min-h-[60px] text-sm border rounded px-2 py-1 bg-background resize-none focus:outline-none focus:ring-1 focus:ring-ring"
                data-testid={`annotation-textarea-${analysisId}`}
              />
              <div className="flex flex-wrap gap-1" data-testid={`annotation-tag-editor-${analysisId}`}>
                {tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs gap-1">
                    {tag}
                    <button
                      type="button"
                      onClick={() => removeTag(tag)}
                      className="ml-1 hover:text-destructive"
                      aria-label={`Retirer le tag ${tag}`}
                      data-testid={`annotation-tag-remove-${tag}`}
                    >
                      ×
                    </button>
                  </Badge>
                ))}
              </div>
              <div className="flex gap-1">
                <input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      addTag()
                    }
                  }}
                  placeholder="Ajouter un tag…"
                  className="flex-1 text-xs border rounded px-2 py-1 bg-background focus:outline-none focus:ring-1 focus:ring-ring"
                  data-testid={`annotation-tag-input-${analysisId}`}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={addTag}
                  disabled={!normalizeTag(tagInput)}
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
