import { useState } from 'react'
import { Pause, Power, Play, Lock, ShieldAlert, HelpCircle, Sparkles, Shield, X } from 'lucide-react'
import { TradingModeSelector } from './TradingModeSelector'
import { useAuth } from '../context/AuthContext'
import { useDemoMode } from '../contexts/DemoModeContext'
import HelpModal from './HelpModal'
import UnlockModal from './UnlockModal'

type WSState = 'connecting' | 'connected' | 'disconnected' | 'error'

interface HeaderProps {
  connected: boolean
  wsState?: WSState
}

export function Header({ connected, wsState = 'disconnected' }: HeaderProps) {
  const { isAuthenticated, token } = useAuth()
  const { edition, isDemoMode, isUnlocked, incrementEasterEgg, showUnlockPrompt, setShowUnlockPrompt, easterEggClicks } = useDemoMode()
  const [logoError, setLogoError] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [showHelpModal, setShowHelpModal] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Handle easter egg click on MIN badge
  const handleMinBadgeClick = () => {
    if (edition === 'XFactor-botMin' && !isUnlocked) {
      incrementEasterEgg()
    }
  }

  const handlePauseResume = async () => {
    if (!isAuthenticated) {
      setShowAuthModal(true)
      return
    }
    
    setActionLoading('pause')
    try {
      const endpoint = isPaused ? '/api/risk/resume' : '/api/risk/pause'
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        setIsPaused(!isPaused)
      }
    } catch (e) {
      console.error('Failed to pause/resume:', e)
    }
    setActionLoading(null)
  }

  const handleKillSwitch = async () => {
    if (!isAuthenticated) {
      setShowAuthModal(true)
      return
    }
    
    if (!confirm('⚠️ KILL SWITCH: This will immediately stop ALL trading activity and close pending orders. Are you sure?')) {
      return
    }
    
    setActionLoading('kill')
    try {
      const res = await fetch('/api/risk/kill-switch', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        setIsPaused(true)
      }
    } catch (e) {
      console.error('Failed to activate kill switch:', e)
    }
    setActionLoading(null)
  }

  return (
    <>
      <header className="border-b border-border bg-card px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* XFactor Bot Logo */}
            {!logoError ? (
              <img 
                src="/assets/xfactor-logo.png" 
                alt="XFactor Bot" 
                className="h-12 w-auto"
                onError={() => setLogoError(true)}
              />
            ) : (
              <div className="h-12 w-12 bg-xfactor-slate rounded-lg flex items-center justify-center border border-xfactor-teal/30">
                <span className="text-2xl font-bold text-xfactor-teal">X</span>
              </div>
            )}
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold xfactor-title tracking-wide">
                  THE XFACTOR BOT
                </h1>
                {/* Edition Badge - MIN badge is clickable for easter egg */}
                <span 
                  onClick={handleMinBadgeClick}
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 select-none ${
                    edition === 'XFactor-botMax' 
                      ? 'bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-400 border border-emerald-500/30'
                      : isDemoMode && !isUnlocked
                        ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 cursor-pointer hover:bg-yellow-500/30 transition-colors'
                        : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  }`}
                  title={edition === 'XFactor-botMin' && !isUnlocked ? 
                    (easterEggClicks > 0 ? `${7 - easterEggClicks} more...` : 'Click to explore') : 
                    undefined
                  }
                >
                  {edition === 'XFactor-botMax' ? (
                    <><Sparkles className="h-3 w-3" /> MAX</>
                  ) : isUnlocked ? (
                    <><Sparkles className="h-3 w-3" /> MIN+</>
                  ) : (
                    <><Shield className="h-3 w-3" /> MIN</>
                  )}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                AI-Powered Trading System {edition === 'XFactor-botMax' ? '• Full Features' : '• Restricted Mode'}
              </span>
            </div>
            
            {/* Trading Mode Selector */}
            <TradingModeSelector />
          </div>
          
          <div className="flex items-center gap-6">
          {/* Connection Status */}
          <div className="flex items-center gap-2">
            <div className={`h-2.5 w-2.5 rounded-full ${
              wsState === 'connected' ? 'bg-profit money-glow' : 
              wsState === 'connecting' ? 'bg-amber-500 animate-pulse' :
              wsState === 'error' ? 'bg-loss animate-pulse' :
              'bg-muted-foreground'
            }`} />
            <span className="text-sm text-muted-foreground">
              {wsState === 'connected' ? 'Connected' : 
               wsState === 'connecting' ? 'Connecting...' :
               wsState === 'error' ? 'Connection Error' :
               'Disconnected'}
            </span>
          </div>
            
            {/* Trading Controls */}
            <div className="flex items-center gap-2">
              <button 
                onClick={handlePauseResume}
                disabled={actionLoading === 'pause'}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm border transition-all ${
                  isPaused 
                    ? 'bg-profit/20 text-profit border-profit/30 hover:bg-profit/30' 
                    : 'bg-secondary border-border hover:bg-secondary/80 hover:border-xfactor-teal'
                }`}
              >
                {isPaused ? (
                  <>
                    <Play className="h-4 w-4" />
                    Resume
                  </>
                ) : (
                  <>
                    <Pause className="h-4 w-4" />
                    Pause
                  </>
                )}
              </button>
              <button 
                onClick={handleKillSwitch}
                disabled={actionLoading === 'kill'}
                className="flex items-center gap-2 rounded-lg bg-destructive px-4 py-2 text-sm text-destructive-foreground hover:bg-destructive/80 transition-all"
              >
                <Power className="h-4 w-4" />
                Kill Switch
              </button>
              
              {/* Help Button */}
              <button 
                onClick={() => setShowHelpModal(true)}
                className="flex items-center gap-2 rounded-lg bg-blue-500/20 border border-blue-500/30 px-4 py-2 text-sm text-blue-400 hover:bg-blue-500/30 hover:text-blue-300 transition-all"
                title="Help & Documentation"
              >
                <HelpCircle className="h-4 w-4" />
                Help
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Auth Required Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-card rounded-xl border border-amber-500/50 max-w-md w-full shadow-2xl shadow-amber-500/10 animate-in fade-in zoom-in duration-200">
            {/* Modal Header */}
            <div className="flex items-center gap-3 p-5 border-b border-border bg-gradient-to-r from-amber-500/10 to-orange-500/10 rounded-t-xl">
              <div className="p-3 rounded-full bg-amber-500/20">
                <ShieldAlert className="h-6 w-6 text-amber-500" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-foreground">Admin Access Required</h2>
                <p className="text-sm text-muted-foreground">Authentication needed for trading controls</p>
              </div>
            </div>
            
            {/* Modal Body */}
            <div className="p-5 space-y-4">
              <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-500/5 border border-amber-500/20">
                <Lock className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <p className="text-foreground font-medium mb-1">
                    Trading controls require admin privileges
                  </p>
                  <p className="text-muted-foreground">
                    The <strong>Pause</strong>, <strong>Resume</strong>, and <strong>Kill Switch</strong> buttons 
                    control live trading activity. To use these features, you must first unlock admin access.
                  </p>
                </div>
              </div>
              
              <div className="text-sm text-muted-foreground">
                <p className="font-medium text-foreground mb-2">How to unlock:</p>
                <ol className="list-decimal list-inside space-y-1 ml-1">
                  <li>Scroll down to the <strong>Admin Panel</strong> section</li>
                  <li>Enter your admin password</li>
                  <li>Click <strong>Login</strong></li>
                  <li>Return here and try again</li>
                </ol>
              </div>
            </div>
            
            {/* Modal Footer */}
            <div className="flex justify-end gap-3 p-4 border-t border-border bg-secondary/30 rounded-b-xl">
              <button
                onClick={() => setShowAuthModal(false)}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Help Modal */}
      <HelpModal isOpen={showHelpModal} onClose={() => setShowHelpModal(false)} />

      {/* Unlock Modal for Easter Egg */}
      <UnlockModal isOpen={showUnlockPrompt} onClose={() => setShowUnlockPrompt(false)} />
    </>
  )
}
