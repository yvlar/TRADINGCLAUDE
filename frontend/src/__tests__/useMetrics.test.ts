import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useMetrics } from '../api/ws'
import type { MetricsPayload } from '../types'

const MOCK_PAYLOAD: MetricsPayload = {
  jobs_en_cours: 2,
  jobs_echoues_1h: 0,
  cout_total_1h_usd: 0.042,
  cache_hit_ratio: 0.73,
  analyses_24h: 15,
  timestamp: '2026-05-09T14:32:00Z',
}

class MockWebSocket {
  static instances: MockWebSocket[] = []
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  readyState = 0

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
    setTimeout(() => {
      this.readyState = 1
      this.onopen?.()
    }, 0)
  }

  send(_data: string) {}

  close() {
    this.readyState = 3
    this.onclose?.()
  }

  simulateMessage(payload: MetricsPayload) {
    this.onmessage?.({ data: JSON.stringify(payload) })
  }
}

describe('useMetrics', () => {
  const OriginalWebSocket = globalThis.WebSocket

  beforeEach(() => {
    MockWebSocket.instances = []
    globalThis.WebSocket = MockWebSocket as unknown as typeof WebSocket
    Object.defineProperty(window, 'location', {
      value: { protocol: 'http:', host: 'localhost:5173' },
      writable: true,
    })
  })

  afterEach(() => {
    globalThis.WebSocket = OriginalWebSocket
    vi.restoreAllMocks()
  })

  it('commence déconnecté sans données', () => {
    const { result } = renderHook(() => useMetrics())
    expect(result.current.connected).toBe(false)
    expect(result.current.data).toBeNull()
  })

  it('passe à connected=true après onopen', async () => {
    const { result } = renderHook(() => useMetrics())
    await waitFor(() => {
      expect(result.current.connected).toBe(true)
    })
  })

  it('met à jour les données sur réception d\'un message WebSocket', async () => {
    const { result } = renderHook(() => useMetrics())

    await waitFor(() => expect(result.current.connected).toBe(true))

    act(() => {
      MockWebSocket.instances[0]?.simulateMessage(MOCK_PAYLOAD)
    })

    await waitFor(() => {
      expect(result.current.data).toBeDefined()
      expect(result.current.data?.jobs_en_cours).toBe(2)
      expect(result.current.data?.cache_hit_ratio).toBe(0.73)
    })
  })

  it('ignore les messages JSON invalides sans planter', async () => {
    const { result } = renderHook(() => useMetrics())
    await waitFor(() => expect(result.current.connected).toBe(true))

    act(() => {
      MockWebSocket.instances[0]?.onmessage?.({ data: 'not valid json {{' })
    })

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('repasse connected=false à la déconnexion', async () => {
    const { result } = renderHook(() => useMetrics())
    await waitFor(() => expect(result.current.connected).toBe(true))

    act(() => {
      MockWebSocket.instances[0]?.close()
    })

    await waitFor(() => {
      expect(result.current.connected).toBe(false)
    })
  })
})
