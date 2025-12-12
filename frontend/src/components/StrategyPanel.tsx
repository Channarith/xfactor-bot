import { useState } from 'react'
import { 
  ChevronDown, ChevronUp, TrendingUp, Brain, BarChart3, 
  Activity, Users, Building2, LineChart, Zap, Target,
  Gauge, Clock, Shield, Sparkles, Waves, Calculator
} from 'lucide-react'

// ============================================================================
// Types
// ============================================================================

interface StrategyToggle {
  id: string
  name: string
  description: string
  enabled: boolean
  category: string
  icon: React.ReactNode
}

interface StrategySlider {
  id: string
  name: string
  description: string
  value: number
  min: number
  max: number
  step: number
  unit: string
  category: string
}

interface StrategySelect {
  id: string
  name: string
  description: string
  value: string
  options: { value: string; label: string }[]
  category: string
}

type CategoryName = 'technical' | 'momentum' | 'sentiment' | 'ai' | 'social' | 'risk'

// ============================================================================
// Initial Strategy Configuration
// ============================================================================

const initialToggles: StrategyToggle[] = [
  // Technical Analysis
  { id: 'technical_enabled', name: 'Technical Analysis', description: 'RSI, MACD, Bollinger Bands', enabled: true, category: 'technical', icon: <LineChart className="h-4 w-4" /> },
  { id: 'moving_averages', name: 'Moving Averages', description: 'SMA/EMA crossovers and trends', enabled: true, category: 'technical', icon: <Waves className="h-4 w-4" /> },
  { id: 'fibonacci_retracement', name: 'Fibonacci Retracement', description: 'Key support/resistance levels', enabled: true, category: 'technical', icon: <Calculator className="h-4 w-4" /> },
  { id: 'volume_analysis', name: 'Volume Analysis', description: 'Volume spikes and divergences', enabled: true, category: 'technical', icon: <BarChart3 className="h-4 w-4" /> },
  
  // Momentum
  { id: 'momentum_enabled', name: 'Momentum Strategy', description: 'Price momentum and acceleration', enabled: true, category: 'momentum', icon: <TrendingUp className="h-4 w-4" /> },
  { id: 'mean_reversion', name: 'Mean Reversion', description: 'Fade extreme moves to mean', enabled: true, category: 'momentum', icon: <Activity className="h-4 w-4" /> },
  { id: 'breakout_detection', name: 'Breakout Detection', description: 'Identify and trade breakouts', enabled: true, category: 'momentum', icon: <Zap className="h-4 w-4" /> },
  
  // Sentiment & News
  { id: 'news_sentiment', name: 'News Sentiment', description: 'NLP-based news analysis', enabled: true, category: 'sentiment', icon: <Sparkles className="h-4 w-4" /> },
  { id: 'social_sentiment', name: 'Social Media Sentiment', description: 'Twitter/Reddit analysis', enabled: true, category: 'sentiment', icon: <Users className="h-4 w-4" /> },
  { id: 'earnings_plays', name: 'Earnings Catalyst', description: 'Pre/post earnings strategies', enabled: false, category: 'sentiment', icon: <Target className="h-4 w-4" /> },
  
  // AI & Machine Learning
  { id: 'ai_predictions', name: 'AI Price Predictions', description: 'GPT-4 & ML model forecasts', enabled: true, category: 'ai', icon: <Brain className="h-4 w-4" /> },
  { id: 'pattern_recognition', name: 'Pattern Recognition', description: 'CNN-based chart patterns', enabled: true, category: 'ai', icon: <Gauge className="h-4 w-4" /> },
  { id: 'anomaly_detection', name: 'Anomaly Detection', description: 'Unusual activity alerts', enabled: true, category: 'ai', icon: <Shield className="h-4 w-4" /> },
  
  // Social Trading
  { id: 'follow_insiders', name: 'Follow Insider Trades', description: 'Mirror SEC Form 4 filings', enabled: true, category: 'social', icon: <Building2 className="h-4 w-4" /> },
  { id: 'follow_top_traders', name: 'Follow Top Traders', description: 'Copy high win-rate traders', enabled: false, category: 'social', icon: <Users className="h-4 w-4" /> },
  { id: 'options_flow', name: 'Options Flow', description: 'Unusual options activity', enabled: true, category: 'social', icon: <Activity className="h-4 w-4" /> },
]

