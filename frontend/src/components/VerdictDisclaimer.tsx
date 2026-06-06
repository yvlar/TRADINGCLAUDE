import { VERDICT_DISCLAIMER_TEXT } from '../constants/disclaimer'

// Avertissement compact rendu adjacent à un verdict actionnable — conformité U4 :
// aucun verdict ne doit être présenté sans avertissement à proximité immédiate.
export function VerdictDisclaimer() {
  return (
    <span
      data-testid="verdict-disclaimer"
      role="note"
      className="inline-flex items-center gap-1 text-[11px] leading-tight text-muted-foreground"
    >
      <span aria-hidden="true">⚖️</span>
      {VERDICT_DISCLAIMER_TEXT}
    </span>
  )
}
