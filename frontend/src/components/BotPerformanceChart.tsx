import { useState, useEffect, useCallback } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { X, TrendingUp, TrendingDown, Activity, Zap, Target, AlertTriangle, Clock, Bot, Settings, BarChart3, Brain } from 'lucide-react'
import { apiUrl } from '../config/api'
import { AutoOptimizer } from './AutoOptimizer'

interface BotDetails {
  id: string
  name: string
  description: string
  status: string
  created_at?: string
  started_at?: string
  stopped_at?: string
  uptime_seconds?: number
  config: {
    symbols: string[]
    strategies: string[]
    max_position_size: number
    max_positions: number
    max_daily_loss_pct: number
    trade_frequency_seconds: number
    instrument_type?: string
    enable_news_trading?: boolean
  }
  stats: {
    trades_today: number
    signals_generated: number
    daily_pnl: number
    total_pnl?: number
    win_rate?: number
    open_positions: number
    errors_count: number
  }
}

interface BotPerformanceChartProps {
  botId: string
  botName: string
  botDetails?: BotDetails | null
  onClose: () => void
}

interface PerformanceData {
  timestamp: string
  value: number
  pnl: number
  pnl_pct: number
}

interface Summary {
  start_value: number
  end_value: number
  total_pnl: number
  total_pnl_pct: number
  max_drawdown_pct: number
  volatility_pct: number
  num_trades: number
  win_rate: number
}

const TIME_RANGES = [
  { value: '1D', label: '1D' },
  { value: '1W', label: '1W' },
  { value: '1M', label: '1M' },
  { value: '3M', label: '3M' },
  { value: '6M', label: '6M' },
  { value: '1Y', label: '1Y' },
  { value: 'YTD', label: 'YTD' },
  { value: 'ALL', label: 'ALL' },
]

