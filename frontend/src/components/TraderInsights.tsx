import { useState, useEffect, useMemo } from 'react'
import { 
  Users, TrendingUp, TrendingDown, ExternalLink, RefreshCw,
  Star, Building2, User, ChevronLeft, ChevronRight,
  BarChart3, Calendar, Megaphone, Brain, Search, SortAsc, SortDesc, X, AlertCircle
} from 'lucide-react'
import { useDataFilters, FilterBar, type FieldDefinition, type SortConfig } from './DataFilters'
import { useTradingMode } from '../context/TradingModeContext'

// ============================================================================
// Types
// ============================================================================

interface InsiderTrade {
  id: string
  ticker: string
  company: string
  insider: string
  title: string
  tradeType: 'Buy' | 'Sell'
  shares: number
  price: number
  value: number
  date: string
  filingDate: string
  aiAnalysis?: string  // AI-generated analysis of why the trade was made
}

interface TopTrader {
  id: string
  name: string
  handle: string
  platform: string
  followers: string
  winRate: number
  recentCalls: TraderCall[]
  verified: boolean
}

interface TraderCall {
  ticker: string
  action: 'Long' | 'Short' | 'Buy Calls' | 'Buy Puts'
  entry: number
  target?: number
  date: string
  status: 'Active' | 'Hit Target' | 'Stopped Out'
}

interface FinvizSignal {
  id: string
  ticker: string
  company: string
  sector: string
  signal: string
  price: number
  change: number
  volume: string
  pattern?: string
}

interface MovingAverageSignal {
  id: string
  ticker: string
  company: string
  price: number
  sma20: number
  sma50: number
  sma200: number
  signal: 'Golden Cross' | 'Death Cross' | 'Above All MAs' | 'Below All MAs' | 'Bounce 50MA' | 'Bounce 200MA'
  strength: number
}

interface EarningsReport {
  id: string
  ticker: string
  company: string
  reportDate: string
  reportTime: 'BMO' | 'AMC'
  epsEstimate: number
  revenueEstimate: string
  surpriseHistory: number
  optionsIV: number
}

interface PressRelease {
  id: string
  ticker: string
  company: string
  title: string
  category: 'FDA' | 'M&A' | 'Partnership' | 'Product' | 'Financial' | 'Legal' | 'Executive'
  timestamp: string
  sentiment: number
  source: string
}

interface AInvestSignal {
  id: string
  ticker: string
  company: string
  aiScore: number
  recommendation: 'Strong Buy' | 'Buy' | 'Hold' | 'Sell' | 'Strong Sell'
  targetPrice: number
  currentPrice: number
  upside: number
  signals: string[]
  confidence: number
}

type TabType = 'insiders' | 'traders' | 'finviz' | 'movingavg' | 'earnings' | 'press' | 'ainvest'

// ============================================================================
// Field Definitions for Each Tab
// ============================================================================

const insiderFields: FieldDefinition[] = [
  { key: 'ticker', label: 'Ticker', type: 'string', sortable: true, filterable: true },
  { key: 'insider', label: 'Insider', type: 'string', sortable: true, filterable: true },
  { key: 'title', label: 'Title', type: 'select', sortable: true, filterable: true, options: [
    { value: 'CEO', label: 'CEO' }, { value: 'CFO', label: 'CFO' }, { value: 'Director', label: 'Director' }, { value: 'VP', label: 'VP' }
  ]},
  { key: 'tradeType', label: 'Trade Type', type: 'select', sortable: true, filterable: true, options: [
    { value: 'Buy', label: 'Buy' }, { value: 'Sell', label: 'Sell' }
  ]},
  { key: 'value', label: 'Value ($)', type: 'number', sortable: true, filterable: true },
  { key: 'shares', label: 'Shares', type: 'number', sortable: true, filterable: true },
  { key: 'date', label: 'Date', type: 'date', sortable: true, filterable: true },
]

const traderFields: FieldDefinition[] = [
  { key: 'name', label: 'Name', type: 'string', sortable: true, filterable: true },
  { key: 'handle', label: 'Handle', type: 'string', sortable: false, filterable: true },
  { key: 'platform', label: 'Platform', type: 'select', sortable: true, filterable: true, options: [
    { value: 'Twitter/X', label: 'Twitter/X' }, { value: 'Discord', label: 'Discord' }, { value: 'Web', label: 'Web' }
  ]},
  { key: 'winRate', label: 'Win Rate', type: 'number', sortable: true, filterable: true },
  { key: 'followers', label: 'Followers', type: 'string', sortable: true, filterable: false },
]

const finvizFields: FieldDefinition[] = [
  { key: 'ticker', label: 'Ticker', type: 'string', sortable: true, filterable: true },
  { key: 'signal', label: 'Signal', type: 'select', sortable: true, filterable: true, options: [
    { value: 'Unusual Volume', label: 'Unusual Volume' }, { value: 'New High', label: 'New High' },
    { value: 'Breakout', label: 'Breakout' }, { value: 'Gap Up', label: 'Gap Up' },
    { value: 'Oversold Bounce', label: 'Oversold Bounce' }, { value: 'Golden Cross', label: 'Golden Cross' }
  ]},
  { key: 'sector', label: 'Sector', type: 'select', sortable: true, filterable: true, options: [
    { value: 'Technology', label: 'Technology' }, { value: 'Finance', label: 'Finance' },
    { value: 'Healthcare', label: 'Healthcare' }, { value: 'Industrials', label: 'Industrials' }
  ]},
  { key: 'change', label: 'Change %', type: 'number', sortable: true, filterable: true },
  { key: 'price', label: 'Price', type: 'number', sortable: true, filterable: true },
]

