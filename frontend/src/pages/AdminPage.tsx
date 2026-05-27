import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listApiKeys, createApiKey, revokeApiKey } from '../api/admin'
import { ApiError } from '../api/client'
import type { ApiKey } from '../types'
import { Button } from '../components/ui/button'

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
                      {k.id.slice(0, 8)}…
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
    </div>
  )
}
