import { useState, useEffect } from 'react'
import { PortfolioCard } from './PortfolioCard'
import { PositionsTable } from './PositionsTable'
import { StrategyPanel } from './StrategyPanel'
import { NewsFeed } from './NewsFeed'
import { RiskControls } from './RiskControls'

export function Dashboard() {
  const [portfolioData, setPortfolioData] = useState({
    totalValue: 1234567.89,
    dailyPnL: 12345.67,
    dailyPnLPct: 1.2,
    openPositions: 24,
    exposure: 450000,
  })

  return (
    <div className="space-y-6">
      {/* Top Stats */}
      <div className="grid grid-cols-3 gap-4">
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
      
      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left Column - Positions & Chart */}
        <div className="col-span-2 space-y-6">
          <div className="rounded-lg border border-border bg-card p-4">
            <h2 className="mb-4 text-lg font-semibold">Equity Curve</h2>
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              [TradingView Chart Component]
            </div>
          </div>
          
          <PositionsTable />
        </div>
        
        {/* Right Column - Controls */}
        <div className="space-y-6">
          <StrategyPanel />
          <RiskControls />
        </div>
      </div>
      
      {/* News Feed */}
      <NewsFeed />
    </div>
  )
}

