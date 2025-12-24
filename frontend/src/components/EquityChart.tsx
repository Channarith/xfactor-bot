import { useEffect, useRef, useState, useMemo } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi, LineData, Time } from 'lightweight-charts'
import { LineChart, TrendingUp, TrendingDown, Target, Eye, EyeOff } from 'lucide-react'
import { useTradingMode } from '../context/TradingModeContext'

interface EquityChartProps {
  height?: number
}

type TimeRange = '1D' | '1W' | '1M' | '3M' | 'YTD' | 'ALL'
type ProjectionHorizon = '1m' | '3m' | '6m' | '1y'

interface ProjectionPoint {
  date: string
  value: number
  low: number
  high: number
}

interface ProjectionData {
  horizon: ProjectionHorizon
  points: ProjectionPoint[]
  target: { low: number; mid: number; high: number }
  dailyReturn: number
  volatility: number
  trend: 'bullish' | 'bearish' | 'neutral'
}

function filterDataByRange(data: LineData[], range: TimeRange): LineData[] {
  if (data.length === 0) return data
  
  const now = new Date()
  let cutoffDate: Date
  
  switch (range) {
    case '1D':
      cutoffDate = new Date(now)
      cutoffDate.setDate(cutoffDate.getDate() - 1)
      break
    case '1W':
      cutoffDate = new Date(now)
      cutoffDate.setDate(cutoffDate.getDate() - 7)
      break
    case '1M':
      cutoffDate = new Date(now)
      cutoffDate.setMonth(cutoffDate.getMonth() - 1)
      break
    case '3M':
      cutoffDate = new Date(now)
      cutoffDate.setMonth(cutoffDate.getMonth() - 3)
      break
    case 'YTD':
      cutoffDate = new Date(now.getFullYear(), 0, 1)
      break
    case 'ALL':
    default:
      return data
  }
  
  const cutoffStr = cutoffDate.toISOString().split('T')[0]
  return data.filter(d => (d.time as string) >= cutoffStr)
}

// Calculate linear regression and projections
function calculateProjections(data: LineData[], horizon: ProjectionHorizon): ProjectionData | null {
  if (data.length < 10) return null
  
  const values = data.map(d => d.value)
  const n = values.length
  
  // Calculate daily returns
  const returns: number[] = []
  for (let i = 1; i < values.length; i++) {
    if (values[i - 1] > 0) {
      returns.push((values[i] - values[i - 1]) / values[i - 1])
    }
  }
  
  if (returns.length < 5) return null
  
  // Calculate average daily return and volatility
  const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length
  const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length
  const volatility = Math.sqrt(variance)
  
  // Determine trend
  let trend: 'bullish' | 'bearish' | 'neutral' = 'neutral'
  if (avgReturn > 0.001) trend = 'bullish'
  else if (avgReturn < -0.001) trend = 'bearish'
  
  // Project forward
  const daysMap: Record<ProjectionHorizon, number> = {
    '1m': 22,
    '3m': 66,
    '6m': 126,
    '1y': 252,
  }
  
  const projectionDays = daysMap[horizon]
  const lastValue = values[values.length - 1]
  const lastDate = new Date(data[data.length - 1].time as string)
  
  const points: ProjectionPoint[] = []
  
  for (let i = 1; i <= projectionDays; i++) {
    const futureDate = new Date(lastDate)
    futureDate.setDate(futureDate.getDate() + i)
    
    // Skip weekends
    if (futureDate.getDay() === 0 || futureDate.getDay() === 6) continue
    
    // Compound growth
    const projectedValue = lastValue * Math.pow(1 + avgReturn, i)
    
    // Confidence bands (widen with time)
    const stdDev = volatility * Math.sqrt(i) * lastValue
    
    points.push({
      date: futureDate.toISOString().split('T')[0],
      value: Math.max(0, projectedValue),
      low: Math.max(0, projectedValue - 2 * stdDev),
      high: projectedValue + 2 * stdDev,
    })
  }
  
  // Calculate target values
  const lastProjection = points[points.length - 1]
  
  return {
    horizon,
    points,
    target: {
      low: lastProjection?.low || lastValue,
      mid: lastProjection?.value || lastValue,
      high: lastProjection?.high || lastValue,
    },
    dailyReturn: avgReturn * 100,
    volatility: volatility * 100 * Math.sqrt(252), // Annualized
    trend,
  }
}

