/**
 * ETF Widget - Top ETFs, International, and Inverse/Leveraged Overview
 * 
 * Features:
 * - Top ETFs by category (S&P 500, Growth, Sector, Bond)
 * - International ETFs (Developed & Emerging Markets)
 * - Inverse & Leveraged ETFs with real-time momentum
 * - Quick-add to bot watchlist
 */

import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Globe, Zap, ArrowUpDown, RefreshCw } from 'lucide-react'
import { getApiBaseUrl } from '../config/api'

interface ETFData {
  symbol: string
  name: string
  price: number
  change: number
  changePct: number
  volume: string
  category: string
}

// ETF categories with symbols
const ETF_CATEGORIES = {
  'S&P 500': ['VOO', 'SPY', 'IVV', 'SPLG', 'VTI'],
  'Growth': ['VUG', 'IWF', 'SCHG', 'MGK', 'QQQ'],
  'Value': ['VTV', 'IWD', 'SCHV', 'MGV', 'RPV'],
  'Dividend': ['VIG', 'SCHD', 'DVY', 'VYM', 'SDY'],
  'Sector': ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY'],
}

const INTERNATIONAL_ETFS = {
  'Developed Markets': ['EFA', 'VEA', 'IEFA', 'VGK', 'EWJ'],
  'Emerging Markets': ['EEM', 'VWO', 'IEMG', 'FXI', 'INDA'],
  'China': ['FXI', 'MCHI', 'KWEB', 'ASHR', 'CQQQ'],
  'Europe': ['VGK', 'EZU', 'HEDJ', 'EWG', 'EWU'],
  'Japan': ['EWJ', 'DXJ', 'HEWJ', 'BBJP', 'JPXN'],
}

const LEVERAGED_ETFS = {
  'Bull 3x': ['TQQQ', 'UPRO', 'SOXL', 'TECL', 'FNGU', 'LABU'],
  'Bear 3x': ['SQQQ', 'SPXU', 'SOXS', 'TECS', 'FNGD', 'LABD'],
  'Bull 2x': ['QLD', 'SSO', 'USD', 'DDM', 'UWM'],
  'Bear 2x': ['QID', 'SDS', 'DXD', 'TWM', 'SZK'],
  'Volatility': ['VXX', 'UVXY', 'SVXY', 'VIXY', 'VIXM'],
}

type TabType = 'top' | 'international' | 'leveraged'

