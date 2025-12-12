import { useEffect, useState } from 'react'
import { Dashboard } from './components/Dashboard'
import { Header } from './components/Header'
import { AIAssistant } from './components/AIAssistant'
import { AuthProvider } from './context/AuthContext'

function App() {
  const [connected, setConnected] = useState(false)
  const [ws, setWs] = useState<WebSocket | null>(null)

  useEffect(() => {
    // Determine WebSocket URL based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`
    
    let websocket: WebSocket | null = null
    let reconnectTimeout: NodeJS.Timeout | null = null
    
    const connect = () => {
      try {
        websocket = new WebSocket(wsUrl)
        
        websocket.onopen = () => {
          console.log('WebSocket connected')
          setConnected(true)
          // Subscribe to updates
          websocket?.send(JSON.stringify({ type: 'subscribe', channel: 'portfolio' }))
          websocket?.send(JSON.stringify({ type: 'subscribe', channel: 'orders' }))
          websocket?.send(JSON.stringify({ type: 'subscribe', channel: 'news' }))
        }
        
        websocket.onclose = () => {
          console.log('WebSocket disconnected')
          setConnected(false)
          // Attempt reconnect after 5 seconds
          reconnectTimeout = setTimeout(connect, 5000)
        }
        
        websocket.onerror = (error) => {
          console.error('WebSocket error:', error)
        }
        
        websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            console.log('WebSocket message:', data)
            // Handle updates
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e)
          }
        }
        
        setWs(websocket)
      } catch (e) {
        console.error('Failed to create WebSocket:', e)
        // Attempt reconnect after 5 seconds
        reconnectTimeout = setTimeout(connect, 5000)
      }
    }
    
    connect()
    
    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
      }
      if (websocket) {
        websocket.close()
      }
    }
  }, [])

  return (
    <AuthProvider>
      <div className="min-h-screen bg-background">
        <Header connected={connected} />
        <main className="container mx-auto p-4">
          <Dashboard />
        </main>
        <AIAssistant />
      </div>
    </AuthProvider>
  )
}

export default App
