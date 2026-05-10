import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WorkflowSelector } from '../components/WorkflowSelector'
import { WORKFLOWS } from '../types'

describe('WorkflowSelector', () => {
  it('rend le trigger combobox', () => {
    render(<WorkflowSelector value="value_graham" onChange={vi.fn()} />)
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('le WORKFLOWS constant contient exactement 5 workflows', () => {
    expect(WORKFLOWS).toHaveLength(5)
  })

  it('les 5 workflows attendus sont dans la constante WORKFLOWS', () => {
    const expectedValues = [
      'value_graham',
      'compounder_buffett',
      'fast_grower_lynch',
      'special_situation',
      'distressed_pabrai',
    ]
    for (const val of expectedValues) {
      expect(WORKFLOWS.find((w) => w.value === val)).toBeDefined()
    }
  })

  it('chaque workflow a un label et une description', () => {
    for (const wf of WORKFLOWS) {
      expect(wf.label.length).toBeGreaterThan(0)
      expect(wf.description.length).toBeGreaterThan(0)
    }
  })

  it('le trigger affiche l\'aria-label correct', () => {
    render(<WorkflowSelector value="value_graham" onChange={vi.fn()} />)
    expect(screen.getByLabelText('Sélectionner un workflow')).toBeInTheDocument()
  })
})
