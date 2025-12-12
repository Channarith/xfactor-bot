import { useState, useEffect } from 'react'
import { Lock, Unlock, Power, AlertTriangle, Check, X, Eye, EyeOff, Bot } from 'lucide-react'
import { BotManager } from './BotManager'
import { useAuth } from '../context/AuthContext'

interface Feature {
  feature: string
  enabled: boolean
  category: string
  display_name: string
}

interface GroupedFeatures {
  [category: string]: Feature[]
}

export function AdminPanel() {
  const { token, isAuthenticated, login: authLogin, logout: authLogout } = useAuth()
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [features, setFeatures] = useState<GroupedFeatures>({})
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'features' | 'bots'>('features')

  // Fetch features when authenticated
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchFeatures(token)
    }
  }, [isAuthenticated, token])

  const login = async () => {
    setError('')
    setLoading(true)
    
    const success = await authLogin(password)
    
    if (success) {
      setPassword('')
    } else {
      setError('Invalid password')
    }
    
    setLoading(false)
  }

  const logout = async () => {
    await authLogout()
    setFeatures({})
  }

  const fetchFeatures = async (authToken: string) => {
    try {
      const response = await fetch('/api/admin/features', {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      
      const data = await response.json()
      setFeatures(data.grouped || {})
    } catch (e) {
      setError('Failed to load features')
    }
  }

  const toggleFeature = async (feature: string, enabled: boolean) => {
    try {
      const response = await fetch(`/api/admin/features/${feature}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ enabled }),
      })
      
      if (response.ok) {
        // Update local state
        const updatedFeatures = { ...features }
        for (const category in updatedFeatures) {
          updatedFeatures[category] = updatedFeatures[category].map((f) =>
            f.feature === feature ? { ...f, enabled } : f
          )
        }
        setFeatures(updatedFeatures)
      }
    } catch (e) {
      setError('Failed to toggle feature')
    }
  }

  const toggleCategory = async (category: string, enabled: boolean) => {
    const categoryMap: { [key: string]: string } = {
      'Strategies': 'strategies',
      'News Sources': 'news',
      'Risk Management': 'risk',
      'Circuit Breakers': 'circuit_breakers',
      'Analysis': 'analysis',
      'Trading': 'trading',
      'Monitoring': 'monitoring',
    }
    
    const apiCategory = categoryMap[category]
    if (!apiCategory) return
    
    try {
      const response = await fetch(`/api/admin/features/category/${apiCategory}/toggle`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ enabled }),
      })
      
      if (response.ok) {
        fetchFeatures(token)
      }
    } catch (e) {
      setError('Failed to toggle category')
    }
  }

  const emergencyDisableTrading = async () => {
    if (!confirm('Are you sure you want to disable ALL trading features?')) return
    
    try {
      await fetch('/api/admin/emergency/disable-all-trading', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      fetchFeatures(token)
    } catch (e) {
      setError('Failed to disable trading')
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Lock className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">Admin Panel</h2>
        </div>
        
        <p className="text-sm text-muted-foreground mb-4">
          Enter admin password to access feature controls
        </p>
        
        <div className="space-y-3">
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && login()}
              placeholder="Enter password"
              className="w-full rounded-lg bg-input px-4 py-2 pr-10 text-sm"
            />
            <button
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          
          <button
            onClick={login}
            disabled={loading || !password}
            className="w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Unlock className="h-5 w-5 text-profit" />
          <h2 className="text-lg font-semibold">Admin Panel</h2>
        </div>
        <button
          onClick={logout}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Logout
        </button>
      </div>
      
      {/* Tab Selector */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('features')}
          className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'features'
              ? 'bg-primary text-primary-foreground'
              : 'bg-secondary text-muted-foreground hover:text-foreground'
          }`}
        >
          Features
        </button>
        <button
          onClick={() => setActiveTab('bots')}
          className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
            activeTab === 'bots'
              ? 'bg-primary text-primary-foreground'
              : 'bg-secondary text-muted-foreground hover:text-foreground'
          }`}
        >
          <Bot className="h-4 w-4" />
          Bots
        </button>
      </div>
      
      {/* Bot Manager Tab */}
      {activeTab === 'bots' && (
        <BotManager token={token} />
      )}
      
      {/* Features Tab */}
      {activeTab === 'features' && (
        <>
      {/* Emergency Controls */}
      <div className="mb-6 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <span className="text-sm font-medium text-destructive">Emergency Controls</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={emergencyDisableTrading}
            className="flex-1 rounded-lg bg-destructive px-3 py-1.5 text-xs font-medium text-destructive-foreground hover:bg-destructive/90"
          >
            Disable All Trading
          </button>
        </div>
      </div>
      
      {error && (
        <p className="text-sm text-destructive mb-4">{error}</p>
      )}
      
      {/* Feature Categories */}
      <div className="space-y-4 max-h-96 overflow-y-auto">
        {Object.entries(features).map(([category, categoryFeatures]) => (
          <div key={category} className="border border-border/50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">{category}</span>
              <div className="flex gap-1">
                <button
                  onClick={() => toggleCategory(category, true)}
                  className="p-1 rounded bg-profit/20 text-profit hover:bg-profit/30"
                  title="Enable all"
                >
                  <Check className="h-3 w-3" />
                </button>
                <button
                  onClick={() => toggleCategory(category, false)}
                  className="p-1 rounded bg-loss/20 text-loss hover:bg-loss/30"
                  title="Disable all"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            </div>
            <div className="space-y-1">
              {categoryFeatures.map((feature) => (
                <div
                  key={feature.feature}
                  className="flex items-center justify-between py-1"
                >
                  <span className="text-xs text-muted-foreground">
                    {feature.display_name}
                  </span>
                  <button
                    onClick={() => toggleFeature(feature.feature, !feature.enabled)}
                    className={`relative h-5 w-9 rounded-full transition-colors ${
                      feature.enabled ? 'bg-profit' : 'bg-muted'
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                        feature.enabled ? 'left-4' : 'left-0.5'
                      }`}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
        </>
      )}
    </div>
  )
}