export function ETFWidget({ onAddSymbol }: { onAddSymbol?: (symbol: string) => void }) {
  const [activeTab, setActiveTab] = useState<TabType>('top')
  const [selectedCategory, setSelectedCategory] = useState<string>('S&P 500')
  const [etfData, setEtfData] = useState<Record<string, ETFData>>({})
  const [loading, setLoading] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const getCurrentCategories = (): Record<string, string[]> => {
    switch (activeTab) {
      case 'top': return ETF_CATEGORIES
      case 'international': return INTERNATIONAL_ETFS
      case 'leveraged': return LEVERAGED_ETFS
      default: return ETF_CATEGORIES
    }
  }

  const fetchETFData = async (symbols: string[]) => {
    setLoading(true)
    try {
      const baseUrl = getApiBaseUrl()
      // Fetch price data for symbols
      const res = await fetch(`${baseUrl}/api/market/quotes?symbols=${symbols.join(',')}`)
      if (res.ok) {
        const data = await res.json()
        const newData: Record<string, ETFData> = {}
        for (const quote of data.quotes || []) {
          newData[quote.symbol] = {
            symbol: quote.symbol,
            name: quote.name || quote.symbol,
            price: quote.price || 0,
            change: quote.change || 0,
            changePct: quote.changePct || 0,
            volume: formatVolume(quote.volume || 0),
            category: selectedCategory,
          }
        }
        setEtfData(prev => ({ ...prev, ...newData }))
        setLastUpdated(new Date())
      }
    } catch (e) {
      console.error('Failed to fetch ETF data:', e)
    } finally {
      setLoading(false)
    }
  }

  const formatVolume = (vol: number): string => {
    if (vol >= 1e9) return `${(vol / 1e9).toFixed(1)}B`
    if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`
    if (vol >= 1e3) return `${(vol / 1e3).toFixed(0)}K`
    return vol.toString()
  }

  useEffect(() => {
    const categories = getCurrentCategories()
    const categoryKeys = Object.keys(categories)
    if (!categoryKeys.includes(selectedCategory)) {
      setSelectedCategory(categoryKeys[0])
    }
  }, [activeTab])

  useEffect(() => {
    const categories = getCurrentCategories()
    const symbols = categories[selectedCategory] || []
    if (symbols.length > 0) {
      fetchETFData(symbols)
    }
  }, [selectedCategory, activeTab])

  const categories = getCurrentCategories()
  const currentSymbols: string[] = categories[selectedCategory] || []

  return (
    <div className="space-y-3">
      {/* Tab Navigation */}
      <div className="flex gap-1 p-1 bg-background/50 rounded-lg">
        <button
          onClick={() => setActiveTab('top')}
          className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            activeTab === 'top' 
              ? 'bg-xfactor-teal text-white' 
              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          }`}
        >
          <TrendingUp className="h-3.5 w-3.5" />
          Top ETFs
        </button>
        <button
          onClick={() => setActiveTab('international')}
          className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            activeTab === 'international' 
              ? 'bg-blue-500 text-white' 
              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          }`}
        >
          <Globe className="h-3.5 w-3.5" />
          International
        </button>
        <button
          onClick={() => setActiveTab('leveraged')}
          className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            activeTab === 'leveraged' 
              ? 'bg-orange-500 text-white' 
              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          }`}
        >
          <Zap className="h-3.5 w-3.5" />
          Leveraged
        </button>
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap gap-1">
        {Object.keys(categories).map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-2 py-1 rounded text-[10px] font-medium transition-colors ${
              selectedCategory === cat
                ? 'bg-foreground text-background'
                : 'bg-accent/50 text-muted-foreground hover:bg-accent hover:text-foreground'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* ETF List */}
      <div className="space-y-1">
        {loading && currentSymbols.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <RefreshCw className="h-4 w-4 animate-spin mr-2" />
            Loading...
          </div>
        ) : (
          currentSymbols.map((symbol) => {
            const data = etfData[symbol]
            const isPositive = (data?.changePct || 0) >= 0
            
            return (
              <div
                key={symbol}
                className="flex items-center justify-between p-2 rounded-lg bg-card/50 hover:bg-card transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                    activeTab === 'leveraged' 
                      ? isPositive ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                      : 'bg-accent text-foreground'
                  }`}>
                    {symbol.slice(0, 2)}
                  </div>
                  <div>
                    <p className="text-sm font-medium">{symbol}</p>
                    <p className="text-[10px] text-muted-foreground">
                      {data?.name || selectedCategory}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  {data ? (
                    <>
                      <div className="text-right">
                        <p className="text-sm font-medium">${data.price.toFixed(2)}</p>
                        <p className={`text-[10px] flex items-center gap-0.5 ${
                          isPositive ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                          {isPositive ? '+' : ''}{data.changePct.toFixed(2)}%
                        </p>
                      </div>
                      <div className="text-right text-[10px] text-muted-foreground">
                        <p>Vol</p>
                        <p>{data.volume}</p>
                      </div>
                    </>
                  ) : (
                    <div className="text-[10px] text-muted-foreground">Loading...</div>
                  )}
                  
                  {onAddSymbol && (
                    <button
                      onClick={() => onAddSymbol(symbol)}
                      className="opacity-0 group-hover:opacity-100 px-2 py-1 rounded bg-xfactor-teal/20 text-xfactor-teal text-[10px] font-medium hover:bg-xfactor-teal/30 transition-all"
                    >
                      + Add
                    </button>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-2 border-t border-border/50">
        <span>
          {activeTab === 'top' && '📈 Core ETF holdings for diversified portfolios'}
          {activeTab === 'international' && '🌍 Global market exposure'}
          {activeTab === 'leveraged' && '⚡ High-risk/reward amplified moves'}
        </span>
        {lastUpdated && (
          <span className="flex items-center gap-1">
            <RefreshCw className="h-3 w-3" />
            {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>
    </div>
  )
}

export default ETFWidget

