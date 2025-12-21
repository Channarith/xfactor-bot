import { useState } from 'react'
import { 
  TestTube2, Wallet, AlertTriangle, CheckCircle, 
  ChevronDown, Shield, Zap, X, ExternalLink, Lock
} from 'lucide-react'
import { useTradingMode, TradingMode } from '../context/TradingModeContext'
import { useDemoMode, useFeatureAvailable } from '../contexts/DemoModeContext'

export function TradingModeSelector() {
  const { mode, setMode, broker, canTradeLive } = useTradingMode()
  const { isDemoMode, isUnlocked, edition } = useDemoMode()
  const { canTrade } = useFeatureAvailable()
  const [showDropdown, setShowDropdown] = useState(false)
  const [showLiveWarning, setShowLiveWarning] = useState(false)
  const [pendingMode, setPendingMode] = useState<TradingMode | null>(null)
  
  // In MIN mode without unlock, Live mode is disabled
  const isLiveLockedByMIN = isDemoMode && !isUnlocked

  const getModeInfo = (m: TradingMode) => {
    switch (m) {
      case 'demo':
        return {
          label: 'Demo',
          icon: <TestTube2 className="h-4 w-4" />,
          color: 'text-blue-400',
          bg: 'bg-blue-500/20',
          border: 'border-blue-500/30',
          description: 'Simulated data for UI testing',
        }
      case 'paper':
        return {
          label: 'Paper',
          icon: <Shield className="h-4 w-4" />,
          color: 'text-amber-400',
          bg: 'bg-amber-500/20',
          border: 'border-amber-500/30',
          description: broker.isPaperTrading 
            ? `${broker.provider?.toUpperCase()} paper: $${(broker.simulatedCash || 100000).toLocaleString()}`
            : 'Live market data, simulated trades',
        }
      case 'live':
        return {
          label: 'LIVE',
          icon: <Zap className="h-4 w-4" />,
          color: 'text-profit',
          bg: 'bg-profit/20',
          border: 'border-profit/30',
          description: 'Real money trading',
        }
    }
  }

  const currentMode = getModeInfo(mode)

  const handleModeChange = (newMode: TradingMode) => {
    if (newMode === 'live') {
      // Block live mode in MIN unless unlocked
      if (isLiveLockedByMIN) {
        return
      }
      if (!canTradeLive) {
        // Can't switch to live without broker
        return
      }
      // Show warning for live mode
      setPendingMode('live')
      setShowLiveWarning(true)
      setShowDropdown(false)
      return
    }
    
    setMode(newMode)
    setShowDropdown(false)
  }

  const confirmLiveMode = () => {
    if (pendingMode === 'live') {
      setMode('live')
    }
    setShowLiveWarning(false)
    setPendingMode(null)
  }

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${currentMode.bg} ${currentMode.border} border transition-all hover:opacity-80`}
        >
          <span className={currentMode.color}>{currentMode.icon}</span>
          <span className={`text-sm font-medium ${currentMode.color}`}>
            {currentMode.label}
          </span>
          <ChevronDown className={`h-3 w-3 ${currentMode.color} transition-transform ${showDropdown ? 'rotate-180' : ''}`} />
        </button>

        {showDropdown && (
          <>
            <div 
              className="fixed inset-0 z-40" 
              onClick={() => setShowDropdown(false)} 
            />
            <div className="absolute top-full mt-2 right-0 w-64 bg-card border border-border rounded-lg shadow-xl z-50 overflow-hidden">
              <div className="p-2 border-b border-border bg-secondary/50">
                <div className="text-xs text-muted-foreground">Trading Mode</div>
              </div>
              
              {(['demo', 'paper', 'live'] as TradingMode[]).map((m) => {
                const info = getModeInfo(m)
                // Disable live if: MIN mode without unlock, or no broker connected
                const isDisabledByMIN = m === 'live' && isLiveLockedByMIN
                const isDisabledByBroker = m === 'live' && !canTradeLive
                const isDisabled = isDisabledByMIN || isDisabledByBroker
                const isActive = mode === m
                
                return (
                  <button
                    key={m}
                    onClick={() => handleModeChange(m)}
                    disabled={isDisabled}
                    className={`w-full flex items-start gap-3 p-3 text-left transition-colors ${
                      isActive ? info.bg : 'hover:bg-secondary/50'
                    } ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <span className={`mt-0.5 ${info.color}`}>
                      {isDisabledByMIN ? <Lock className="h-4 w-4 text-amber-500" /> : info.icon}
                    </span>
                    <div className="flex-1">
                      <div className={`font-medium ${isActive ? info.color : ''}`}>
                        {info.label}
                        {isActive && <CheckCircle className="h-3 w-3 inline ml-2" />}
                        {isDisabledByMIN && <Lock className="h-3 w-3 inline ml-2 text-amber-500" />}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {info.description}
                      </div>
                      {m === 'live' && isDisabledByMIN && (
                        <div className="text-xs text-amber-400 mt-1 flex items-center gap-1">
                          <Lock className="h-3 w-3" />
                          MIN mode: Unlock required for Live trading
                        </div>
                      )}
                      {m === 'live' && !isDisabledByMIN && !canTradeLive && (
                        <div className="text-xs text-loss mt-1">
                          Connect broker in Admin panel first
                        </div>
                      )}
                    </div>
                  </button>
                )
              })}
              
              {broker.isConnected && (
                <div className="p-3 border-t border-border bg-secondary/30">
                  <div className="flex items-center gap-2 text-xs">
                    <CheckCircle className="h-3 w-3 text-profit" />
                    <span className="text-muted-foreground">
                      Connected: <span className="text-foreground font-medium">{broker.provider?.toUpperCase()}</span>
                      {broker.isPaperTrading && (
                        <span className="ml-1 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 text-[10px]">PAPER</span>
                      )}
                    </span>
                  </div>
                  {broker.accountId && (
                    <div className="text-xs text-muted-foreground mt-1">
                      Account: {broker.accountId}
                    </div>
                  )}
                  {broker.isPaperTrading && broker.simulatedCash && (
                    <div className="text-xs text-amber-400 mt-1">
                      Simulated: ${broker.simulatedCash.toLocaleString()} paper trading
                    </div>
                  )}
                  {broker.buyingPower && (
                    <div className="text-xs text-muted-foreground mt-1">
                      Buying Power: <span className="text-profit font-medium">${broker.buyingPower.toLocaleString()}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Live Mode Warning Modal */}
      {showLiveWarning && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-card rounded-xl border-2 border-loss/50 max-w-md w-full shadow-2xl animate-in fade-in zoom-in duration-200">
            {/* Header */}
            <div className="flex items-center gap-3 p-5 border-b border-border bg-loss/10 rounded-t-xl">
              <div className="p-3 rounded-full bg-loss/20">
                <AlertTriangle className="h-6 w-6 text-loss" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-loss">⚠️ LIVE TRADING MODE</h2>
                <p className="text-sm text-muted-foreground">Real money will be used</p>
              </div>
              <button
                onClick={() => setShowLiveWarning(false)}
                className="ml-auto p-2 rounded hover:bg-secondary"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            {/* Body */}
            <div className="p-5 space-y-4">
              <div className="p-4 rounded-lg bg-loss/5 border border-loss/20">
                <p className="text-sm text-foreground font-medium mb-2">
                  You are about to enable LIVE trading mode.
                </p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• All bot trades will execute with <strong className="text-loss">real money</strong></li>
                  <li>• Orders will be sent to your {broker.provider?.toUpperCase()} account</li>
                  <li>• You can lose money - trading involves significant risk</li>
                  <li>• Ensure your risk settings are properly configured</li>
                </ul>
              </div>
              
              {broker.portfolioValue && (
                <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/50">
                  <span className="text-sm text-muted-foreground">Account Value:</span>
                  <span className="font-bold text-lg">
                    ${broker.portfolioValue.toLocaleString()}
                  </span>
                </div>
              )}
              
              <div className="text-xs text-muted-foreground">
                By clicking "Enable Live Trading", you acknowledge that you understand the risks 
                involved and accept full responsibility for any trading losses.
              </div>
            </div>
            
            {/* Footer */}
            <div className="flex gap-3 p-4 border-t border-border bg-secondary/30 rounded-b-xl">
              <button
                onClick={() => setShowLiveWarning(false)}
                className="flex-1 px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-sm transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmLiveMode}
                className="flex-1 px-4 py-2 rounded-lg bg-loss text-white font-medium hover:bg-loss/90 text-sm transition-colors flex items-center justify-center gap-2"
              >
                <Zap className="h-4 w-4" />
                Enable Live Trading
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

