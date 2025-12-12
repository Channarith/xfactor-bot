import { useEffect, useState, useRef, useCallback } from 'react'
import { Dashboard } from './components/Dashboard'
import { Header } from './components/Header'
import { AIAssistant } from './components/AIAssistant'
import { AuthProvider } from './context/AuthContext'
import { TradingModeProvider } from './context/TradingModeContext'

// WebSocket connection states
type WSState = 'connecting' | 'connected' | 'disconnected' | 'error'

function App() {
  const [connected, setConnected] = useState(false)
  const [wsState, setWsState] = useState<WSState>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10
  const isUnmounting = useRef(false)
  const heartbeatInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  // Exponential backoff for reconnection
  const getReconnectDelay = useCallback(() => {
    const baseDelay = 1000
    const maxDelay = 30000
    const delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts.current), maxDelay)
    return delay + Math.random() * 1000 // Add jitter
  }, [])

  const connect = useCallback(() => {
    // Don't reconnect if unmounting
    if (isUnmounting.current) return
    
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      wsRef.current.onopen = null
      wsRef.current.onmessage = null
      if (wsRef.current.readyState === WebSocket.OPEN || 
          wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close()
      }
      wsRef.current = null
    }
    
    // Clear heartbeat
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current)
      heartbeatInterval.current = null
    }

    setWsState('connecting')
    
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws`
      
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws
      
      // Connection timeout - if not connected in 10s, retry
      const connectionTimeout = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          console.warn('WebSocket connection timeout, retrying...')
          ws.close()
        }
      }, 10000)
      
      ws.onopen = () => {
        clearTimeout(connectionTimeout)
        console.log('WebSocket connected')
        setConnected(true)
        setWsState('connected')
        reconnectAttempts.current = 0
        
        // Subscribe to updates with slight delay to ensure connection is stable
        setTimeout(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'subscribe', channel: 'portfolio' }))
            ws.send(JSON.stringify({ type: 'subscribe', channel: 'orders' }))
            ws.send(JSON.stringify({ type: 'subscribe', channel: 'news' }))
          }
        }, 100)
        
        // Start heartbeat to keep connection alive
        heartbeatInterval.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))
          }
        }, 30000) // Ping every 30 seconds
      }
      
      ws.onclose = (event) => {
        clearTimeout(connectionTimeout)
        
        // Clear heartbeat
        if (heartbeatInterval.current) {
          clearInterval(heartbeatInterval.current)
          heartbeatInterval.current = null
        }
        
        console.log(`WebSocket closed: code=${event.code}, reason=${event.reason || 'none'}, clean=${event.wasClean}`)
        setConnected(false)
        setWsState('disconnected')
        wsRef.current = null
        
        // Don't reconnect if unmounting or if closed cleanly by us
        if (isUnmounting.current || event.code === 1000) return
        
        // Attempt reconnect with exponential backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++
          const delay = getReconnectDelay()
          console.log(`Reconnecting in ${Math.round(delay/1000)}s (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})`)
          reconnectTimeoutRef.current = setTimeout(connect, delay)
        } else {
          console.error('Max reconnect attempts reached. Please refresh the page.')
          setWsState('error')
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        // onclose will be called after onerror, so reconnect logic is there
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          // Handle ping/pong for keepalive
          if (data.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }))
            return
          }
          if (data.type === 'pong') {
            // Server acknowledged our ping
            return
          }
          // Dispatch custom event for components to listen
          window.dispatchEvent(new CustomEvent('ws-message', { detail: data }))
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }
      
    } catch (e) {
      console.error('Failed to create WebSocket:', e)
      setWsState('error')
      
      // Retry connection
      if (reconnectAttempts.current < maxReconnectAttempts && !isUnmounting.current) {
        reconnectAttempts.current++
        const delay = getReconnectDelay()
        reconnectTimeoutRef.current = setTimeout(connect, delay)
      }
    }
  }, [getReconnectDelay])

  useEffect(() => {
    isUnmounting.current = false
    connect()
    
    // Reconnect on visibility change (tab becomes visible again)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('Tab visible, checking WebSocket connection...')
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          reconnectAttempts.current = 0
          connect()
        }
      }
    }
    
    // Reconnect on online event
    const handleOnline = () => {
      console.log('Network online, reconnecting WebSocket...')
      reconnectAttempts.current = 0
      connect()
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('online', handleOnline)
    
    return () => {
      isUnmounting.current = true
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('online', handleOnline)
      
      if (heartbeatInterval.current) {
        clearInterval(heartbeatInterval.current)
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting')
      }
    }
  }, [connect])

  return (
    <AuthProvider>
      <TradingModeProvider>
        <div className="min-h-screen bg-background">
          <Header connected={connected} wsState={wsState} />
          <main className="container mx-auto p-4">
            <Dashboard />
          </main>
          <AIAssistant />
        </div>
      </TradingModeProvider>
    </AuthProvider>
  )
}

export default App
