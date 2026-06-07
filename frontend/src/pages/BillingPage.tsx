import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'
import { PageTransition } from '../components/PageTransition'
import { SkillCostPieChart } from '../components/SkillCostPieChart'
import { DailyCostTrendChart } from '../components/DailyCostTrendChart'
import { QuotaBanner, isQuotaError } from '../components/QuotaBanner'
import { useAuth } from '../contexts/AuthContext'
import { getUsage } from '../api/usage'
import { createCheckout, openPortal } from '../api/billing'
import { ApiError } from '../api/client'
import type { UsageBySkill } from '../types'

/** Convertit la ventilation par skill en dict {skill: coût} attendu par SkillCostPieChart. */
function bySkillToCostMap(bySkill: UsageBySkill[]): Record<string, number> {
  return Object.fromEntries(bySkill.map((s) => [s.skill, s.cost_usd]))
}

/** Message d'erreur assaini : 503 → facturation indisponible, sinon le détail renvoyé. */
function actionErrorMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 503) {
    return 'Facturation indisponible pour le moment.'
  }
  if (err instanceof ApiError) return err.message
  return 'Une erreur est survenue.'
}

export default function BillingPage() {
  const { user } = useAuth()
  const plan = user?.plan ?? 'free'
  const isFree = plan === 'free'

  const usage = useQuery({
    queryKey: ['usage', 30],
    queryFn: () => getUsage(30),
  })

  const [actionLoading, setActionLoading] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  async function handleCta() {
    setActionLoading(true)
    setActionError(null)
    try {
      const url = isFree ? await createCheckout('pro') : await openPortal()
      window.location.href = url
    } catch (err) {
      setActionError(actionErrorMessage(err))
      setActionLoading(false)
    }
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold mb-1">Facturation</h2>
          <p className="text-sm text-muted-foreground">
            Plan courant, consommation du mois et gestion de l'abonnement.
          </p>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <CardTitle>Plan</CardTitle>
                <Badge
                  variant={isFree ? 'outline' : 'success'}
                  data-testid="billing-plan-badge"
                >
                  {plan.toUpperCase()}
                </Badge>
              </div>
              <Button
                onClick={handleCta}
                disabled={actionLoading}
                data-testid={isFree ? 'billing-checkout-btn' : 'billing-portal-btn'}
              >
                {actionLoading
                  ? 'Redirection…'
                  : isFree
                    ? 'Passer à Pro'
                    : "Gérer l'abonnement"}
              </Button>
            </div>
          </CardHeader>
          {actionError && (
            <CardContent>
              <p className="text-sm text-destructive" data-testid="billing-action-error">
                {actionError}
              </p>
            </CardContent>
          )}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Consommation — 30 derniers jours</CardTitle>
          </CardHeader>
          <CardContent>
            {usage.isLoading ? (
              <div data-testid="billing-usage-loading">
                <Skeleton className="h-[120px] w-full" />
              </div>
            ) : usage.isError ? (
              isQuotaError(usage.error) ? (
                <QuotaBanner message="Quota mensuel d'analyses atteint pour votre plan." />
              ) : (
                <p className="text-sm text-destructive" data-testid="billing-usage-error">
                  Impossible de charger la consommation.
                </p>
              )
            ) : usage.data ? (
              <div className="space-y-6" data-testid="billing-usage">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Coût total</p>
                    <p className="text-2xl font-bold tabular-nums" data-testid="billing-total-cost">
                      ${usage.data.total_cost_usd.toFixed(4)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">
                      Tokens entrée
                    </p>
                    <p className="text-2xl font-bold tabular-nums">
                      {usage.data.total_tokens_input.toLocaleString('fr-CA')}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">
                      Tokens sortie
                    </p>
                    <p className="text-2xl font-bold tabular-nums">
                      {usage.data.total_tokens_output.toLocaleString('fr-CA')}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
                      Coût par skill (USD)
                    </p>
                    <SkillCostPieChart skillsCost={bySkillToCostMap(usage.data.by_skill)} />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
                      Tendance du coût par jour (USD)
                    </p>
                    <DailyCostTrendChart dailyCost={usage.data.daily_cost} />
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  )
}
