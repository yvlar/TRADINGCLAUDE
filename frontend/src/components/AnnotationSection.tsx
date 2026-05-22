import { useState } from 'react'
import { Button } from './ui/button'
import { getAnnotation, upsertAnnotation } from '../api/annotations'
import type { Annotation } from '../types'

interface AnnotationSectionProps {
  analysisId: string
}

export function AnnotationSection({ analysisId }: AnnotationSectionProps) {
  const [open, setOpen] = useState(false)
  const [annotation, setAnnotation] = useState<Annotation | null | undefined>(undefined)
  const [note, setNote] = useState('')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleToggle() {
    if (!open && annotation === undefined) {
      const existing = await getAnnotation(analysisId)
      setAnnotation(existing)
      if (existing) setNote(existing.note)
    }
    setOpen((prev) => !prev)
    setEditing(false)
    setError(null)
  }

  async function handleSave() {
    if (!note.trim()) return
    setSaving(true)
    setError(null)
    try {
      const saved = await upsertAnnotation({ analysis_id: analysisId, note: note.trim() })
      setAnnotation(saved)
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
              <Button
                variant="ghost"
                size="sm"
                className="ml-2 h-5 text-xs"
                onClick={() => {
                  setNote(annotation.note)
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