const initialSliders: StrategySlider[] = [
  // Technical Parameters
  { id: 'rsi_oversold', name: 'RSI Oversold', description: 'Buy signal threshold', value: 30, min: 10, max: 40, step: 1, unit: '', category: 'technical' },
  { id: 'rsi_overbought', name: 'RSI Overbought', description: 'Sell signal threshold', value: 70, min: 60, max: 90, step: 1, unit: '', category: 'technical' },
  { id: 'macd_signal_period', name: 'MACD Signal Period', description: 'Signal line smoothing', value: 9, min: 5, max: 20, step: 1, unit: ' bars', category: 'technical' },
  { id: 'bollinger_std', name: 'Bollinger Band StdDev', description: 'Band width multiplier', value: 2.0, min: 1.0, max: 3.0, step: 0.1, unit: 'σ', category: 'technical' },
  
  // Moving Averages
  { id: 'sma_fast', name: 'Fast SMA Period', description: 'Short-term trend', value: 20, min: 5, max: 50, step: 1, unit: ' days', category: 'technical' },
  { id: 'sma_slow', name: 'Slow SMA Period', description: 'Long-term trend', value: 50, min: 20, max: 200, step: 5, unit: ' days', category: 'technical' },
  { id: 'ema_period', name: 'EMA Period', description: 'Exponential moving avg', value: 21, min: 5, max: 100, step: 1, unit: ' days', category: 'technical' },
  
  // Momentum
  { id: 'momentum_lookback', name: 'Momentum Lookback', description: 'Price change period', value: 14, min: 5, max: 60, step: 1, unit: ' days', category: 'momentum' },
  { id: 'momentum_threshold', name: 'Momentum Threshold', description: 'Min % change for signal', value: 5, min: 1, max: 20, step: 0.5, unit: '%', category: 'momentum' },
  { id: 'mean_reversion_zscore', name: 'Mean Reversion Z-Score', description: 'Entry trigger level', value: 2.0, min: 1.0, max: 4.0, step: 0.1, unit: 'σ', category: 'momentum' },
  { id: 'breakout_volume_mult', name: 'Breakout Volume Mult', description: 'Volume confirmation', value: 2.5, min: 1.5, max: 5.0, step: 0.5, unit: 'x avg', category: 'momentum' },
  
  // Sentiment
  { id: 'sentiment_threshold', name: 'Sentiment Threshold', description: 'Min score for signal', value: 0.6, min: 0.3, max: 0.9, step: 0.05, unit: '', category: 'sentiment' },
  { id: 'news_recency', name: 'News Recency Weight', description: 'Freshness importance', value: 60, min: 20, max: 100, step: 5, unit: '%', category: 'sentiment' },
  { id: 'social_volume_spike', name: 'Social Volume Spike', description: 'Unusual mention trigger', value: 3.0, min: 1.5, max: 10.0, step: 0.5, unit: 'x avg', category: 'sentiment' },
  
  // AI
  { id: 'ai_confidence', name: 'AI Confidence Threshold', description: 'Min prediction confidence', value: 75, min: 50, max: 95, step: 5, unit: '%', category: 'ai' },
  { id: 'pattern_match_score', name: 'Pattern Match Score', description: 'Min pattern similarity', value: 80, min: 60, max: 99, step: 1, unit: '%', category: 'ai' },
  { id: 'anomaly_sensitivity', name: 'Anomaly Sensitivity', description: 'Detection sensitivity', value: 70, min: 30, max: 100, step: 5, unit: '%', category: 'ai' },
  
  // Social Trading
  { id: 'insider_min_value', name: 'Insider Min Trade Value', description: 'Min $ to follow', value: 1000000, min: 100000, max: 10000000, step: 100000, unit: '', category: 'social' },
  { id: 'trader_min_winrate', name: 'Trader Min Win Rate', description: 'Min % to follow', value: 65, min: 50, max: 90, step: 5, unit: '%', category: 'social' },
  { id: 'options_flow_premium', name: 'Options Flow Premium', description: 'Min premium to track', value: 100000, min: 10000, max: 1000000, step: 10000, unit: '', category: 'social' },
  
  // Risk Management
  { id: 'position_size_pct', name: 'Max Position Size', description: '% of portfolio per trade', value: 5, min: 1, max: 20, step: 1, unit: '%', category: 'risk' },
  { id: 'stop_loss_pct', name: 'Stop Loss', description: 'Auto exit on loss', value: 3, min: 1, max: 10, step: 0.5, unit: '%', category: 'risk' },
  { id: 'take_profit_pct', name: 'Take Profit', description: 'Auto exit on gain', value: 8, min: 2, max: 30, step: 1, unit: '%', category: 'risk' },
  { id: 'max_correlation', name: 'Max Correlation', description: 'Portfolio diversification', value: 0.7, min: 0.3, max: 1.0, step: 0.05, unit: '', category: 'risk' },
]

