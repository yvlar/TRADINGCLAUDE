import { DISCLAIMER_HEADING, DISCLAIMER_TEXT } from '../constants/disclaimer'

interface DisclaimerProps {
  // inline : bandeau encadré sous un bloc de résultats actionnables.
  // footer : ligne discrète pour le pied de page global.
  variant?: 'inline' | 'footer'
}

export function Disclaimer({ variant = 'inline' }: DisclaimerProps) {
  if (variant === 'footer') {
    return (
      <p
        data-testid="disclaimer"
        data-variant="footer"
        role="note"
        className="text-center text-xs text-muted-foreground"
      >
        {DISCLAIMER_TEXT}
      </p>
    )
  }

  return (
    <div
      data-testid="disclaimer"
      data-variant="inline"
      role="note"
      className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground"
    >
      <span className="font-semibold text-foreground">{DISCLAIMER_HEADING} — </span>
      {DISCLAIMER_TEXT}
    </div>
  )
}
