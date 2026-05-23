import { useState } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Input } from './ui/input'
import type { WatchlistEntry } from '../types'
import { patchEsgThreshold, patchPriceThreshold } from '../api/watchlist'
import { CompositeSparkline } from './CompositeSparkline'

interface WatchlistTableProps {
  entries: WatchlistEntry[]
  onDelete: (id: string) => void
  onAnalyze: (id: string) => void
  deletingId?: string | null
  analyzingId?: string | null
  onDownloadPdf?: (ticker: string, id: string) => void
  pdfLoadingId?: string | null
  onRefresh?: () => void
}

function esgBadgeProps(score: number | null): { label: string; variant: 'success' | 'warning' | 'destructive' | 'secondary' } {
  if (score === null) return { label: 'N/A', variant: 'secondary' }
  if (score >= 10) return { label: 'FORT', variant: 'success' }
  if (score >= 5) return { label: 'MODERE', variant: 'warning' }
  return { label: 'FAIBLE', variant: 'destructive' }
}

function computeAlerte(entry: WatchlistEntry): boolean | null {
  if (
    entry.last_price_checked == null ||
    entry.last_intrinsic_value == null ||
    entry.last_intrinsic_value === 0
  ) {
    return null
  }
  const ecart =
    Math.abs((entry.last_price_checked - entry.last_intrinsic_value) / entry.last_intrinsic_value)
  return ecart >= entry.price_alert_threshold_pct
}