const initialSelects: StrategySelect[] = [
  { id: 'ma_type', name: 'Moving Average Type', description: 'Primary MA calculation', value: 'EMA', options: [
    { value: 'SMA', label: 'Simple (SMA)' },
    { value: 'EMA', label: 'Exponential (EMA)' },
    { value: 'WMA', label: 'Weighted (WMA)' },
    { value: 'DEMA', label: 'Double Exp (DEMA)' },
    { value: 'TEMA', label: 'Triple Exp (TEMA)' },
  ], category: 'technical' },
  { id: 'ai_model', name: 'AI Model', description: 'Prediction model to use', value: 'gpt4', options: [
    { value: 'gpt4', label: 'GPT-4 Turbo' },
    { value: 'claude', label: 'Claude 3.5' },
    { value: 'finbert', label: 'FinBERT' },
    { value: 'lstm', label: 'LSTM Neural Net' },
    { value: 'xgboost', label: 'XGBoost Ensemble' },
  ], category: 'ai' },
  { id: 'trend_timeframe', name: 'Trend Timeframe', description: 'Primary analysis period', value: 'daily', options: [
    { value: '1min', label: '1 Minute' },
    { value: '5min', label: '5 Minutes' },
    { value: '15min', label: '15 Minutes' },
    { value: '1hour', label: '1 Hour' },
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly' },
  ], category: 'technical' },
  { id: 'entry_signal_mode', name: 'Entry Signal Mode', description: 'How signals combine', value: 'majority', options: [
    { value: 'any', label: 'Any Signal' },
    { value: 'majority', label: 'Majority Vote' },
    { value: 'all', label: 'All Must Agree' },
    { value: 'weighted', label: 'Weighted Score' },
  ], category: 'risk' },
  { id: 'exit_strategy', name: 'Exit Strategy', description: 'Position closing method', value: 'trailing', options: [
    { value: 'fixed', label: 'Fixed Stop/Target' },
    { value: 'trailing', label: 'Trailing Stop' },
    { value: 'atr', label: 'ATR-Based' },
    { value: 'time', label: 'Time-Based' },
    { value: 'signal', label: 'Signal Reversal' },
  ], category: 'risk' },
]

const categories: { id: CategoryName; name: string; icon: React.ReactNode; color: string }[] = [
  { id: 'technical', name: 'Technical Analysis', icon: <LineChart className="h-4 w-4" />, color: 'text-blue-400' },
  { id: 'momentum', name: 'Momentum & Trend', icon: <TrendingUp className="h-4 w-4" />, color: 'text-green-400' },
  { id: 'sentiment', name: 'News & Sentiment', icon: <Sparkles className="h-4 w-4" />, color: 'text-yellow-400' },
  { id: 'ai', name: 'AI & Machine Learning', icon: <Brain className="h-4 w-4" />, color: 'text-purple-400' },
  { id: 'social', name: 'Social Trading', icon: <Users className="h-4 w-4" />, color: 'text-orange-400' },
  { id: 'risk', name: 'Risk Management', icon: <Shield className="h-4 w-4" />, color: 'text-red-400' },
]

// ============================================================================
// Component
// ============================================================================

