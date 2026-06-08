import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listApiKeys, createApiKey, revokeApiKey, getAuditLog } from '../api/admin'
import { ApiError } from '../api/client'
import type { ApiKey, AuditLogEntry } from '../types'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { SkeletonTable } from '../components/ui/skeleton'

function shortId(id: string | null): string {
  if (!id) return '—'
  return `${id.slice(0, 8)}…`
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function AdminPage() {
  const qc = useQueryClient()
  const [newName, setNewName] = useState('')
  const [newRole, setNewRole] = useState('user')
  const [generatedKey, setGeneratedKey] = useState<string | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)

  const { data: keys, error: listError, isLoading } = useQuery<ApiKey[], Error>({
    queryKey: ['admin-keys'],
    queryFn: listApiKeys,
    retry: false,
  })

  const createMutation = useMutation({
    mutationFn: createApiKey,
    onSuccess: (result) => {
      setGeneratedKey(result.key)
      setNewName('')
      setNewRole('user')
      setCreateError(null)
      void qc.invalidateQueries({ queryKey: ['admin-keys'] })
    },
    onError: (err: Error) => {
      setCreateError(err.message)
    },
  })

  const revokeMutation = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['admin-keys'] })
    },
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return
    setGeneratedKey(null)
    createMutation.mutate({ name: newName.trim(), role: newRole })
  }

  const handleRevoke = (key: ApiKey) => {
    if (!window.confirm(`Révoquer la clé "${key.name}" ? Cette action est irréversible.`)) return
    revokeMutation.mutate(key.id)
  }

  const is403 = listError instanceof ApiError && listError.status === 403

  // --- Journal d'audit (filtre côté client sur la liste déjà chargée) ---
  const [filterAction, setFilterAction] = useState('')
  const [filterCibleType, setFilterCibleType] = useState('')

  const {
    data: auditEntries,
    error: auditError,
    isLoading: auditLoading,
  } = useQuery<AuditLogEntry[], Error>({
    queryKey: ['admin-audit-log'],
    queryFn: () => getAuditLog(),
    retry: false,
  })

  const actionOptions = useMemo(
    () => Array.from(new Set((auditEntries ?? []).map((e) => e.action))).sort(),
    [auditEntries],
  )
  const cibleTypeOptions = useMemo(
    () => Array.from(new Set((auditEntries ?? []).map((e) => e.cible_type))).sort(),
    [auditEntries],
  )

  const filteredEntries = useMemo(
    () =>
      (auditEntries ?? []).filter(
        (e) =>
          (!filterAction || e.action === filterAction) &&
          (!filterCibleType || e.cible_type === filterCibleType),
      ),
    [auditEntries, filterAction, filterCibleType],
  )

  const auditIs403 = auditError instanceof ApiError && auditError.status === 403

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Administration — Clés API</h2>
        <p className="text-muted-foreground mt-1">
          Gérez les clés d'accès à l'API du copilote financier.
        </p>
      </div>

      {/* Formulaire création */}
      <section className="bg-card border border-border rounded-lg p-6 space-y-4">
        <h3 className="font-semibold text-lg">Créer une clé</h3>
        <form onSubmit={handleCreate} className="flex items-end gap-3 flex-wrap">
          <div className="flex flex-col gap-1">
            <label htmlFor="key-name" className="text-sm font-medium">
              Nom de la clé
            </label>
            <input
              id="key-name"
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="ex: CI pipeline"
              className="border border-border rounded px-3 py-2 text-sm bg-background w-56"
              required
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="key-role" className="text-sm font-medium">
              Rôle
            </label>
            <select
              id="key-role"
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              className="border border-border rounded px-3 py-2 text-sm bg-background"
            >
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
          </div>
          <Button type="submit" disabled={createMutation.isPending || !newName.trim()}>
            {createMutation.isPending ? 'Création...' : 'Créer'}
          </Button>
        </form>
        {createError && (
          <p className="text-destructive text-sm">{createError}</p>
        )}
        {generatedKey && (
          <div className="mt-4 space-y-2">
            <p className="text-sm text-amber-600 font-medium">
              Copiez cette clé maintenant — elle ne sera plus affichée.
            </p>
            <code
              data-testid="new-key-display"
              className="block bg-muted px-4 py-3 rounded text-sm font-mono break-all"
            >
              {generatedKey}
            </code>
          </div>
        )}
      </section>

      {/* Tableau des clés */}
      <section className="bg-card border border-border rounded-lg p-6 space-y-4">
        <h3 className="font-semibold text-lg">Clés existantes</h3>

        {is403 && (
          <p className="text-destructive text-sm">
            Accès refusé — vous devez être administrateur.
          </p>
        )}
        {!is403 && listError && (
          <p className="text-destructive text-sm">{listError.message}</p>
        )}
        {isLoading && <p className="text-muted-foreground text-sm">Chargement...</p>}

        {keys && keys.length === 0 && (
          <p className="text-muted-foreground text-sm">Aucune clé API configurée.</p>
        )}

        {keys && keys.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">ID</th>
                  <th className="pb-2 pr-4 font-medium">Nom</th>
                  <th className="pb-2 pr-4 font-medium">Rôle</th>
                  <th className="pb-2 pr-4 font-medium">Créée le</th>
                  <th className="pb-2 pr-4 font-medium">Dernière utilisation</th>
                  <th className="pb-2 pr-4 font-medium">Statut</th>
                  <th className="pb-2 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((k) => (
                  <tr
                    key={k.id}
                    data-testid={`key-row-${k.id}`}
                    className="border-b border-border last:border-0"
                  >
                    <td className="py-3 pr-4 font-mono text-xs text-muted-foreground">
                      {shortId(k.id)}
                    </td>
                    <td className="py-3 pr-4">{k.name}</td>
                    <td className="py-3 pr-4">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        k.role === 'admin'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-slate-100 text-slate-700'
                      }`}>
                        {k.role}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-muted-foreground">{formatDate(k.created_at)}</td>
                    <td className="py-3 pr-4 text-muted-foreground">{formatDate(k.last_used_at)}</td>
                    <td className="py-3 pr-4">
                      {k.is_active ? (
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full border border-bull/40 bg-bull/15 text-bull">
                          Actif
                        </span>
                      ) : (
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full border border-bear/40 bg-bear/15 text-bear">
                          Révoqué
                        </span>
                      )}
                    </td>
                    <td className="py-3">
                      {k.is_active && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleRevoke(k)}
                          disabled={revokeMutation.isPending}
                        >
                          Révoquer
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Journal d'audit (Sprint 180) */}
      <section
        data-testid="audit-log-section"
        className="bg-card border border-border rounded-lg p-6 space-y-4"
      >
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h3 className="font-semibold text-lg">Journal d'audit</h3>
            <p className="text-muted-foreground text-sm mt-1">
              Mutations métier récentes (watchlist, annotation, clé API) — traçabilité Loi 25.
            </p>
          </div>
          <div className="flex items-end gap-3 flex-wrap">
            <div className="flex flex-col gap-1">
              <label htmlFor="audit-filter-action" className="text-sm font-medium">
                Action
              </label>
              <select
                id="audit-filter-action"
                data-testid="audit-filter-action"
                value={filterAction}
                onChange={(e) => setFilterAction(e.target.value)}
                className="border border-border rounded px-3 py-2 text-sm bg-background"
              >
                <option value="">Toutes</option>
                {actionOptions.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="audit-filter-cible-type" className="text-sm font-medium">
                Type de cible
              </label>
              <select
                id="audit-filter-cible-type"
                data-testid="audit-filter-cible-type"
                value={filterCibleType}
                onChange={(e) => setFilterCibleType(e.target.value)}
                className="border border-border rounded px-3 py-2 text-sm bg-background"
              >
                <option value="">Tous</option>
                {cibleTypeOptions.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {auditIs403 && (
          <p data-testid="audit-log-error" className="text-destructive text-sm">
            Accès refusé — vous devez être administrateur.
          </p>
        )}
        {!auditIs403 && auditError && (
          <p data-testid="audit-log-error" className="text-destructive text-sm">
            {auditError.message}
          </p>
        )}
        {auditLoading && (
          <div data-testid="audit-log-loading">
            <SkeletonTable rows={5} cols={5} />
          </div>
        )}

        {!auditError && !auditLoading && auditEntries && auditEntries.length === 0 && (
          <p data-testid="audit-log-empty" className="text-muted-foreground text-sm">
            Aucune entrée d'audit enregistrée.
          </p>
        )}

        {!auditError && auditEntries && auditEntries.length > 0 && (
          <div className="overflow-x-auto">
            <table data-testid="audit-log-table" className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Date</th>
                  <th className="pb-2 pr-4 font-medium">Action</th>
                  <th className="pb-2 pr-4 font-medium">Type de cible</th>
                  <th className="pb-2 pr-4 font-medium">Cible</th>
                  <th className="pb-2 font-medium">Espace (tenant)</th>
                </tr>
              </thead>
              <tbody>
                {filteredEntries.map((entry) => (
                  <tr
                    key={entry.id}
                    data-testid={`audit-row-${entry.id}`}
                    className="border-b border-border last:border-0"
                  >
                    <td className="py-3 pr-4 text-muted-foreground whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </td>
                    <td className="py-3 pr-4">
                      <Badge variant="secondary">{entry.action}</Badge>
                    </td>
                    <td className="py-3 pr-4">{entry.cible_type}</td>
                    <td className="py-3 pr-4 font-mono text-xs break-all">
                      {entry.cible_id ?? '—'}
                    </td>
                    <td className="py-3 font-mono text-xs text-muted-foreground">
                      {shortId(entry.tenant_id)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredEntries.length === 0 && (
              <p
                data-testid="audit-log-no-match"
                className="text-muted-foreground text-sm pt-3"
              >
                Aucune entrée ne correspond au filtre.
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