export function WatchlistTable({
  entries,
  onDelete,
  onAnalyze,
  deletingId,
  analyzingId,
  onDownloadPdf,
  pdfLoadingId,
  onRefresh,
}: WatchlistTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [editError, setEditError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [priceEditingId, setPriceEditingId] = useState<string | null>(null)
  const [priceEditValue, setPriceEditValue] = useState('')
  const [priceEditError, setPriceEditError] = useState<string | null>(null)
  const [priceSaving, setPriceSaving] = useState(false)

  const handleEditStart = (entry: WatchlistEntry) => {
    setEditingId(entry.id)
    setEditValue(String(entry.esg_alert_threshold))
    setEditError(null)
  }

  const handleEditCancel = () => {
    setEditingId(null)
    setEditError(null)
  }

  const handleEditSave = async (id: string) => {
    const threshold = parseFloat(editValue)
    if (isNaN(threshold) || threshold < 0 || threshold > 15) {
      setEditError('Valeur entre 0 et 15')
      return
    }
    setSaving(true)
    try {
      await patchEsgThreshold(id, threshold)
      setEditingId(null)
      setEditError(null)
      onRefresh?.()
    } catch {
      setEditError('Erreur lors de la mise à jour')
    } finally {
      setSaving(false)
    }
  }

  const handlePriceEditStart = (entry: WatchlistEntry) => {
    setPriceEditingId(entry.id)
    setPriceEditValue(String((entry.price_alert_threshold_pct * 100).toFixed(1)))
    setPriceEditError(null)
  }

  const handlePriceEditCancel = () => {
    setPriceEditingId(null)
    setPriceEditError(null)
  }

  const handlePriceEditSave = async (id: string) => {
    const pct = parseFloat(priceEditValue)
    if (isNaN(pct) || pct <= 0 || pct > 100) {
      setPriceEditError('Valeur entre 0 et 100')
      return
    }
    setPriceSaving(true)
    try {
      await patchPriceThreshold(id, pct)
      setPriceEditingId(null)
      setPriceEditError(null)
      onRefresh?.()
    } catch {
      setPriceEditError('Erreur lors de la mise à jour')
    } finally {
      setPriceSaving(false)
    }
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticker</TableHead>
          <TableHead>Workflow</TableHead>
          <TableHead>Dernier score</TableHead>
          <TableHead>Valeur intrinsèque</TableHead>
          <TableHead>Prix vérifié</TableHead>
          <TableHead>Alerte</TableHead>
          <TableHead>Score composite</TableHead>
          <TableHead>Tendance</TableHead>
          <TableHead>ESG</TableHead>
          <TableHead>Seuil ESG</TableHead>
          <TableHead>Seuil Prix (%)</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry) => {
          const alerte = computeAlerte(entry)
          const esg = esgBadgeProps(entry.last_esg_score)
          return (
            <TableRow key={entry.id} data-testid="watchlist-row">
              <TableCell className="font-mono font-semibold">{entry.ticker}</TableCell>
              <TableCell>{entry.workflow}</TableCell>
              <TableCell>
                {entry.last_score != null ? (
                  <span className="tabular-nums">{entry.last_score}/8</span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                {entry.last_intrinsic_value != null
                  ? `$${entry.last_intrinsic_value.toFixed(2)}`
                  : <span className="text-muted-foreground">—</span>}
              </TableCell>
              <TableCell>
                {entry.last_price_checked != null
                  ? `$${entry.last_price_checked.toFixed(2)}`
                  : <span className="text-muted-foreground">—</span>}
              </TableCell>
              <TableCell>
                {alerte === null ? (
                  <span className="text-muted-foreground">—</span>
                ) : alerte ? (
                  <Badge variant="destructive">Alerte</Badge>
                ) : (
                  <Badge variant="success">OK</Badge>
                )}
              </TableCell>
              <TableCell data-testid="composite-score-cell">
                {entry.last_composite_score != null ? (
                  <span className={
                    entry.last_composite_score >= 70 ? 'text-green-400 font-semibold' :
                    entry.last_composite_score >= 45 ? 'text-yellow-400 font-semibold' :
                    'text-red-400 font-semibold'
                  }>
                    {entry.last_composite_score.toFixed(1)}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                <CompositeSparkline ticker={entry.ticker} />
              </TableCell>
              <TableCell>
                <Badge
                  variant={esg.variant}
                  data-testid={`esg-badge-${entry.ticker}`}
                >
                  {esg.label}
                </Badge>
              </TableCell>
              <TableCell>
                {editingId === entry.id ? (
                  <div className="flex items-center gap-1">
                    <Input
                      type="number"
                      min={0}
                      max={15}
                      step={0.5}
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="w-20"
                      data-testid="esg-threshold-input"
                    />
                    <Button
                      size="sm"
                      disabled={saving}
                      onClick={() => void handleEditSave(entry.id)}
                      data-testid="esg-threshold-save-btn"
                    >
                      Sauvegarder
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={saving}
                      onClick={handleEditCancel}
                      data-testid="esg-threshold-cancel-btn"
                    >
                      Annuler
                    </Button>
                    {editError && (
                      <span className="text-sm text-destructive" data-testid="esg-threshold-error">
                        {editError}
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-1">
                    <span data-testid="esg-threshold-display">
                      {entry.esg_alert_threshold.toFixed(1)}
                    </span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleEditStart(entry)}
                      data-testid="esg-threshold-edit-btn"
                      aria-label="Modifier le seuil ESG"
                    >
                      ✎
                    </Button>
                  </div>
                )}
              </TableCell>
              <TableCell>
                {priceEditingId === entry.id ? (
                  <div className="flex items-center gap-1">
                    <Input
                      type="number"
                      min={0.1}
                      max={100}
                      step={0.5}
                      value={priceEditValue}
                      onChange={(e) => setPriceEditValue(e.target.value)}
                      className="w-20"
                      data-testid={`watchlist-price-threshold-${entry.id}-input`}
                    />
                    <Button
                      size="sm"
                      disabled={priceSaving}
                      onClick={() => void handlePriceEditSave(entry.id)}
                      data-testid={`watchlist-price-threshold-${entry.id}-save-btn`}
                    >
                      Sauvegarder
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={priceSaving}
                      onClick={handlePriceEditCancel}
                      data-testid={`watchlist-price-threshold-${entry.id}-cancel-btn`}
                    >
                      Annuler
                    </Button>
                    {priceEditError && (
                      <span className="text-sm text-destructive" data-testid={`watchlist-price-threshold-${entry.id}-error`}>
                        {priceEditError}
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-1">
                    <span data-testid={`watchlist-price-threshold-${entry.id}-display`}>
                      {(entry.price_alert_threshold_pct * 100).toFixed(1)}
                    </span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handlePriceEditStart(entry)}
                      data-testid={`watchlist-price-threshold-${entry.id}-edit-btn`}
                      aria-label="Modifier le seuil de prix"
                    >
                      ✎
                    </Button>
                  </div>
                )}
              </TableCell>
              <TableCell>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={analyzingId === entry.id}
                    onClick={() => onAnalyze(entry.id)}
                  >
                    {analyzingId === entry.id ? '...' : 'Analyser'}
                  </Button>
                  {onDownloadPdf && (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={pdfLoadingId === entry.id}
                      onClick={() => onDownloadPdf(entry.ticker, entry.id)}
                      data-testid={`pdf-btn-${entry.ticker}`}
                    >
                      {pdfLoadingId === entry.id ? '...' : 'PDF'}
                    </Button>
                  )}
                  <Button
                    variant="destructive"
                    size="sm"
                    aria-label="Supprimer"
                    disabled={deletingId === entry.id}
                    onClick={() => onDelete(entry.id)}
                  >
                    {deletingId === entry.id ? '...' : 'Supprimer'}
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
