import { useState, useEffect } from 'react'
import { 
  TrendingUp, 
  Bot, 
  Table, 
  Settings, 
  Shield, 
  Lock, 
  Newspaper,
  Wallet,
  Users,
  Gem,
  Coins,
  DollarSign,
  Brain
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { PortfolioCard } from './PortfolioCard'
import { PositionsTable } from './PositionsTable'
import { StrategyPanel } from './StrategyPanel'
import { NewsFeed } from './NewsFeed'
import { RiskControls } from './RiskControls'
import { AdminPanel } from './AdminPanel'
import { EquityChart } from './EquityChart'
import { BotManager } from './BotManager'
import { CollapsiblePanel } from './CollapsiblePanel'
import { TraderInsights } from './TraderInsights'
import CommodityPanel from './CommodityPanel'
import { CryptoPanel } from './CryptoPanel'
import { FeeTracker } from './FeeTracker'
import AgenticTuning from './AgenticTuning'

export function Dashboard() {
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

      {/* News & Sentiment Feed - TOP PRIORITY */}
      <CollapsiblePanel 
        title="📰 Live News & Sentiment Feed" 
        icon={<Newspaper className="h-5 w-5" />}
        badge="100"
        defaultExpanded={true}
      >
        <NewsFeed maxItems={100} itemsPerPage={10} />
      </CollapsiblePanel>
      
      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left Column - Positions & Chart */}
        <div className="lg:col-span-2 space-y-4">
          <CollapsiblePanel 
            title="Equity Curve" 
            icon={<TrendingUp className="h-5 w-5" />}
            defaultExpanded={true}
          >
            <EquityChart height={240} />
          </CollapsiblePanel>
          
          <CollapsiblePanel 
            title="Bot Manager" 
            icon={<Bot className="h-5 w-5" />}
            badge="10"
            defaultExpanded={true}
          >
            <BotManagerInner />
          </CollapsiblePanel>
          
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
        
        {/* Right Column - Controls */}
        <div className="space-y-4">
          <CollapsiblePanel 
            title="Strategy Controls" 
            icon={<Settings className="h-5 w-5" />}
            defaultExpanded={true}
          >
            <StrategyPanelInner />
          </CollapsiblePanel>
          
          <CollapsiblePanel 
            title="Risk Management" 
            icon={<Shield className="h-5 w-5" />}
            defaultExpanded={false}
          >
            <RiskControlsInner />
          </CollapsiblePanel>
          
          <CollapsiblePanel 
            title="Admin Panel" 
            icon={<Lock className="h-5 w-5" />}
            defaultExpanded={false}
          >
            <AdminPanelInner />
          </CollapsiblePanel>
          
          <CollapsiblePanel 
            title="Integrations" 
            icon={<Wallet className="h-5 w-5" />}
            defaultExpanded={false}
          >
            <IntegrationsPanel />
          </CollapsiblePanel>
          
          <CollapsiblePanel 
            title="Fees & Expenses" 
            icon={<DollarSign className="h-5 w-5" />}
            badge="costs"
            defaultExpanded={false}
          >
            <FeeTracker />
          </CollapsiblePanel>
        </div>
      </div>
      
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

function StrategyPanelInner() {
  return <StrategyPanel />
}

function RiskControlsInner() {
  const { token } = useAuth()
  return <RiskControls token={token} />
}

function AdminPanelInner() {
  return <AdminPanel />
}

function IntegrationsPanel() {
  const brokers = [
    { name: 'Interactive Brokers', status: 'connected', color: 'text-profit' },
    { name: 'Alpaca', status: 'ready', color: 'text-muted-foreground' },
    { name: 'Charles Schwab', status: 'ready', color: 'text-muted-foreground' },
    { name: 'Tradier', status: 'ready', color: 'text-muted-foreground' },
  ]
  
  const dataSources = [
    { name: 'TradingView', status: 'webhooks active', color: 'text-profit' },
    { name: 'Polygon.io', status: 'ready', color: 'text-muted-foreground' },
    { name: 'Yahoo Finance', status: 'enabled', color: 'text-profit' },
  ]
  
  const banking = [
    { name: 'Plaid', status: 'ready', color: 'text-muted-foreground' },
  ]

  return (
    <div className="space-y-4">
      {/* Brokers */}
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2">Brokers</h4>
        <div className="space-y-2">
          {brokers.map((broker) => (
            <div key={broker.name} className="flex items-center justify-between text-sm">
              <span className="text-foreground">{broker.name}</span>
              <span className={broker.color}>{broker.status}</span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Data Sources */}
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2">Data Sources</h4>
        <div className="space-y-2">
          {dataSources.map((source) => (
            <div key={source.name} className="flex items-center justify-between text-sm">
              <span className="text-foreground">{source.name}</span>
              <span className={source.color}>{source.status}</span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Banking */}
      <div>
        <h4 className="text-sm font-medium text-muted-foreground mb-2">Banking</h4>
        <div className="space-y-2">
          {banking.map((bank) => (
            <div key={bank.name} className="flex items-center justify-between text-sm">
              <span className="text-foreground">{bank.name}</span>
              <span className={bank.color}>{bank.status}</span>
            </div>
          ))}
        </div>
      </div>
      
      <button className="w-full mt-2 px-4 py-2 bg-secondary hover:bg-secondary/80 text-sm rounded-lg transition-colors border border-border">
        Manage Integrations
      </button>
    </div>
  )
}
