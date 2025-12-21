import { useState, useEffect } from 'react'
import { 
  TrendingUp, 
  Bot, 
  Table, 
  Lock, 
  Newspaper,
  Users,
  Gem,
  Coins,
  Brain,
  Sparkles,
  Video,
  AlertTriangle,
  CandlestickChart,
  Crosshair
} from 'lucide-react'
import { useDemoMode, useFeatureAvailable } from '../contexts/DemoModeContext'
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
import StockAnalyzer from './StockAnalyzer'

export function Dashboard() {
  const { isDemoMode, isUnlocked } = useDemoMode()
  const { isFullFeaturesAvailable } = useFeatureAvailable()
  
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
          setPortfolioData({
            totalValue: data.total_value || 0,
            dailyPnL: data.daily_pnl || 0,
            dailyPnLPct: data.total_value > 0 ? (data.daily_pnl / data.total_value) * 100 : 0,
            openPositions: data.position_count || 0,
            exposure: data.positions_value || 0,
          })
        }
      } catch (e) {
        console.error('Failed to fetch portfolio:', e)
      }
    }
    
    fetchPortfolio()
    const interval = setInterval(fetchPortfolio, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-4">
      {/* Top Stats - Always visible */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PortfolioCard
          title="Portfolio Value"
          value={`$${portfolioData.totalValue.toLocaleString()}`}
          subtitle="+2.4% MTD"
          trend="up"
        />
        <PortfolioCard
          title="Today's P&L"
          value={`+$${portfolioData.dailyPnL.toLocaleString()}`}
          subtitle={`+${portfolioData.dailyPnLPct}%`}
          trend="up"
        />
        <PortfolioCard
          title="Open Positions"
          value={portfolioData.openPositions.toString()}
          subtitle={`$${(portfolioData.exposure / 1000).toFixed(0)}K exposure`}
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
      
      {/* Main Content - Full width in MAX mode, with sidebar in restricted mode */}
      <div className={`grid gap-4 ${isFullFeaturesAvailable ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-3'}`}>
        {/* Main Column - Full width when settings moved to Setup page */}
        <div className={`space-y-4 ${!isFullFeaturesAvailable ? 'lg:col-span-2' : ''}`}>
          {/* Two-column grid for Equity and Bot Manager in MAX mode */}
          <div className={`grid gap-4 ${isFullFeaturesAvailable ? 'grid-cols-1 xl:grid-cols-2' : 'grid-cols-1'}`}>
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
          
          {/* Two-column grid for Agentic Tuning and Positions in MAX mode */}
          <div className={`grid gap-4 ${isFullFeaturesAvailable ? 'grid-cols-1 xl:grid-cols-2' : 'grid-cols-1'}`}>
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
        
        {/* Right Column - Only shown in restricted mode */}
        {!isFullFeaturesAvailable && (
          <div className="space-y-4">
            {/* Restricted Mode - Show info message */}
            <div className="bg-card rounded-xl border border-slate-600 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-3 bg-slate-700 rounded-full">
                  <Lock className="h-6 w-6 text-slate-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg text-slate-300">Available Features</h3>
                  <p className="text-sm text-muted-foreground">Additional trading features require authentication</p>
                </div>
              </div>
              <div className="bg-slate-800 rounded-lg p-4">
                <h4 className="text-sm font-medium text-slate-400 mb-2">Available Features:</h4>
                <ul className="text-sm text-slate-400 space-y-1">
                  <li>✓ AI Market Forecasting</li>
                  <li>✓ News & Sentiment Analysis</li>
                  <li>✓ Stock Analyzer</li>
                  <li>✓ Video Platforms Intelligence</li>
                  <li>✓ Forex & Crypto Research</li>
                  <li>✓ Trading Glossary (500+ terms)</li>
                </ul>
              </div>
            </div>
          </div>
        )}
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
  return <BotManager />
}

function PositionsTableInner() {
  return <PositionsTable />
}