const maFields: FieldDefinition[] = [
  { key: 'ticker', label: 'Ticker', type: 'string', sortable: true, filterable: true },
  { key: 'signal', label: 'Signal', type: 'select', sortable: true, filterable: true, options: [
    { value: 'Golden Cross', label: 'Golden Cross' }, { value: 'Death Cross', label: 'Death Cross' },
    { value: 'Above All MAs', label: 'Above All MAs' }, { value: 'Below All MAs', label: 'Below All MAs' },
    { value: 'Bounce 50MA', label: 'Bounce 50MA' }, { value: 'Bounce 200MA', label: 'Bounce 200MA' }
  ]},
  { key: 'price', label: 'Price', type: 'number', sortable: true, filterable: true },
  { key: 'strength', label: 'Strength', type: 'number', sortable: true, filterable: true },
]

const earningsFields: FieldDefinition[] = [
  { key: 'ticker', label: 'Ticker', type: 'string', sortable: true, filterable: true },
  { key: 'reportDate', label: 'Report Date', type: 'date', sortable: true, filterable: true },
  { key: 'reportTime', label: 'Time', type: 'select', sortable: true, filterable: true, options: [
    { value: 'BMO', label: 'Before Market Open' }, { value: 'AMC', label: 'After Market Close' }
  ]},
  { key: 'epsEstimate', label: 'EPS Est', type: 'number', sortable: true, filterable: true },
  { key: 'optionsIV', label: 'Options IV', type: 'number', sortable: true, filterable: true },
]

const pressFields: FieldDefinition[] = [
  { key: 'ticker', label: 'Ticker', type: 'string', sortable: true, filterable: true },
  { key: 'title', label: 'Title', type: 'string', sortable: false, filterable: true },
  { key: 'category', label: 'Category', type: 'select', sortable: true, filterable: true, options: [
    { value: 'FDA', label: 'FDA' }, { value: 'M&A', label: 'M&A' }, { value: 'Partnership', label: 'Partnership' },
    { value: 'Product', label: 'Product' }, { value: 'Financial', label: 'Financial' },
    { value: 'Legal', label: 'Legal' }, { value: 'Executive', label: 'Executive' }
  ]},
  { key: 'sentiment', label: 'Sentiment', type: 'number', sortable: true, filterable: true },
  { key: 'source', label: 'Source', type: 'string', sortable: true, filterable: true },
]

const ainvestFields: FieldDefinition[] = [
  { key: 'ticker', label: 'Ticker', type: 'string', sortable: true, filterable: true },
  { key: 'recommendation', label: 'Rating', type: 'select', sortable: true, filterable: true, options: [
    { value: 'Strong Buy', label: 'Strong Buy' }, { value: 'Buy', label: 'Buy' },
    { value: 'Hold', label: 'Hold' }, { value: 'Sell', label: 'Sell' }, { value: 'Strong Sell', label: 'Strong Sell' }
  ]},
  { key: 'aiScore', label: 'AI Score', type: 'number', sortable: true, filterable: true },
  { key: 'upside', label: 'Upside %', type: 'number', sortable: true, filterable: true },
  { key: 'confidence', label: 'Confidence', type: 'number', sortable: true, filterable: true },
]

// ============================================================================
// Data Generation (same as before, keeping for brevity)
// ============================================================================

// AI Analysis templates for insider trades
const generateAIAnalysis = (
  ticker: string, 
  tradeType: 'Buy' | 'Sell', 
  title: string, 
  value: number,
  insider: string
): string => {
  const buyReasons = [
    `${title} likely sees strong growth potential ahead of upcoming product launches and expects revenue acceleration.`,
    `Insider accumulation suggests confidence in Q4 earnings beat. Management may have visibility into stronger-than-expected demand.`,
    `${title} adding to position could signal positive internal developments not yet public. Often precedes major announcements.`,
    `Large insider buy at current levels indicates ${title} believes shares are undervalued relative to future growth trajectory.`,
    `Strategic accumulation by ${title} may indicate upcoming catalyst: possible M&A, partnership, or product breakthrough.`,
    `${insider}'s purchase timing suggests confidence in near-term fundamentals. Historically, this insider's buys precede 15-20% gains.`,
    `Insider buying during market weakness often signals conviction in company's competitive position and long-term outlook.`,
    `${title}-level purchase typically indicates awareness of positive developments. Consider sector tailwinds and company fundamentals.`,
  ]
  
  const sellReasons = [
    `${title} sale appears routine for diversification/tax planning. No unusual timing relative to scheduled selling plans.`,
    `Partial position reduction by ${title} - likely portfolio rebalancing rather than negative signal. Retains significant holdings.`,
    `Exercise & sell pattern common for executives. Stock-based compensation vesting often triggers these transactions.`,
    `${title} reducing exposure after significant stock appreciation. Profit-taking after ${ticker}'s strong YTD performance.`,
    `Planned sale under 10b5-1 trading plan. Pre-scheduled selling not indicative of insider sentiment on fundamentals.`,
    `${insider} trimming position ahead of potential tax law changes. Estate planning common for executives at this level.`,
    `Sale coincides with lockup expiration. Institutional selling pressure may create short-term volatility but not fundamental concern.`,
    `${title} selling to fund personal investments. Filed Form 4 shows continued significant ownership stake.`,
  ]
  
  const reasons = tradeType === 'Buy' ? buyReasons : sellReasons
  const randomIndex = Math.floor(Math.random() * reasons.length)
  
  // Add value context
  const valueStr = value >= 10000000 
    ? `💰 Large ${tradeType.toLowerCase()} ($${(value/1000000).toFixed(1)}M) - ` 
    : value >= 1000000 
    ? `📊 Notable ${tradeType.toLowerCase()} ($${(value/1000000).toFixed(1)}M) - `
    : `📝 Standard ${tradeType.toLowerCase()} - `
  
  return valueStr + reasons[randomIndex]
}

