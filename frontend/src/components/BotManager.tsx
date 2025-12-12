import { useState, useEffect, useMemo } from 'react'
import { 
  Bot, Play, Pause, Square, Plus, Trash2, Settings, 
  Activity, AlertTriangle, ChevronDown, ChevronUp,
  Search, SortAsc, SortDesc, X, Filter
} from 'lucide-react'

interface BotSummary {
  id: string
  name: string
  status: string
  symbols_count: number
  strategies: string[]
  daily_pnl: number
  uptime_seconds: number
}

type SortField = 'name' | 'status' | 'daily_pnl' | 'uptime_seconds' | 'symbols_count'
type SortDirection = 'asc' | 'desc'

interface BotDetails {
  id: string
  name: string
  description: string
  status: string
  config: {
    symbols: string[]
    strategies: string[]
    max_position_size: number
    max_positions: number
    max_daily_loss_pct: number
    trade_frequency_seconds: number
  }
  stats: {
    trades_today: number
    signals_generated: number
    daily_pnl: number
    open_positions: number
    errors_count: number
  }
}

interface BotManagerProps {
  token?: string
}

export function BotManager({ token = '' }: BotManagerProps) {
  const [bots, setBots] = useState<BotSummary[]>([])
  const [selectedBot, setSelectedBot] = useState<BotDetails | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [expandedBot, setExpandedBot] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Search, Sort, Filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [showFilters, setShowFilters] = useState(false)
  
  // New bot form state
  const [newBotName, setNewBotName] = useState('')
  const [newBotSymbols, setNewBotSymbols] = useState('SPY,QQQ,AAPL,MSFT,NVDA')
  const [newBotStrategies, setNewBotStrategies] = useState(['Technical', 'Momentum'])
  
  // Filtered and sorted bots
  const filteredBots = useMemo(() => {
    let result = [...bots]
    
    // Apply search
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(bot => 
        bot.name.toLowerCase().includes(query) ||
        bot.strategies.some(s => s.toLowerCase().includes(query)) ||
        bot.id.toLowerCase().includes(query)
      )
    }
    
    // Apply status filter
    if (statusFilter !== 'all') {
      result = result.filter(bot => bot.status === statusFilter)
    }
    
    // Apply sort
    result.sort((a, b) => {
      let aVal = a[sortField]
      let bVal = b[sortField]
      
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase()
        bVal = (bVal as string).toLowerCase()
      }
      
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
      return 0
    })
    
    return result
  }, [bots, searchQuery, statusFilter, sortField, sortDirection])
  
  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }
  
  const clearFilters = () => {
    setSearchQuery('')
    setStatusFilter('all')
    setSortField('name')
    setSortDirection('asc')
  }
  
  const hasActiveFilters = searchQuery || statusFilter !== 'all'

  const authHeaders = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }

  const fetchBots = async () => {
    try {
      const response = await fetch('/api/bots/summary')
      const data = await response.json()
      setBots(data.bots || [])
    } catch (e) {
      setError('Failed to fetch bots')
    }
  }

  useEffect(() => {
    fetchBots()
    const interval = setInterval(fetchBots, 5000)
    return () => clearInterval(interval)
  }, [])

  const createBot = async () => {
    setLoading(true)
    setError('')
    
    try {
      const response = await fetch('/api/bots/', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          name: newBotName,
          symbols: newBotSymbols.split(',').map(s => s.trim()),
          strategies: newBotStrategies,
        }),
      })
      
      if (response.ok) {
        setShowCreateForm(false)
        setNewBotName('')
        fetchBots()
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to create bot')
      }
    } catch (e) {
      setError('Failed to create bot')
    }
    
    setLoading(false)
  }

  const controlBot = async (botId: string, action: string) => {
    try {
      await fetch(`/api/bots/${botId}/${action}`, {
        method: 'POST',
        headers: authHeaders,
      })
      fetchBots()
    } catch (e) {
      setError(`Failed to ${action} bot`)
    }
  }

  const deleteBot = async (botId: string) => {
    if (!confirm('Are you sure you want to delete this bot?')) return
    
    try {
      await fetch(`/api/bots/${botId}`, {
        method: 'DELETE',
        headers: authHeaders,
      })
      fetchBots()
    } catch (e) {
      setError('Failed to delete bot')
    }
  }

  const controlAllBots = async (action: string) => {
    try {
      await fetch(`/api/bots/${action}`, {
        method: 'POST',
        headers: authHeaders,
      })
      fetchBots()
    } catch (e) {
      setError(`Failed to ${action}`)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-profit'
      case 'paused': return 'bg-yellow-500'
      case 'stopped': return 'bg-muted'
      case 'error': return 'bg-loss'
      default: return 'bg-muted'
    }
  }

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">Bot Manager</h2>
          <span className="text-sm text-muted-foreground">
            ({filteredBots.length}/{bots.length} shown, max 25)
          </span>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => controlAllBots('start-all')}
            className="p-1.5 rounded bg-profit/20 text-profit hover:bg-profit/30"
            title="Start all"
          >
            <Play className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => controlAllBots('pause-all')}
            className="p-1.5 rounded bg-yellow-500/20 text-yellow-500 hover:bg-yellow-500/30"
            title="Pause all"
          >
            <Pause className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => controlAllBots('stop-all')}
            className="p-1.5 rounded bg-loss/20 text-loss hover:bg-loss/30"
            title="Stop all"
          >
            <Square className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      
      {/* Search, Sort, Filter Bar */}
      <div className="mb-4 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search bots by name, strategy..."
              className="w-full pl-10 pr-8 py-2 text-sm rounded-lg bg-secondary border border-border focus:border-xfactor-teal focus:outline-none"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
              statusFilter !== 'all' ? 'bg-xfactor-teal/20 border-xfactor-teal text-xfactor-teal' : 'bg-secondary border-border'
            }`}
          >
            <option value="all">All Status</option>
            <option value="running">🟢 Running</option>
            <option value="paused">🟡 Paused</option>
            <option value="stopped">⚫ Stopped</option>
            <option value="error">🔴 Error</option>
          </select>
          
          {/* Sort Dropdown */}
          <div className="flex items-center gap-1">
            <select
              value={sortField}
              onChange={(e) => setSortField(e.target.value as SortField)}
              className="px-3 py-2 text-sm rounded-lg bg-secondary border border-border"
            >
              <option value="name">Sort: Name</option>
              <option value="status">Sort: Status</option>
              <option value="daily_pnl">Sort: P&L</option>
              <option value="uptime_seconds">Sort: Uptime</option>
              <option value="symbols_count">Sort: Symbols</option>
            </select>
            <button
              onClick={() => setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')}
              className="p-2 rounded-lg bg-secondary border border-border hover:bg-secondary/80"
              title={sortDirection === 'asc' ? 'Ascending' : 'Descending'}
            >
              {sortDirection === 'asc' ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />}
            </button>
          </div>
          
          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="px-3 py-2 text-sm text-loss hover:text-loss/80"
            >
              Clear
            </button>
          )}
        </div>
        
        {/* Quick Status Filters */}
        <div className="flex gap-2">
          {['all', 'running', 'paused', 'stopped'].map((status) => {
            const count = status === 'all' ? bots.length : bots.filter(b => b.status === status).length
            return (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-1 text-xs rounded-full transition-colors ${
                  statusFilter === status
                    ? 'bg-xfactor-teal text-white'
                    : 'bg-secondary text-muted-foreground hover:text-foreground'
                }`}
              >
                {status === 'all' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1)} ({count})
              </button>
            )
          })}
        </div>
      </div>
      
      {error && (
        <div className="mb-3 p-2 rounded bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}
      
      {/* Bot List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredBots.map((bot) => (
          <div
            key={bot.id}
            className="border border-border/50 rounded-lg p-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`h-2 w-2 rounded-full ${getStatusColor(bot.status)}`} />
                <div>
                  <span className="font-medium text-sm">{bot.name}</span>
                  <span className="text-xs text-muted-foreground ml-2">({bot.id})</span>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <span className={`text-xs ${bot.daily_pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                  {bot.daily_pnl >= 0 ? '+' : ''}${bot.daily_pnl.toFixed(2)}
                </span>
                
                {/* Control buttons */}
                {bot.status === 'running' ? (
                  <>
                    <button
                      onClick={() => controlBot(bot.id, 'pause')}
                      className="p-1 rounded hover:bg-secondary"
                      title="Pause"
                    >
                      <Pause className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => controlBot(bot.id, 'stop')}
                      className="p-1 rounded hover:bg-secondary"
                      title="Stop"
                    >
                      <Square className="h-3.5 w-3.5" />
                    </button>
                  </>
                ) : bot.status === 'paused' ? (
                  <>
                    <button
                      onClick={() => controlBot(bot.id, 'resume')}
                      className="p-1 rounded hover:bg-secondary"
                      title="Resume"
                    >
                      <Play className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => controlBot(bot.id, 'stop')}
                      className="p-1 rounded hover:bg-secondary"
                      title="Stop"
                    >
                      <Square className="h-3.5 w-3.5" />
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => controlBot(bot.id, 'start')}
                    className="p-1 rounded hover:bg-secondary text-profit"
                    title="Start"
                  >
                    <Play className="h-3.5 w-3.5" />
                  </button>
                )}
                
                <button
                  onClick={() => deleteBot(bot.id)}
                  className="p-1 rounded hover:bg-destructive/20 text-destructive"
                  title="Delete"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
                
                <button
                  onClick={() => setExpandedBot(expandedBot === bot.id ? null : bot.id)}
                  className="p-1 rounded hover:bg-secondary"
                >
                  {expandedBot === bot.id ? (
                    <ChevronUp className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>
            
            {/* Expanded details */}
            {expandedBot === bot.id && (
              <div className="mt-3 pt-3 border-t border-border/50 text-xs text-muted-foreground">
                <div className="grid grid-cols-2 gap-2">
                  <div>Symbols: {bot.symbols_count}</div>
                  <div>Uptime: {formatUptime(bot.uptime_seconds)}</div>
                  <div>Strategies: {bot.strategies.join(', ')}</div>
                  <div>Status: {bot.status}</div>
                </div>
              </div>
            )}
          </div>
        ))}
        
        {filteredBots.length === 0 && bots.length > 0 && (
          <p className="text-center text-muted-foreground text-sm py-4">
            No bots match your filters
          </p>
        )}
        
        {bots.length === 0 && (
          <p className="text-center text-muted-foreground text-sm py-4">
            No bots created yet
          </p>
        )}
      </div>
      
      {/* Create Bot Form */}
      {showCreateForm ? (
        <div className="mt-4 p-3 border border-border/50 rounded-lg">
          <h3 className="text-sm font-medium mb-3">Create New Bot</h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground">Name</label>
              <input
                type="text"
                value={newBotName}
                onChange={(e) => setNewBotName(e.target.value)}
                placeholder="My Trading Bot"
                className="w-full mt-1 rounded bg-input px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Symbols (comma-separated)</label>
              <input
                type="text"
                value={newBotSymbols}
                onChange={(e) => setNewBotSymbols(e.target.value)}
                placeholder="SPY,QQQ,AAPL"
                className="w-full mt-1 rounded bg-input px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Strategies</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {['Technical', 'Momentum', 'MeanReversion', 'NewsSentiment'].map((strat) => (
                  <button
                    key={strat}
                    onClick={() => {
                      if (newBotStrategies.includes(strat)) {
                        setNewBotStrategies(newBotStrategies.filter(s => s !== strat))
                      } else {
                        setNewBotStrategies([...newBotStrategies, strat])
                      }
                    }}
                    className={`px-2 py-1 rounded text-xs ${
                      newBotStrategies.includes(strat)
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-secondary text-muted-foreground'
                    }`}
                  >
                    {strat}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={createBot}
                disabled={loading || !newBotName}
                className="flex-1 rounded bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create Bot'}
              </button>
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-3 py-1.5 rounded bg-secondary text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowCreateForm(true)}
          disabled={bots.length >= 25}
          className="mt-4 w-full flex items-center justify-center gap-2 rounded-lg border border-dashed border-border py-2 text-sm text-muted-foreground hover:border-primary hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="h-4 w-4" />
          Add New Bot
        </button>
      )}
    </div>
  )
}