export function StrategyPanel() {
  const [toggles, setToggles] = useState<StrategyToggle[]>(initialToggles)
  const [sliders, setSliders] = useState<StrategySlider[]>(initialSliders)
  const [selects, setSelects] = useState<StrategySelect[]>(initialSelects)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['technical', 'ai']))
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }

  const updateToggle = (id: string, enabled: boolean) => {
    setToggles(prev => prev.map(t => t.id === id ? { ...t, enabled } : t))
    setSaved(false)
  }

  const updateSlider = (id: string, value: number) => {
    setSliders(prev => prev.map(s => s.id === id ? { ...s, value } : s))
    setSaved(false)
  }

  const updateSelect = (id: string, value: string) => {
    setSelects(prev => prev.map(s => s.id === id ? { ...s, value } : s))
    setSaved(false)
  }

  const saveSettings = async () => {
    setSaving(true)
    try {
      // Save strategy toggles
      const strategyUpdates = toggles.reduce((acc, t) => {
        if (t.category === 'technical' || t.category === 'momentum' || t.category === 'sentiment') {
          acc[t.id] = t.enabled
        }
        return acc
      }, {} as Record<string, boolean>)
      
      // Save key parameters
      const updates = [
        { category: 'strategies', parameter: 'technical_weight', value: sliders.find(s => s.id === 'rsi_oversold')?.value || 30 },
        { category: 'technical', parameter: 'rsi_oversold', value: sliders.find(s => s.id === 'rsi_oversold')?.value || 30 },
        { category: 'technical', parameter: 'rsi_overbought', value: sliders.find(s => s.id === 'rsi_overbought')?.value || 70 },
        { category: 'technical', parameter: 'ma_fast_period', value: sliders.find(s => s.id === 'sma_fast')?.value || 20 },
        { category: 'technical', parameter: 'ma_slow_period', value: sliders.find(s => s.id === 'sma_slow')?.value || 50 },
        { category: 'news', parameter: 'sentiment_threshold', value: sliders.find(s => s.id === 'sentiment_threshold')?.value || 0.6 },
      ]
      
      // Send all updates
      await Promise.all(updates.map(u => 
        fetch(`/api/config/parameters/${u.category}/${u.parameter}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ value: u.value }),
        })
      ))
      
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      console.error('Failed to save settings:', e)
    }
    setSaving(false)
  }

  const resetToDefaults = () => {
    setToggles(initialToggles)
    setSliders(initialSliders)
    setSelects(initialSelects)
    setSaved(false)
  }

  const formatValue = (slider: StrategySlider): string => {
    if (slider.id.includes('min_value') || slider.id.includes('premium')) {
      if (slider.value >= 1000000) return `$${(slider.value / 1000000).toFixed(1)}M`
      if (slider.value >= 1000) return `$${(slider.value / 1000).toFixed(0)}K`
      return `$${slider.value}`
    }
    if (slider.step < 1) return slider.value.toFixed(1) + slider.unit
    return slider.value + slider.unit
  }

  // Stats
  const enabledCount = toggles.filter(t => t.enabled).length
  const totalCount = toggles.length

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {enabledCount}/{totalCount} strategies enabled
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={resetToDefaults}
            className="px-3 py-1.5 text-xs rounded-lg bg-secondary hover:bg-secondary/80 text-muted-foreground"
          >
            Reset Defaults
          </button>
          <button
            onClick={saveSettings}
            disabled={saving}
            className={`px-4 py-1.5 text-xs rounded-lg transition-colors ${
              saved 
                ? 'bg-profit text-white' 
                : 'bg-xfactor-teal text-white hover:bg-xfactor-teal/80'
            }`}
          >
            {saving ? 'Saving...' : saved ? '✓ Saved' : 'Save Settings'}
          </button>
        </div>
      </div>

      {/* Categories */}
      <div className="space-y-3">
        {categories.map(category => {
          const categoryToggles = toggles.filter(t => t.category === category.id)
          const categorySliders = sliders.filter(s => s.category === category.id)
          const categorySelects = selects.filter(s => s.category === category.id)
          const isExpanded = expandedCategories.has(category.id)
          const enabledInCategory = categoryToggles.filter(t => t.enabled).length

          return (
            <div key={category.id} className="rounded-lg border border-border bg-secondary/30">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category.id)}
                className="w-full flex items-center justify-between p-3 hover:bg-secondary/50 rounded-t-lg"
              >
                <div className="flex items-center gap-3">
                  <span className={category.color}>{category.icon}</span>
                  <span className="font-medium">{category.name}</span>
                  <span className="text-xs text-muted-foreground">
                    ({enabledInCategory}/{categoryToggles.length} active)
                  </span>
                </div>
                {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {/* Category Content */}
              {isExpanded && (
                <div className="p-3 pt-0 space-y-4">
                  {/* Toggles */}
                  {categoryToggles.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Strategies</div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {categoryToggles.map(toggle => (
                          <div
                            key={toggle.id}
                            className={`flex items-center justify-between p-2 rounded-lg border transition-colors ${
                              toggle.enabled ? 'border-xfactor-teal/50 bg-xfactor-teal/10' : 'border-border bg-secondary/50'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <span className={toggle.enabled ? 'text-xfactor-teal' : 'text-muted-foreground'}>
                                {toggle.icon}
                              </span>
                              <div>
                                <div className={`text-sm ${toggle.enabled ? 'text-foreground' : 'text-muted-foreground'}`}>
                                  {toggle.name}
                                </div>
                                <div className="text-xs text-muted-foreground">{toggle.description}</div>
                              </div>
                            </div>
                            <button
                              onClick={() => updateToggle(toggle.id, !toggle.enabled)}
                              className={`h-5 w-10 rounded-full transition-colors ${
                                toggle.enabled ? 'bg-xfactor-teal' : 'bg-muted'
                              }`}
                            >
                              <div
                                className={`h-4 w-4 rounded-full bg-white transition-transform ${
                                  toggle.enabled ? 'translate-x-5' : 'translate-x-0.5'
                                }`}
                              />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Selects */}
                  {categorySelects.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Options</div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {categorySelects.map(select => (
                          <div key={select.id} className="space-y-1">
                            <label className="text-sm font-medium">{select.name}</label>
                            <select
                              value={select.value}
                              onChange={(e) => updateSelect(select.id, e.target.value)}
                              className="w-full px-3 py-2 text-sm rounded-lg bg-secondary border border-border focus:border-xfactor-teal"
                            >
                              {select.options.map(opt => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                              ))}
                            </select>
                            <div className="text-xs text-muted-foreground">{select.description}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Sliders */}
                  {categorySliders.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Parameters</div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {categorySliders.map(slider => (
                          <div key={slider.id} className="space-y-1">
                            <div className="flex items-center justify-between">
                              <label className="text-sm font-medium">{slider.name}</label>
                              <span className="text-sm font-mono text-xfactor-teal">
                                {formatValue(slider)}
                              </span>
                            </div>
                            <input
                              type="range"
                              min={slider.min}
                              max={slider.max}
                              step={slider.step}
                              value={slider.value}
                              onChange={(e) => updateSlider(slider.id, parseFloat(e.target.value))}
                              className="w-full accent-xfactor-teal"
                            />
                            <div className="flex justify-between text-xs text-muted-foreground">
                              <span>{slider.min}{slider.unit}</span>
                              <span>{slider.description}</span>
                              <span>{slider.max}{slider.unit}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-border">
        <div className="text-center p-2 rounded-lg bg-secondary/50">
          <div className="text-lg font-bold text-xfactor-teal">{enabledCount}</div>
          <div className="text-xs text-muted-foreground">Active Strategies</div>
        </div>
        <div className="text-center p-2 rounded-lg bg-secondary/50">
          <div className="text-lg font-bold text-profit">{sliders.length}</div>
          <div className="text-xs text-muted-foreground">Parameters</div>
        </div>
        <div className="text-center p-2 rounded-lg bg-secondary/50">
          <div className="text-lg font-bold text-yellow-400">{selects.length}</div>
          <div className="text-xs text-muted-foreground">Configurable Options</div>
        </div>
        <div className="text-center p-2 rounded-lg bg-secondary/50">
          <div className="text-lg font-bold text-purple-400">6</div>
          <div className="text-xs text-muted-foreground">AI Models Available</div>
        </div>
      </div>
    </div>
  )
}