const generateInsiderTrades = (count: number): InsiderTrade[] => {
  const tickers = ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMZN', 'AMD', 'CRM', 'ORCL']
  const companies: Record<string, string> = {
    'NVDA': 'NVIDIA Corporation', 'AAPL': 'Apple Inc', 'MSFT': 'Microsoft Corp',
    'GOOGL': 'Alphabet Inc', 'META': 'Meta Platforms', 'TSLA': 'Tesla Inc',
    'AMZN': 'Amazon.com', 'AMD': 'AMD Inc', 'CRM': 'Salesforce', 'ORCL': 'Oracle Corp'
  }
  const insiders = [
    { name: 'Jensen Huang', title: 'CEO' }, { name: 'Tim Cook', title: 'CEO' },
    { name: 'Satya Nadella', title: 'CEO' }, { name: 'Mark Zuckerberg', title: 'CEO' },
    { name: 'Elon Musk', title: 'CEO' }, { name: 'Andy Jassy', title: 'CEO' },
    { name: 'Lisa Su', title: 'CEO' }, { name: 'CFO Office', title: 'CFO' },
    { name: 'Board Member', title: 'Director' }, { name: 'VP Sales', title: 'VP' }
  ]
  return Array.from({ length: count }, (_, i) => {
    const ticker = tickers[i % tickers.length]
    const insider = insiders[Math.floor(Math.random() * insiders.length)]
    const tradeType: 'Buy' | 'Sell' = Math.random() > 0.3 ? 'Sell' : 'Buy'
    const value = Math.floor(Math.random() * 100000000) + 1000000
    return {
      id: `insider-${i}`, ticker, company: companies[ticker], insider: insider.name, title: insider.title,
      tradeType, shares: Math.floor(Math.random() * 200000) + 10000,
      price: Math.floor(Math.random() * 500) + 50, value,
      date: new Date(Date.now() - i * 86400000).toISOString().split('T')[0],
      filingDate: new Date(Date.now() - i * 86400000 + 86400000).toISOString().split('T')[0],
      aiAnalysis: generateAIAnalysis(ticker, tradeType, insider.title, value, insider.name)
    }
  })
}

const generateTopTraders = (count: number): TopTrader[] => {
  const traders = [
    { name: 'Unusual Whales', handle: '@unusual_whales', platform: 'Twitter/X', followers: '850K', winRate: 68 },
    { name: 'Cheddar Flow', handle: '@CheddarFlow', platform: 'Twitter/X', followers: '320K', winRate: 72 },
    { name: 'Market Rebellion', handle: '@MarketRebels', platform: 'Twitter/X', followers: '180K', winRate: 65 },
    { name: 'Sweep Cast', handle: '@SweepCast', platform: 'Discord', followers: '95K', winRate: 70 },
    { name: 'Options Profit', handle: '@OptionsProfit', platform: 'Twitter/X', followers: '420K', winRate: 66 },
    { name: 'Flow Algo', handle: '@FlowAlgo', platform: 'Web', followers: '150K', winRate: 71 },
    { name: 'Dark Pool Charts', handle: '@DarkPoolCharts', platform: 'Twitter/X', followers: '280K', winRate: 63 },
    { name: 'Quant Data', handle: '@QuantData', platform: 'Discord', followers: '75K', winRate: 74 },
    { name: 'Gamma Squeeze', handle: '@GammaSqueeze', platform: 'Twitter/X', followers: '190K', winRate: 67 },
    { name: 'Whale Wisdom', handle: '@WhaleWisdom', platform: 'Web', followers: '110K', winRate: 69 },
  ]
  const actions: TraderCall['action'][] = ['Long', 'Short', 'Buy Calls', 'Buy Puts']
  const tickers = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'AMD', 'META', 'GOOGL', 'AMZN', 'MSFT']
  return Array.from({ length: count }, (_, i) => {
    const base = traders[i % traders.length]
    return {
      id: `trader-${i}`, ...base, verified: Math.random() > 0.3,
      recentCalls: Array.from({ length: Math.floor(Math.random() * 3) + 1 }, (_, j) => ({
        ticker: tickers[Math.floor(Math.random() * tickers.length)],
        action: actions[Math.floor(Math.random() * actions.length)],
        entry: Math.floor(Math.random() * 500) + 50, target: Math.floor(Math.random() * 600) + 60,
        date: new Date(Date.now() - j * 86400000).toISOString().split('T')[0],
        status: ['Active', 'Hit Target', 'Stopped Out'][Math.floor(Math.random() * 3)] as TraderCall['status']
      }))
    }
  })
}

const generateFinvizSignals = (count: number): FinvizSignal[] => {
  const signals = ['Unusual Volume', 'New High', 'Breakout', 'Gap Up', 'Oversold Bounce', 'Golden Cross']
  const patterns = ['Bull Flag', 'Cup & Handle', 'Ascending Triangle', 'Double Bottom', 'Breakout', null]
  const tickers = ['SMCI', 'PLTR', 'MSTR', 'COIN', 'RKLB', 'IONQ', 'AFRM', 'SNOW', 'NET', 'CRWD']
  return Array.from({ length: count }, (_, i) => ({
    id: `finviz-${i}`, ticker: tickers[i % tickers.length], company: `Company ${tickers[i % tickers.length]}`,
    sector: ['Technology', 'Finance', 'Healthcare', 'Industrials'][i % 4],
    signal: signals[Math.floor(Math.random() * signals.length)], price: Math.floor(Math.random() * 400) + 20,
    change: Math.floor(Math.random() * 25) + 1, volume: `${Math.floor(Math.random() * 80) + 5}M`,
    pattern: patterns[Math.floor(Math.random() * patterns.length)] || undefined
  }))
}

