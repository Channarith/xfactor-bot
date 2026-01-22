import { useState, useEffect, useCallback } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { X, TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { apiUrl } from '../config/api'

interface PositionPerformanceChartProps {
  symbol: string
  onClose: () => void
}

interface PriceData {
  timestamp: string
  price: number
  change: number
  change_pct: number
}

interface Summary {
  symbol: string
  start_price: number
  current_price: number
  change: number
  change_pct: number
  high: number
  low: number
  range_pct: number
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

export function PositionPerformanceChart({ symbol, onClose }: PositionPerformanceChartProps) {
  const [timeRange, setTimeRange] = useState('1D')
  const [data, setData] = useState<PriceData[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    
    try {
      const response = await fetch(apiUrl(`/api/performance/position/${symbol}?time_range=${timeRange}`))
      const result = await response.json()
      
      if (result.error) {
        setError(result.error)
        return
      }
      
      setData(result.data_points || [])
      setSummary(result.summary || null)
    } catch (err) {
      setError('Failed to load price data')
    } finally {
      setLoading(false)
    }
  }, [symbol, timeRange])

  useEffect(() => {
    fetchData()
    
    // Auto-refresh every 30 seconds for 1D view
    if (timeRange === '1D') {
      const interval = setInterval(fetchData, 30000)
      return () => clearInterval(interval)
    }
  }, [fetchData, timeRange])

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
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  const isPositive = summary ? summary.change >= 0 : true
  const chartColor = isPositive ? '#10b981' : '#ef4444'
  const gradientId = `gradient-${symbol}`

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <div 
        className="bg-card border border-border rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
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
              <h2 className="text-xl font-bold">{symbol}</h2>
              {summary && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-foreground font-medium">
                    {formatCurrency(summary.current_price)}
                  </span>
                  <span className={`flex items-center ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
                    {isPositive ? (
                      <ArrowUpRight className="h-4 w-4" />
                    ) : (
                      <ArrowDownRight className="h-4 w-4" />
                    )}
                    {isPositive ? '+' : ''}{summary.change_pct.toFixed(2)}%
                  </span>
                </div>
              )}
            </div>
          </div>
          
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-secondary transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

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
          <div className="grid grid-cols-5 gap-4 p-4 border-b border-border">
            <div className="text-center">
              <p className="text-xs text-muted-foreground mb-1">Open</p>
              <p className="text-sm font-medium">{formatCurrency(summary.start_price)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-muted-foreground mb-1">Current</p>
              <p className="text-sm font-medium">{formatCurrency(summary.current_price)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-muted-foreground mb-1">High</p>
              <p className="text-sm font-medium text-green-500">{formatCurrency(summary.high)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-muted-foreground mb-1">Low</p>
              <p className="text-sm font-medium text-red-500">{formatCurrency(summary.low)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-muted-foreground mb-1">Range</p>
              <p className="text-sm font-medium">{summary.range_pct.toFixed(2)}%</p>
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
                  formatter={(value: number) => [formatCurrency(value), 'Price']}
                />
                <Area
                  type="monotone"
                  dataKey="price"
                  stroke={chartColor}
                  strokeWidth={2}
                  fillOpacity={1}
                  fill={`url(#${gradientId})`}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  )
}

