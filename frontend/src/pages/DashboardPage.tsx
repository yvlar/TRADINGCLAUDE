import { MetricsDashboard } from '../components/MetricsDashboard'

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold mb-1">Dashboard temps réel</h2>
        <p className="text-sm text-muted-foreground">
          Métriques live via WebSocket /ws/metrics — mise à jour automatique toutes les 5 secondes.
        </p>
      </div>
      <MetricsDashboard />
    </div>
  )
}
