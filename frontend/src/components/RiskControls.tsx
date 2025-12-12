import { useState, useEffect } from 'react'
import { AlertTriangle, RefreshCw, Shield, Pause, Play, Skull } from 'lucide-react'

interface RiskLimits {
  max_position_size: number
  max_portfolio_pct: number
  daily_loss_limit_pct: number
  weekly_loss_limit_pct: number
  max_drawdown_pct: number
  vix_pause_threshold: number
  max_open_positions: number
}

interface RiskStatus {
  trading_allowed: boolean
  paused: boolean
  killed: boolean
  daily_pnl: number
  daily_pnl_pct: number
  current_drawdown_pct: number
  vix: number
  open_positions: number
}

interface RiskControlsProps {
  token?: string
}

export function RiskControls({ token = '' }: RiskControlsProps) {
  const [limits, setLimits] = useState<RiskLimits>({
    max_position_size: 50000,
    max_portfolio_pct: 5,
    daily_loss_limit_pct: 3,
    weekly_loss_limit_pct: 7,
    max_drawdown_pct: 10,
    vix_pause_threshold: 35,
    max_open_positions: 50,
  })
  
  const [status, setStatus] = useState<RiskStatus>({
    trading_allowed: true,
    paused: false,
    killed: false,
    daily_pnl: 0,
    daily_pnl_pct: 0,
    current_drawdown_pct: 0,
    vix: 0,
    open_positions: 0,
  })
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showKillConfirm, setShowKillConfirm] = useState(false)

  const authHeaders = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }

  const fetchRiskData = async () => {
    try {
      const [limitsRes, statusRes] = await Promise.all([
        fetch('/api/risk/limits'),
        fetch('/api/risk/status'),
      ])
      
      if (limitsRes.ok) {
        const limitsData = await limitsRes.json()
        setLimits(limitsData)
      }
      
      if (statusRes.ok) {
        const statusData = await statusRes.json()
        setStatus(statusData)
      }
    } catch (e) {
      console.error('Failed to fetch risk data:', e)
    }
  }

  useEffect(() => {
    fetchRiskData()
    const interval = setInterval(fetchRiskData, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  const pauseTrading = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/risk/pause', {
        method: 'POST',
        headers: authHeaders,
      })
      if (res.ok) {
        setStatus(prev => ({ ...prev, paused: true }))
      } else {
        setError('Failed to pause trading')
      }
    } catch (e) {
      setError('Network error')
    }
    setLoading(false)
  }

  const resumeTrading = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/risk/resume', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ confirmation: 'CONFIRM' }),
      })
      if (res.ok) {
        setStatus(prev => ({ ...prev, paused: false }))
      } else {
        setError('Failed to resume trading')
      }
    } catch (e) {
      setError('Network error')
    }
    setLoading(false)
  }

  const activateKillSwitch = async (closePositions: boolean) => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/risk/kill-switch', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ 
          reason: 'Manual activation via UI',
          close_positions: closePositions,
        }),
      })
      if (res.ok) {
        setStatus(prev => ({ ...prev, killed: true, trading_allowed: false }))
        setShowKillConfirm(false)
      } else {
        setError('Failed to activate kill switch')
      }
    } catch (e) {
      setError('Network error')
    }
    setLoading(false)
  }

  const resetKillSwitch = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/risk/kill-switch/reset', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ confirmation: 'CONFIRM_DEACTIVATE' }),
      })
      if (res.ok) {
        setStatus(prev => ({ ...prev, killed: false, trading_allowed: true }))
      } else {
        setError('Failed to reset kill switch')
      }
    } catch (e) {
      setError('Network error')
    }
    setLoading(false)
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value)
  }

  return (
    <div className="space-y-4">
      {/* Status Banner */}
      <div className={`rounded-lg p-3 flex items-center justify-between ${
        status.killed ? 'bg-loss/20 border border-loss' :
        status.paused ? 'bg-yellow-500/20 border border-yellow-500' :
        'bg-profit/20 border border-profit'
      }`}>
        <div className="flex items-center gap-2">
          <Shield className={`h-5 w-5 ${
            status.killed ? 'text-loss' : status.paused ? 'text-yellow-500' : 'text-profit'
          }`} />
          <div>
            <div className={`font-medium ${
              status.killed ? 'text-loss' : status.paused ? 'text-yellow-500' : 'text-profit'
            }`}>
              {status.killed ? 'KILL SWITCH ACTIVE' : status.paused ? 'Trading Paused' : 'Trading Active'}
            </div>
            <div className="text-xs text-muted-foreground">
              {status.open_positions} open positions • VIX: {status.vix.toFixed(1)}
            </div>
          </div>
        </div>
        <button onClick={fetchRiskData} className="p-1 hover:bg-secondary rounded">
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {error && (
        <div className="p-2 rounded bg-loss/20 text-loss text-sm">{error}</div>
      )}

      {/* Risk Limits */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Risk Limits</h3>
        
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-secondary/50">
            <div className="text-xs text-muted-foreground">Max Position Size</div>
            <div className="text-lg font-semibold">{formatCurrency(limits.max_position_size)}</div>
          </div>
          <div className="p-3 rounded-lg bg-secondary/50">
            <div className="text-xs text-muted-foreground">Max Open Positions</div>
            <div className="text-lg font-semibold">{limits.max_open_positions}</div>
          </div>
          <div className="p-3 rounded-lg bg-secondary/50">
            <div className="text-xs text-muted-foreground">Daily Loss Limit</div>
            <div className="text-lg font-semibold text-loss">-{limits.daily_loss_limit_pct}%</div>
          </div>
          <div className="p-3 rounded-lg bg-secondary/50">
            <div className="text-xs text-muted-foreground">Max Drawdown</div>
            <div className="text-lg font-semibold text-loss">-{limits.max_drawdown_pct}%</div>
          </div>
          <div className="p-3 rounded-lg bg-secondary/50">
            <div className="text-xs text-muted-foreground">Weekly Loss Limit</div>
            <div className="text-lg font-semibold text-loss">-{limits.weekly_loss_limit_pct}%</div>
          </div>
          <div className="p-3 rounded-lg bg-secondary/50">
            <div className="text-xs text-muted-foreground">VIX Pause Threshold</div>
            <div className="text-lg font-semibold">{limits.vix_pause_threshold}</div>
          </div>
        </div>
      </div>

      {/* Current Risk Metrics */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Current Status</h3>
        
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 rounded-lg bg-secondary/50 text-center">
            <div className="text-xs text-muted-foreground">Daily P&L</div>
            <div className={`text-lg font-semibold ${status.daily_pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
              {status.daily_pnl >= 0 ? '+' : ''}{formatCurrency(status.daily_pnl)}
            </div>
            <div className={`text-xs ${status.daily_pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
              ({status.daily_pnl_pct >= 0 ? '+' : ''}{status.daily_pnl_pct.toFixed(2)}%)
            </div>
          </div>
          <div className="p-3 rounded-lg bg-secondary/50 text-center">
            <div className="text-xs text-muted-foreground">Current Drawdown</div>
            <div className="text-lg font-semibold text-loss">
              -{status.current_drawdown_pct.toFixed(1)}%
            </div>
          </div>
          <div className="p-3 rounded-lg bg-secondary/50 text-center">
            <div className="text-xs text-muted-foreground">VIX Level</div>
            <div className={`text-lg font-semibold ${status.vix > limits.vix_pause_threshold ? 'text-loss' : 'text-foreground'}`}>
              {status.vix.toFixed(1)}
            </div>
          </div>
        </div>
      </div>

      {/* Control Buttons */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Controls</h3>
        
        <div className="flex gap-2">
          {status.paused ? (
            <button
              onClick={resumeTrading}
              disabled={loading || status.killed}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-profit text-white hover:bg-profit/80 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              Resume Trading
            </button>
          ) : (
            <button
              onClick={pauseTrading}
              disabled={loading || status.killed}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-yellow-500 text-white hover:bg-yellow-500/80 disabled:opacity-50"
            >
              <Pause className="h-4 w-4" />
              Pause Trading
            </button>
          )}
        </div>

        {/* Kill Switch */}
        {status.killed ? (
          <button
            onClick={resetKillSwitch}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-secondary border border-border hover:bg-secondary/80"
          >
            <Shield className="h-4 w-4" />
            Reset Kill Switch
          </button>
        ) : showKillConfirm ? (
          <div className="p-4 rounded-lg bg-loss/20 border border-loss space-y-3">
            <div className="flex items-center gap-2 text-loss">
              <AlertTriangle className="h-5 w-5" />
              <span className="font-medium">Confirm Kill Switch Activation</span>
            </div>
            <p className="text-sm text-muted-foreground">
              This will immediately stop all trading activity.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => activateKillSwitch(false)}
                disabled={loading}
                className="flex-1 px-3 py-2 rounded-lg bg-loss text-white hover:bg-loss/80 text-sm"
              >
                Stop Trading Only
              </button>
              <button
                onClick={() => activateKillSwitch(true)}
                disabled={loading}
                className="flex-1 px-3 py-2 rounded-lg bg-loss text-white hover:bg-loss/80 text-sm"
              >
                Stop & Close Positions
              </button>
            </div>
            <button
              onClick={() => setShowKillConfirm(false)}
              className="w-full px-3 py-2 rounded-lg bg-secondary text-sm"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowKillConfirm(true)}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-loss/20 border border-loss text-loss hover:bg-loss/30"
          >
            <Skull className="h-4 w-4" />
            Kill Switch (Emergency Stop)
          </button>
        )}
      </div>
    </div>
  )
}
