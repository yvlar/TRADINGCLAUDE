import { describe, it, expect, beforeEach } from 'vitest'
import {
  availableLabels,
  buildScreenerCsv,
  formatFreshness,
  loadLabelFilter,
  loadSortState,
  saveLabelFilter,
  saveSortState,
  SORT_STORAGE_KEY,
} from '../lib/screenerView'
import type { ScreenEntry } from '../types'

function entry(overrides: Partial<ScreenEntry>): ScreenEntry {
  return {
    ticker: 'BNS',
    defensive_score: 6,
    verdict: 'SOLIDE',
    composite_score: 70,
    composite_label: 'FORT',
    workflow_utilise: 'value_graham',
    cost_usd: 0.002,
    depuis_cache: false,
    analyzed_at: '2026-05-26T10:00:00+00:00',
    erreur: null,
    ...overrides,
  }
}

describe('screenerView helpers', () => {
  beforeEach(() => localStorage.clear())

  describe('formatFreshness', () => {
    const now = new Date('2026-05-26T12:00:00+00:00')

    it('retourne — pour null', () => {
      expect(formatFreshness(null, now)).toEqual({ label: '—', stale: false })
    })

    it("retourne « à l'instant » à moins d'une heure", () => {
      const r = formatFreshness('2026-05-26T11:30:00+00:00', now)
      expect(r).toEqual({ label: "à l'instant", stale: false })
    })

    it('retourne les heures et reste frais sous 24h', () => {
      const r = formatFreshness('2026-05-26T06:00:00+00:00', now)
      expect(r.label).toBe('il y a 6 h')
      expect(r.stale).toBe(false)
    })

    it('marque comme périmé au-delà de 24h', () => {
      const r = formatFreshness('2026-05-23T12:00:00+00:00', now)
      expect(r.label).toBe('il y a 3 j')
      expect(r.stale).toBe(true)
    })

    it('gère une date invalide', () => {
      expect(formatFreshness('pas-une-date', now)).toEqual({ label: '—', stale: false })
    })
  })

  describe('availableLabels', () => {
    it('extrait les labels distincts dans l\'ordre d\'apparition', () => {
      const entries = [
        entry({ ticker: 'A', composite_label: 'MODÉRÉ' }),
        entry({ ticker: 'B', composite_label: 'FORT' }),
        entry({ ticker: 'C', composite_label: 'FORT' }),
        entry({ ticker: 'D', composite_label: null }),
      ]
      expect(availableLabels(entries)).toEqual(['MODÉRÉ', 'FORT'])
    })
  })

  describe('persistance localStorage', () => {
    it('charge le défaut score desc sans valeur stockée', () => {
      expect(loadSortState()).toEqual({ key: 'score', asc: false })
    })

    it('persiste et recharge un état de tri', () => {
      saveSortState({ key: 'cost', asc: true })
      expect(loadSortState()).toEqual({ key: 'cost', asc: true })
    })

    it('ignore une clé de tri invalide', () => {
      localStorage.setItem(SORT_STORAGE_KEY, JSON.stringify({ key: 'bogus', asc: true }))
      expect(loadSortState()).toEqual({ key: 'score', asc: false })
    })

    it('persiste et recharge le filtre de labels', () => {
      saveLabelFilter(['FORT', 'MODÉRÉ'])
      expect(loadLabelFilter()).toEqual(['FORT', 'MODÉRÉ'])
    })

    it('retourne un filtre vide par défaut', () => {
      expect(loadLabelFilter()).toEqual([])
    })
  })

  describe('buildScreenerCsv', () => {
    it('produit un en-tête et une ligne par entrée', () => {
      const csv = buildScreenerCsv([entry({ ticker: 'BNS' }), entry({ ticker: 'TD' })])
      const lines = csv.split('\n')
      expect(lines).toHaveLength(3)
      expect(lines[0]).toContain('Ticker')
      expect(lines[1]).toContain('BNS')
      expect(lines[2]).toContain('TD')
    })

    it('échappe les valeurs contenant des virgules', () => {
      const csv = buildScreenerCsv([entry({ erreur: 'timeout, retry' })])
      expect(csv).toContain('"timeout, retry"')
    })

    it('sérialise cache en oui/non et la date d\'analyse', () => {
      const csv = buildScreenerCsv([entry({ depuis_cache: true })])
      expect(csv).toContain('oui')
      expect(csv).toContain('2026-05-26T10:00:00+00:00')
    })
  })
})
