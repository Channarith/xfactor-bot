import { useState, useEffect, useCallback } from 'react'
import { 
  TrendingUp, 
  Bot, 
  Table, 
  Newspaper,
  Users,
  Gem,
  Coins,
  Brain,
  Sparkles,
  Video,
  AlertTriangle,
  CandlestickChart,
  Crosshair,
  Activity,
  Layers,
  Database,
  RefreshCw
} from 'lucide-react'
import { PortfolioCard } from './PortfolioCard'
import { PositionsTable } from './PositionsTable'
import { NewsFeed } from './NewsFeed'
import { EquityChart } from './EquityChart'
import { BotManager } from './BotManager'
import { CollapsiblePanel } from './CollapsiblePanel'
import { TraderInsights } from './TraderInsights'
import CommodityPanel from './CommodityPanel'
import { CryptoPanel } from './CryptoPanel'
import AgenticTuning from './AgenticTuning'
import ForecastingPanel from './ForecastingPanel'
import VideoPlatformsPanel from './VideoPlatformsPanel'
import BotRiskPanel from './BotRiskPanel'
import ForexPanel from './ForexPanel'
import { useAuth } from '../context/AuthContext'
import StockAnalyzer from './StockAnalyzer'
import { useTradingMode } from '../context/TradingModeContext'
import { MomentumDashboard } from './MomentumDashboard'
import { ETFWidget } from './ETFWidget'
import { type CachedBotData, formatLastSaved } from '../utils/botDataStore'

