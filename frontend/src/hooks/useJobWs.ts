import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import type { JobDetail, JobItem } from '../api/jobs'

export function useJobWs(jobId: number | undefined, enabled = true) {
  const qc = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)

  useEffect(() => {
    if (!enabled || jobId === undefined) return
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const url = `${proto}://${window.location.host}/ws/jobs/${jobId}`
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => { retryRef.current = 0 }
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === 'item_update') {
            const itemPayload: Partial<JobItem> & { id: number; job_id: number } = msg.item
            qc.setQueryData<JobDetail>(['job', jobId], (old) => {
              if (!old) return old
              const items = old.items.map((it) =>
                it.id === itemPayload.id ? { ...it, ...itemPayload } as JobItem : it,
              )
              return { ...old, items }
            })
          }
        } catch { /* ignore */ }
      }
      ws.onclose = () => {
        if (cancelled) return
        retryRef.current = Math.min(retryRef.current + 1, 5)
        setTimeout(connect, 500 * 2 ** retryRef.current)
      }
    }
    connect()

    return () => {
      cancelled = true
      wsRef.current?.close()
    }
  }, [jobId, enabled, qc])
}
