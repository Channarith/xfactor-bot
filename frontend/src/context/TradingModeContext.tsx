import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export type TradingMode = 'demo' | 'paper' | 'live'

// Check if running in MIN/demo mode based on hostname
const isMinMode = (): boolean => {
  const hostname = window.location.hostname
  const envDemoMode = (import.meta as any).env?.VITE_DEMO_MODE === 'true'
  
  // MIN mode hosts
  const isForesight = hostname.includes('foresight.nvidia.com') || hostname.includes('foresight')
  const isNvidiaGitLab = hostname.includes('nvidia.com') || hostname.includes('gitlab-master')
  const isPublicGitLab = hostname.includes('gitlab.io') || hostname.includes('gitlab.com')
  
  // Full feature hosts
  const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1'
  const isGitHub = hostname.includes('github.io') || hostname.includes('github.com')
  const isTauri = (window as any).__TAURI__ !== undefined
  
  if (isLocalhost || isGitHub || isTauri) return false
  return envDemoMode || isForesight || isNvidiaGitLab || isPublicGitLab
}

interface BrokerConfig {
  provider: 'ibkr' | 'alpaca' | 'schwab' | 'tradier' | null
  isConnected: boolean
  accountId?: string
  accountType?: 'paper' | 'live'
  isPaperTrading?: boolean
  buyingPower?: number
  portfolioValue?: number
  simulatedCash?: number  // Initial paper trading balance
  lastSync?: string
}

interface TradingModeContextType {
  mode: TradingMode
  setMode: (mode: TradingMode) => void
  broker: BrokerConfig
  setBroker: (config: BrokerConfig) => void
  canTradeLive: boolean
  connectBroker: (provider: string, credentials: any) => Promise<boolean>
  disconnectBroker: () => void
  refreshBrokerData: () => Promise<void>
}

const TradingModeContext = createContext<TradingModeContextType | null>(null)

export function TradingModeProvider({ children }: { children: ReactNode }) {
  // In MIN mode, default to 'demo' mode; otherwise 'paper'
  const [isMinModeActive] = useState(() => isMinMode())
  const [mode, setModeState] = useState<TradingMode>(isMinModeActive ? 'demo' : 'paper')
  const [broker, setBroker] = useState<BrokerConfig>({
    provider: null,
    isConnected: false,
  })

  // Load saved mode from localStorage
  useEffect(() => {
    const savedMode = localStorage.getItem('xfactor-trading-mode') as TradingMode
    if (savedMode && ['demo', 'paper', 'live'].includes(savedMode)) {
      // In MIN mode, never restore live mode
      if (isMinModeActive) {
        // Only allow demo mode in MIN unless unlocked
        setModeState('demo')
      } else {
        // Don't auto-restore live mode for safety
        setModeState(savedMode === 'live' ? 'paper' : savedMode)
      }
    }
    
    // Check broker connection status (skip in MIN mode)
    if (!isMinModeActive) {
      checkBrokerConnection()
    }
  }, [isMinModeActive])

  const checkBrokerConnection = async () => {
    try {
      const res = await fetch('/api/integrations/broker/status')
      if (res.ok) {
        const data = await res.json()
        if (data.connected) {
          setBroker({
            provider: data.provider,
            isConnected: true,
            accountId: data.account_id,
            accountType: data.account_type,
            buyingPower: data.buying_power,
            portfolioValue: data.portfolio_value,
            lastSync: data.last_sync,
          })
        }
      }
    } catch (e) {
      console.error('Failed to check broker connection:', e)
    }
  }

  const setMode = (newMode: TradingMode) => {
    // In MIN mode, live mode is always disabled
    if (isMinModeActive && newMode === 'live') {
      console.warn('Live mode is disabled in MIN mode')
      return
    }
    
    // Require broker connection for live mode
    if (newMode === 'live' && !broker.isConnected) {
      console.warn('Cannot switch to live mode without broker connection')
      return
    }
    
    setModeState(newMode)
    localStorage.setItem('xfactor-trading-mode', newMode)
  }

  const connectBroker = async (provider: string, credentials: any): Promise<boolean> => {
    try {
      const isPaper = credentials.paper_trading === true
      
      const res = await fetch('/api/integrations/broker/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, ...credentials }),
      })
      
      if (res.ok) {
        const data = await res.json()
        
        // Determine simulated cash based on broker for paper trading
        let simulatedCash = undefined
        if (isPaper) {
          if (provider === 'ibkr') simulatedCash = 1000000  // IBKR provides $1M for paper
          else if (provider === 'alpaca') simulatedCash = 100000  // Alpaca provides $100K
          else simulatedCash = 100000  // Default paper trading balance
        }
        
        setBroker({
          provider: provider as any,
          isConnected: true,
          accountId: data.account_id,
          accountType: isPaper ? 'paper' : 'live',
          isPaperTrading: isPaper,
          buyingPower: data.buying_power ?? simulatedCash,
          portfolioValue: data.portfolio_value ?? simulatedCash,
          simulatedCash,
          lastSync: new Date().toISOString(),
        })
        
        // Auto-set mode based on connection type
        if (isPaper) {
          setModeState('paper')
          localStorage.setItem('xfactor-trading-mode', 'paper')
        }
        
        return true
      }
      return false
    } catch (e) {
      console.error('Failed to connect broker:', e)
      return false
    }
  }

  const disconnectBroker = () => {
    // Switch back to paper mode when disconnecting
    if (mode === 'live') {
      setMode('paper')
    }
    setBroker({ provider: null, isConnected: false })
    fetch('/api/integrations/broker/disconnect', { method: 'POST' }).catch(() => {})
  }

  const refreshBrokerData = async () => {
    await checkBrokerConnection()
  }

  const canTradeLive = broker.isConnected && broker.provider !== null

  return (
    <TradingModeContext.Provider value={{
      mode,
      setMode,
      broker,
      setBroker,
      canTradeLive,
      connectBroker,
      disconnectBroker,
      refreshBrokerData,
    }}>
      {children}
    </TradingModeContext.Provider>
  )
}

export function useTradingMode() {
  const context = useContext(TradingModeContext)
  if (!context) {
    throw new Error('useTradingMode must be used within TradingModeProvider')
  }
  return context
}

