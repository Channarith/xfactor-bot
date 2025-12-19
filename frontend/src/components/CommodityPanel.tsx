import { useState, useEffect } from 'react'
import { 
  TrendingUp, TrendingDown, Droplet, Zap, Factory, 
  Wheat, Diamond, RefreshCw, ChevronDown, ChevronUp,
  Flame, Atom, Gem
} from 'lucide-react'

interface CommodityPrice {
  symbol: string
  name: string
  category: string
  price: number
  change: number
  change_pct: number
  high_24h: number
  low_24h: number
  volume: number
  timestamp: string
}

interface CommodityNews {
  title: string
  summary: string
  source: string
  url: string
  published: string
  commodities: string[]
  sentiment: number
}

const categoryIcons: Record<string, React.ReactNode> = {
  precious_metals: <Gem className="w-4 h-4 text-yellow-400" />,
  energy: <Flame className="w-4 h-4 text-orange-400" />,
  industrial_metals: <Factory className="w-4 h-4 text-gray-400" />,
  agriculture: <Wheat className="w-4 h-4 text-green-400" />,
  nuclear: <Atom className="w-4 h-4 text-purple-400" />,
  rare_earth: <Diamond className="w-4 h-4 text-cyan-400" />,
}

const categoryLabels: Record<string, string> = {
  precious_metals: "Precious Metals",
  energy: "Energy",
  industrial_metals: "Industrial Metals",
  agriculture: "Agriculture",
  nuclear: "Nuclear/Uranium",
  rare_earth: "Rare Earth",
}

