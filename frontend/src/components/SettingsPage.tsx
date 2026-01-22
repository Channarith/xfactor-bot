import { useState, useEffect } from 'react'
import { Settings, Shield, Lock, Wallet, DollarSign, ArrowLeft, Moon, Cpu, Clock } from 'lucide-react'
import { StrategyPanel } from './StrategyPanel'
import { RiskControls } from './RiskControls'
import { AdminPanel } from './AdminPanel'
import { IntegrationsPanel } from './IntegrationsPanel'
import { FeeTracker } from './FeeTracker'
import { CollapsiblePanel } from './CollapsiblePanel'
import { getApiBaseUrl } from '../config/api'

interface SettingsPageProps {
  onBack: () => void
}

interface MarketHoursStatus {
  current_time_et: string
  is_market_day: boolean
  is_market_open: boolean
  is_active_window: boolean
  is_quiet_mode: boolean
  quiet_mode_enabled: boolean
  active_window_start: string
  active_window_end: string
  poll_interval_seconds: number
  next_active_start: string | null
}

export function SettingsPage({ onBack }: SettingsPageProps) {
  const [marketHoursStatus, setMarketHoursStatus] = useState<MarketHoursStatus | null>(null)
  const [quietModeEnabled, setQuietModeEnabled] = useState(true)
  const [isUpdating, setIsUpdating] = useState(false)
  
  // Fetch market hours status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const baseUrl = getApiBaseUrl()
        const res = await fetch(`${baseUrl}/api/market/hours`)
        if (res.ok) {
          const data = await res.json()
          setMarketHoursStatus(data)
          setQuietModeEnabled(data.quiet_mode_enabled)
        }
      } catch (e) {
        console.error('Failed to fetch market hours status:', e)
      }
    }
    
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000) // Update every 30s
    return () => clearInterval(interval)
  }, [])
  
  // Toggle quiet mode
  const handleQuietModeToggle = async () => {
    setIsUpdating(true)
    try {
      const baseUrl = getApiBaseUrl()
      const newValue = !quietModeEnabled
      const res = await fetch(`${baseUrl}/api/market/hours/quiet-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: newValue }),
      })
      
      if (res.ok) {
        setQuietModeEnabled(newValue)
        // Refresh status
        const statusRes = await fetch(`${baseUrl}/api/market/hours`)
        if (statusRes.ok) {
          setMarketHoursStatus(await statusRes.json())
        }
      }
    } catch (e) {
      console.error('Failed to toggle quiet mode:', e)
    }
    setIsUpdating(false)
  }
  return (
    <div className="space-y-6">
      {/* Header with Back Button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Dashboard</span>
          </button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Settings className="h-6 w-6 text-teal-400" />
              Settings & Configuration
            </h1>
            <p className="text-sm text-muted-foreground">
              Manage strategies, risk controls, integrations, and administrative settings
            </p>
          </div>
        </div>
      </div>

      {/* Settings Panels Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          <CollapsiblePanel
            title="Strategy Controls"
            icon={<Settings className="h-5 w-5" />}
            defaultExpanded={true}
          >
            <StrategyPanel />
          </CollapsiblePanel>

          <CollapsiblePanel
            title="Risk Management"
            icon={<Shield className="h-5 w-5" />}
            defaultExpanded={true}
          >
            <RiskControls />
          </CollapsiblePanel>

          <CollapsiblePanel
            title="Fees & Expenses"
            icon={<DollarSign className="h-5 w-5" />}
            badge="costs"
            defaultExpanded={false}
          >
            <FeeTracker />
          </CollapsiblePanel>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* System Settings - Quiet Mode Toggle */}
          <CollapsiblePanel
            title="System Settings"
            icon={<Cpu className="h-5 w-5" />}
            defaultExpanded={true}
          >
            <div className="space-y-4">
              {/* Quiet Mode Toggle */}
              <div className="p-4 rounded-lg bg-secondary/50 border border-border">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${quietModeEnabled ? 'bg-indigo-500/20' : 'bg-orange-500/20'}`}>
                      <Moon className={`h-5 w-5 ${quietModeEnabled ? 'text-indigo-400' : 'text-orange-400'}`} />
                    </div>
                    <div>
                      <h3 className="font-medium">Quiet Mode (Off-Hours)</h3>
                      <p className="text-sm text-muted-foreground">
                        Reduce polling and analytics outside trading hours
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleQuietModeToggle}
                    disabled={isUpdating}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      quietModeEnabled ? 'bg-indigo-500' : 'bg-gray-600'
                    } ${isUpdating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        quietModeEnabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
                
                {/* Status Info */}
                <div className="mt-3 pt-3 border-t border-border/50 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-muted-foreground">Status: </span>
                    <span className={marketHoursStatus?.is_quiet_mode ? 'text-indigo-400' : 'text-green-400'}>
                      {marketHoursStatus?.is_quiet_mode ? '🌙 Quiet Mode' : '🟢 Active Mode'}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Market: </span>
                    <span className={marketHoursStatus?.is_market_open ? 'text-green-400' : 'text-muted-foreground'}>
                      {marketHoursStatus?.is_market_open ? 'Open' : 'Closed'}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Poll Interval: </span>
                    <span>{marketHoursStatus?.poll_interval_seconds || 30}s</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Time (ET): </span>
                    <span className="font-mono text-xs">
                      {marketHoursStatus?.current_time_et?.split(' ')[1] || '--:--:--'}
                    </span>
                  </div>
                </div>
                
                {/* Description */}
                <div className="mt-3 p-2 rounded bg-background/50 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3 inline mr-1" />
                  Active window: {marketHoursStatus?.active_window_start || '08:50:00'} - {marketHoursStatus?.active_window_end || '16:40:00'} ET
                  <br />
                  {quietModeEnabled 
                    ? 'During off-hours, polling is reduced to 5 minutes to save resources.'
                    : 'System runs at full speed 24/7 (higher CPU/network usage).'
                  }
                </div>
              </div>
            </div>
          </CollapsiblePanel>
          
          <CollapsiblePanel
            title="Admin Panel"
            icon={<Lock className="h-5 w-5" />}
            defaultExpanded={true}
          >
            <AdminPanel />
          </CollapsiblePanel>

          <CollapsiblePanel
            title="Integrations"
            icon={<Wallet className="h-5 w-5" />}
            defaultExpanded={true}
          >
            <IntegrationsPanel />
          </CollapsiblePanel>
        </div>
      </div>
    </div>
  )
}

