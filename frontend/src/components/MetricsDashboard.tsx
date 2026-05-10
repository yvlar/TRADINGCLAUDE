import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { useMetrics } from '../api/ws'

function MetricCard({
  label,
  value,
  sub,
}: {
  label: string
  value: string | number
  sub?: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold tabular-nums">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  )
}

export function MetricsDashboard() {
  const { data, connected, error } = useMetrics()

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 shadow-[0_0_6px_#22c55e]' : 'bg-red-500'}`}
        />
        <span className="text-sm text-muted-foreground">
          WebSocket {connected ? 'connecté' : 'déconnecté'}
        </span>
        {data?.timestamp && (
          <span className="text-xs text-muted-foreground ml-auto">
            Mis à jour : {new Date(data.timestamp).toLocaleTimeString('fr-CA')}
          </span>
        )}
      </div>

      {error && (
        <div className="border border-destructive bg-destructive/10 text-destructive rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {!data && !error && (
        <p className="text-muted-foreground text-sm">En attente des données...</p>
      )}

      {data && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <MetricCard
            label="Jobs en cours"
            value={data.jobs_en_cours}
            sub="actifs maintenant"
          />
          <MetricCard
            label="Jobs échoués 1h"
            value={data.jobs_echoues_1h}
            sub="dernière heure"
          />
          <MetricCard
            label="Coût total"
            value={`$${data.cout_total_1h_usd.toFixed(3)}`}
            sub="aujourd'hui (USD)"
          />
          <MetricCard
            label="Taux cache"
            value={`${(data.cache_hit_ratio * 100).toFixed(0)}%`}
            sub="hits Redis"
          />
          <MetricCard
            label="Analyses 24h"
            value={data.analyses_24h}
            sub="requêtes"
          />
        </div>
      )}

      {data && (
        <div className="flex flex-wrap gap-2">
          <Badge variant={data.jobs_en_cours > 0 ? 'warning' : 'secondary'}>
            {data.jobs_en_cours} job(s) actif(s)
          </Badge>
          <Badge variant={data.cache_hit_ratio >= 0.7 ? 'success' : 'warning'}>
            Cache {(data.cache_hit_ratio * 100).toFixed(0)}%
          </Badge>
        </div>
      )}
    </div>
  )
}
