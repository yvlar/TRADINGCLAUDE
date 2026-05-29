import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AnnotationSection } from '../components/AnnotationSection'
import * as annotationsApi from '../api/annotations'
import type { Annotation } from '../types'

vi.mock('../api/annotations')

const ANALYSIS_ID = '550e8400-e29b-41d4-a716-446655440000'

function makeAnnotation(note: string, tags: string[] = []): Annotation {
  return {
    annotation_id: '11111111-1111-1111-1111-111111111111',
    analysis_id: ANALYSIS_ID,
    note,
    tags,
    created_at: '2026-05-18T12:00:00Z',
    updated_at: '2026-05-18T12:00:00Z',
  }
}

describe('AnnotationSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le bouton toggle fermé par défaut', () => {
    render(<AnnotationSection analysisId={ANALYSIS_ID} />)
    expect(screen.getByTestId(`annotation-toggle-${ANALYSIS_ID}`)).toBeInTheDocument()
    expect(screen.queryByTestId(`annotation-textarea-${ANALYSIS_ID}`)).not.toBeInTheDocument()
  })

  it('ouvre le textarea vide quand aucune annotation existante', async () => {
    vi.mocked(annotationsApi.getAnnotation).mockResolvedValue(null)

    render(<AnnotationSection analysisId={ANALYSIS_ID} />)
    await userEvent.click(screen.getByTestId(`annotation-toggle-${ANALYSIS_ID}`))

    await waitFor(() => {
      expect(screen.getByTestId(`annotation-textarea-${ANALYSIS_ID}`)).toBeInTheDocument()
    })
    expect(screen.getByTestId(`annotation-save-${ANALYSIS_ID}`)).toBeInTheDocument()
  })

  it('affiche la note existante sans textarea au premier toggle', async () => {
    vi.mocked(annotationsApi.getAnnotation).mockResolvedValue(makeAnnotation('Note BNS ACHAT'))

    render(<AnnotationSection analysisId={ANALYSIS_ID} />)
    await userEvent.click(screen.getByTestId(`annotation-toggle-${ANALYSIS_ID}`))

    await waitFor(() => {
      expect(screen.getByText('Note BNS ACHAT')).toBeInTheDocument()
    })
    expect(screen.queryByTestId(`annotation-textarea-${ANALYSIS_ID}`)).not.toBeInTheDocument()
  })

  it('sauvegarde une nouvelle note via upsertAnnotation', async () => {
    vi.mocked(annotationsApi.getAnnotation).mockResolvedValue(null)
    vi.mocked(annotationsApi.upsertAnnotation).mockResolvedValue(makeAnnotation('Ma note'))

    render(<AnnotationSection analysisId={ANALYSIS_ID} />)
    await userEvent.click(screen.getByTestId(`annotation-toggle-${ANALYSIS_ID}`))
    await waitFor(() =>
      expect(screen.getByTestId(`annotation-textarea-${ANALYSIS_ID}`)).toBeInTheDocument(),
    )

    await userEvent.type(screen.getByTestId(`annotation-textarea-${ANALYSIS_ID}`), 'Ma note')
    await userEvent.click(screen.getByTestId(`annotation-save-${ANALYSIS_ID}`))

    await waitFor(() => {
      expect(annotationsApi.upsertAnnotation).toHaveBeenCalledWith({
        analysis_id: ANALYSIS_ID,
        note: 'Ma note',
        tags: [],
      })
    })
  })

  it('ajoute un tag et l\'inclut dans l\'upsert', async () => {
    vi.mocked(annotationsApi.getAnnotation).mockResolvedValue(null)
    vi.mocked(annotationsApi.upsertAnnotation).mockResolvedValue(makeAnnotation('Note', ['value']))

    render(<AnnotationSection analysisId={ANALYSIS_ID} />)
    await userEvent.click(screen.getByTestId(`annotation-toggle-${ANALYSIS_ID}`))
    await waitFor(() =>
      expect(screen.getByTestId(`annotation-textarea-${ANALYSIS_ID}`)).toBeInTheDocument(),
    )

    await userEvent.type(screen.getByTestId(`annotation-textarea-${ANALYSIS_ID}`), 'Note')
    await userEvent.type(screen.getByTestId(`annotation-tag-input-${ANALYSIS_ID}`), 'value')
    await userEvent.click(screen.getByTestId(`annotation-tag-add-${ANALYSIS_ID}`))
    await userEvent.click(screen.getByTestId(`annotation-save-${ANALYSIS_ID}`))

    await waitFor(() => {
      expect(annotationsApi.upsertAnnotation).toHaveBeenCalledWith({
        analysis_id: ANALYSIS_ID,
        note: 'Note',
        tags: ['value'],
      })
    })
  })

  it('retire un tag avant la sauvegarde', async () => {
    vi.mocked(annotationsApi.getAnnotation).mockResolvedValue(makeAnnotation('Note', ['value', 'growth']))
    vi.mocked(annotationsApi.upsertAnnotation).mockResolvedValue(makeAnnotation('Note', ['growth']))

    render(<AnnotationSection analysisId={ANALYSIS_ID} />)
    await userEvent.click(screen.getByTestId(`annotation-toggle-${ANALYSIS_ID}`))
    await waitFor(() => expect(screen.getByText('Note')).toBeInTheDocument())

    await userEvent.click(screen.getByText('Modifier'))
    await userEvent.click(screen.getByTestId(`annotation-tag-remove-${ANALYSIS_ID}-value`))
    await userEvent.click(screen.getByTestId(`annotation-save-${ANALYSIS_ID}`))

    await waitFor(() => {
      expect(annotationsApi.upsertAnnotation).toHaveBeenCalledWith({
        analysis_id: ANALYSIS_ID,
        note: 'Note',
        tags: ['growth'],
      })
    })
  })

  it('affiche un message d\'erreur si la sauvegarde échoue', async () => {
    vi.mocked(annotationsApi.getAnnotation).mockResolvedValue(null)
    vi.mocked(annotationsApi.upsertAnnotation).mockRejectedValue(new Error('boom'))

    render(<AnnotationSection analysisId={ANALYSIS_ID} />)
    await userEvent.click(screen.getByTestId(`annotation-toggle-${ANALYSIS_ID}`))
    await waitFor(() =>
      expect(screen.getByTestId(`annotation-textarea-${ANALYSIS_ID}`)).toBeInTheDocument(),
    )

    await userEvent.type(screen.getByTestId(`annotation-textarea-${ANALYSIS_ID}`), 'Note')
    await userEvent.click(screen.getByTestId(`annotation-save-${ANALYSIS_ID}`))

    await waitFor(() => {
      expect(screen.getByText('Erreur lors de la sauvegarde.')).toBeInTheDocument()
    })
  })

  it('passe en mode édition après clic Modifier et soumet correctement', async () => {
    vi.mocked(annotationsApi.getAnnotation).mockResolvedValue(makeAnnotation('Ancienne note'))
    vi.mocked(annotationsApi.upsertAnnotation).mockResolvedValue(makeAnnotation('Nouvelle note'))

    render(<AnnotationSection analysisId={ANALYSIS_ID} />)
    await userEvent.click(screen.getByTestId(`annotation-toggle-${ANALYSIS_ID}`))
    await waitFor(() => expect(screen.getByText('Ancienne note')).toBeInTheDocument())

    await userEvent.click(screen.getByText('Modifier'))
    const textarea = screen.getByTestId(`annotation-textarea-${ANALYSIS_ID}`)
    await userEvent.clear(textarea)
    await userEvent.type(textarea, 'Nouvelle note')
    await userEvent.click(screen.getByTestId(`annotation-save-${ANALYSIS_ID}`))

    await waitFor(() => {
      expect(annotationsApi.upsertAnnotation).toHaveBeenCalledWith({
        analysis_id: ANALYSIS_ID,
        note: 'Nouvelle note',
        tags: [],
      })
    })
  })
})
