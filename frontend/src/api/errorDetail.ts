// Source unique d'extraction d'un message lisible depuis le corps `detail` d'une réponse
// d'erreur HTTP. Avant ce module, trois sites (`request`, `streamAnalyze`, `authFetch`)
// parsaient le même contrat dans un ordre de gardes divergent — risque de dérive silencieuse à
// chaque évolution du contrat d'erreur backend. `quotaDetailFromError` (QuotaBanner) reste distinct :
// sa finalité est la validation de forme typée (`QuotaErrorDetail`), pas l'extraction d'un message.

/** Corps d'erreur tel que renvoyé par FastAPI : `detail` polymorphe + `error` optionnel. */
interface ErrorBody {
  detail?: unknown
  error?: string
}

/** Une entrée d'erreur de validation Pydantic FastAPI : `{loc, msg, type}`. */
interface PydanticError {
  msg?: string
  loc?: string[]
}

export interface ExtractedDetail {
  message: string
  // Corps `detail` brut conservé pour les consommateurs structurés (ex. 429 quota → QuotaBanner).
  detail: unknown
}

/** Aplatit un tableau d'erreurs de validation Pydantic en un message lisible « champ : msg | … ». */
function flattenPydanticErrors(errors: PydanticError[]): string {
  return errors
    .map(e => {
      // loc[0] est la source (« body », « query »…) — superflue pour l'utilisateur.
      const field = e.loc ? e.loc.slice(1).join('.') : ''
      return field ? `${field} : ${e.msg ?? 'invalide'}` : (e.msg ?? 'invalide')
    })
    .join(' | ')
}

/**
 * Extrait un message lisible du corps `detail` d'une réponse d'erreur HTTP.
 *
 * Ordre canonique des gardes (array-first) : tableau de validation Pydantic → objet structuré
 * → string. Retourne aussi le `detail` brut, transporté tel quel par `ApiError` jusqu'aux
 * consommateurs structurés (un 429 quota porte un objet décodé par `quotaDetailFromError`).
 */
export function extractDetailMessage(body: unknown, fallback: string): ExtractedDetail {
  const b: ErrorBody = body !== null && typeof body === 'object' ? (body as ErrorBody) : {}
  const detail = b.detail

  let message: string
  if (Array.isArray(detail)) {
    message = flattenPydanticErrors(detail as PydanticError[])
  } else if (detail !== null && typeof detail === 'object') {
    message = (detail as { message?: string }).message ?? b.error ?? fallback
  } else {
    // String → telle quelle ; tout autre scalaire (null/undefined/number/boolean) → repli sûr,
    // jamais de coercition trompeuse d'un non-string dans un champ `message: string`.
    message = typeof detail === 'string' ? detail : b.error ?? fallback
  }

  return { message, detail }
}
