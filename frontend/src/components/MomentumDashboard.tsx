import { useState, useEffect } from 'react'
import { 
  TrendingUp, TrendingDown, Activity, RefreshCw, 
  Flame, MessageCircle, Newspaper, Target, Clock,
  ChevronDown, ChevronUp, ExternalLink
} from 'lucide-react'
import { getApiBaseUrl } from '../config/api'

interface MomentumStock {
  rank: number
  symbol: string
  sector: string
  composite_score: number
  price_momentum: number
  volume_ratio: number
  social_buzz: number
  price_change_pct: number
}

interface SectorData {
  id: string
  name: string
  momentum_score: number
  symbol_count: number
}

interface ScanStatus {
  tier: string
  last_scan: string | null
  symbols_scanned: number
  is_running: boolean
}

type TabType = 'leaderboard' | 'sectors' | 'social' | 'news'

export function MomentumDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('leaderboard')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Data states
  const [leaderboard, setLeaderboard] = useState<MomentumStock[]>([])
  const [sectors, setSectors] = useState<SectorData[]>([])
  const [scanStatus, setScanStatus] = useState<Record<string, ScanStatus>>({})
  const [trending, setTrending] = useState<any[]>([])
  const [hotNews, setHotNews] = useState<any[]>([])
  
  const [expandedSector, setExpandedSector] = useState<string | null>(null)
  
  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [activeTab])
  
  const fetchData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const baseUrl = getApiBaseUrl()
      
      // Always fetch scan status
      const statusRes = await fetch(`${baseUrl}/api/momentum/scan/status`)
      if (statusRes.ok) {
        const data = await statusRes.json()
        setScanStatus(data)
      }
      
      if (activeTab === 'leaderboard') {
        const res = await fetch(`${baseUrl}/api/momentum/leaderboard?count=20`)
        if (res.ok) {
          const data = await res.json()
          setLeaderboard(data.leaderboard || [])
        }
      } else if (activeTab === 'sectors') {
        const res = await fetch(`${baseUrl}/api/momentum/sectors`)
        if (res.ok) {
          const data = await res.json()
          setSectors(data.sectors || [])
        }
      } else if (activeTab === 'social') {
        const res = await fetch(`${baseUrl}/api/momentum/social/trending?count=15`)
        if (res.ok) {
          const data = await res.json()
          setTrending(data.trending || [])
        }
      } else if (activeTab === 'news') {
        const res = await fetch(`${baseUrl}/api/momentum/news/hot?count=15`)
        if (res.ok) {
          const data = await res.json()
          setHotNews(data.stocks || [])
        }
      }
    } catch (e) {
      setError('Failed to fetch momentum data')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }
  
  const triggerScan = async (tier: string) => {
    try {
      const baseUrl = getApiBaseUrl()
      await fetch(`${baseUrl}/api/momentum/scan/trigger/${tier}`, { method: 'POST' })
      // Refresh status after triggering
      setTimeout(fetchData, 2000)
    } catch (e) {
      console.error('Failed to trigger scan:', e)
    }
  }
  
  const formatTime = (isoString: string | null) => {
    if (!isoString) return 'Never'
    const date = new Date(isoString)
    const now = new Date()
    const diffMinutes = Math.floor((now.getTime() - date.getTime()) / 60000)
    
    if (diffMinutes < 1) return 'Just now'
    if (diffMinutes < 60) return `${diffMinutes}m ago`
    const diffHours = Math.floor(diffMinutes / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    return `${Math.floor(diffHours / 24)}d ago`
  }
  
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    if (score >= 40) return 'text-orange-400'
    return 'text-red-400'
  }
  
  const getChangeColor = (change: number) => {
    if (change > 0) return 'text-green-400'
    if (change < 0) return 'text-red-400'
    return 'text-muted-foreground'
  }
  
  return (
    <div className="bg-card/50 rounded-xl border border-border/50 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-xfactor-teal" />
            <h2 className="font-semibold">Momentum Scanner</h2>
            {loading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
          </div>
          
          {/* Scan Status */}
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
            <div className="flex items-center gap-1">
              <span className={`w-2 h-2 rounded-full ${scanStatus.hot_100?.is_running ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
              Hot 100: {formatTime(scanStatus.hot_100?.last_scan)}
            </div>
            <div className="flex items-center gap-1">
              <span className={`w-2 h-2 rounded-full ${scanStatus.active_1000?.is_running ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
              Active 1K: {formatTime(scanStatus.active_1000?.last_scan)}
            </div>
            <button
              onClick={() => triggerScan('hot_100')}
              className="px-2 py-0.5 rounded bg-xfactor-teal/20 text-xfactor-teal hover:bg-xfactor-teal/30"
            >
              Scan Now
            </button>
          </div>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-2 mt-3">
          {[
            { id: 'leaderboard' as TabType, label: 'Leaderboard', icon: TrendingUp },
            { id: 'sectors' as TabType, label: 'Sectors', icon: Target },
            { id: 'social' as TabType, label: 'Social', icon: MessageCircle },
            { id: 'news' as TabType, label: 'News', icon: Newspaper },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
                activeTab === tab.id
                  ? 'bg-xfactor-teal/20 text-xfactor-teal'
                  : 'text-muted-foreground hover:bg-secondary/50'
              }`}
            >
              <tab.icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      
      {/* Content */}
      <div className="p-4 max-h-[400px] overflow-y-auto">
        {error && (
          <div className="text-center text-red-400 text-sm py-4">{error}</div>
        )}
        
        {/* Leaderboard Tab */}
        {activeTab === 'leaderboard' && (
          <div className="space-y-1">
            <div className="grid grid-cols-7 gap-2 text-[10px] text-muted-foreground px-2 pb-2 border-b border-border/50">
              <span>#</span>
              <span>Symbol</span>
              <span>Sector</span>
              <span className="text-right">Score</span>
              <span className="text-right">Price Mom</span>
              <span className="text-right">Volume</span>
              <span className="text-right">Change</span>
            </div>
            
            {leaderboard.length === 0 && !loading && (
              <div className="text-center text-muted-foreground text-sm py-8">
                No momentum data yet. Trigger a scan to populate rankings.
              </div>
            )}
            
            {leaderboard.map((stock) => (
              <div
                key={stock.symbol}
                className="grid grid-cols-7 gap-2 items-center px-2 py-1.5 rounded hover:bg-secondary/30 text-xs"
              >
                <span className="text-muted-foreground">{stock.rank}</span>
                <span className="font-medium">{stock.symbol}</span>
                <span className="text-muted-foreground truncate text-[10px]">{stock.sector || '-'}</span>
                <span className={`text-right font-mono ${getScoreColor(stock.composite_score)}`}>
                  {stock.composite_score.toFixed(0)}
                </span>
                <span className={`text-right font-mono ${getScoreColor(stock.price_momentum)}`}>
                  {stock.price_momentum.toFixed(0)}
                </span>
                <span className="text-right font-mono text-muted-foreground">
                  {stock.volume_ratio.toFixed(1)}x
                </span>
                <span className={`text-right font-mono ${getChangeColor(stock.price_change_pct)}`}>
                  {stock.price_change_pct > 0 ? '+' : ''}{stock.price_change_pct.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        )}
        
        {/* Sectors Tab */}
        {activeTab === 'sectors' && (
          <div className="space-y-2">
            {sectors.length === 0 && !loading && (
              <div className="text-center text-muted-foreground text-sm py-8">
                No sector data available.
              </div>
            )}
            
            {sectors.slice(0, 15).map((sector) => (
              <div
                key={sector.id}
                className="p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 cursor-pointer"
                onClick={() => setExpandedSector(expandedSector === sector.id ? null : sector.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-2 h-8 rounded-full"
                      style={{
                        background: `linear-gradient(to top, hsl(${sector.momentum_score * 1.2}, 80%, 50%) 0%, hsl(${sector.momentum_score * 1.2}, 80%, 40%) 100%)`
                      }}
                    />
                    <div>
                      <div className="text-sm font-medium">{sector.name}</div>
                      <div className="text-[10px] text-muted-foreground">{sector.symbol_count} stocks</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className={`text-xl font-bold ${getScoreColor(sector.momentum_score)}`}>
                      {sector.momentum_score.toFixed(0)}
                    </div>
                    {expandedSector === sector.id ? (
                      <ChevronUp className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Social Tab */}
        {activeTab === 'social' && (
          <div className="space-y-2">
            {trending.length === 0 && !loading && (
              <div className="text-center text-muted-foreground text-sm py-8">
                No trending stocks found. Social data updates periodically.
              </div>
            )}
            
            {trending.map((item, i) => (
              <div
                key={item.symbol}
                className="flex items-center justify-between p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50"
              >
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground text-xs w-5">{i + 1}</span>
                  <Flame className={`h-4 w-4 ${item.buzz_score >= 80 ? 'text-orange-400' : 'text-muted-foreground'}`} />
                  <span className="font-medium">{item.symbol}</span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-xs">{item.mentions} mentions</div>
                    <div className={`text-[10px] ${item.avg_sentiment > 0 ? 'text-green-400' : item.avg_sentiment < 0 ? 'text-red-400' : 'text-muted-foreground'}`}>
                      Sentiment: {(item.avg_sentiment * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className={`px-2 py-1 rounded text-xs font-mono ${getScoreColor(item.buzz_score)}`}>
                    {item.buzz_score}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* News Tab */}
        {activeTab === 'news' && (
          <div className="space-y-2">
            {hotNews.length === 0 && !loading && (
              <div className="text-center text-muted-foreground text-sm py-8">
                No news momentum data available.
              </div>
            )}
            
            {hotNews.map((item, i) => (
              <div
                key={item.symbol}
                className="p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-xs w-5">{i + 1}</span>
                    <span className="font-medium">{item.symbol}</span>
                    {item.breaking_count > 0 && (
                      <span className="px-1.5 py-0.5 text-[10px] rounded bg-red-500/20 text-red-400">
                        BREAKING
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">
                      {item.article_count_24h} articles
                    </span>
                    <span className={`text-xs ${item.avg_sentiment > 0 ? 'text-green-400' : item.avg_sentiment < 0 ? 'text-red-400' : 'text-muted-foreground'}`}>
                      {item.avg_sentiment > 0 ? '↑' : item.avg_sentiment < 0 ? '↓' : '→'} {(item.avg_sentiment * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                {item.recent_headlines?.[0] && (
                  <div className="mt-1 text-[10px] text-muted-foreground truncate pl-7">
                    📰 {item.recent_headlines[0]}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