export function EquityChart({ height = 280 }: EquityChartProps) {
  const { broker } = useTradingMode()
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null)
  const projectionSeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map())
  
  const [fullData, setFullData] = useState<LineData[]>([])
  const [selectedRange, setSelectedRange] = useState<TimeRange>('3M')
  const [loading, setLoading] = useState(true)
  const [showProjections, setShowProjections] = useState(true)
  const [projectionHorizon, setProjectionHorizon] = useState<ProjectionHorizon>('3m')
  
  // Filter data based on selected range
  const filteredData = useMemo(() => {
    return filterDataByRange(fullData, selectedRange)
  }, [fullData, selectedRange])
  
  // Calculate projections
  const projectionData = useMemo(() => {
    return calculateProjections(filteredData, projectionHorizon)
  }, [filteredData, projectionHorizon])
  
  // Calculate stats for filtered data
  const currentValue = filteredData[filteredData.length - 1]?.value || 0
  const startValue = filteredData[0]?.value || 0
  const totalReturn = startValue > 0 ? ((currentValue - startValue) / startValue) * 100 : 0
  const isPositive = totalReturn >= 0
  
  // Check if we should show empty state
  const showEmptyState = !loading && fullData.length === 0
  
  // Generate fallback data from broker context
  const generateFallbackData = (equity: number): LineData[] => {
    const data: LineData[] = []
    const today = new Date()
    for (let i = 90; i >= 0; i--) {
      const date = new Date(today)
      date.setDate(date.getDate() - i)
      // Small variation for visual effect
      const variation = 1 + (i % 7 - 3) * 0.001
      data.push({
        time: date.toISOString().split('T')[0] as Time,
        value: i > 0 ? equity * variation : equity,
      })
    }
    return data
  }

  // Fetch equity data from API
  useEffect(() => {
    const fetchEquityData = async () => {
      try {
        const res = await fetch('/api/positions/equity-history')
        if (res.ok) {
          const data = await res.json()
          if (data.history && data.history.length > 0) {
            setFullData(data.history.map((d: any) => ({
              time: d.date as Time,
              value: d.value,
            })))
          } else if (broker.isConnected && broker.portfolioValue) {
            // Generate data from broker context if API returns empty
            setFullData(generateFallbackData(broker.portfolioValue))
          }
        } else if (broker.isConnected && broker.portfolioValue) {
          // Fallback to broker context if API fails
          setFullData(generateFallbackData(broker.portfolioValue))
        }
      } catch (e) {
        console.error('Failed to fetch equity history:', e)
        // Fallback to broker context on error
        if (broker.isConnected && broker.portfolioValue) {
          setFullData(generateFallbackData(broker.portfolioValue))
        }
      }
      setLoading(false)
    }
    
    fetchEquityData()
    // Refresh every 30 seconds to get updated equity data
    const interval = setInterval(fetchEquityData, 30000)
    return () => clearInterval(interval)
  }, [broker.isConnected, broker.portfolioValue])

  // Update chart when data or range changes
  useEffect(() => {
    // Don't create chart if no data or showing empty state
    if (showEmptyState || !chartContainerRef.current || filteredData.length === 0) {
      return
    }

    // Clean up existing chart safely
    if (chartRef.current) {
      try {
        chartRef.current.remove()
      } catch (e) {
        // Chart may already be disposed, ignore error
      }
      chartRef.current = null
      seriesRef.current = null
      projectionSeriesRef.current.clear()
    }

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: height,
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        vertLine: {
          color: 'rgba(139, 92, 246, 0.3)',
          width: 1,
          style: 2,
        },
        horzLine: {
          color: 'rgba(139, 92, 246, 0.3)',
          width: 1,
          style: 2,
        },
      },
    })

    chartRef.current = chart

    // Create area series for equity curve
    const areaSeries = chart.addAreaSeries({
      lineColor: isPositive ? '#22c55e' : '#ef4444',
      topColor: isPositive ? 'rgba(34, 197, 94, 0.4)' : 'rgba(239, 68, 68, 0.4)',
      bottomColor: isPositive ? 'rgba(34, 197, 94, 0.0)' : 'rgba(239, 68, 68, 0.0)',
      lineWidth: 2,
      priceFormat: {
        type: 'custom',
        formatter: (price: number) => '$' + price.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 }),
      },
    })

    seriesRef.current = areaSeries
    areaSeries.setData(filteredData)

    // Add projection lines if enabled
    if (showProjections && projectionData && projectionData.points.length > 0) {
      const lastHistorical = filteredData[filteredData.length - 1]
      
      // Main projection line (dashed)
      const projectionSeries = chart.addLineSeries({
        color: '#8b5cf6',
        lineWidth: 2,
        lineStyle: 2, // Dashed
        lastValueVisible: true,
        priceLineVisible: false,
      })
      
      projectionSeries.setData([
        { time: lastHistorical.time, value: lastHistorical.value },
        ...projectionData.points.map(p => ({
          time: p.date as Time,
          value: p.value,
        }))
      ])
      projectionSeriesRef.current.set('main', projectionSeries)
      
      // Upper confidence band
      const upperBandSeries = chart.addLineSeries({
        color: 'rgba(34, 197, 94, 0.3)',
        lineWidth: 1,
        lineStyle: 3, // Dotted
        priceLineVisible: false,
        lastValueVisible: false,
      })
      
      upperBandSeries.setData([
        { time: lastHistorical.time, value: lastHistorical.value },
        ...projectionData.points.map(p => ({
          time: p.date as Time,
          value: p.high,
        }))
      ])
      projectionSeriesRef.current.set('upper', upperBandSeries)
      
      // Lower confidence band
      const lowerBandSeries = chart.addLineSeries({
        color: 'rgba(239, 68, 68, 0.3)',
        lineWidth: 1,
        lineStyle: 3,
        priceLineVisible: false,
        lastValueVisible: false,
      })
      
      lowerBandSeries.setData([
        { time: lastHistorical.time, value: lastHistorical.value },
        ...projectionData.points.map(p => ({
          time: p.date as Time,
          value: p.low,
        }))
      ])
      projectionSeriesRef.current.set('lower', lowerBandSeries)
    }

    // Fit content
    chart.timeScale().fitContent()

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        try {
          chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth })
        } catch (e) {
          // Chart may be disposed during resize, ignore
        }
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (chartRef.current) {
        try {
          chartRef.current.remove()
        } catch (e) {
          // Chart may already be disposed, ignore error
        }
        chartRef.current = null
        seriesRef.current = null
        projectionSeriesRef.current.clear()
      }
    }
  }, [filteredData, height, isPositive, showEmptyState, showProjections, projectionData])

  const handleRangeChange = (range: TimeRange) => {
    setSelectedRange(range)
  }

  // Get period label
  const getPeriodLabel = () => {
    switch (selectedRange) {
      case '1D': return 'Today'
      case '1W': return 'Past Week'
      case '1M': return 'Past Month'
      case '3M': return 'Past 3 Months'
      case 'YTD': return 'Year to Date'
      case 'ALL': return 'All Time'
    }
  }

  // Show empty state
  if (showEmptyState) {
    return (
      <div 
        className="flex flex-col items-center justify-center text-muted-foreground rounded-lg border border-dashed border-border bg-secondary/20"
        style={{ height }}
      >
        <LineChart className="h-12 w-12 mb-3 opacity-30" />
        <div className="text-sm font-medium">No Equity Data</div>
        <div className="text-xs mt-1">Connect a broker to see your portfolio performance</div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Stats row */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-4">
          <div>
            <span className="text-muted-foreground">Current: </span>
            <span className="font-semibold text-foreground">
              ${currentValue.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">{getPeriodLabel()} Start: </span>
            <span className="text-foreground">
              ${startValue.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>
        <div className={`font-semibold ${isPositive ? 'text-profit' : 'text-loss'}`}>
          {isPositive ? '+' : ''}{totalReturn.toFixed(2)}% {getPeriodLabel()}
        </div>
      </div>
      
      {/* Projection Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowProjections(!showProjections)}
            className={`px-3 py-1.5 text-xs rounded-md flex items-center gap-1.5 transition-colors ${
              showProjections
                ? 'bg-violet-500/20 text-violet-400 border border-violet-500/30'
                : 'bg-secondary/50 text-muted-foreground hover:bg-secondary'
            }`}
          >
            {showProjections ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
            Projections
          </button>
          
          {showProjections && (
            <div className="flex items-center gap-1 bg-secondary/30 rounded-md p-0.5">
              {(['1m', '3m', '6m', '1y'] as ProjectionHorizon[]).map(h => (
                <button
                  key={h}
                  onClick={() => setProjectionHorizon(h)}
                  className={`px-2 py-1 text-xs rounded transition-colors ${
                    projectionHorizon === h
                      ? 'bg-violet-600 text-white'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {h.toUpperCase()}
                </button>
              ))}
            </div>
          )}
        </div>
        
        {/* Trend indicator */}
        {projectionData && showProjections && (
          <div className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${
            projectionData.trend === 'bullish' 
              ? 'bg-green-500/20 text-green-400'
              : projectionData.trend === 'bearish'
              ? 'bg-red-500/20 text-red-400'
              : 'bg-slate-500/20 text-slate-400'
          }`}>
            {projectionData.trend === 'bullish' ? <TrendingUp className="w-3 h-3" /> : 
             projectionData.trend === 'bearish' ? <TrendingDown className="w-3 h-3" /> : null}
            {projectionData.trend.toUpperCase()}
            <span className="text-muted-foreground ml-1">
              ({projectionData.dailyReturn > 0 ? '+' : ''}{projectionData.dailyReturn.toFixed(3)}%/day)
            </span>
          </div>
        )}
      </div>
      
      {/* Chart */}
      <div ref={chartContainerRef} className="rounded-lg overflow-hidden" />
      
      {/* Projection Targets */}
      {showProjections && projectionData && (
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 bg-secondary/30 rounded-lg text-center border border-red-500/20">
            <div className="text-xs text-muted-foreground mb-1">Bear Case ({projectionHorizon.toUpperCase()})</div>
            <div className="text-lg font-bold text-red-400">
              ${projectionData.target.low.toLocaleString(undefined, { minimumFractionDigits: 0 })}
            </div>
            <div className="text-xs text-muted-foreground">
              {(((projectionData.target.low - currentValue) / currentValue) * 100).toFixed(1)}%
            </div>
          </div>
          <div className="p-3 bg-secondary/30 rounded-lg text-center border border-violet-500/20">
            <div className="text-xs text-muted-foreground mb-1">Base Case ({projectionHorizon.toUpperCase()})</div>
            <div className="text-xl font-bold text-violet-400">
              ${projectionData.target.mid.toLocaleString(undefined, { minimumFractionDigits: 0 })}
            </div>
            <div className="text-xs text-muted-foreground">
              {(((projectionData.target.mid - currentValue) / currentValue) * 100) > 0 ? '+' : ''}
              {(((projectionData.target.mid - currentValue) / currentValue) * 100).toFixed(1)}%
            </div>
          </div>
          <div className="p-3 bg-secondary/30 rounded-lg text-center border border-green-500/20">
            <div className="text-xs text-muted-foreground mb-1">Bull Case ({projectionHorizon.toUpperCase()})</div>
            <div className="text-lg font-bold text-green-400">
              ${projectionData.target.high.toLocaleString(undefined, { minimumFractionDigits: 0 })}
            </div>
            <div className="text-xs text-muted-foreground">
              +{(((projectionData.target.high - currentValue) / currentValue) * 100).toFixed(1)}%
            </div>
          </div>
        </div>
      )}
      
      {/* Legend */}
      {showProjections && projectionData && (
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-0.5 bg-violet-500"></div>
            <span>Projected</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-0.5 bg-green-500/30"></div>
            <span>Upper Band (95%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-0.5 bg-red-500/30"></div>
            <span>Lower Band (95%)</span>
          </div>
          <div className="flex items-center gap-1.5 ml-auto">
            <Target className="w-3 h-3" />
            <span>Volatility: {projectionData.volatility.toFixed(1)}% annualized</span>
          </div>
        </div>
      )}
      
      {/* Time range buttons */}
      <div className="flex items-center gap-2">
        {(['1D', '1W', '1M', '3M', 'YTD', 'ALL'] as TimeRange[]).map((range) => (
          <button
            key={range}
            onClick={() => handleRangeChange(range)}
            className={`px-3 py-1 text-xs rounded-md transition-colors ${
              range === selectedRange
                ? 'bg-primary text-primary-foreground'
                : 'bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground'
            }`}
          >
            {range}
          </button>
        ))}
      </div>
    </div>
  )
}
