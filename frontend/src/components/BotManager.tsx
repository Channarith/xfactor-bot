import { useState, useEffect, useMemo } from 'react'
import { 
  Bot, Play, Pause, Square, Plus, Trash2,
  ChevronDown, ChevronUp,
  Search, SortAsc, SortDesc, X, RefreshCw,
  Activity, TrendingUp, TrendingDown, Clock, AlertCircle, Target, BarChart3,
  Lock, ShieldAlert, LineChart
} from 'lucide-react'
import { BotPerformanceChart } from './BotPerformanceChart'
import { getApiBaseUrl } from '../config/api'

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
    uptime_seconds?: number
  }
}

interface BotManagerProps {
  token?: string
}

export function BotManager({ token = '' }: BotManagerProps) {
  const [bots, setBots] = useState<BotSummary[]>([])
  const [selectedBot, setSelectedBot] = useState<BotDetails | null>(null)
  const [showBotDetail, setShowBotDetail] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [expandedBot, setExpandedBot] = useState<string | null>(null)
  const [performanceBot, setPerformanceBot] = useState<{ id: string; name: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showAuthModal, setShowAuthModal] = useState(false)
  
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
      // Use explicit URL for desktop app compatibility
      const baseUrl = getApiBaseUrl();
      const url = baseUrl ? `${baseUrl}/api/bots/summary` : '/api/bots/summary';
      
      console.log('[BotManager] === FETCH BOTS DEBUG ===');
      console.log('[BotManager] Base URL:', baseUrl || '(relative)');
      console.log('[BotManager] Full URL:', url);
      console.log('[BotManager] Window location:', window.location.href);
      console.log('[BotManager] Is Tauri?:', typeof window !== 'undefined' && (window.hasOwnProperty('__TAURI__') || window.hasOwnProperty('__TAURI_INTERNALS__')));
      
      const response = await fetch(url);
      
      console.log('[BotManager] Response status:', response.status, response.statusText);
      console.log('[BotManager] Response headers:', Object.fromEntries(response.headers.entries()));
      
      if (!response.ok) {
        const errorBody = await response.text().catch(() => 'Could not read response body');
        console.error('[BotManager] Error response body:', errorBody);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('[BotManager] Fetched', data.bots?.length || 0, 'bots successfully');
      setBots(data.bots || []);
      setError(''); // Clear any previous errors
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'Unknown error';
      const errorStack = e instanceof Error ? e.stack : '';
      
      console.error('[BotManager] === FETCH BOTS ERROR ===');
      console.error('[BotManager] Error type:', e?.constructor?.name);
      console.error('[BotManager] Error message:', errorMessage);
      console.error('[BotManager] Error stack:', errorStack);
      console.error('[BotManager] Is network error?:', errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('Failed to fetch'));
      
      // Check if backend is reachable at all
      try {
        const healthUrl = getApiBaseUrl() ? `${getApiBaseUrl()}/health` : '/health';
        console.log('[BotManager] Checking backend health at:', healthUrl);
        const healthResponse = await fetch(healthUrl);
        console.log('[BotManager] Health check status:', healthResponse.status);
      } catch (healthError) {
        console.error('[BotManager] Health check also failed - backend is unreachable');
      }
      
      setError(`Failed to fetch bots: ${errorMessage}`);
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
      
      if (response.status === 401) {
        setShowAuthModal(true)
        setLoading(false)
        return
      }
      
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
      const response = await fetch(`/api/bots/${botId}/${action}`, {
        method: 'POST',
        headers: authHeaders,
      })
      
      if (response.status === 401) {
        setShowAuthModal(true)
        return
      }
      
      if (!response.ok) {
        const data = await response.json()
        setError(data.detail || `Failed to ${action} bot`)
        return
      }
      
      fetchBots()
      // Refresh selected bot if it's the one being controlled
      if (selectedBot?.id === botId) {
        fetchBotDetails(botId)
      }
    } catch (e) {
      setError(`Failed to ${action} bot`)
    }
  }

  const fetchBotDetails = async (botId: string) => {
    try {
      const response = await fetch(`/api/bots/${botId}`, {
        headers: authHeaders,
      })
      
      if (response.status === 401) {
        setShowAuthModal(true)
        return
      }
      
      if (response.ok) {
        const data = await response.json()
        setSelectedBot(data)
        setShowBotDetail(true)
      } else {
        setError('Failed to fetch bot details')
      }
    } catch (e) {
      setError('Failed to fetch bot details')
    }
  }

  const deleteBot = async (botId: string) => {
    if (!confirm('Are you sure you want to delete this bot?')) return
    
    try {
      const response = await fetch(`/api/bots/${botId}`, {
        method: 'DELETE',
        headers: authHeaders,
      })
      
      if (response.status === 401) {
        setShowAuthModal(true)
        return
      }
      
      fetchBots()
    } catch (e) {
      setError('Failed to delete bot')
    }
  }

  const controlAllBots = async (action: string) => {
    try {
      const response = await fetch(`/api/bots/${action}`, {
        method: 'POST',
        headers: authHeaders,
      })
      
      if (response.status === 401) {
        setShowAuthModal(true)
        return
      }
      
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
            ({filteredBots.length}/{bots.length} shown, max 100)
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
                  <button 
                    onClick={() => {
                      fetchBotDetails(bot.id)
                      setPerformanceBot({ id: bot.id, name: bot.name })
                    }}
                    className="font-medium text-sm hover:text-primary hover:underline text-left flex items-center gap-1"
                    title="View bot details and performance"
                  >
                    <LineChart className="h-3 w-3 text-muted-foreground" />
                    {bot.name}
                  </button>
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
              <label className="text-xs text-muted-foreground flex items-center gap-2">
                Symbols (comma-separated)
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-xfactor-teal/20 text-xfactor-teal">
                  40+ Global Exchanges
                </span>
              </label>
              <input
                type="text"
                value={newBotSymbols}
                onChange={(e) => setNewBotSymbols(e.target.value)}
                placeholder="AAPL, MSFT, 7203.T, HSBA.L, 9988.HK, TSM, SAP.DE..."
                className="w-full mt-1 rounded bg-input px-3 py-2 text-sm border border-border"
              />
              <p className="text-[10px] text-muted-foreground mt-1">
                🌍 <strong>Any stock worldwide</strong> - Use exchange suffix for international: .L (London), .T (Tokyo), .HK (Hong Kong), .DE (Germany), .SS (Shanghai), .AX (Australia), .TO (Toronto), etc.
              </p>
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
          disabled={bots.length >= 100}
          className="mt-4 w-full flex items-center justify-center gap-2 rounded-lg border border-dashed border-border py-2 text-sm text-muted-foreground hover:border-primary hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="h-4 w-4" />
          Add New Bot
        </button>
      )}
      
      {/* Bot Detail Modal */}
      {showBotDetail && selectedBot && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-xl border border-border max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-border sticky top-0 bg-card">
              <div className="flex items-center gap-3">
                <div className={`h-3 w-3 rounded-full ${getStatusColor(selectedBot.status)}`} />
                <div>
                  <h2 className="text-lg font-bold">{selectedBot.name}</h2>
                  <p className="text-xs text-muted-foreground">{selectedBot.description || `Bot ID: ${selectedBot.id}`}</p>
                </div>
              </div>
              <button
                onClick={() => setShowBotDetail(false)}
                className="p-2 rounded hover:bg-secondary"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            {/* Bot Stats */}
            <div className="p-4 space-y-4">
              {/* Status & Controls */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    selectedBot.status === 'running' ? 'bg-profit/20 text-profit' :
                    selectedBot.status === 'paused' ? 'bg-yellow-500/20 text-yellow-500' :
                    selectedBot.status === 'error' ? 'bg-loss/20 text-loss' :
                    'bg-muted text-muted-foreground'
                  }`}>
                    {selectedBot.status.toUpperCase()}
                  </span>
                  {selectedBot.status === 'running' && (
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Activity className="h-3 w-3 animate-pulse" />
                      Live
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  {selectedBot.status === 'running' ? (
                    <>
                      <button
                        onClick={() => controlBot(selectedBot.id, 'pause')}
                        className="px-3 py-1 rounded bg-yellow-500/20 text-yellow-500 text-sm"
                      >
                        <Pause className="h-4 w-4 inline mr-1" />
                        Pause
                      </button>
                      <button
                        onClick={() => controlBot(selectedBot.id, 'stop')}
                        className="px-3 py-1 rounded bg-loss/20 text-loss text-sm"
                      >
                        <Square className="h-4 w-4 inline mr-1" />
                        Stop
                      </button>
                    </>
                  ) : selectedBot.status === 'paused' ? (
                    <button
                      onClick={() => controlBot(selectedBot.id, 'resume')}
                      className="px-3 py-1 rounded bg-profit/20 text-profit text-sm"
                    >
                      <Play className="h-4 w-4 inline mr-1" />
                      Resume
                    </button>
                  ) : (
                    <button
                      onClick={() => controlBot(selectedBot.id, 'start')}
                      className="px-3 py-1 rounded bg-profit/20 text-profit text-sm"
                    >
                      <Play className="h-4 w-4 inline mr-1" />
                      Start
                    </button>
                  )}
                </div>
              </div>
              
              {/* Performance Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-background/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <TrendingUp className="h-3 w-3" />
                    Daily P&L
                  </div>
                  <div className={`text-lg font-bold ${selectedBot.stats.daily_pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                    {selectedBot.stats.daily_pnl >= 0 ? '+' : ''}${selectedBot.stats.daily_pnl.toFixed(2)}
                  </div>
                </div>
                <div className="bg-background/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <BarChart3 className="h-3 w-3" />
                    Trades Today
                  </div>
                  <div className="text-lg font-bold">{selectedBot.stats.trades_today}</div>
                </div>
                <div className="bg-background/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <Target className="h-3 w-3" />
                    Win Rate
                  </div>
                  <div className="text-lg font-bold">
                    {selectedBot.stats.win_rate ? `${(selectedBot.stats.win_rate * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                </div>
                <div className="bg-background/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <Clock className="h-3 w-3" />
                    Uptime
                  </div>
                  <div className="text-lg font-bold">{formatUptime(selectedBot.stats.uptime_seconds || 0)}</div>
                </div>
              </div>
              
              {/* Additional Stats */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-background/50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold">{selectedBot.stats.signals_generated || 0}</div>
                  <div className="text-xs text-muted-foreground">Signals</div>
                </div>
                <div className="bg-background/50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold">{selectedBot.stats.open_positions || 0}</div>
                  <div className="text-xs text-muted-foreground">Open Positions</div>
                </div>
                <div className="bg-background/50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-loss">{selectedBot.stats.errors_count || 0}</div>
                  <div className="text-xs text-muted-foreground">Errors</div>
                </div>
              </div>
              
              {/* Configuration */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium flex items-center gap-2">
                  <Bot className="h-4 w-4" />
                  Configuration
                </h3>
                
                <div className="bg-background/50 rounded-lg p-3 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Symbols</span>
                    <span className="font-mono text-xs">
                      {selectedBot.config.symbols?.join(', ') || 'None'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Strategies</span>
                    <span className="font-mono text-xs">
                      {selectedBot.config.strategies?.slice(0, 3).join(', ')}
                      {(selectedBot.config.strategies?.length || 0) > 3 && ` +${selectedBot.config.strategies!.length - 3} more`}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Max Position Size</span>
                    <span>${selectedBot.config.max_position_size?.toLocaleString() || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Max Positions</span>
                    <span>{selectedBot.config.max_positions || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Max Daily Loss</span>
                    <span>{selectedBot.config.max_daily_loss_pct || 0}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Trade Frequency</span>
                    <span>Every {selectedBot.config.trade_frequency_seconds || 60}s</span>
                  </div>
                </div>
              </div>
              
              {/* Timestamps */}
              <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t border-border">
                <div>Created: {selectedBot.created_at ? new Date(selectedBot.created_at).toLocaleString() : 'N/A'}</div>
                {selectedBot.started_at && <div>Started: {new Date(selectedBot.started_at).toLocaleString()}</div>}
                {selectedBot.stopped_at && <div>Stopped: {new Date(selectedBot.stopped_at).toLocaleString()}</div>}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Auth Required Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-card rounded-xl border border-amber-500/50 max-w-md w-full shadow-2xl shadow-amber-500/10 animate-in fade-in zoom-in duration-200">
            {/* Modal Header */}
            <div className="flex items-center gap-3 p-5 border-b border-border bg-gradient-to-r from-amber-500/10 to-orange-500/10 rounded-t-xl">
              <div className="p-3 rounded-full bg-amber-500/20">
                <ShieldAlert className="h-6 w-6 text-amber-500" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-foreground">Admin Access Required</h2>
                <p className="text-sm text-muted-foreground">Authentication needed to continue</p>
              </div>
            </div>
            
            {/* Modal Body */}
            <div className="p-5 space-y-4">
              <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-500/5 border border-amber-500/20">
                <Lock className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <p className="text-foreground font-medium mb-1">
                    This action requires admin privileges
                  </p>
                  <p className="text-muted-foreground">
                    To start, stop, pause, create, or delete bots, you must first unlock admin access using the 
                    <span className="inline-flex items-center gap-1 mx-1 px-2 py-0.5 rounded bg-secondary text-foreground font-mono text-xs">
                      <Lock className="h-3 w-3" /> Admin
                    </span>
                    button in the header.
                  </p>
                </div>
              </div>
              
              <div className="text-sm text-muted-foreground">
                <p className="font-medium text-foreground mb-2">How to unlock:</p>
                <ol className="list-decimal list-inside space-y-1 ml-1">
                  <li>Click the <strong>Admin</strong> lock icon in the top navigation</li>
                  <li>Enter your admin password</li>
                  <li>The lock will turn green when unlocked</li>
                  <li>Try your action again</li>
                </ol>
              </div>
            </div>
            
            {/* Modal Footer */}
            <div className="flex justify-end gap-3 p-4 border-t border-border bg-secondary/30 rounded-b-xl">
              <button
                onClick={() => setShowAuthModal(false)}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Bot Performance Chart Modal with Details */}
      {performanceBot && (
        <BotPerformanceChart
          botId={performanceBot.id}
          botName={performanceBot.name}
          botDetails={selectedBot}
          onClose={() => {
            setPerformanceBot(null)
            setSelectedBot(null)
          }}
        />
      )}
    </div>
  )
}

