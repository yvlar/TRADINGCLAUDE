import { useQuery } from '@tanstack/react-query'
import { fetchAlerts } from '../api/alerts'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import { Badge } from '../components/ui/badge'
import type { AlertEntry } from '../types'

function alertTypeBadgeVariant(type: string): 'destructive' | 'warning' | 'success' | 'secondary' {
  if (type === 'ESG_DEGRADATION') return 'destructive'
  if (type === 'COMPOSITE_BAISSE' || type === 'PRIX_SEUIL') return 'warning'
  if (type === 'SCREENER_FORT') return 'success'
  return 'secondary'
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('fr-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function AlertRow({ alert }: { alert: AlertEntry }) {
  return (
    <TableRow data-testid={`alert-row-${alert.id}`}>
      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
        {formatDate(alert.created_at)}
      </TableCell>
      <TableCell className="font-mono font-semibold">{alert.ticker}</TableCell>
      <TableCell>
        <Badge
          variant={alertTypeBadgeVariant(alert.type)}
          data-testid={`alert-type-badge-${alert.id}`}
        >
          {alert.type}
        </Badge>
      </TableCell>
      <TableCell>{alert.valeur !== null ? alert.valeur.toFixed(2) : '—'}</TableCell>
      <TableCell>{alert.seuil !== null ? alert.seuil.toFixed(2) : '—'}</TableCell>
      <TableCell className="text-sm text-muted-foreground">
        {alert.message ?? '—'}
      </TableCell>
    </TableRow>
  )
}

export default function AlertsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => fetchAlerts(50),
  })

  if (isLoading) {
    return <p data-testid="alerts-spinner" className="text-muted-foreground">Chargement...</p>
  }

  if (isError) {
    return (
      <p data-testid="alerts-error" className="text-destructive">
        Impossible de charger les alertes.
      </p>
    )
  }

  const alerts = data?.alerts ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Alertes</h1>

      {alerts.length === 0 ? (
        <p data-testid="alerts-empty" className="text-muted-foreground">
          Aucune alerte enregistrée.
        </p>
      ) : (
        <Table data-testid="alerts-table">
          <TableHeader>
            <TableRow>
              <TableHead>Horodatage</TableHead>
              <TableHead>Ticker</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Valeur</TableHead>
              <TableHead>Seuil</TableHead>
              <TableHead>Message</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {alerts.map((alert) => (
              <AlertRow key={alert.id} alert={alert} />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