const generateMovingAverageSignals = (count: number): MovingAverageSignal[] => {
  const signals: MovingAverageSignal['signal'][] = ['Golden Cross', 'Death Cross', 'Above All MAs', 'Below All MAs', 'Bounce 50MA', 'Bounce 200MA']
  const tickers = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'AMD', 'TSLA', 'META', 'GOOGL', 'AMZN']
  return Array.from({ length: count }, (_, i) => {
    const price = Math.floor(Math.random() * 400) + 50
    return {
      id: `ma-${i}`, ticker: tickers[i % tickers.length], company: `${tickers[i % tickers.length]} Inc`, price,
      sma20: price * (0.95 + Math.random() * 0.1), sma50: price * (0.9 + Math.random() * 0.2),
      sma200: price * (0.85 + Math.random() * 0.3), signal: signals[Math.floor(Math.random() * signals.length)],
      strength: Math.floor(Math.random() * 100)
    }
  })
}

const generateEarningsReports = (count: number): EarningsReport[] => {
  const tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'CRM', 'ORCL']
  return Array.from({ length: count }, (_, i) => ({
    id: `earnings-${i}`, ticker: tickers[i % tickers.length], company: `${tickers[i % tickers.length]} Corporation`,
    reportDate: new Date(Date.now() + (i + 1) * 86400000 * 3).toISOString().split('T')[0],
    reportTime: Math.random() > 0.5 ? 'BMO' : 'AMC',
    epsEstimate: Math.floor(Math.random() * 500) / 100 + 1, revenueEstimate: `$${Math.floor(Math.random() * 50) + 10}B`,
    surpriseHistory: Math.floor(Math.random() * 20) - 5, optionsIV: Math.floor(Math.random() * 80) + 30
  }))
}

