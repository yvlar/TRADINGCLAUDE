import { Badge } from './ui/badge'

interface TenantBadgeProps {
  // Nullable : une réponse /auth/me en cache d'avant le Sprint 169 peut ne pas
  // porter le nom du tenant — on n'affiche alors rien plutôt qu'un libellé vide.
  tenantName: string | null | undefined
}

export function TenantBadge({ tenantName }: TenantBadgeProps) {
  if (!tenantName) return null
  return (
    <Badge
      variant="outline"
      data-testid="tenant-badge"
      className="hidden gap-1 rounded-md font-normal text-muted-foreground md:inline-flex"
    >
      Espace :<span className="font-medium text-foreground">{tenantName}</span>
    </Badge>
  )
}
