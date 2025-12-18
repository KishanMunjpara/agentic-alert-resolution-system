import React, { useState, useCallback, useEffect } from 'react'
import { alertService, Alert } from '../services/apiClient'

export const useAlert = (alertId: string) => {
  const [alert, setAlert] = useState<Alert | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAlert = async () => {
      try {
        setLoading(true)
        const data = await alertService.getAlert(alertId)
        setAlert(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch alert')
      } finally {
        setLoading(false)
      }
    }

    fetchAlert()
  }, [alertId])

  const investigate = useCallback(async () => {
    try {
      await alertService.investigateAlert(alertId)
      const updated = await alertService.getAlert(alertId)
      setAlert(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to investigate')
    }
  }, [alertId])

  return { alert, loading, error, investigate }
}

export const useAlerts = () => {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true)
        const data = await alertService.listAlerts({ limit: 50 })
        setAlerts(data.alerts)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch alerts')
      } finally {
        setLoading(false)
      }
    }

    fetchAlerts()
    // Refresh every 5 seconds
    const interval = setInterval(fetchAlerts, 5000)
    return () => clearInterval(interval)
  }, [])

  return { alerts, loading, error }
}

export const useDashboardMetrics = () => {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true)
        const data = await alertService.getDashboardMetrics()
        setMetrics(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch metrics')
      } finally {
        setLoading(false)
      }
    }

    fetchMetrics()
    // Refresh every 10 seconds
    const interval = setInterval(fetchMetrics, 10000)
    return () => clearInterval(interval)
  }, [])

  return { metrics, loading, error }
}

export const useWebSocket = (onMessage: (event: any) => void) => {
  const onMessageRef = React.useRef(onMessage)
  
  // Update ref when callback changes
  useEffect(() => {
    onMessageRef.current = onMessage
  }, [onMessage])

  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/alerts'
    console.log('Connecting to WebSocket:', wsUrl)
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('✓ WebSocket connected successfully')
    }
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        console.log('Raw WebSocket message:', event.data)
        console.log('Parsed message:', message)
        // Use ref to get latest callback
        onMessageRef.current(message)
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err, event.data)
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason)
    }

    return () => {
      console.log('Closing WebSocket connection')
      ws.close()
    }
  }, []) // Only connect once
}