export function Dashboard() {
  const { broker } = useTradingMode()
  
  // Broker selector state
  const [selectedBroker, setSelectedBroker] = useState<string>('all')
  const [connectedBrokers, setConnectedBrokers] = useState<Array<{broker: string, equity: number}>>([])
  
  // Cache state - tracks if we're showing cached data
  const [usingCachedData, setUsingCachedData] = useState(false)
  const [cacheLastSaved, setCacheLastSaved] = useState<string>('')
  const [isRefreshingFromBrokerage, setIsRefreshingFromBrokerage] = useState(false)
  
  // Portfolio data - will be populated when broker is connected
  const [portfolioData, setPortfolioData] = useState({
    totalValue: 0,
    dailyPnL: 0,
    dailyPnLPct: 0,
    openPositions: 0,
    exposure: 0,
  })
  
  // Listen for cached data on startup
  useEffect(() => {
    const handleCacheLoaded = (event: CustomEvent<CachedBotData>) => {
      const cached = event.detail
      if (cached.portfolioData) {
        console.log('[Dashboard] Loaded portfolio from cache:', cached.portfolioData)
        setPortfolioData({
          totalValue: cached.portfolioData.totalValue,
          dailyPnL: cached.portfolioData.dailyPnL,
          dailyPnLPct: cached.portfolioData.dailyPnLPct,
          openPositions: cached.portfolioData.openPositions,
          exposure: cached.portfolioData.exposure,
        })
        if (cached.portfolioData.connectedBrokers) {
          setConnectedBrokers(cached.portfolioData.connectedBrokers)
        }
        setUsingCachedData(true)
        setCacheLastSaved(cached.lastSaved)
      }
    }
    
    window.addEventListener('bot-cache-loaded', handleCacheLoaded as EventListener)
    return () => {
      window.removeEventListener('bot-cache-loaded', handleCacheLoaded as EventListener)
    }
  }, [])
  
  // Fetch portfolio summary with broker filter
  const fetchPortfolio = useCallback(async (isManualRefresh: boolean = false) => {
    try {
      if (isManualRefresh) {
        setIsRefreshingFromBrokerage(true)
      }
      
      const brokerParam = selectedBroker !== 'all' ? `?broker=${selectedBroker}` : ''
      const res = await fetch(`/api/positions/summary${brokerParam}`)
      if (res.ok) {
        const data = await res.json()
        // Use API data if available, otherwise fall back to broker context
        const totalValue = data.total_value || broker.portfolioValue || 0
        const dailyPnL = data.daily_pnl || 0
        
        setPortfolioData({
          totalValue,
          dailyPnL,
          dailyPnLPct: totalValue > 0 ? (dailyPnL / totalValue) * 100 : 0,
          openPositions: data.position_count || 0,
          exposure: data.positions_value || 0,
        })
        
        // Update connected brokers list (for the selector)
        if (data.broker_details && data.broker_details.length > 0) {
          setConnectedBrokers(data.broker_details.map((b: {broker: string, equity: number}) => ({
            broker: b.broker,
            equity: b.equity,
          })))
        }
        
        // Mark as live data (not cached)
        setUsingCachedData(false)
        setIsRefreshingFromBrokerage(false)
      } else if (broker.isConnected && broker.portfolioValue) {
        // Fallback to broker context if API fails
        setPortfolioData({
          totalValue: broker.portfolioValue,
          dailyPnL: 0,
          dailyPnLPct: 0,
          openPositions: 0,
          exposure: 0,
        })
        setIsRefreshingFromBrokerage(false)
      }
    } catch (e) {
      console.error('Failed to fetch portfolio:', e)
      // Fallback to broker context on error
      if (broker.isConnected && broker.portfolioValue) {
        setPortfolioData({
          totalValue: broker.portfolioValue,
          dailyPnL: 0,
          dailyPnLPct: 0,
          openPositions: 0,
          exposure: 0,
        })
      }
      setIsRefreshingFromBrokerage(false)
    }
  }, [broker.isConnected, broker.portfolioValue, selectedBroker])
  
  useEffect(() => {
    fetchPortfolio(false)
    // Reduced from 15s to 30s to prevent API rate limiting
    const interval = setInterval(() => fetchPortfolio(false), 30000)
    return () => clearInterval(interval)
  }, [fetchPortfolio])
  
  // Get broker display name
  const getBrokerLabel = (brokerId: string) => {
    const labels: Record<string, string> = {
      'all': 'All Brokers',
      'ibkr': 'IBKR',
      'alpaca': 'Alpaca',
      'schwab': 'Schwab',
      'tradier': 'Tradier',
    }
    return labels[brokerId] || brokerId.toUpperCase()
  }

  return (
    <div className="space-y-4">
      {/* Cache Indicator Banner */}
      {usingCachedData && portfolioData.totalValue > 0 && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-between">
          <div className="flex items-center gap-2 text-amber-500 text-sm">
            <Database className="h-4 w-4" />
            <span>
              Showing cached data from {formatLastSaved(cacheLastSaved)} — will refresh once connected to brokerage
            </span>
          </div>
          <button
            onClick={() => fetchPortfolio(true)}
            disabled={isRefreshingFromBrokerage}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-500 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshingFromBrokerage ? 'animate-spin' : ''}`} />
            {isRefreshingFromBrokerage ? 'Refreshing...' : 'Refresh now'}
          </button>
        </div>
      )}
      
      {/* Broker Selector - Only show if multiple brokers connected */}
      {connectedBrokers.length > 1 && (
        <div className="flex items-center gap-3 p-3 bg-secondary/30 rounded-lg border border-border">
          <span className="text-sm text-muted-foreground">View Portfolio:</span>
          <select
            value={selectedBroker}
            onChange={(e) => setSelectedBroker(e.target.value)}
            className="bg-input border border-border rounded-md px-3 py-1.5 text-sm font-medium cursor-pointer hover:border-primary transition-colors"
          >
            <option value="all">
              All Brokers (${connectedBrokers.reduce((sum, b) => sum + b.equity, 0).toLocaleString()})
            </option>
            {connectedBrokers.map((b) => (
              <option key={b.broker} value={b.broker}>
                {getBrokerLabel(b.broker)} (${b.equity.toLocaleString()})
              </option>
            ))}
          </select>
          {selectedBroker !== 'all' && (
            <span className="text-xs text-muted-foreground">
              Showing only {getBrokerLabel(selectedBroker)} data
            </span>
          )}
        </div>
      )}
      
      {/* Top Stats - Always visible */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PortfolioCard
          title="Portfolio Value"
          value={`$${portfolioData.totalValue.toLocaleString()}`}
          subtitle={
            portfolioData.totalValue > 0 
              ? usingCachedData
                ? `📦 Cached from ${formatLastSaved(cacheLastSaved)}`
                : connectedBrokers.length === 1
                  ? `🟢 Live from ${getBrokerLabel(connectedBrokers[0].broker)}`
                  : selectedBroker === 'all' && connectedBrokers.length > 1
                    ? `🟢 Live - Combined from ${connectedBrokers.length} brokers`
                    : `🟢 Live from ${getBrokerLabel(selectedBroker)}`
              : "Connect broker to see data"
          }
          trend={portfolioData.totalValue > 0 ? "up" : "neutral"}
        />
        <PortfolioCard
          title="Today's P&L"
          value={`${portfolioData.dailyPnL >= 0 ? '+' : ''}$${portfolioData.dailyPnL.toLocaleString()}`}
          subtitle={`${portfolioData.dailyPnLPct >= 0 ? '+' : ''}${portfolioData.dailyPnLPct.toFixed(2)}%`}
          trend={portfolioData.dailyPnL >= 0 ? "up" : "down"}
        />
        <PortfolioCard
          title="Open Positions"
          value={portfolioData.openPositions.toString()}
          subtitle={portfolioData.exposure > 0 ? `$${(portfolioData.exposure / 1000).toFixed(1)}K exposure` : "No positions"}
          trend="neutral"
        />
      </div>

      {/* Stock Analyzer - Deep Analysis with Overlays */}
      <CollapsiblePanel 
        title="📊 Stock Analyzer" 
        icon={<Crosshair className="h-5 w-5" />}
        badge="NEW"
        defaultExpanded={true}
      >
        <StockAnalyzer />
      </CollapsiblePanel>

      {/* AI Market Forecasting - NEW v1.0.3 */}
      <CollapsiblePanel 
        title="🔮 AI Market Forecasting" 
        icon={<Sparkles className="h-5 w-5" />}
        badge="NEW"
        defaultExpanded={false}
      >
        <ForecastingPanel />
      </CollapsiblePanel>

      {/* News & Sentiment Feed - TOP PRIORITY */}
      <CollapsiblePanel 
        title="📰 Live News & Sentiment Feed" 
        icon={<Newspaper className="h-5 w-5" />}
        badge="100"
        defaultExpanded={true}
      >
        <NewsFeed maxItems={100} itemsPerPage={10} />
      </CollapsiblePanel>
      
      {/* Momentum Scanner - NEW v1.2.1 */}
      <CollapsiblePanel 
        title="📊 Momentum Scanner" 
        icon={<Activity className="h-5 w-5" />}
        badge="12k+"
        defaultExpanded={true}
      >
        <MomentumDashboard />
      </CollapsiblePanel>
      
      {/* ETF Overview Widget - NEW v1.2.2 */}
      <CollapsiblePanel 
        title="📈 ETF Overview" 
        icon={<Layers className="h-5 w-5" />}
        badge="50+"
        defaultExpanded={true}
      >
        <ETFWidget />
      </CollapsiblePanel>
      
      {/* Main Content - Always full width (Settings moved to Setup page) */}
      <div className="space-y-4">
        {/* Two-column grid for Equity and Bot Manager */}
        <div className="grid gap-4 grid-cols-1 xl:grid-cols-2">
          <CollapsiblePanel 
            title="Equity Curve" 
            icon={<TrendingUp className="h-5 w-5" />}
            defaultExpanded={true}
          >
            <EquityChart height={280} />
          </CollapsiblePanel>
          
          <CollapsiblePanel 
            title="Bot Manager" 
            icon={<Bot className="h-5 w-5" />}
            defaultExpanded={true}
          >
            <BotManagerInner />
          </CollapsiblePanel>
        </div>
        
        {/* Two-column grid for Agentic Tuning and Positions */}
        <div className="grid gap-4 grid-cols-1 xl:grid-cols-2">
          <CollapsiblePanel 
            title="Agentic Tuning" 
            icon={<Brain className="h-5 w-5" />}
            badge="ATRWAC"
            defaultExpanded={false}
          >
            <AgenticTuning />
          </CollapsiblePanel>
          
          <CollapsiblePanel 
            title="Open Positions" 
            icon={<Table className="h-5 w-5" />}
            badge={portfolioData.openPositions}
            defaultExpanded={false}
          >
            <PositionsTableInner />
          </CollapsiblePanel>
        </div>
      </div>
      
      {/* Video Platforms Intelligence - NEW v1.0.3 */}
      <CollapsiblePanel 
        title="📹 Video Platforms Intelligence" 
        icon={<Video className="h-5 w-5" />}
        badge="NEW"
        defaultExpanded={false}
      >
        <VideoPlatformsPanel />
      </CollapsiblePanel>

      {/* Bot Risk Management - NEW v1.0.3 */}
      <CollapsiblePanel 
        title="🛡️ Bot Risk Management" 
        icon={<AlertTriangle className="h-5 w-5" />}
        badge="risk"
        defaultExpanded={false}
      >
        <BotRiskPanel />
      </CollapsiblePanel>

      {/* Forex Trading - NEW v1.0.2 */}
      <CollapsiblePanel 
        title="💱 Forex Trading" 
        icon={<CandlestickChart className="h-5 w-5" />}
        badge="forex"
        defaultExpanded={false}
      >
        <ForexPanel />
      </CollapsiblePanel>

      {/* Cryptocurrency Trading */}
      <CollapsiblePanel 
        title="₿ Cryptocurrency Trading" 
        icon={<Coins className="h-5 w-5" />}
        badge="crypto"
        defaultExpanded={true}
      >
        <CryptoPanel />
      </CollapsiblePanel>
      
      {/* Commodities & Resources */}
      <CollapsiblePanel 
        title="⛏️ Commodities & Resources" 
        icon={<Gem className="h-5 w-5" />}
        badge="minerals"
        defaultExpanded={false}
      >
        <CommodityPanel />
      </CollapsiblePanel>
      
      {/* Trader Insights & Market Intelligence */}
      <CollapsiblePanel 
        title="Top Traders & Insider Activity" 
        icon={<Users className="h-5 w-5" />}
        defaultExpanded={true}
      >
        <TraderInsights />
      </CollapsiblePanel>
    </div>
  )
}

// Inner components that strip the card wrapper
function BotManagerInner() {
  const { token } = useAuth()
  return <BotManager token={token} />
}

function PositionsTableInner() {
  return <PositionsTable />
}
