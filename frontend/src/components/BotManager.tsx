import { useState, useEffect, useMemo } from 'react'
import { 
  Bot, Play, Pause, Square, Plus, Trash2, Settings, 
  Activity, AlertTriangle, ChevronDown, ChevronUp,
  Search, SortAsc, SortDesc, X, Filter, RefreshCw
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
  
  // All available strategies
  const ALL_STRATEGIES = [
    { name: 'Technical', category: 'Technical Analysis', description: 'RSI, MACD, chart patterns' },
    { name: 'Momentum', category: 'Momentum', description: 'Price and volume momentum' },
    { name: 'MeanReversion', category: 'Mean Reversion', description: 'Fade extreme moves' },
    { name: 'NewsSentiment', category: 'Sentiment', description: 'News-based trading' },
    { name: 'Breakout', category: 'Technical Analysis', description: 'Price breakouts' },
    { name: 'TrendFollowing', category: 'Momentum', description: 'Follow trends' },
    { name: 'Scalping', category: 'Short-Term', description: 'Quick small profits' },
    { name: 'SwingTrading', category: 'Medium-Term', description: 'Multi-day holds' },
    { name: 'VWAP', category: 'Technical Analysis', description: 'Volume-weighted strategies' },
    { name: 'RSI', category: 'Technical Analysis', description: 'Overbought/oversold signals' },
    { name: 'MACD', category: 'Technical Analysis', description: 'MACD crossovers' },
    { name: 'BollingerBands', category: 'Technical Analysis', description: 'Band breakouts' },
    { name: 'MovingAverageCrossover', category: 'Technical Analysis', description: 'SMA/EMA crosses' },
    { name: 'InsiderFollowing', category: 'Sentiment', description: 'Follow insider trades' },
    { name: 'SocialSentiment', category: 'Sentiment', description: 'Social media buzz' },
    { name: 'AIAnalysis', category: 'AI/ML', description: 'AI pattern recognition' },
  ]
  
  // New bot form state
  const [newBotName, setNewBotName] = useState('')
  const [newBotSymbols, setNewBotSymbols] = useState('SPY,QQQ,AAPL,MSFT,NVDA')
  const [newBotStrategies, setNewBotStrategies] = useState<string[]>(ALL_STRATEGIES.map(s => s.name))
  const [newBotAIPrompt, setNewBotAIPrompt] = useState('')
  const [aiInterpretation, setAiInterpretation] = useState<any>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [instrumentType, setInstrumentType] = useState('stock')
  
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
    setAiInterpretation(null)
    
    try {
      const response = await fetch('/api/bots/', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          name: newBotName,
          symbols: newBotSymbols.split(',').map(s => s.trim()),
          strategies: newBotStrategies,
          ai_strategy_prompt: newBotAIPrompt,
          instrument_type: instrumentType,
        }),
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.ai_interpretation) {
          setAiInterpretation(data.ai_interpretation)
        }
        setShowCreateForm(false)
        setNewBotAIPrompt('')
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
        <div className="mt-4 p-4 border border-border/50 rounded-lg bg-card/50">
          <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
            <Bot className="h-4 w-4" />
            Create New Bot
          </h3>
          <div className="space-y-4">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">Bot Name *</label>
                <input
                  type="text"
                  value={newBotName}
                  onChange={(e) => setNewBotName(e.target.value)}
                  placeholder="My Trading Bot"
                  className="w-full mt-1 rounded bg-input px-3 py-2 text-sm border border-border"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Instrument Type</label>
                <select
                  value={instrumentType}
                  onChange={(e) => setInstrumentType(e.target.value)}
                  className="w-full mt-1 rounded bg-input px-3 py-2 text-sm border border-border"
                >
                  <option value="stock">Stocks</option>
                  <option value="options">Options</option>
                  <option value="futures">Futures</option>
                  <option value="crypto">Crypto</option>
                </select>
              </div>
            </div>
            
            <div>
              <label className="text-xs text-muted-foreground">Symbols (comma-separated)</label>
              <input
                type="text"
                value={newBotSymbols}
                onChange={(e) => setNewBotSymbols(e.target.value)}
                placeholder="SPY, QQQ, AAPL, MSFT, NVDA"
                className="w-full mt-1 rounded bg-input px-3 py-2 text-sm border border-border"
              />
            </div>
            
            {/* AI Strategy Prompt */}
            <div className="p-3 rounded-lg bg-gradient-to-r from-violet-500/10 to-indigo-500/10 border border-violet-500/20">
              <label className="text-xs font-medium text-violet-300 flex items-center gap-1">
                🤖 AI Strategy Prompt (Optional)
              </label>
              <p className="text-[10px] text-muted-foreground mt-0.5 mb-2">
                Describe your strategy in plain English. AI will configure the bot accordingly.
              </p>
              <textarea
                value={newBotAIPrompt}
                onChange={(e) => setNewBotAIPrompt(e.target.value)}
                placeholder="Example: I want to follow momentum stocks that are breaking out on high volume. Focus on tech stocks, use tight stop losses, and take profits quickly. Follow insider buying activity and social media buzz."
                className="w-full rounded bg-input/50 px-3 py-2 text-sm border border-border resize-none"
                rows={3}
              />
            </div>
            
            {/* AI Interpretation Result */}
            {aiInterpretation && (
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                <p className="text-xs font-medium text-green-400 mb-2">✨ AI Interpretation</p>
                <p className="text-xs text-muted-foreground">{aiInterpretation.interpretation}</p>
                {aiInterpretation.warnings?.length > 0 && (
                  <div className="mt-2">
                    <p className="text-[10px] text-yellow-400">Warnings:</p>
                    {aiInterpretation.warnings.map((w: string, i: number) => (
                      <p key={i} className="text-[10px] text-yellow-300/70">• {w}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* Strategies Section */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs text-muted-foreground">
                  Trading Strategies ({newBotStrategies.length} selected)
                </label>
                <div className="flex gap-1">
                  <button
                    onClick={() => setNewBotStrategies(ALL_STRATEGIES.map(s => s.name))}
                    className="text-[10px] text-primary hover:underline"
                  >
                    Select All
                  </button>
                  <span className="text-muted-foreground">|</span>
                  <button
                    onClick={() => setNewBotStrategies([])}
                    className="text-[10px] text-muted-foreground hover:underline"
                  >
                    Clear
                  </button>
                </div>
              </div>
              
              {/* Strategy Categories */}
              {['Technical Analysis', 'Momentum', 'Mean Reversion', 'Sentiment', 'Short-Term', 'Medium-Term', 'AI/ML'].map((category) => (
                <div key={category} className="mb-2">
                  <p className="text-[10px] text-muted-foreground mb-1">{category}</p>
                  <div className="flex flex-wrap gap-1">
                    {ALL_STRATEGIES.filter(s => s.category === category).map((strat) => (
                      <button
                        key={strat.name}
                        onClick={() => {
                          if (newBotStrategies.includes(strat.name)) {
                            setNewBotStrategies(newBotStrategies.filter(s => s !== strat.name))
                          } else {
                            setNewBotStrategies([...newBotStrategies, strat.name])
                          }
                        }}
                        title={strat.description}
                        className={`px-2 py-1 rounded text-[10px] transition-colors ${
                          newBotStrategies.includes(strat.name)
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
                        }`}
                      >
                        {strat.name}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            
            {/* Advanced Options Toggle */}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              {showAdvanced ? '▼' : '▶'} Advanced Options
            </button>
            
            {showAdvanced && (
              <div className="p-3 rounded bg-secondary/30 space-y-3">
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-[10px] text-muted-foreground">Max Position Size</label>
                    <input
                      type="number"
                      defaultValue={25000}
                      className="w-full mt-1 rounded bg-input px-2 py-1 text-xs border border-border"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground">Max Positions</label>
                    <input
                      type="number"
                      defaultValue={10}
                      className="w-full mt-1 rounded bg-input px-2 py-1 text-xs border border-border"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground">Daily Loss Limit %</label>
                    <input
                      type="number"
                      defaultValue={2}
                      className="w-full mt-1 rounded bg-input px-2 py-1 text-xs border border-border"
                    />
                  </div>
                </div>
              </div>
            )}
            
            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={createBot}
                disabled={loading || !newBotName}
                className="flex-1 rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4" />
                    Create Bot
                  </>
                )}
              </button>
              <button
                onClick={() => {
                  setShowCreateForm(false)
                  setAiInterpretation(null)
                }}
                className="px-4 py-2 rounded bg-secondary text-sm hover:bg-secondary/80"
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

