import { useEffect, useState, useRef, useCallback } from 'react'
import { Dashboard } from './components/Dashboard'
import { Header } from './components/Header'
import { AIAssistant } from './components/AIAssistant'
import { SettingsPage } from './components/SettingsPage'
import { AuthProvider } from './context/AuthContext'
import { TradingModeProvider } from './context/TradingModeContext'
import { DemoModeProvider } from './contexts/DemoModeContext'
import DemoModeBanner from './components/DemoModeBanner'
import { getWsBaseUrl, getApiBaseUrl } from './config/api'

// Page types
type PageType = 'dashboard' | 'settings'

// WebSocket connection states
type WSState = 'connecting' | 'connected' | 'disconnected' | 'error'

// Check if running in Tauri desktop app
const isTauri = typeof window !== 'undefined' && !!(window as any).__TAURI__

function App() {
  const [connected, setConnected] = useState(false)
  const [wsState, setWsState] = useState<WSState>('disconnected')
  const [currentPage, setCurrentPage] = useState<PageType>('dashboard')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)
  const isUnmounting = useRef(false)
  const heartbeatInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const healthCheckInterval = useRef<ReturnType<typeof setInterval> | null>(null)
  const cleanupDone = useRef(false)
  const isConnectedRef = useRef(false) // Ref to avoid dependency loops
  const connectRef = useRef<() => void>(() => {}) // Stable reference to connect function
  
  // Track if app is visible (for reducing API calls when in background)
  const [isVisible, setIsVisible] = useState(!document.hidden)
  
  // Reconnection config with rate limiting
  const RECONNECT_CONFIG = {
    baseDelay: 1000,        // Start at 1 second
    maxDelay: 30000,        // Max 30 seconds between attempts
    fastRetryThreshold: 5,  // First 5 attempts use faster backoff
    healthCheckInterval: 30000, // Increased: Check backend health every 30 seconds when disconnected
  }
  
  // Listen for visibility changes to reduce API calls when app is in background
  useEffect(() => {
    const handleVisibilityChange = () => {
      const visible = !document.hidden
      setIsVisible(visible)
      console.log(`[App] Visibility changed: ${visible ? 'visible' : 'hidden'}`)
      
      // When app becomes visible again, refresh connection status
      if (visible && !isConnectedRef.current) {
        console.log('[App] App became visible, checking connection...')
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [])

  // Soft cleanup - for component unmount (DON'T kill backend)
  const performSoftCleanup = useCallback(() => {
    console.log('[Cleanup] Soft cleanup - clearing intervals and WebSocket only')
    
    // Close WebSocket cleanly
    if (wsRef.current) {
      wsRef.current.close(1000, 'Component cleanup')
      wsRef.current = null
    }
    
    // Clear intervals
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current)
      heartbeatInterval.current = null
    }
    if (healthCheckInterval.current) {
      clearInterval(healthCheckInterval.current)
      healthCheckInterval.current = null
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
  }, [])

  // Hard cleanup - ONLY for actual app/window close (kills backend)
  const performHardCleanup = useCallback(async (reason: string) => {
    if (cleanupDone.current) {
      console.log('[Cleanup] Already cleaned up, skipping')
      return
    }
    cleanupDone.current = true
    
    console.log(`[Cleanup] Hard cleanup triggered: ${reason}`)
    
    // Send cleanup signal via WebSocket if connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'cleanup' }))
      } catch (e) {
        console.warn('[Cleanup] Failed to send cleanup signal:', e)
      }
    }
    
    // Stop all bots via API
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/bots/stop-all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (response.ok) {
        console.log('[Cleanup] All bots stopped successfully')
      }
    } catch (e) {
      console.warn('[Cleanup] Failed to stop bots:', e)
    }
    
    // Soft cleanup first
    performSoftCleanup()
    
    // ONLY kill backend if in Tauri AND this is a real app close
    if (isTauri) {
      try {
        console.log('[Cleanup] Invoking Tauri force_cleanup...')
        const { invoke } = await import('@tauri-apps/api/core')
        await invoke('force_cleanup')
        console.log('[Cleanup] Tauri cleanup completed')
      } catch (e) {
        console.warn('[Cleanup] Tauri cleanup failed:', e)
      }
    }
    
    console.log('[Cleanup] Hard cleanup completed')
  }, [performSoftCleanup])

  // Exponential backoff for reconnection with rate limiting
  const getReconnectDelay = useCallback(() => {
    const { baseDelay, maxDelay, fastRetryThreshold } = RECONNECT_CONFIG
    
    // Fast retries for first few attempts (1s, 2s, 4s, 8s, 16s)
    // Then settle at maxDelay (30s) for continuous background checking
    let delay: number
    if (reconnectAttempts.current < fastRetryThreshold) {
      delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts.current), maxDelay)
    } else {
      // After initial fast retries, use consistent interval with slight randomization
      delay = maxDelay
    }
    
    // Add jitter (10-20% randomization) to prevent thundering herd
    const jitter = delay * (0.1 + Math.random() * 0.1)
    return delay + jitter
  }, [])

  // Check if backend is available via health endpoint
  const checkBackendHealth = useCallback(async (): Promise<boolean> => {
    const healthUrl = `${getApiBaseUrl()}/health`
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 3000) // 3s timeout
      
      const response = await fetch(healthUrl, {
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      
      if (response.ok) {
        console.log(`Backend health check passed: ${healthUrl}`)
        return true
      } else {
        console.warn(`Backend health check failed: ${response.status} ${response.statusText}`)
        return false
      }
    } catch (e) {
      // Only log occasionally to avoid spam
      if (reconnectAttempts.current <= 3 || reconnectAttempts.current % 10 === 0) {
        console.warn(`Backend health check error (${healthUrl}):`, e instanceof Error ? e.message : e)
      }
      return false
    }
  }, [])

  // Stop health check interval
  const stopHealthCheck = useCallback(() => {
    if (healthCheckInterval.current) {
      clearInterval(healthCheckInterval.current)
      healthCheckInterval.current = null
    }
  }, [])

  // Start health check interval when disconnected
  const startHealthCheck = useCallback(() => {
    // Don't start if already running or if we're connected
    if (healthCheckInterval.current || isConnectedRef.current) return
    
    console.log(`Starting backend health check (every ${RECONNECT_CONFIG.healthCheckInterval / 1000}s)`)
    
    healthCheckInterval.current = setInterval(async () => {
      if (isUnmounting.current) return
      
      const isHealthy = await checkBackendHealth()
      if (isHealthy && !isConnectedRef.current) {
        console.log('Backend health check passed! Triggering reconnect...')
        // Reset attempts for faster reconnection
        reconnectAttempts.current = 0
        // Clear any pending reconnect timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }
        // Stop health check (will be restarted if disconnect happens again)
        stopHealthCheck()
        // Reconnect immediately using the ref
        connectRef.current()
      }
    }, RECONNECT_CONFIG.healthCheckInterval)
  }, [checkBackendHealth, stopHealthCheck])

  const connect = useCallback(() => {
    // Don't reconnect if unmounting
    if (isUnmounting.current) return
    
    // Prevent duplicate connections - if already connecting or connected, skip
    if (wsRef.current && 
        (wsRef.current.readyState === WebSocket.OPEN || 
         wsRef.current.readyState === WebSocket.CONNECTING)) {
      console.log('WebSocket already open or connecting, skipping duplicate connect')
      return
    }
    
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      wsRef.current.onopen = null
      wsRef.current.onmessage = null
      wsRef.current.close()
      wsRef.current = null
    }
    
    // Clear heartbeat
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current)
      heartbeatInterval.current = null
    }

    setWsState('connecting')
    
    try {
      const wsUrl = `${getWsBaseUrl()}/ws`
      console.log('Connecting WebSocket to:', wsUrl)
      
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
        console.log('WebSocket connected successfully')
        isConnectedRef.current = true
        setConnected(true)
        setWsState('connected')
        reconnectAttempts.current = 0
        
        // Stop health check since we're connected now
        stopHealthCheck()
        
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
        
        // Log detailed close information
        const closeCodeMeanings: Record<number, string> = {
          1000: 'Normal closure',
          1001: 'Going away (page closing)',
          1002: 'Protocol error',
          1003: 'Unsupported data',
          1005: 'No status received',
          1006: 'Abnormal closure (connection lost)',
          1007: 'Invalid payload data',
          1008: 'Policy violation',
          1009: 'Message too big',
          1010: 'Extension required',
          1011: 'Internal server error',
          1012: 'Service restart',
          1013: 'Try again later',
          1014: 'Bad gateway',
          1015: 'TLS handshake failure',
        }
        
        const codeMeaning = closeCodeMeanings[event.code] || 'Unknown'
        console.log(`WebSocket closed: code=${event.code} (${codeMeaning}), reason="${event.reason || 'none'}", clean=${event.wasClean}`)
        
        // Provide helpful debug info for connection failures
        if (event.code === 1006) {
          console.warn('=== Connection Lost Debug Info ===')
          console.warn('Code 1006 usually means:')
          console.warn('  1. Backend server crashed or stopped')
          console.warn('  2. Network connection dropped')
          console.warn('  3. Firewall blocked the connection')
          console.warn('  4. Backend took too long to respond')
          console.warn('Checking backend health...')
        }
        
        isConnectedRef.current = false
        setConnected(false)
        setWsState('disconnected')
        wsRef.current = null
        
        // Don't reconnect if unmounting or if closed cleanly by us
        if (isUnmounting.current || event.code === 1000) return
        
        // Start background health check for faster reconnection when backend comes back
        startHealthCheck()
        
        // Attempt reconnect with exponential backoff
        // NEVER give up - keep trying indefinitely (backend might come back)
        reconnectAttempts.current++
        const delay = getReconnectDelay()
        
        // Log less frequently after many attempts to reduce console spam
        if (reconnectAttempts.current <= 10 || reconnectAttempts.current % 10 === 0) {
          console.log(`Reconnecting in ${Math.round(delay/1000)}s (attempt ${reconnectAttempts.current})`)
        }
        
        reconnectTimeoutRef.current = setTimeout(() => connectRef.current(), delay)
      }
      
      ws.onerror = (error) => {
        console.error('=== WebSocket Connection Error ===')
        console.error('Error details:', error)
        console.error('Attempted URL:', wsUrl)
        console.error('Troubleshooting tips:')
        console.error('  1. Check if backend is running (port 9876)')
        console.error('  2. On Windows: Run "netstat -ano | findstr :9876"')
        console.error('  3. On Linux: Run "lsof -i :9876" or "ss -tulpn | grep 9876"')
        console.error('  4. Check firewall settings')
        console.error('  5. Try opening http://127.0.0.1:9876/health in browser')
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
      
      // Retry connection - never give up
      if (!isUnmounting.current) {
        reconnectAttempts.current++
        const delay = getReconnectDelay()
        reconnectTimeoutRef.current = setTimeout(() => connectRef.current(), delay)
      }
    }
  }, [getReconnectDelay, startHealthCheck, stopHealthCheck])
  
  // Keep the connectRef up to date
  useEffect(() => {
    connectRef.current = connect
  }, [connect])

  // Main effect - runs only once on mount
  useEffect(() => {
    isUnmounting.current = false
    cleanupDone.current = false
    
    // Initial connection
    connectRef.current()
    
    // Reconnect on visibility change (tab becomes visible again)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('Tab visible, checking WebSocket connection...')
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          reconnectAttempts.current = 0
          connectRef.current()
        }
      }
    }
    
    // Reconnect on online event
    const handleOnline = () => {
      console.log('Network online, reconnecting WebSocket...')
      reconnectAttempts.current = 0
      connectRef.current()
    }
    
    // Handle browser/tab close - HARD cleanup (kills backend)
    const handleBeforeUnload = () => {
      console.log('[App] Browser/tab closing - triggering hard cleanup')
      performHardCleanup('browser/tab close')
    }
    
    // Handle Tauri window close events
    let unlistenTauriClose: (() => void) | null = null
    if (isTauri) {
      import('@tauri-apps/api/event').then(({ listen }) => {
        // Listen for window close request - HARD cleanup
        listen('tauri://close-requested', async () => {
          console.log('[App] Tauri window close requested - triggering hard cleanup')
          await performHardCleanup('window close')
        }).then(unlisten => {
          unlistenTauriClose = unlisten
        })
        
        // Listen for kill switch from menu - HARD cleanup
        listen('kill-switch', async () => {
          console.log('[App] Kill switch activated - triggering hard cleanup')
          await performHardCleanup('kill switch')
        })
      }).catch(console.error)
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('online', handleOnline)
    window.addEventListener('beforeunload', handleBeforeUnload)
    
    return () => {
      isUnmounting.current = true
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('beforeunload', handleBeforeUnload)
      
      if (unlistenTauriClose) {
        unlistenTauriClose()
      }
      
      // SOFT cleanup on unmount - DON'T kill backend!
      // This can happen during React re-renders or hot reload
      console.log('[App] Component unmounting - soft cleanup only (keeping backend alive)')
      performSoftCleanup()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Empty deps - runs only once, uses refs for latest values

  return (
    <DemoModeProvider>
      <AuthProvider>
        <TradingModeProvider>
          <div className="min-h-screen bg-background">
            <DemoModeBanner />
            <Header 
              connected={connected} 
              wsState={wsState} 
              onSettingsClick={() => setCurrentPage('settings')}
              showSettingsButton={currentPage === 'dashboard'}
            />
            <main className="container mx-auto p-4">
              {currentPage === 'dashboard' ? (
                <Dashboard />
              ) : (
                <SettingsPage onBack={() => setCurrentPage('dashboard')} />
              )}
            </main>
            <AIAssistant />
          </div>
        </TradingModeProvider>
      </AuthProvider>
    </DemoModeProvider>
  )
}

export default App
