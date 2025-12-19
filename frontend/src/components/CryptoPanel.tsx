import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Coins, Activity, AlertTriangle, Bot, RefreshCw } from 'lucide-react'

interface CryptoPrice {
  symbol: string
  name: string
  category: string
  price: number
  change_24h_pct: number
  volume_24h: number
  market_cap: number
}

interface FearGreed {
  value: number
  classification: string
}

interface CryptoBotInfo {
  id: string
  name: string
  status: string
  symbols: string[]
}

interface WhaleAlert {
  symbol: string
  amount: number
  usd_value: number
  type: string
  tx_hash?: string
  url?: string
}

const categories = [
  { id: 'all', name: 'All', icon: '🌐' },
  { id: 'major', name: 'Major', icon: '₿' },
  { id: 'defi', name: 'DeFi', icon: '🔗' },
  { id: 'layer2', name: 'Layer 2', icon: '⚡' },
  { id: 'ai', name: 'AI', icon: '🤖' },
  { id: 'meme', name: 'Meme', icon: '🐕' },
  { id: 'gaming', name: 'Gaming', icon: '🎮' },
]

export function CryptoPanel() {
  const [prices, setPrices] = useState<CryptoPrice[]>([])
  const [fearGreed, setFearGreed] = useState<FearGreed | null>(null)
  const [bots, setBots] = useState<CryptoBotInfo[]>([])
  const [whaleAlerts, setWhaleAlerts] = useState<WhaleAlert[]>([])
  const [activeCategory, setActiveCategory] = useState('all')
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [activeCategory])

  const fetchData = async () => {
    try {
      const categoryParam = activeCategory !== 'all' ? `?category=${activeCategory}` : ''
      const [pricesRes, fgRes, botsRes, alertsRes] = await Promise.all([
        fetch(`/api/crypto/prices${categoryParam}`),
        fetch('/api/crypto/fear-greed'),
        fetch('/api/crypto/bots'),
        fetch('/api/crypto/whale-alerts?limit=5'),
      ])
      
      if (pricesRes.ok) setPrices((await pricesRes.json()).prices || [])
      if (fgRes.ok) setFearGreed(await fgRes.json())
      if (botsRes.ok) setBots((await botsRes.json()).bots || [])
      if (alertsRes.ok) setWhaleAlerts((await alertsRes.json()).alerts || [])
    } catch (e) {
      console.error('Error fetching crypto data:', e)
    }
    setLoading(false)
  }

  const filteredPrices = prices.filter(p => 
    p.symbol.toLowerCase().includes(search.toLowerCase()) ||
    p.name.toLowerCase().includes(search.toLowerCase())
  )

  const formatPrice = (price: number) => {
    if (price < 0.01) return `$${price.toFixed(6)}`
    if (price < 1) return `$${price.toFixed(4)}`
    return `$${price.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
  }

  const formatVolume = (vol: number) => {
    if (vol >= 1e9) return `$${(vol / 1e9).toFixed(1)}B`
    if (vol >= 1e6) return `$${(vol / 1e6).toFixed(1)}M`
    return `$${vol.toLocaleString()}`
  }

  const getFearGreedColor = (value: number) => {
    if (value < 25) return 'text-red-500'
    if (value < 40) return 'text-orange-500'
    if (value < 60) return 'text-yellow-400'
    if (value < 75) return 'text-green-400'
    return 'text-green-500'
  }

  return (
    <div className="space-y-4">
      {/* Header Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Fear & Greed */}
        <div className="p-3 rounded-lg bg-secondary/50 border border-border">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
            <Activity className="h-3 w-3" />
            Fear & Greed
          </div>
          <div className={`text-xl font-bold ${fearGreed ? getFearGreedColor(fearGreed.value) : ''}`}>
            {fearGreed?.value ?? '--'}
          </div>
          <div className="text-xs text-muted-foreground">{fearGreed?.classification ?? 'Loading...'}</div>
        </div>

        {/* Active Bots */}
        <div className="p-3 rounded-lg bg-secondary/50 border border-border">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
            <Bot className="h-3 w-3" />
            Crypto Bots
          </div>
          <div className="text-xl font-bold text-xfactor-teal">{bots.length}</div>
          <div className="text-xs text-muted-foreground">
            {bots.filter(b => b.status === 'running').length} active
          </div>
        </div>

        {/* Whale Alerts */}
        <div className="p-3 rounded-lg bg-secondary/50 border border-border">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
            <AlertTriangle className="h-3 w-3" />
            Whale Activity
          </div>
          <div className="text-xl font-bold text-yellow-400">{whaleAlerts.length}</div>
          <div className="text-xs text-muted-foreground">Large txns</div>
        </div>

        {/* Tracked Coins */}
        <div className="p-3 rounded-lg bg-secondary/50 border border-border">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
            <Coins className="h-3 w-3" />
            Tracking
          </div>
          <div className="text-xl font-bold text-purple-400">{prices.length}</div>
          <div className="text-xs text-muted-foreground">cryptocurrencies</div>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2">
        {categories.map(cat => (
          <button
            key={cat.id}
            onClick={() => setActiveCategory(cat.id)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              activeCategory === cat.id
                ? 'bg-xfactor-teal text-white'
                : 'bg-secondary hover:bg-secondary/80 text-muted-foreground'
            }`}
          >
            {cat.icon} {cat.name}
          </button>
        ))}
        <button onClick={fetchData} className="ml-auto p-1.5 rounded-lg bg-secondary hover:bg-secondary/80">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Search coins..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full px-3 py-2 text-sm rounded-lg bg-secondary border border-border focus:border-xfactor-teal"
      />

      {/* Price Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-muted-foreground text-left">
              <th className="py-2 font-medium">Coin</th>
              <th className="py-2 font-medium text-right">Price</th>
              <th className="py-2 font-medium text-right">24h %</th>
              <th className="py-2 font-medium text-right hidden md:table-cell">Volume</th>
              <th className="py-2 font-medium text-right hidden lg:table-cell">Market Cap</th>
            </tr>
          </thead>
          <tbody>
            {filteredPrices.map(coin => (
              <tr key={coin.symbol} className="border-t border-border/50 hover:bg-secondary/30">
                <td className="py-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold">{coin.symbol}</span>
                    <span className="text-muted-foreground text-xs">{coin.name}</span>
                  </div>
                </td>
                <td className="py-2 text-right font-mono">{formatPrice(coin.price ?? 0)}</td>
                <td className={`py-2 text-right font-mono ${(coin.change_24h_pct ?? 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                  <span className="flex items-center justify-end gap-1">
                    {(coin.change_24h_pct ?? 0) >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                    {(coin.change_24h_pct ?? 0).toFixed(2)}%
                  </span>
                </td>
                <td className="py-2 text-right font-mono text-muted-foreground hidden md:table-cell">
                  {formatVolume(coin.volume_24h ?? 0)}
                </td>
                <td className="py-2 text-right font-mono text-muted-foreground hidden lg:table-cell">
                  {formatVolume(coin.market_cap ?? 0)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Whale Alerts Mini */}
      {whaleAlerts.length > 0 && (
        <div className="mt-4 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
          <div className="flex items-center justify-between text-sm font-medium text-yellow-400 mb-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> Recent Whale Activity
            </div>
            <a 
              href="https://whale-alert.io" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-yellow-400 transition-colors"
            >
              View All →
            </a>
          </div>
          <div className="space-y-1 text-xs">
            {whaleAlerts.slice(0, 3).map((alert, i) => {
              const explorerUrl = alert.url 
                ? alert.url 
                : alert.tx_hash 
                  ? `https://whale-alert.io/transaction/${alert.symbol.toLowerCase()}/${alert.tx_hash}`
                  : `https://whale-alert.io`;
              return (
                <a 
                  key={i} 
                  href={explorerUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex justify-between hover:bg-yellow-500/10 p-1 rounded transition-colors cursor-pointer group"
                >
                  <span className="text-muted-foreground group-hover:text-yellow-400 transition-colors">{alert.type?.replace('_', ' ') || 'transfer'}</span>
                  <span className="group-hover:text-yellow-400 transition-colors">{(alert.amount ?? 0).toFixed(2)} {alert.symbol} (${((alert.usd_value ?? 0) / 1e6).toFixed(1)}M)</span>
                </a>
              );
            })}
          </div>
        </div>
      )}

      {/* Crypto Bots */}
      {bots.length > 0 && (
        <div className="mt-4">
          <div className="text-sm font-medium mb-2 flex items-center gap-2">
            <Bot className="h-4 w-4 text-xfactor-teal" /> Crypto Trading Bots
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {bots.slice(0, 4).map(bot => (
              <div key={bot.id} className="p-2 rounded-lg bg-secondary/50 border border-border flex justify-between items-center">
                <div>
                  <div className="font-medium text-sm">{bot.name}</div>
                  <div className="text-xs text-muted-foreground">{bot.symbols.slice(0, 3).join(', ')}</div>
                </div>
                <span className={`px-2 py-0.5 text-xs rounded ${
                  bot.status === 'running' ? 'bg-profit/20 text-profit' : 'bg-secondary text-muted-foreground'
                }`}>
                  {bot.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

