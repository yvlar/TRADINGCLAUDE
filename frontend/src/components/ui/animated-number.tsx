import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

interface AnimatedNumberProps {
  /** Valeur cible à atteindre. */
  value: number
  /** Durée de l'animation en ms. */
  duration?: number
  /** Formateur de la valeur affichée. */
  formatter?: (n: number) => string
  className?: string
}

/**
 * Affiche un nombre qui "compte" vers sa valeur cible avec easing cubic-out.
 * Déclenche une légère pulsation à l'arrivée pour signaler la mise à jour.
 */
export function AnimatedNumber({
  value,
  duration = 900,
  formatter,
  className,
}: AnimatedNumberProps) {
  const [displayed, setDisplayed] = useState(value)
  const [pulsing, setPulsing] = useState(false)
  const startRef = useRef({ from: value, time: 0 })
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    startRef.current = { from: displayed, time: 0 }
    setPulsing(false)

    const animate = (ts: number) => {
      if (startRef.current.time === 0) startRef.current.time = ts
      const elapsed = ts - startRef.current.time
      const t = Math.min(elapsed / duration, 1)
      // easing cubic-out
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplayed(startRef.current.from + (value - startRef.current.from) * eased)
      if (t < 1) {
        rafRef.current = requestAnimationFrame(animate)
      } else {
        setDisplayed(value)
        setPulsing(true)
        setTimeout(() => setPulsing(false), 1500)
      }
    }

    rafRef.current = requestAnimationFrame(animate)
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
    // displayed intentionnellement exclu — on ne veut pas boucler
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, duration])

  const text = formatter ? formatter(displayed) : displayed.toFixed(0)

  return (
    <span
      className={cn(
        'tabular-nums transition-opacity',
        pulsing && 'animate-count-pulse',
        className,
      )}
    >
      {text}
    </span>
  )
}