export default function CommodityPanel() {
  const [prices, setPrices] = useState<CommodityPrice[]>([])
  const [news, setNews] = useState<CommodityNews[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['precious_metals', 'energy']))
  const [showNews, setShowNews] = useState(true)
  
  const fetchData = async () => {
    setLoading(true)
    try {
      const [pricesRes, newsRes] = await Promise.all([
        fetch('/api/commodities/prices'),
        fetch('/api/commodities/news?limit=10')
      ])
      
      if (pricesRes.ok) {
        const pricesData = await pricesRes.json()
        setPrices(pricesData)
      }
      
      if (newsRes.ok) {
        const newsData = await newsRes.json()
        setNews(newsData)
      }
    } catch (error) {
      console.error('Error fetching commodity data:', error)
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])
  
  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories)
    if (newExpanded.has(category)) {
      newExpanded.delete(category)
    } else {
      newExpanded.add(category)
    }
    setExpandedCategories(newExpanded)
  }
  
  // Group prices by category
  const pricesByCategory = prices.reduce((acc, price) => {
    if (!acc[price.category]) {
      acc[price.category] = []
    }
    acc[price.category].push(price)
    return acc
  }, {} as Record<string, CommodityPrice[]>)
  
  const categories = Object.keys(categoryLabels)
  
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Gem className="w-5 h-5 text-yellow-400" />
          <span className="text-sm text-muted-foreground">
            {prices.length} commodities tracked
          </span>
        </div>
        <button 
          onClick={fetchData}
          className="p-2 hover:bg-card rounded-lg transition-colors"
          disabled={loading}
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
      
      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-card/50 rounded-lg p-3">
          <div className="text-xs text-muted-foreground">Gold (GLD)</div>
          <div className="text-lg font-bold text-yellow-400">
            ${prices.find(p => p.symbol === 'GLD')?.price.toFixed(2) || '---'}
          </div>
          {prices.find(p => p.symbol === 'GLD') && (
            <div className={`text-xs ${prices.find(p => p.symbol === 'GLD')!.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {prices.find(p => p.symbol === 'GLD')!.change >= 0 ? '+' : ''}
              {prices.find(p => p.symbol === 'GLD')!.change_pct.toFixed(2)}%
            </div>
          )}
        </div>
        <div className="bg-card/50 rounded-lg p-3">
          <div className="text-xs text-muted-foreground">Oil (USO)</div>
          <div className="text-lg font-bold text-orange-400">
            ${prices.find(p => p.symbol === 'USO')?.price.toFixed(2) || '---'}
          </div>
          {prices.find(p => p.symbol === 'USO') && (
            <div className={`text-xs ${prices.find(p => p.symbol === 'USO')!.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {prices.find(p => p.symbol === 'USO')!.change >= 0 ? '+' : ''}
              {prices.find(p => p.symbol === 'USO')!.change_pct.toFixed(2)}%
            </div>
          )}
        </div>
        <div className="bg-card/50 rounded-lg p-3">
          <div className="text-xs text-muted-foreground">Uranium (URA)</div>
          <div className="text-lg font-bold text-purple-400">
            ${prices.find(p => p.symbol === 'URA')?.price.toFixed(2) || '---'}
          </div>
          {prices.find(p => p.symbol === 'URA') && (
            <div className={`text-xs ${prices.find(p => p.symbol === 'URA')!.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {prices.find(p => p.symbol === 'URA')!.change >= 0 ? '+' : ''}
              {prices.find(p => p.symbol === 'URA')!.change_pct.toFixed(2)}%
            </div>
          )}
        </div>
      </div>
      
      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`px-3 py-1 rounded-full text-xs transition-colors ${
            selectedCategory === null 
              ? 'bg-primary text-primary-foreground' 
              : 'bg-card hover:bg-card/80'
          }`}
        >
          All
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1 rounded-full text-xs transition-colors flex items-center gap-1 ${
              selectedCategory === cat 
                ? 'bg-primary text-primary-foreground' 
                : 'bg-card hover:bg-card/80'
            }`}
          >
            {categoryIcons[cat]}
            {categoryLabels[cat]}
          </button>
        ))}
      </div>
      
      {/* Commodity Lists by Category */}
      <div className="space-y-2">
        {categories
          .filter(cat => !selectedCategory || selectedCategory === cat)
          .map(category => {
            const categoryPrices = pricesByCategory[category] || []
            const isExpanded = expandedCategories.has(category)
            
            if (categoryPrices.length === 0) return null
            
            return (
              <div key={category} className="bg-card/30 rounded-lg overflow-hidden">
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full px-4 py-2 flex items-center justify-between hover:bg-card/50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {categoryIcons[category]}
                    <span className="font-medium">{categoryLabels[category]}</span>
                    <span className="text-xs text-muted-foreground">
                      ({categoryPrices.length})
                    </span>
                  </div>
                  {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                
                {/* Category Content */}
                {isExpanded && (
                  <div className="px-2 pb-2">
                    <div className="grid gap-1">
                      {categoryPrices.map(commodity => (
                        <div
                          key={commodity.symbol}
                          className="flex items-center justify-between px-3 py-2 bg-background/50 rounded-lg hover:bg-background/80 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-card flex items-center justify-center font-bold text-xs">
                              {commodity.symbol.slice(0, 4)}
                            </div>
                            <div>
                              <div className="font-medium text-sm">{commodity.name}</div>
                              <div className="text-xs text-muted-foreground">{commodity.symbol}</div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-bold">${commodity.price.toFixed(2)}</div>
                            <div className={`flex items-center gap-1 text-xs ${
                              commodity.change >= 0 ? 'text-green-400' : 'text-red-400'
                            }`}>
                              {commodity.change >= 0 ? (
                                <TrendingUp className="w-3 h-3" />
                              ) : (
                                <TrendingDown className="w-3 h-3" />
                              )}
                              {commodity.change >= 0 ? '+' : ''}{commodity.change_pct.toFixed(2)}%
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
      </div>
      
      {/* Commodity News */}
      <div className="mt-4">
        <button
          onClick={() => setShowNews(!showNews)}
          className="flex items-center gap-2 mb-2 text-sm font-medium"
        >
          {showNews ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          Commodity News
        </button>
        
        {showNews && (
          <div className="space-y-2">
            {news.slice(0, 5).map((article, i) => (
              <a 
                key={i} 
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block bg-card/30 rounded-lg p-3 hover:bg-card/50 transition-colors cursor-pointer group"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <div className="font-medium text-sm group-hover:text-blue-400 transition-colors">{article.title}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {article.source} • {new Date(article.published).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`px-2 py-0.5 rounded text-xs ${
                      article.sentiment > 0.3 
                        ? 'bg-green-500/20 text-green-400' 
                        : article.sentiment < -0.3 
                          ? 'bg-red-500/20 text-red-400' 
                          : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      {article.sentiment > 0.3 ? 'Bullish' : article.sentiment < -0.3 ? 'Bearish' : 'Neutral'}
                    </div>
                    <span className="text-muted-foreground group-hover:text-blue-400 transition-colors">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </span>
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
      
      {/* Loading State */}
      {loading && prices.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
          Loading commodity data...
        </div>
      )}
    </div>
  )
}

