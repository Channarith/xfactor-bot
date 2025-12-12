import { useState, useEffect, useMemo } from 'react'
import { RefreshCw, TrendingUp, TrendingDown, Search, SortAsc, SortDesc, X } from 'lucide-react'

interface Position {
  symbol: string
  quantity: number
  avg_cost: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  sector?: string
  strategy?: string
}

interface PortfolioSummary {
  total_value: number
  cash: number
  positions_value: number
  unrealized_pnl: number
  realized_pnl: number
  daily_pnl: number
  position_count: number
}

// Mock data for development
const mockPositions: Position[] = [
  { symbol: 'NVDA', quantity: 100, avg_cost: 450.50, current_price: 475.25, market_value: 47525, unrealized_pnl: 2475, unrealized_pnl_pct: 5.49, sector: 'Technology', strategy: 'Momentum' },
  { symbol: 'AAPL', quantity: 200, avg_cost: 175.00, current_price: 179.50, market_value: 35900, unrealized_pnl: 900, unrealized_pnl_pct: 2.57, sector: 'Technology', strategy: 'Technical' },
  { symbol: 'TSLA', quantity: -50, avg_cost: 240.00, current_price: 245.80, market_value: -12290, unrealized_pnl: -290, unrealized_pnl_pct: -2.42, sector: 'Consumer', strategy: 'MeanReversion' },
  { symbol: 'MSFT', quantity: 150, avg_cost: 360.00, current_price: 368.25, market_value: 55237.5, unrealized_pnl: 1237.5, unrealized_pnl_pct: 2.29, sector: 'Technology', strategy: 'Technical' },
  { symbol: 'AMD', quantity: 300, avg_cost: 115.00, current_price: 117.50, market_value: 35250, unrealized_pnl: 750, unrealized_pnl_pct: 2.17, sector: 'Technology', strategy: 'NewsSentiment' },
  { symbol: 'GOOGL', quantity: 80, avg_cost: 140.00, current_price: 142.30, market_value: 11384, unrealized_pnl: 184, unrealized_pnl_pct: 1.64, sector: 'Technology', strategy: 'Momentum' },
  { symbol: 'SPY', quantity: 100, avg_cost: 450.00, current_price: 455.20, market_value: 45520, unrealized_pnl: 520, unrealized_pnl_pct: 1.16, sector: 'ETF', strategy: 'Technical' },
]

type SortField = 'symbol' | 'quantity' | 'market_value' | 'unrealized_pnl' | 'unrealized_pnl_pct'
type SortDir = 'asc' | 'desc'