export function BotPerformanceChart({ botId, botName, botDetails: initialBotDetails, onClose }: BotPerformanceChartProps) {
  const [timeRange, setTimeRange] = useState('1D')
  const [data, setData] = useState<PerformanceData[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'chart' | 'details' | 'optimizer'>('chart')
  const [botDetails, setBotDetails] = useState<BotDetails | null>(initialBotDetails || null)

  // Fetch bot details for live updates
  const fetchBotDetails = useCallback(async () => {
    try {
      const response = await fetch(apiUrl(`/api/bots/${botId}`))
      if (response.ok) {
        const details = await response.json()
        setBotDetails(details)
      }
    } catch (err) {
      console.error('Failed to fetch bot details:', err)
    }
  }, [botId])

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    
    try {
      const response = await fetch(apiUrl(`/api/performance/bot/${botId}?time_range=${timeRange}`))
      const result = await response.json()
      
      if (result.error) {
        setError(result.error)
        return
      }
      
      setData(result.data_points || [])
      setSummary(result.summary || null)
    } catch (err) {
      setError('Failed to load performance data')
    } finally {
      setLoading(false)
    }
  }, [botId, timeRange])

  useEffect(() => {
    fetchData()
    fetchBotDetails()
    
    // Auto-refresh every 30 seconds for both performance data and bot details
    const interval = setInterval(() => {
      if (timeRange === '1D') {
        fetchData()
      }
      fetchBotDetails()  // Always refresh bot details
    }, 30000)
    
    return () => clearInterval(interval)
  }, [fetchData, fetchBotDetails, timeRange])

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    if (timeRange === '1D') {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (timeRange === '1W') {
      return date.toLocaleDateString([], { weekday: 'short', hour: '2-digit' })
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours > 24) {
      const days = Math.floor(hours / 24)
      return `${days}d ${hours % 24}h`
    }
    return `${hours}h ${minutes}m`
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-green-500'
      case 'paused': return 'bg-yellow-500'
      case 'stopped': return 'bg-red-500'
      case 'starting': return 'bg-blue-500'
      default: return 'bg-gray-500'
    }
  }

  const isPositive = summary ? summary.total_pnl >= 0 : true
  const chartColor = isPositive ? '#10b981' : '#ef4444'
  const gradientId = `gradient-${botId}`

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isPositive ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
              {isPositive ? (
                <TrendingUp className="h-5 w-5 text-green-500" />
              ) : (
                <TrendingDown className="h-5 w-5 text-red-500" />
              )}
            </div>
            <div>
              <h2 className="text-lg font-semibold flex items-center gap-2">
                {botName}
                {botDetails && (
                  <span className={`px-2 py-0.5 text-xs rounded-full ${getStatusColor(botDetails.status)} text-white`}>
                    {botDetails.status}
                  </span>
                )}
              </h2>
              <p className="text-sm text-muted-foreground">Bot ID: {botId}</p>
            </div>
          </div>
          
          {/* Tab Switcher */}
          <div className="flex items-center gap-2 bg-secondary rounded-lg p-1">
            <button
              onClick={() => setActiveTab('chart')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-1 ${
                activeTab === 'chart' ? 'bg-xfactor-teal text-white' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <BarChart3 className="h-4 w-4" />
              Performance
            </button>
            <button
              onClick={() => setActiveTab('details')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-1 ${
                activeTab === 'details' ? 'bg-xfactor-teal text-white' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Settings className="h-4 w-4" />
              Details
            </button>
            <button
              onClick={() => setActiveTab('optimizer')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-1 ${
                activeTab === 'optimizer' ? 'bg-xfactor-teal text-white' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Brain className="h-4 w-4" />
              Auto-Tune
            </button>
          </div>
          
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-secondary transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {activeTab === 'chart' && (
          <>
            {/* Time Range Selector */}
            <div className="flex items-center gap-1 p-4 border-b border-border">
              {TIME_RANGES.map((range) => (
                <button
                  key={range.value}
                  onClick={() => setTimeRange(range.value)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                    timeRange === range.value
                      ? 'bg-xfactor-teal text-white'
                      : 'bg-secondary hover:bg-secondary/80 text-muted-foreground'
                  }`}
                >
                  {range.label}
                </button>
              ))}
            </div>

            {/* Summary Stats */}
            {summary && (
              <div className="grid grid-cols-4 gap-4 p-4 border-b border-border">
                <div className="text-center">
                  <p className="text-xs text-muted-foreground mb-1">Total P&L</p>
                  <p className={`text-lg font-bold ${summary.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {summary.total_pnl >= 0 ? '+' : ''}{formatCurrency(summary.total_pnl)}
                  </p>
                  <p className={`text-xs ${summary.total_pnl_pct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {summary.total_pnl_pct >= 0 ? '+' : ''}{summary.total_pnl_pct.toFixed(2)}%
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground mb-1">Win Rate</p>
                  <p className="text-lg font-bold text-foreground flex items-center justify-center gap-1">
                    <Target className="h-4 w-4 text-xfactor-teal" />
                    {(summary.win_rate * 100).toFixed(0)}%
                  </p>
                  <p className="text-xs text-muted-foreground">{summary.num_trades} trades</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground mb-1">Max Drawdown</p>
                  <p className="text-lg font-bold text-orange-500 flex items-center justify-center gap-1">
                    <AlertTriangle className="h-4 w-4" />
                    {summary.max_drawdown_pct.toFixed(2)}%
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground mb-1">Volatility</p>
                  <p className="text-lg font-bold text-foreground flex items-center justify-center gap-1">
                    <Activity className="h-4 w-4 text-purple-500" />
                    {summary.volatility_pct.toFixed(1)}%
                  </p>
                </div>
              </div>
            )}

            {/* Chart */}
            <div className="flex-1 p-4 min-h-[350px]">
              {loading ? (
                <div className="h-full flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-2 border-xfactor-teal border-t-transparent" />
                </div>
              ) : error ? (
                <div className="h-full flex items-center justify-center text-red-500">
                  {error}
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={formatTime}
                      stroke="#666"
                      tick={{ fill: '#888', fontSize: 11 }}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      tickFormatter={(val) => formatCurrency(val)}
                      stroke="#666"
                      tick={{ fill: '#888', fontSize: 11 }}
                      domain={['auto', 'auto']}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1a1a2e',
                        border: '1px solid #333',
                        borderRadius: '8px',
                      }}
                      labelFormatter={(label) => new Date(label).toLocaleString()}
                      formatter={(value: number, name: string) => {
                        if (name === 'value') return [formatCurrency(value), 'Value']
                        if (name === 'pnl') return [formatCurrency(value), 'P&L']
                        return [value, name]
                      }}
                    />
                    {summary && (
                      <ReferenceLine
                        y={summary.start_value}
                        stroke="#666"
                        strokeDasharray="5 5"
                        label={{ value: 'Start', fill: '#888', fontSize: 10 }}
                      />
                    )}
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke={chartColor}
                      strokeWidth={2}
                      fillOpacity={1}
                      fill={`url(#${gradientId})`}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </>
        )}

        {/* Details Tab */}
        {activeTab === 'details' && (
          <div className="flex-1 p-6 overflow-y-auto">
            {botDetails ? (
              <div className="grid grid-cols-2 gap-6">
                {/* Left Column - Configuration */}
                <div className="space-y-4">
                  <div className="bg-secondary/50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Bot className="h-4 w-4 text-xfactor-teal" />
                      Bot Configuration
                    </h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Instrument Type</span>
                        <span className="font-medium">{botDetails.config.instrument_type || 'Stock'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Max Position Size</span>
                        <span className="font-medium">{formatCurrency(botDetails.config.max_position_size)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Max Positions</span>
                        <span className="font-medium">{botDetails.config.max_positions}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Max Daily Loss</span>
                        <span className="font-medium text-orange-500">{botDetails.config.max_daily_loss_pct}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Trade Frequency</span>
                        <span className="font-medium">{botDetails.config.trade_frequency_seconds}s</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">News Trading</span>
                        <span className={`font-medium ${botDetails.config.enable_news_trading ? 'text-green-500' : 'text-muted-foreground'}`}>
                          {botDetails.config.enable_news_trading ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-secondary/50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold mb-3">Symbols ({botDetails.config.symbols.length})</h3>
                    <div className="flex flex-wrap gap-1">
                      {botDetails.config.symbols.map((symbol) => (
                        <span key={symbol} className="px-2 py-0.5 bg-xfactor-teal/20 text-xfactor-teal rounded text-xs font-medium">
                          {symbol}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="bg-secondary/50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold mb-3">Strategies ({botDetails.config.strategies.length})</h3>
                    <div className="flex flex-wrap gap-1">
                      {botDetails.config.strategies.map((strategy) => (
                        <span key={strategy} className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs font-medium">
                          {strategy}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Right Column - Stats */}
                <div className="space-y-4">
                  {/* Key Performance Metrics */}
                  <div className="bg-secondary/50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Target className="h-4 w-4 text-xfactor-teal" />
                      Performance Metrics
                    </h3>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="text-center p-3 bg-background rounded-lg">
                        <p className={`text-xl font-bold ${(botDetails.stats.win_rate || 0) >= 50 ? 'text-green-500' : 'text-orange-500'}`}>
                          {((botDetails.stats.win_rate || 0) * 100).toFixed(1)}%
                        </p>
                        <p className="text-xs text-muted-foreground">Win Rate</p>
                      </div>
                      <div className="text-center p-3 bg-background rounded-lg">
                        <p className={`text-xl font-bold ${(botDetails.stats.total_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {formatCurrency(botDetails.stats.total_pnl || 0)}
                        </p>
                        <p className="text-xs text-muted-foreground">Total P&L</p>
                      </div>
                      <div className="text-center p-3 bg-background rounded-lg">
                        <p className="text-xl font-bold text-xfactor-teal">
                          {formatUptime(botDetails.uptime_seconds || 0)}
                        </p>
                        <p className="text-xs text-muted-foreground">Uptime</p>
                      </div>
                    </div>
                  </div>

                  {/* Live Statistics */}
                  <div className="bg-secondary/50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Activity className="h-4 w-4 text-xfactor-teal" />
                      Live Statistics
                    </h3>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="text-center p-3 bg-background rounded-lg">
                        <p className="text-2xl font-bold text-foreground">{botDetails.stats.trades_today}</p>
                        <p className="text-xs text-muted-foreground">Trades Today</p>
                      </div>
                      <div className="text-center p-3 bg-background rounded-lg">
                        <p className="text-2xl font-bold text-foreground">{botDetails.stats.signals_generated}</p>
                        <p className="text-xs text-muted-foreground">Signals</p>
                      </div>
                      <div className="text-center p-3 bg-background rounded-lg">
                        <p className={`text-2xl font-bold ${botDetails.stats.daily_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {formatCurrency(botDetails.stats.daily_pnl)}
                        </p>
                        <p className="text-xs text-muted-foreground">Daily P&L</p>
                      </div>
                      <div className="text-center p-3 bg-background rounded-lg">
                        <p className="text-2xl font-bold text-foreground">{botDetails.stats.open_positions}</p>
                        <p className="text-xs text-muted-foreground">Open Positions</p>
                      </div>
                    </div>
                  </div>

                  {/* Errors Section - Always show */}
                  <div className={`rounded-lg p-4 ${botDetails.stats.errors_count > 0 ? 'bg-red-500/10 border border-red-500/30' : 'bg-green-500/10 border border-green-500/30'}`}>
                    <h3 className={`text-sm font-semibold mb-2 flex items-center gap-2 ${botDetails.stats.errors_count > 0 ? 'text-red-500' : 'text-green-500'}`}>
                      {botDetails.stats.errors_count > 0 ? (
                        <AlertTriangle className="h-4 w-4" />
                      ) : (
                        <Target className="h-4 w-4" />
                      )}
                      {botDetails.stats.errors_count > 0 ? 'Errors Detected' : 'No Errors'}
                    </h3>
                    <p className={`text-sm ${botDetails.stats.errors_count > 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {botDetails.stats.errors_count > 0 
                        ? `${botDetails.stats.errors_count} error(s) detected - check logs`
                        : 'Bot running smoothly with no errors'}
                    </p>
                  </div>

                  <div className="bg-secondary/50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Clock className="h-4 w-4 text-xfactor-teal" />
                      Timing
                    </h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Created</span>
                        <span className="font-medium">
                          {botDetails.created_at ? new Date(botDetails.created_at).toLocaleDateString() : 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Started</span>
                        <span className="font-medium">
                          {botDetails.started_at ? new Date(botDetails.started_at).toLocaleString() : 'Not started'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Uptime</span>
                        <span className="font-medium text-green-500">
                          {botDetails.uptime_seconds ? formatUptime(botDetails.uptime_seconds) : '0h 0m'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Loading bot details...</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Optimizer Tab */}
        {activeTab === 'optimizer' && (
          <div className="flex-1 p-6 overflow-y-auto">
            <AutoOptimizer botId={botId} botName={botName} />
          </div>
        )}

        {/* Footer */}
        <div className="p-4 border-t border-border flex justify-between items-center text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-xfactor-teal" />
            <span>Auto-refreshes every 30 seconds</span>
          </div>
          <div>
            Last updated: {new Date().toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  )
}
