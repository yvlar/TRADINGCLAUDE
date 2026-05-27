import { cn } from '@/lib/utils'

interface SkeletonProps {
  className?: string
}

/** Rectangle avec animation shimmer — base de tous les squelettes. */
function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn('skeleton-shimmer', className)}
    />
  )
}

/** Ligne de tableau squelette — N colonnes de largeurs variables. */
function SkeletonRow({ cols = 5 }: { cols?: number }) {
  const widths = ['w-16', 'w-24', 'w-20', 'w-28', 'w-16', 'w-32', 'w-20']
  return (
    <tr className="border-b border-border">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className={cn('h-4', widths[i % widths.length])} />
        </td>
      ))}
    </tr>
  )
}

/** Carte métrique squelette (titre + grande valeur + sous-titre). */
function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-3">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-3 w-44" />
    </div>
  )
}

/** Grille de N cartes squelettes. */
function SkeletonCardGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

/** Bloc graphique squelette. */
function SkeletonChart({ className }: SkeletonProps) {
  return (
    <div className={cn('rounded-xl border border-border bg-card p-5 space-y-3', className)}>
      <Skeleton className="h-3 w-28" />
      <Skeleton className="h-48 w-full" />
    </div>
  )
}

/** Tableau complet squelette — N lignes × N colonnes. */
function SkeletonTable({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <table className="w-full text-sm">
      <tbody>
        {Array.from({ length: rows }).map((_, i) => (
          <SkeletonRow key={i} cols={cols} />
        ))}
      </tbody>
    </table>
  )
}

export { Skeleton, SkeletonRow, SkeletonCard, SkeletonCardGrid, SkeletonChart, SkeletonTable }
