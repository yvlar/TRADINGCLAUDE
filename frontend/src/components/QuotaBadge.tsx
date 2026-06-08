import { useQuery } from '@tanstack/react-query'
import { Badge } from './ui/badge'
import { getQuota } from '../api/quota'

interface QuotaBadgeProps {
  // tenant courant : présent ⇔ authentifié. Sert aussi de clé de cache (cf. queryKey) pour
  // éviter qu'une re-connexion sous un autre tenant (sans rechargement) serve un quota périmé.
  tenantId: string | undefined
}

export function QuotaBadge({ tenantId }: QuotaBadgeProps) {
  const { data } = useQuery({
    queryKey: ['quota', tenantId],
    queryFn: () => getQuota(),
    enabled: Boolean(tenantId),
    // Header global : pas de retry agressif ni de refetch au focus — l'erreur reste silencieuse
    // (le header ne doit jamais casser) et le chargement est discret (rien tant que data absente).
    retry: false,
    refetchOnWindowFocus: false,
  })

  // Non authentifié, chargement ou erreur → on n'affiche rien (rétrocompat + header robuste).
  if (!data) return null

  return (
    <Badge
      variant="outline"
      data-testid="quota-badge"
      className="hidden gap-1 rounded-md font-normal text-muted-foreground md:inline-flex"
    >
      plan <span className="font-medium text-foreground">{data.plan.toUpperCase()}</span>
      {data.remaining !== null && (
        <span data-testid="quota-remaining">· {data.remaining} analyses restantes</span>
      )}
    </Badge>
  )
}
