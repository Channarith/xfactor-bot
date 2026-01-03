import { useState, useEffect } from 'react'
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
  Activity
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

export function Dashboard() {
  const { broker } = useTradingMode()
  
  // Portfolio data - will be populated when broker is connected
  const [portfolioData, setPortfolioData] = useState({
    totalValue: 0,
    dailyPnL: 0,
    dailyPnLPct: 0,
    openPositions: 0,
    exposure: 0,
  })
  
  // Fetch portfolio summary
  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const res = await fetch('/api/positions/summary')
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
        } else if (broker.isConnected && broker.portfolioValue) {
          // Fallback to broker context if API fails
          setPortfolioData({
            totalValue: broker.portfolioValue,
            dailyPnL: 0,
            dailyPnLPct: 0,
            openPositions: 0,
            exposure: 0,
          })
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
      }
    }
    
    fetchPortfolio()
    const interval = setInterval(fetchPortfolio, 15000)
    return () => clearInterval(interval)
  }, [broker.isConnected, broker.portfolioValue])

  return (
    <div className="space-y-4">
      {/* Top Stats - Always visible */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PortfolioCard
          title="Portfolio Value"
          value={`$${portfolioData.totalValue.toLocaleString()}`}
          subtitle={portfolioData.totalValue > 0 ? "Live from broker" : "Connect broker to see data"}
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
            badge="40"
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
