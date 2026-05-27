import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface PageTransitionProps {
  children: ReactNode
  className?: string
}

/**
 * Enveloppe chaque page dans un fade-in-up discret.
 * Déclenché à chaque montage (navigation entre pages).
 */
export function PageTransition({ children, className }: PageTransitionProps) {
  return (
    <div className={cn('animate-fade-in-up', className)}>
      {children}
    </div>
  )
}

interface StaggerItemProps {
  children: ReactNode
  index: number
  className?: string
}

/**
 * Élément d'une liste animée — chaque item apparaît avec un décalage
 * proportionnel à son index (max 400 ms pour éviter l'attente).
 */
export function StaggerItem({ children, index, className }: StaggerItemProps) {
  const delay = Math.min(index * 55, 400)
  return (
    <div
      className={cn('animate-fade-in-up', className)}
      style={{ animationDelay: `${delay}ms` }}
    >
      {children}
    </div>
  )
}
