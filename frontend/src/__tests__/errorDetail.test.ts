import { describe, it, expect } from 'vitest'
import { extractDetailMessage } from '../api/errorDetail'

describe('extractDetailMessage', () => {
  const FALLBACK = 'Service Unavailable'

  describe('objet structuré (ex. 429 quota)', () => {
    it('extrait detail.message et conserve l’objet brut', () => {
      const body = { detail: { message: 'Quota atteint', plan: 'free', used: 50, limit: 50 } }
      const { message, detail } = extractDetailMessage(body, FALLBACK)
      expect(message).toBe('Quota atteint')
      expect(detail).toBe(body.detail)
    })

    it('replie sur error puis fallback quand message est absent', () => {
      expect(extractDetailMessage({ detail: { plan: 'free' }, error: 'erreur API' }, FALLBACK).message)
        .toBe('erreur API')
      expect(extractDetailMessage({ detail: { plan: 'free' } }, FALLBACK).message)
        .toBe(FALLBACK)
    })
  })

  describe('tableau de validation Pydantic', () => {
    it('aplatit [{loc, msg}] en « champ : msg | … » (loc[0] = source, ignorée)', () => {
      const body = {
        detail: [
          { loc: ['body', 'ticker'], msg: 'champ requis', type: 'missing' },
          { loc: ['body', 'eps'], msg: 'doit être un nombre' },
        ],
      }
      const { message, detail } = extractDetailMessage(body, FALLBACK)
      expect(message).toBe('ticker : champ requis | eps : doit être un nombre')
      expect(detail).toBe(body.detail)
    })

    it('sans champ exploitable, garde le msg seul', () => {
      expect(extractDetailMessage({ detail: [{ loc: ['body'], msg: 'invalide' }] }, FALLBACK).message)
        .toBe('invalide')
      expect(extractDetailMessage({ detail: [{}] }, FALLBACK).message).toBe('invalide')
    })
  })

  describe('detail string', () => {
    it('retourne la string telle quelle', () => {
      const { message, detail } = extractDetailMessage({ detail: 'Ratios invalides' }, FALLBACK)
      expect(message).toBe('Ratios invalides')
      expect(detail).toBe('Ratios invalides')
    })
  })

  describe('replis sûrs', () => {
    it('detail absent + error présent → error', () => {
      expect(extractDetailMessage({ error: 'boom' }, FALLBACK).message).toBe('boom')
    })

    it('corps vide / null / non-objet → fallback, detail undefined', () => {
      expect(extractDetailMessage({}, FALLBACK)).toEqual({ message: FALLBACK, detail: undefined })
      expect(extractDetailMessage(null, FALLBACK)).toEqual({ message: FALLBACK, detail: undefined })
      expect(extractDetailMessage('texte brut', FALLBACK)).toEqual({ message: FALLBACK, detail: undefined })
    })

    it('detail null explicite → fallback', () => {
      expect(extractDetailMessage({ detail: null }, FALLBACK).message).toBe(FALLBACK)
    })

    it('detail scalaire non-string (number/boolean) → repli sûr, jamais coercé', () => {
      // message est typé string : un detail numérique/booléen ne doit pas y atterrir tel quel.
      expect(extractDetailMessage({ detail: 42, error: 'boom' }, FALLBACK).message).toBe('boom')
      expect(extractDetailMessage({ detail: true }, FALLBACK).message).toBe(FALLBACK)
      expect(extractDetailMessage({ detail: [] }, FALLBACK).message).toBe('')
    })
  })

  describe('parité de comportement (cas dominants S194)', () => {
    it('429 quota (objet) produit le même message qu’avant la centralisation', () => {
      const body = { detail: { message: 'Quota mensuel atteint (plan free : 50/50 analyses).', plan: 'free', used: 50, limit: 50, remaining: 0 } }
      expect(extractDetailMessage(body, 'Too Many Requests').message)
        .toBe('Quota mensuel atteint (plan free : 50/50 analyses).')
    })

    it('422 validation (tableau) produit le même message qu’avant', () => {
      const body = { detail: [{ loc: ['body', 'eps'], msg: 'doit être un nombre' }] }
      expect(extractDetailMessage(body, 'Unprocessable Entity').message)
        .toBe('eps : doit être un nombre')
    })
  })
})