const generatePressReleases = (count: number): PressRelease[] => {
  const categories: PressRelease['category'][] = ['FDA', 'M&A', 'Partnership', 'Product', 'Financial', 'Legal', 'Executive']
  const tickers = ['MRNA', 'PFE', 'NVDA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'AMD', 'META']
  const titles = ['{ticker} Announces Strategic Partnership', '{ticker} Receives FDA Approval', '{ticker} Reports Record Quarter',
    '{ticker} Launches New Product Line', '{ticker} Acquires Competitor', '{ticker} Appoints New CEO',
    '{ticker} Settles Legal Dispute', '{ticker} Expands Into New Markets']
  return Array.from({ length: count }, (_, i) => {
    const ticker = tickers[i % tickers.length]
    return {
      id: `press-${i}`, ticker, company: `${ticker} Inc`,
      title: titles[Math.floor(Math.random() * titles.length)].replace('{ticker}', ticker),
      category: categories[Math.floor(Math.random() * categories.length)],
      timestamp: new Date(Date.now() - i * 3600000).toISOString(),
      sentiment: (Math.random() - 0.3) * 1.5, source: ['PR Newswire', 'Business Wire', 'GlobeNewswire', 'Company IR'][Math.floor(Math.random() * 4)]
    }
  })
}

const generateAInvestSignals = (count: number): AInvestSignal[] => {
  const recommendations: AInvestSignal['recommendation'][] = ['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell']
  const tickers = ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMZN', 'AMD', 'PLTR', 'SMCI']
  const signalTypes = ['Momentum Surge', 'Value Play', 'Breakout Imminent', 'Oversold Bounce', 'Earnings Catalyst', 'Insider Buying', 'Institutional Accumulation', 'Technical Breakout']
  return Array.from({ length: count }, (_, i) => {
    const currentPrice = Math.floor(Math.random() * 500) + 50
    const targetPrice = currentPrice * (1 + (Math.random() * 0.5 - 0.1))
    return {
      id: `ainvest-${i}`, ticker: tickers[i % tickers.length], company: `${tickers[i % tickers.length]} Corporation`,
      aiScore: Math.floor(Math.random() * 40) + 60, recommendation: recommendations[Math.floor(Math.random() * 3)],
      targetPrice: Math.floor(targetPrice), currentPrice, upside: ((targetPrice - currentPrice) / currentPrice) * 100,
      signals: Array.from({ length: Math.floor(Math.random() * 3) + 1 }, () => signalTypes[Math.floor(Math.random() * signalTypes.length)]),
      confidence: Math.floor(Math.random() * 30) + 70
    }
  })
}

// ============================================================================
// Component
// ============================================================================

export function TraderInsights() {
  const { mode } = useTradingMode()
  const [activeTab, setActiveTab] = useState<TabType>('insiders')
  const [currentPage, setCurrentPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [itemsPerPage, setItemsPerPage] = useState(10)
  const [isUsingMockData, setIsUsingMockData] = useState(false)
  const [mockDataTabs, setMockDataTabs] = useState<Set<TabType>>(new Set())
  
  // Data states
  const [insiderTrades, setInsiderTrades] = useState<InsiderTrade[]>([])
  const [topTraders, setTopTraders] = useState<TopTrader[]>([])
  const [finvizSignals, setFinvizSignals] = useState<FinvizSignal[]>([])
  const [maSignals, setMaSignals] = useState<MovingAverageSignal[]>([])
  const [earnings, setEarnings] = useState<EarningsReport[]>([])
  const [pressReleases, setPressReleases] = useState<PressRelease[]>([])
  const [ainvestSignals, setAinvestSignals] = useState<AInvestSignal[]>([])

  // Filter states per tab
  const insiderFilter = useDataFilters(insiderTrades, insiderFields)
  const traderFilter = useDataFilters(topTraders, traderFields)
  const finvizFilter = useDataFilters(finvizSignals, finvizFields)
  const maFilter = useDataFilters(maSignals, maFields)
  const earningsFilter = useDataFilters(earnings, earningsFields)
  const pressFilter = useDataFilters(pressReleases, pressFields)
  const ainvestFilter = useDataFilters(ainvestSignals, ainvestFields)

  const maxItems = 100
  const itemsPerPageOptions = [10, 25, 50, 100]

  useEffect(() => {
    loadAllData()
  }, [mode])

  useEffect(() => {
    setCurrentPage(1)
  }, [activeTab])

  const loadAllData = async () => {
    setLoading(true)
    
    // In demo mode, always use mock data
    if (mode === 'demo') {
      setTimeout(() => {
        setInsiderTrades(generateInsiderTrades(maxItems))
        setTopTraders(generateTopTraders(maxItems))
        setFinvizSignals(generateFinvizSignals(maxItems))
        setMaSignals(generateMovingAverageSignals(maxItems))
        setEarnings(generateEarningsReports(maxItems))
        setPressReleases(generatePressReleases(maxItems))
        setAinvestSignals(generateAInvestSignals(maxItems))
        setLastUpdate(new Date())
        setLoading(false)
        setIsUsingMockData(true)
        setMockDataTabs(new Set(['insiders', 'traders', 'finviz', 'movingavg', 'earnings', 'press', 'ainvest']))
      }, 500)
      return
    }
    
    // In paper/live mode, fetch ALL data from real APIs
    const fetchPromises: Promise<void>[] = []
    
    // 1. Insider Trades (OpenInsider scraping)
    fetchPromises.push(
      fetch('/api/market/insider-trades')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.trades?.length > 0) {
            setInsiderTrades(data.trades)
          }
        })
        .catch(() => {})
    )
    
    // 2. Earnings Calendar
    fetchPromises.push(
      fetch('/api/market/earnings-calendar')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.earnings?.length > 0) {
            setEarnings(data.earnings)
          }
        })
        .catch(() => {})
    )
    
    // 3. Screener Signals (Finviz-style)
    fetchPromises.push(
      fetch('/api/market/screener-signals')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.signals?.length > 0) {
            setFinvizSignals(data.signals.map((s: FinvizSignal, i: number) => ({
              ...s,
              id: s.id || `signal-${i}`,
              volume: typeof s.volume === 'number' ? formatVolume(s.volume as unknown as number) : s.volume,
            })))
          }
        })
        .catch(() => {})
    )
    
    // 4. Moving Average Signals
    fetchPromises.push(
      fetch('/api/market/ma-signals')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.signals?.length > 0) {
            setMaSignals(data.signals.map((s: MovingAverageSignal, i: number) => ({
              ...s,
              id: s.id || `ma-${i}`,
            })))
          }
        })
        .catch(() => {})
    )
    
    // 5. Top Traders (institutional holdings + whale activity)
    fetchPromises.push(
      fetch('/api/market/top-traders')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.traders?.length > 0) {
            setTopTraders(data.traders)
          }
        })
        .catch(() => {})
    )
    
    // 6. Press Releases (from news API)
    fetchPromises.push(
      fetch('/api/market/press-releases')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.releases?.length > 0) {
            setPressReleases(data.releases)
          }
        })
        .catch(() => {})
    )
    
    // 7. AI Invest Signals (from bot analysis)
    fetchPromises.push(
      fetch('/api/market/ai-signals')
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.signals?.length > 0) {
            setAinvestSignals(data.signals)
          }
        })
        .catch(() => {})
    )
    
    await Promise.all(fetchPromises)
    
    setMockDataTabs(new Set()) // No mock data in paper/live mode
    setIsUsingMockData(false)
    setLastUpdate(new Date())
    setLoading(false)
  }
  
  const formatVolume = (vol: number): string => {
    if (vol >= 1e9) return `${(vol / 1e9).toFixed(1)}B`
    if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`
    if (vol >= 1e3) return `${(vol / 1e3).toFixed(0)}K`
    return vol.toString()
  }

  const getCurrentFilter = () => {
    switch (activeTab) {
      case 'insiders': return insiderFilter
      case 'traders': return traderFilter
      case 'finviz': return finvizFilter
      case 'movingavg': return maFilter
      case 'earnings': return earningsFilter
      case 'press': return pressFilter
      case 'ainvest': return ainvestFilter
    }
  }

  const getCurrentFields = () => {
    switch (activeTab) {
      case 'insiders': return insiderFields
      case 'traders': return traderFields
      case 'finviz': return finvizFields
      case 'movingavg': return maFields
      case 'earnings': return earningsFields
      case 'press': return pressFields
      case 'ainvest': return ainvestFields
    }
  }

  const filter = getCurrentFilter()
  const fields = getCurrentFields()
  const data = filter.filteredData
  const totalPages = Math.ceil(data.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const displayedData = data.slice(startIndex, startIndex + itemsPerPage)

  const formatValue = (value: number) => {
    if (value >= 1000000000) return `$${(value / 1000000000).toFixed(1)}B`
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`
    return `$${value.toFixed(0)}`
  }

  const tabs: { id: TabType; label: string; icon: React.ReactNode; count: number }[] = [
    { id: 'insiders', label: 'OpenInsider', icon: <Building2 className="h-4 w-4" />, count: insiderFilter.filteredCount },
    { id: 'traders', label: 'Top Traders', icon: <Users className="h-4 w-4" />, count: traderFilter.filteredCount },
    { id: 'finviz', label: 'Finviz', icon: <TrendingUp className="h-4 w-4" />, count: finvizFilter.filteredCount },
    { id: 'movingavg', label: 'Moving Avg', icon: <BarChart3 className="h-4 w-4" />, count: maFilter.filteredCount },
    { id: 'earnings', label: 'Earnings', icon: <Calendar className="h-4 w-4" />, count: earningsFilter.filteredCount },
    { id: 'press', label: 'Press Releases', icon: <Megaphone className="h-4 w-4" />, count: pressFilter.filteredCount },
    { id: 'ainvest', label: 'AInvest AI', icon: <Brain className="h-4 w-4" />, count: ainvestFilter.filteredCount },
  ]

  // Handle items per page change
  const handleItemsPerPageChange = (newValue: number) => {
    setItemsPerPage(newValue)
    setCurrentPage(1) // Reset to first page when changing items per page
  }

  // Pagination component
  const Pagination = () => (
    <div className="flex items-center justify-between pt-3 border-t border-border">
      <div className="flex items-center gap-3">
        <div className="text-sm text-muted-foreground">
          {startIndex + 1}-{Math.min(startIndex + itemsPerPage, data.length)} of {data.length}
        </div>
        {/* Items per page selector */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Show:</span>
          <select
            value={itemsPerPage}
            onChange={(e) => handleItemsPerPageChange(Number(e.target.value))}
            className="px-2 py-1 rounded-lg bg-secondary border border-border text-foreground text-sm"
          >
            {itemsPerPageOptions.map(option => (
              <option key={option} value={option}>
                {option === 100 ? 'All' : option}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
          disabled={currentPage === 1}
          className="p-2 rounded-lg bg-secondary hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="flex gap-1">
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let pageNum = i + 1
            if (totalPages > 5) {
              if (currentPage <= 3) pageNum = i + 1
              else if (currentPage >= totalPages - 2) pageNum = totalPages - 4 + i
              else pageNum = currentPage - 2 + i
            }
            return (
              <button
                key={pageNum}
                onClick={() => setCurrentPage(pageNum)}
                className={`w-8 h-8 rounded-lg text-sm ${
                  currentPage === pageNum ? 'bg-xfactor-teal text-white' : 'bg-secondary hover:bg-secondary/80'
                }`}
              >
                {pageNum}
              </button>
            )
          })}
        </div>
        <button
          onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
          disabled={currentPage === totalPages || totalPages === 0}
          className="p-2 rounded-lg bg-secondary hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex flex-wrap gap-1 items-center">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setCurrentPage(1) }}
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === tab.id
                  ? 'bg-xfactor-teal text-white'
                  : 'bg-secondary text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.icon}
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="text-[10px] opacity-70">({tab.count})</span>
            </button>
          ))}
          {mode === 'demo' ? (
            <span className="ml-2 px-1.5 py-0.5 bg-amber-500/20 text-amber-400 rounded text-[10px] font-medium flex items-center gap-1">
              <AlertCircle className="h-3 w-3" />
              DEMO DATA
            </span>
          ) : (
            <span className="ml-2 px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded text-[10px] font-medium flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              LIVE DATA
            </span>
          )}
        </div>
        <button
          onClick={loadAllData}
          disabled={loading}
          className="p-2 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Filter Bar */}
      <FilterBar
        searchQuery={filter.searchQuery}
        onSearchChange={filter.setSearchQuery}
        sort={filter.sort}
        onSortChange={filter.toggleSort}
        filters={filter.filters}
        onRemoveFilter={filter.removeFilter}
        onClearAll={filter.clearFilters}
        fields={fields}
        onAddFilter={filter.addFilter}
        totalCount={filter.totalCount}
        filteredCount={filter.filteredCount}
        placeholder={`Search ${activeTab}...`}
        compact
      />

      {/* OpenInsider Tab */}
      {activeTab === 'insiders' && (
        <div className="space-y-2">
          {(displayedData as InsiderTrade[]).map((trade) => (
            <a 
              key={trade.id} 
              href={`http://openinsider.com/search?q=${encodeURIComponent(trade.ticker)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg bg-secondary/30 border border-border hover:border-xfactor-teal/50 cursor-pointer group"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${trade.tradeType === 'Buy' ? 'bg-profit/20' : 'bg-loss/20'}`}>
                    {trade.tradeType === 'Buy' ? <TrendingUp className="h-4 w-4 text-profit" /> : <TrendingDown className="h-4 w-4 text-loss" />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold group-hover:text-xfactor-teal transition-colors">{trade.ticker}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${trade.tradeType === 'Buy' ? 'bg-profit/20 text-profit' : 'bg-loss/20 text-loss'}`}>
                        {trade.tradeType}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">{trade.company}</div>
                  </div>
                </div>
                <div className="text-right flex items-center gap-2">
                  <div>
                    <div className="font-semibold">{formatValue(trade.value)}</div>
                    <div className="text-xs text-muted-foreground">{trade.shares.toLocaleString()} shares</div>
                  </div>
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground group-hover:text-xfactor-teal transition-colors" />
                </div>
              </div>
              <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                <span><User className="h-3 w-3 inline mr-1" />{trade.insider} ({trade.title})</span>
                <span>Filed: {trade.filingDate}</span>
              </div>
              {/* AI Analysis */}
              {trade.aiAnalysis && (
                <div className="mt-2 p-2 rounded bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20">
                  <div className="flex items-start gap-2">
                    <Brain className="h-3.5 w-3.5 text-purple-400 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      <span className="text-purple-400 font-medium">AI Analysis: </span>
                      {trade.aiAnalysis}
                    </p>
                  </div>
                </div>
              )}
            </a>
          ))}
          {displayedData.length === 0 && <div className="text-center py-8 text-muted-foreground">No results found</div>}
          {data.length > 0 && <Pagination />}
        </div>
      )}

      {/* Top Traders Tab */}
      {activeTab === 'traders' && (
        <div className="space-y-2">
          {(displayedData as TopTrader[]).map((trader) => {
            const platformUrl = trader.platform === 'Twitter' 
              ? `https://twitter.com/${trader.handle.replace('@', '')}` 
              : trader.platform === 'Reddit'
              ? `https://reddit.com/user/${trader.handle.replace('u/', '')}`
              : trader.platform === 'StockTwits'
              ? `https://stocktwits.com/${trader.handle.replace('@', '')}`
              : `https://www.google.com/search?q=${encodeURIComponent(trader.name + ' trader')}`;
            return (
            <a 
              key={trader.id} 
              href={platformUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg bg-secondary/30 border border-border hover:border-xfactor-teal/50 cursor-pointer group"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-xfactor-teal/20 flex items-center justify-center">
                    <Users className="h-5 w-5 text-xfactor-teal" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold group-hover:text-xfactor-teal transition-colors">{trader.name}</span>
                      {trader.verified && <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />}
                    </div>
                    <div className="text-xs text-muted-foreground">{trader.handle} • {trader.followers}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`text-sm font-bold ${trader.winRate >= 70 ? 'text-profit' : 'text-yellow-500'}`}>
                    {trader.winRate}% Win
                  </div>
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground group-hover:text-xfactor-teal transition-colors" />
                </div>
              </div>
              {trader.recentCalls.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {trader.recentCalls.map((call, i) => (
                    <span key={i} className={`px-2 py-0.5 rounded text-xs ${
                      call.status === 'Hit Target' ? 'bg-profit/20 text-profit' : 
                      call.status === 'Stopped Out' ? 'bg-loss/20 text-loss' : 'bg-xfactor-teal/20 text-xfactor-teal'
                    }`}>
                      {call.ticker} {call.action}
                    </span>
                  ))}
                </div>
              )}
            </a>
          )})}
          {displayedData.length === 0 && <div className="text-center py-8 text-muted-foreground">No results found</div>}
          {data.length > 0 && <Pagination />}
        </div>
      )}

      {/* Finviz Tab */}
      {activeTab === 'finviz' && (
        <div className="space-y-2">
          {(displayedData as FinvizSignal[]).map((signal) => (
            <a 
              key={signal.id} 
              href={`https://finviz.com/quote.ashx?t=${signal.ticker}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg bg-secondary/30 border border-border hover:border-xfactor-teal/50 cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold group-hover:text-xfactor-teal transition-colors">{signal.ticker}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${signal.change >= 10 ? 'bg-profit/30 text-profit' : 'bg-profit/20 text-profit'}`}>
                      +{signal.change.toFixed(1)}%
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">{signal.sector}</div>
                </div>
                <div className="text-right flex items-center gap-2">
                  <div>
                    <div className="font-semibold">${signal.price}</div>
                    <div className="text-xs text-muted-foreground">Vol: {signal.volume}</div>
                  </div>
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground group-hover:text-xfactor-teal transition-colors" />
                </div>
              </div>
              <div className="mt-2 flex gap-2">
                <span className="text-xs px-2 py-0.5 rounded bg-xfactor-teal/20 text-xfactor-teal">{signal.signal}</span>
                {signal.pattern && <span className="text-xs px-2 py-0.5 rounded bg-xfactor-money/20 text-xfactor-money">{signal.pattern}</span>}
              </div>
            </a>
          ))}
          {displayedData.length === 0 && <div className="text-center py-8 text-muted-foreground">No results found</div>}
          {data.length > 0 && <Pagination />}
        </div>
      )}

      {/* Moving Averages Tab */}
      {activeTab === 'movingavg' && (
        <div className="space-y-2">
          {(displayedData as MovingAverageSignal[]).map((ma) => (
            <a 
              key={ma.id} 
              href={`https://www.tradingview.com/symbols/${ma.ticker}/`}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg bg-secondary/30 border border-border hover:border-xfactor-teal/50 cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold group-hover:text-xfactor-teal transition-colors">{ma.ticker}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      ma.signal.includes('Golden') || ma.signal.includes('Above') ? 'bg-profit/20 text-profit' : 
                      ma.signal.includes('Death') || ma.signal.includes('Below') ? 'bg-loss/20 text-loss' : 'bg-yellow-500/20 text-yellow-500'
                    }`}>
                      {ma.signal}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    SMA20: ${ma.sma20.toFixed(0)} | SMA50: ${ma.sma50.toFixed(0)} | SMA200: ${ma.sma200.toFixed(0)}
                  </div>
                </div>
                <div className="text-right flex items-center gap-2">
                  <div>
                    <div className="font-semibold">${ma.price.toFixed(2)}</div>
                    <div className="text-xs text-muted-foreground">Strength: {ma.strength}%</div>
                  </div>
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground group-hover:text-xfactor-teal transition-colors" />
                </div>
              </div>
            </a>
          ))}
          {displayedData.length === 0 && <div className="text-center py-8 text-muted-foreground">No results found</div>}
          {data.length > 0 && <Pagination />}
        </div>
      )}

      {/* Earnings Tab */}
      {activeTab === 'earnings' && (
        <div className="space-y-2">
          {(displayedData as EarningsReport[]).map((er) => (
            <a 
              key={er.id} 
              href={`https://www.earningswhispers.com/stocks/${er.ticker}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg bg-secondary/30 border border-border hover:border-xfactor-teal/50 cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold group-hover:text-xfactor-teal transition-colors">{er.ticker}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-xfactor-teal/20 text-xfactor-teal">
                      {er.reportDate} {er.reportTime}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">{er.company}</div>
                </div>
                <div className="text-right flex items-center gap-2">
                  <div>
                    <div className="font-semibold">EPS Est: ${er.epsEstimate.toFixed(2)}</div>
                    <div className="text-xs text-muted-foreground">Rev: {er.revenueEstimate}</div>
                  </div>
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground group-hover:text-xfactor-teal transition-colors" />
                </div>
              </div>
              <div className="mt-2 flex gap-3 text-xs">
                <span className={er.surpriseHistory > 0 ? 'text-profit' : 'text-loss'}>
                  Avg Surprise: {er.surpriseHistory > 0 ? '+' : ''}{er.surpriseHistory}%
                </span>
                <span className="text-muted-foreground">Options IV: {er.optionsIV}%</span>
              </div>
            </a>
          ))}
          {displayedData.length === 0 && <div className="text-center py-8 text-muted-foreground">No results found</div>}
          {data.length > 0 && <Pagination />}
        </div>
      )}

      {/* Press Releases Tab */}
      {activeTab === 'press' && (
        <div className="space-y-2">
          {(displayedData as PressRelease[]).map((pr) => (
            <a 
              key={pr.id} 
              href={`https://www.google.com/search?q=${encodeURIComponent(pr.ticker + ' ' + pr.title + ' press release')}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg bg-secondary/30 border border-border hover:border-xfactor-teal/50 cursor-pointer group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold group-hover:text-xfactor-teal transition-colors">{pr.ticker}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      pr.category === 'FDA' ? 'bg-blue-500/20 text-blue-400' :
                      pr.category === 'M&A' ? 'bg-purple-500/20 text-purple-400' :
                      pr.category === 'Partnership' ? 'bg-green-500/20 text-green-400' :
                      'bg-secondary text-muted-foreground'
                    }`}>
                      {pr.category}
                    </span>
                    <span className={`text-xs ${pr.sentiment > 0.2 ? 'text-profit' : pr.sentiment < -0.2 ? 'text-loss' : 'text-muted-foreground'}`}>
                      {pr.sentiment > 0 ? '+' : ''}{pr.sentiment.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-sm mt-1 group-hover:text-xfactor-teal transition-colors">{pr.title}</div>
                  <div className="text-xs text-muted-foreground mt-1">{pr.source} • {new Date(pr.timestamp).toLocaleString()}</div>
                </div>
                <ExternalLink className="h-3.5 w-3.5 text-muted-foreground group-hover:text-xfactor-teal transition-colors shrink-0" />
              </div>
            </a>
          ))}
          {displayedData.length === 0 && <div className="text-center py-8 text-muted-foreground">No results found</div>}
          {data.length > 0 && <Pagination />}
        </div>
      )}

      {/* AInvest AI Tab */}
      {activeTab === 'ainvest' && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
            <Brain className="h-4 w-4 text-xfactor-teal" />
            <span>AI-powered stock analysis from AInvest</span>
            <a href="https://ainvest.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xfactor-teal hover:underline">
              ainvest.com <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          {(displayedData as AInvestSignal[]).map((ai) => (
            <a 
              key={ai.id} 
              href={`https://ainvest.com/stock/${ai.ticker}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg bg-secondary/30 border border-border hover:border-xfactor-teal/50 cursor-pointer group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold group-hover:text-xfactor-teal transition-colors">{ai.ticker}</span>
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                      ai.recommendation === 'Strong Buy' ? 'bg-profit/30 text-profit' :
                      ai.recommendation === 'Buy' ? 'bg-profit/20 text-profit' :
                      ai.recommendation === 'Hold' ? 'bg-yellow-500/20 text-yellow-500' :
                      'bg-loss/20 text-loss'
                    }`}>
                      {ai.recommendation}
                    </span>
                    <span className="text-xs text-muted-foreground">AI Score: {ai.aiScore}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">{ai.company}</div>
                </div>
                <div className="text-right flex items-center gap-2">
                  <div>
                    <div className="font-semibold">${ai.currentPrice} → ${ai.targetPrice}</div>
                    <div className={`text-xs ${ai.upside > 0 ? 'text-profit' : 'text-loss'}`}>
                      {ai.upside > 0 ? '+' : ''}{ai.upside.toFixed(1)}% upside
                    </div>
                  </div>
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground group-hover:text-xfactor-teal transition-colors" />
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {ai.signals.map((sig, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 rounded bg-xfactor-teal/10 text-xfactor-teal">{sig}</span>
                ))}
                <span className="text-xs px-2 py-0.5 rounded bg-secondary text-muted-foreground">
                  {ai.confidence}% confidence
                </span>
              </div>
            </a>
          ))}
          {displayedData.length === 0 && <div className="text-center py-8 text-muted-foreground">No results found</div>}
          {data.length > 0 && <Pagination />}
        </div>
      )}

      {/* Last Update */}
      <div className="text-xs text-muted-foreground text-right">
        Updated: {lastUpdate.toLocaleTimeString()}
      </div>
    </div>
  )
}