export function PositionsTable() {
  const [positions, setPositions] = useState<Position[]>(mockPositions)
  const [summary, setSummary] = useState<PortfolioSummary>({
    total_value: 250000,
    cash: 31383.5,
    positions_value: 218616.5,
    unrealized_pnl: 5776.5,
    realized_pnl: 12500,
    daily_pnl: 3240,
    position_count: 7,
  })
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortField, setSortField] = useState<SortField>('unrealized_pnl')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const fetchPositions = async () => {
    setLoading(true)
    try {
      const [posRes, summaryRes] = await Promise.all([
        fetch('/api/positions/'),
        fetch('/api/positions/summary'),
      ])
      
      if (posRes.ok) {
        const data = await posRes.json()
        if (data.positions && data.positions.length > 0) {
          setPositions(data.positions)
        }
        // If no positions from API, keep mock data
      }
      
      if (summaryRes.ok) {
        const data = await summaryRes.json()
        if (data.total_value > 0) {
          setSummary(data)
        }
      }
    } catch (e) {
      console.error('Failed to fetch positions:', e)
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchPositions()
    const interval = setInterval(fetchPositions, 15000) // Refresh every 15s
    return () => clearInterval(interval)
  }, [])

  // Filtered and sorted positions
  const filteredPositions = useMemo(() => {
    let result = [...positions]
    
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(p => 
        p.symbol.toLowerCase().includes(query) ||
        p.strategy?.toLowerCase().includes(query) ||
        p.sector?.toLowerCase().includes(query)
      )
    }
    
    result.sort((a, b) => {
      let aVal = a[sortField]
      let bVal = b[sortField]
      
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase() as any
        bVal = (bVal as string).toLowerCase() as any
      }
      
      if ((aVal as number) < (bVal as number)) return sortDir === 'asc' ? -1 : 1
      if ((aVal as number) > (bVal as number)) return sortDir === 'asc' ? 1 : -1
      return 0
    })
    
    return result
  }, [positions, searchQuery, sortField, sortDir])

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value)
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <SortAsc className="h-3 w-3 opacity-30" />
    return sortDir === 'asc' ? <SortAsc className="h-3 w-3" /> : <SortDesc className="h-3 w-3" />
  }

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-secondary/50">
          <div className="text-xs text-muted-foreground">Total Value</div>
          <div className="text-lg font-semibold">{formatCurrency(summary.total_value)}</div>
        </div>
        <div className="p-3 rounded-lg bg-secondary/50">
          <div className="text-xs text-muted-foreground">Unrealized P&L</div>
          <div className={`text-lg font-semibold ${summary.unrealized_pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
            {summary.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(summary.unrealized_pnl)}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-secondary/50">
          <div className="text-xs text-muted-foreground">Daily P&L</div>
          <div className={`text-lg font-semibold ${summary.daily_pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
            {summary.daily_pnl >= 0 ? '+' : ''}{formatCurrency(summary.daily_pnl)}
          </div>
        </div>
        <div className="p-3 rounded-lg bg-secondary/50">
          <div className="text-xs text-muted-foreground">Cash</div>
          <div className="text-lg font-semibold">{formatCurrency(summary.cash)}</div>
        </div>
      </div>

      {/* Search and Controls */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search positions..."
            className="w-full pl-10 pr-8 py-2 text-sm rounded-lg bg-secondary border border-border"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2">
              <X className="h-4 w-4 text-muted-foreground" />
            </button>
          )}
        </div>
        <button
          onClick={fetchPositions}
          disabled={loading}
          className="p-2 rounded-lg bg-secondary hover:bg-secondary/80"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Positions Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-sm text-muted-foreground">
              <th className="pb-2">
                <button onClick={() => toggleSort('symbol')} className="flex items-center gap-1 hover:text-foreground">
                  Symbol <SortIcon field="symbol" />
                </button>
              </th>
              <th className="pb-2">
                <button onClick={() => toggleSort('quantity')} className="flex items-center gap-1 hover:text-foreground">
                  Qty <SortIcon field="quantity" />
                </button>
              </th>
              <th className="pb-2">Avg Cost</th>
              <th className="pb-2">Price</th>
              <th className="pb-2">
                <button onClick={() => toggleSort('market_value')} className="flex items-center gap-1 hover:text-foreground">
                  Value <SortIcon field="market_value" />
                </button>
              </th>
              <th className="pb-2">
                <button onClick={() => toggleSort('unrealized_pnl')} className="flex items-center gap-1 hover:text-foreground">
                  P&L <SortIcon field="unrealized_pnl" />
                </button>
              </th>
              <th className="pb-2">
                <button onClick={() => toggleSort('unrealized_pnl_pct')} className="flex items-center gap-1 hover:text-foreground">
                  P&L % <SortIcon field="unrealized_pnl_pct" />
                </button>
              </th>
              <th className="pb-2">Strategy</th>
            </tr>
          </thead>
          <tbody>
            {filteredPositions.map((pos) => (
              <tr key={pos.symbol} className="border-b border-border/50 hover:bg-secondary/30">
                <td className="py-2 font-medium flex items-center gap-2">
                  {pos.quantity > 0 ? (
                    <TrendingUp className="h-3 w-3 text-profit" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-loss" />
                  )}
                  {pos.symbol}
                </td>
                <td className={`py-2 ${pos.quantity < 0 ? 'text-loss' : ''}`}>
                  {pos.quantity.toLocaleString()}
                </td>
                <td className="py-2">${pos.avg_cost.toFixed(2)}</td>
                <td className="py-2">${pos.current_price.toFixed(2)}</td>
                <td className="py-2">{formatCurrency(Math.abs(pos.market_value))}</td>
                <td className={`py-2 ${pos.unrealized_pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                  {pos.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(pos.unrealized_pnl)}
                </td>
                <td className={`py-2 ${pos.unrealized_pnl_pct >= 0 ? 'text-profit' : 'text-loss'}`}>
                  {pos.unrealized_pnl_pct >= 0 ? '+' : ''}{pos.unrealized_pnl_pct.toFixed(2)}%
                </td>
                <td className="py-2">
                  <span className="px-2 py-0.5 text-xs rounded bg-secondary text-muted-foreground">
                    {pos.strategy}
                  </span>
                </td>
              </tr>
            ))}
            {filteredPositions.length === 0 && (
              <tr>
                <td colSpan={8} className="py-4 text-center text-muted-foreground">
                  {searchQuery ? 'No positions match your search' : 'No open positions'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Position Count */}
      <div className="text-xs text-muted-foreground text-right">
        {filteredPositions.length} of {positions.length} positions
      </div>
    </div>
  )
}
