import { useState } from 'react'
import type { FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchSemanticSearch } from '../api/search'
import { Input } from '../components/ui/input'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { SkeletonCard } from '../components/ui/skeleton'
import { PageTransition, StaggerItem } from '../components/PageTransition'
import type { SemanticSearchResult } from '../types'

function scoreBadgeVariant(score: number): 'success' | 'warning' | 'secondary' {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'secondary'
}

// ".claude/skills/graham-stock-screening/references/x.md" → "graham-stock-screening › x.md"
function sourceLabel(source: string): string {
  const parts = source.split('/').filter((p) => p && p !== '.claude' && p !== 'skills')
  if (parts.length <= 1) return source
  const skill = parts[0]
  const file = parts[parts.length - 1]
  return `${skill} › ${file}`
}

function ResultCard({ result, index }: { result: SemanticSearchResult; index: number }) {
  return (
    <Card data-testid={`search-result-${index}`}>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="truncate normal-case text-xs" title={result.source}>
          {sourceLabel(result.source)}
        </CardTitle>
        <Badge variant={scoreBadgeVariant(result.score)} className="shrink-0">
          {result.score.toFixed(2)}
        </Badge>
      </CardHeader>
      <CardContent>
        <p className="whitespace-pre-wrap text-sm text-foreground">{result.extrait}</p>
      </CardContent>
    </Card>
  )
}

export default function SearchPage() {
  const [input, setInput] = useState('')
  const [query, setQuery] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['semantic-search', query],
    queryFn: () => fetchSemanticSearch(query, 5),
    enabled: query.trim().length >= 2,
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setQuery(input.trim())
  }

  const results = data?.results ?? []
  const ragDisabled = data !== undefined && !data.rag_enabled

  return (
    <PageTransition>
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">Recherche sémantique</h1>
        <p className="text-sm text-muted-foreground">
          Interroge la base de connaissances investissement (formules, seuils, frameworks)
          en langage naturel.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          data-testid="search-input"
          aria-label="Requête"
          placeholder="ex. comment calculer la marge de sécurité ?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <Button type="submit" data-testid="search-submit" disabled={input.trim().length < 2}>
          Rechercher
        </Button>
      </form>

      {query.trim().length < 2 ? (
        <p data-testid="search-idle" className="text-muted-foreground">
          Entrez une requête d'au moins 2 caractères pour interroger le corpus.
        </p>
      ) : isLoading ? (
        <div className="space-y-3" data-testid="search-spinner">
          {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : isError ? (
        <p data-testid="search-error" className="text-destructive">
          Impossible d'effectuer la recherche.
        </p>
      ) : ragDisabled ? (
        <p data-testid="search-rag-disabled" className="text-muted-foreground">
          La recherche sémantique est désactivée (OPENAI_API_KEY absente côté serveur).
        </p>
      ) : results.length === 0 ? (
        <p data-testid="search-empty" className="text-muted-foreground">
          Aucun passage pertinent trouvé pour « {query} ».
        </p>
      ) : (
        <div data-testid="search-results" className="space-y-3">
          {results.map((result, i) => (
            <StaggerItem key={`${result.source}-${i}`} index={i}>
              <ResultCard result={result} index={i} />
            </StaggerItem>
          ))}
        </div>
      )}
    </div>
    </PageTransition>
  )
}
