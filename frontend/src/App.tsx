import { useEffect, useState } from 'react'
import { Dashboard } from './components/Dashboard'
import { Header } from './components/Header'

function App() {
  const [connected, setConnected] = useState(false)
  const [ws, setWs] = useState<WebSocket | null>(null)

  useEffect(() => {
    // Connect to WebSocket
    const websocket = new WebSocket('ws://localhost:8000/ws')
    
    websocket.onopen = () => {
      console.log('WebSocket connected')
      setConnected(true)
      // Subscribe to updates
      websocket.send(JSON.stringify({ type: 'subscribe', channel: 'portfolio' }))
      websocket.send(JSON.stringify({ type: 'subscribe', channel: 'orders' }))
      websocket.send(JSON.stringify({ type: 'subscribe', channel: 'news' }))
    }
    
    websocket.onclose = () => {
      console.log('WebSocket disconnected')
      setConnected(false)
    }
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('WebSocket message:', data)
      // Handle updates
    }
    
    setWs(websocket)
    
    return () => {
      websocket.close()
    }
  }, [])

  return (
    <div className="min-h-screen bg-background">
      <Header connected={connected} />
      <main className="container mx-auto p-4">
        <Dashboard />
      </main>
    </div>
  )
}

export default App

