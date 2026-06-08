import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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
import { getUsage, getUsageReporting } from '../api/usage'
import { createCheckout, openPortal } from '../api/billing'
import { ApiError } from '../api/client'
import type { UsageBySkill } from '../types'

// Fenêtre de re-synchronisation post-checkout : le webhook Stripe peut mettre `tenants.plan`
// à jour APRÈS le refresh ponctuel du retour. On sonde à intervalle borné (~30 s) jusqu'à la
// bascule du plan, puis on s'arrête — jamais de boucle infinie.
export const POLL_INTERVAL_MS = 3000
export const MAX_POLL_ATTEMPTS = 10

/** Convertit la ventilation par skill en dict {skill: coût} attendu par SkillCostPieChart. */
function bySkillToCostMap(bySkill: UsageBySkill[]): Record<string, number> {
  return Object.fromEntries(bySkill.map((s) => [s.skill, s.cost_usd]))
}

/** Formate le curseur de report (ISO) en date locale fr-CA, ou un libellé neutre si jamais rapporté. */
function formatReportedThrough(reportedThrough: string | null): string {
  if (reportedThrough === null) return 'Aucun report effectué pour le moment'
  return `Rapporté à Stripe jusqu'au ${new Date(reportedThrough).toLocaleDateString('fr-CA')}`
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
  const { user, refreshUser } = useAuth()
  const plan = user?.plan ?? 'free'
  const isFree = plan === 'free'

  // Retour de checkout Stripe : `?status=success|cancel`. On capture le statut dans un
  // état local puis on nettoie le param (évite de re-déclencher le refresh à un F5 manuel).
  const [searchParams, setSearchParams] = useSearchParams()
  const [checkoutResult, setCheckoutResult] = useState<'success' | 'cancel' | null>(null)
  // Garde-fou : un seul traitement du retour de checkout, même si l'effet est rejoué
  // (StrictMode en dev, ou avant que le nettoyage du param ait propagé un nouveau searchParams).
  const checkoutHandled = useRef(false)
  useEffect(() => {
    if (checkoutHandled.current) return
    const status = searchParams.get('status')
    if (status !== 'success' && status !== 'cancel') return
    checkoutHandled.current = true
    setCheckoutResult(status)
    // Le webhook met `tenants.plan` à jour de façon asynchrone → on resync le plan affiché.
    if (status === 'success') void refreshUser()
    setSearchParams({}, { replace: true })
  }, [searchParams, setSearchParams, refreshUser])

  // Resync borné après un retour de checkout réussi, le temps que le webhook rattrape le refresh
  // ponctuel ci-dessus. La bascule de `plan` est le signal d'arrêt : la dépendance change →
  // cleanup de l'interval + retour anticipé (guard `plan !== 'free'`). Sans bascule, l'interval
  // s'auto-arrête au plafond d'itérations — jamais de boucle infinie.
  useEffect(() => {
    if (checkoutResult !== 'success' || plan !== 'free') return
    let attempts = 0
    const timer = setInterval(() => {
      void refreshUser()
      attempts += 1
      if (attempts >= MAX_POLL_ATTEMPTS) clearInterval(timer)
    }, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [checkoutResult, plan, refreshUser])

  const usage = useQuery({
    queryKey: ['usage', 30],
    queryFn: () => getUsage(30),
  })

  const reporting = useQuery({
    queryKey: ['usage-reporting'],
    queryFn: () => getUsageReporting(),
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

        {checkoutResult === 'success' && (
          <div
            className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300"
            data-testid="billing-success-banner"
          >
            Abonnement activé — merci. Votre plan est en cours de mise à jour.
          </div>
        )}
        {checkoutResult === 'cancel' && (
          <div
            className="rounded-md border border-border bg-muted px-4 py-3 text-sm text-muted-foreground"
            data-testid="billing-cancel-banner"
          >
            Paiement annulé. Aucun changement n'a été apporté à votre abonnement.
          </div>
        )}

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

        <Card>
          <CardHeader>
            <CardTitle>Facturation à l'usage</CardTitle>
          </CardHeader>
          <CardContent>
            {reporting.isLoading ? (
              <div data-testid="billing-reporting-loading">
                <Skeleton className="h-[80px] w-full" />
              </div>
            ) : reporting.isError ? (
              <p className="text-sm text-muted-foreground" data-testid="billing-reporting-error">
                Facturation à l'usage indisponible pour le moment.
              </p>
            ) : reporting.data ? (
              <div className="space-y-3" data-testid="billing-usage-reporting">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">
                    En attente du prochain cycle
                  </p>
                  <p className="text-2xl font-bold tabular-nums" data-testid="billing-reporting-pending">
                    {reporting.data.pending_events.toLocaleString('fr-CA')}
                    <span className="ml-1 text-sm font-normal text-muted-foreground">unité(s)</span>
                  </p>
                </div>
                <p className="text-sm text-muted-foreground" data-testid="billing-reporting-through">
                  {formatReportedThrough(reporting.data.reported_through)}
                </p>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  )
}
