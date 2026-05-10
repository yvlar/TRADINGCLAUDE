import { useState, useEffect, useRef, useCallback } from 'react'
import type { MetricsPayload } from '../types'

function buildWsUrl(): string {
  const wsBase = import.meta.env.VITE_WS_URL as string | undefined
  if (wsBase) return `${wsBase}/ws/metrics`
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/metrics`
}

interface UseMetricsState {
  data: MetricsPayload | null
  connected: boolean
  error: string | null
}

export function useMetrics(): UseMetricsState {
  const [state, setState] = useState<UseMetricsState>({
    data: null,
    connected: false,
    error: null,
  })
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    const url = buildWsUrl()

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current) return
        setState(s => ({ ...s, connected: true, error: null }))
      }

      ws.onmessage = (event: MessageEvent<string>) => {
        if (!mountedRef.current) return
        try {
          const payload = JSON.parse(event.data) as MetricsPayload
          setState(s => ({ ...s, data: payload }))
        } catch {
          // ignore invalid JSON
        }
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        setState(s => ({ ...s, connected: false }))
        reconnectTimerRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        if (!mountedRef.current) return
        setState(s => ({ ...s, error: 'Connexion WebSocket échouée', connected: false }))
        ws.close()
      }
    } catch (err) {
      setState(s => ({ ...s, error: String(err), connected: false }))
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return state
}
