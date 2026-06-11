import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Microscope, PiggyBank, ShieldCheck } from 'lucide-react'
import { fetchDiscoveryCategories, fetchDiscoveryCategory } from '../api/discovery'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { SkeletonCard } from '../components/ui/skeleton'
import { PageTransition, StaggerItem } from '../components/PageTransition'
import { GlossaryTerm } from '../components/GlossaryTerm'
import { useUIMode } from '../contexts/UIModeContext'
import type { DiscoveryCategorySummary, DiscoverySuggestion } from '../types'

function riskBadgeVariant(risk: string): 'success' | 'warning' | 'destructive' {
  if (risk === 'faible') return 'success'
  if (risk === 'moyen') return 'warning'
  return 'destructive'
}

function riskLabel(risk: string): string {
  return `Risque ${risk}`
}

// "2026-06-11T06:00:00+00:00" → "11 juin 2026" (fraîcheur lisible par un débutant)
function formatAsOf(asOf: string | null): string | null {
  if (!asOf) return null
  const date = new Date(asOf)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString('fr-CA', { day: 'numeric', month: 'long', year: 'numeric' })
}

function CategoryCard({
  category,
  onSelect,
}: {
  category: DiscoveryCategorySummary
  onSelect: (id: string) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(category.id)}
      data-testid={`category-card-${category.id}`}
      className="text-left w-full"
      aria-label={`Explorer la catégorie ${category.titre}`}
    >
      <Card className="h-full transition-all hover:border-primary/60 hover:shadow-md">
        <CardHeader className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-2xl" aria-hidden>{category.emoji}</span>
            <Badge variant={riskBadgeVariant(category.niveau_risque)}>
              {riskLabel(category.niveau_risque)}
            </Badge>
          </div>
          <CardTitle className="text-base">{category.titre}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{category.description}</p>
          {category.nb_suggestions > 0 && (
            <p className="mt-2 text-xs text-muted-foreground">
              {category.nb_suggestions} titre{category.nb_suggestions > 1 ? 's' : ''} de qualité
            </p>
          )}
        </CardContent>
      </Card>
    </button>
  )
}

function SuggestionCard({
  suggestion,
  isBeginner,
}: {
  suggestion: DiscoverySuggestion
  isBeginner: boolean
}) {
  return (
    <Card data-testid={`suggestion-${suggestion.ticker}`}>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm normal-case">
          {suggestion.name}{' '}
          <span className="font-mono text-xs text-muted-foreground">({suggestion.ticker})</span>
        </CardTitle>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant={riskBadgeVariant(suggestion.risk_badge)}>
            {riskLabel(suggestion.risk_badge)}
          </Badge>
          {suggestion.composite_label !== null && suggestion.composite_score !== null && (
            <Badge variant="secondary">
              Qualité {suggestion.composite_label} · {Math.round(suggestion.composite_score)}/100
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-foreground">{suggestion.why}</p>

        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
          {suggestion.price !== null && <span>Prix : {suggestion.price.toFixed(2)} $</span>}
          {suggestion.dividend_yield !== null && (
            <span className="inline-flex items-center gap-1">
              <GlossaryTerm term="rendement_dividende">Dividende</GlossaryTerm> :{' '}
              {(suggestion.dividend_yield * 100).toFixed(1)} % par an
            </span>
          )}
          {suggestion.dividend_years !== null && (
            <span>Versé depuis {suggestion.dividend_years} ans</span>
          )}
          {suggestion.pe !== null && (
            <span className="inline-flex items-center gap-1">
              <GlossaryTerm term="pe" /> : {suggestion.pe.toFixed(1)}
            </span>
          )}
        </div>

        {!isBeginner && suggestion.composite_score !== null && (
          <p
            className="text-xs text-muted-foreground"
            data-testid={`suggestion-advanced-${suggestion.ticker}`}
          >
            <GlossaryTerm term="qualite">Score composite</GlossaryTerm> :{' '}
            {suggestion.composite_score.toFixed(1)}/100 — pondère Graham, Buffett, valorisation,
            moat Dorsey, qualité des bénéfices et cycles de marché.
          </p>
        )}

        <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
          <PiggyBank size={14} className="mt-0.5 shrink-0" aria-hidden />
          {suggestion.account_hint}
        </p>

        <Button asChild size="sm" variant="outline" data-testid={`analyze-${suggestion.ticker}`}>
          <Link to={`/?ticker=${encodeURIComponent(suggestion.ticker)}`}>
            <Microscope size={14} className="mr-1.5" aria-hidden />
            Analyse approfondie
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}

function CategoryDetail({ categoryId, onBack }: { categoryId: string; onBack: () => void }) {
  const { isBeginner } = useUIMode()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['discovery-category', categoryId],
    queryFn: () => fetchDiscoveryCategory(categoryId),
  })

  const asOf = formatAsOf(data?.as_of ?? null)

  return (
    <div className="space-y-4">
      <Button variant="ghost" size="sm" onClick={onBack} data-testid="discovery-back">
        <ArrowLeft size={14} className="mr-1.5" aria-hidden />
        Toutes les catégories
      </Button>

      {isLoading && <SkeletonCard />}
      {isError && (
        <p className="text-sm text-destructive" data-testid="discovery-detail-error">
          Impossible de charger cette catégorie. Réessaie dans un instant.
        </p>
      )}

      {data && (
        <>
          <div className="space-y-1">
            <h2 className="text-lg font-semibold">
              <span aria-hidden>{data.emoji}</span> {data.titre}
            </h2>
            <p className="text-sm text-muted-foreground">{data.description}</p>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ShieldCheck size={13} aria-hidden />
              Seuls les titres qui passent nos filtres de qualité sont affichés
              {asOf ? ` · Mis à jour le ${asOf}` : ''}
            </p>
          </div>

          {data.suggestions.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="discovery-empty">
              Les suggestions de cette catégorie sont en préparation — reviens bientôt.
            </p>
          ) : (
            <div className="space-y-3">
              {data.suggestions.map((s, i) => (
                <StaggerItem key={s.ticker} index={i}>
                  <SuggestionCard suggestion={s} isBeginner={isBeginner} />
                </StaggerItem>
              ))}
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            💡 Rappel : ne mets jamais tout sur un seul titre — la diversification réduit le
            risque. Ces suggestions sont un point de départ d'étude, pas un conseil financier.
          </p>
        </>
      )}
    </div>
  )
}

export default function DiscoveryPage() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['discovery-categories'],
    queryFn: fetchDiscoveryCategories,
  })

  return (
    <PageTransition>
      <div className="space-y-6">
        {selectedCategory === null ? (
          <>
            <div className="space-y-1">
              <h1 className="text-xl font-bold">👋 Quel est ton objectif d'investissement ?</h1>
              <p className="text-sm text-muted-foreground">
                Pas besoin de connaître les symboles boursiers — choisis une catégorie et
                explore des titres déjà filtrés sur la qualité. Chaque terme est expliqué.
              </p>
            </div>

            {isLoading && <SkeletonCard />}
            {isError && (
              <p className="text-sm text-destructive" data-testid="discovery-error">
                Impossible de charger les catégories. Réessaie dans un instant.
              </p>
            )}

            {data && (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {data.categories.map((cat, i) => (
                  <StaggerItem key={cat.id} index={i}>
                    <CategoryCard category={cat} onSelect={setSelectedCategory} />
                  </StaggerItem>
                ))}
              </div>
            )}
          </>
        ) : (
          <CategoryDetail
            categoryId={selectedCategory}
            onBack={() => setSelectedCategory(null)}
          />
        )}
      </div>
    </PageTransition>
  )
}
