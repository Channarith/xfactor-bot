import { useState, useEffect, useMemo, useRef } from 'react'
import { 
  RefreshCw, ChevronLeft, ChevronRight, TrendingUp, TrendingDown, 
  Minus, Clock, Globe, Search, SortAsc, SortDesc, X, ExternalLink,
  Info, Newspaper, BarChart3, AlertCircle, Building2, Radio, Volume2, VolumeX
} from 'lucide-react'
import { speak, stopSpeaking, isSpeaking, isSpeechSynthesisSupported } from '../utils/audio'
import { 
  useDataFilters, FilterBar, QuickFilters, 
  type FieldDefinition, type FilterConfig 
} from './DataFilters'
import { openExternalUrl } from '../utils/openUrl'

interface NewsItem {
  id: string
  time: string
  timestamp: Date
  ticker: string
  sentiment: number
  headline: string
  source: string
  url: string
  category: string
  region: string
  summary?: string
  keyPoints?: string[]
  relatedTickers?: string[]
  priceImpact?: string
}

interface NewsFeedProps {
  maxItems?: number
  itemsPerPage?: number
}

// Source URL mappings
const sourceUrls: Record<string, string> = {
  'Reuters': 'https://www.reuters.com/markets/',
  'Bloomberg': 'https://www.bloomberg.com/markets',
  'WSJ': 'https://www.wsj.com/market-data',
  'CNBC': 'https://www.cnbc.com/markets/',
  'Financial Times': 'https://www.ft.com/markets',
  'Barrons': 'https://www.barrons.com/market-data',
  'MarketWatch': 'https://www.marketwatch.com/',
  'Yahoo Finance': 'https://finance.yahoo.com/',
  'Benzinga': 'https://www.benzinga.com/',
  'Seeking Alpha': 'https://seekingalpha.com/',
  'CNN Business': 'https://www.cnn.com/business',
  'Fox Business': 'https://www.foxbusiness.com/markets',
  'Caixin': 'https://www.caixinglobal.com/finance/',
  'Nikkei': 'https://asia.nikkei.com/Business/Markets',
  'Handelsblatt': 'https://www.handelsblatt.com/finanzen/',
  'The Economist': 'https://www.economist.com/finance-and-economics',
}

// Generate comprehensive mock news
const generateMockNews = (count: number): NewsItem[] => {
  const tickers = ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMZN', 'AMD', 'SPY', 'QQQ', 
                   'BABA', 'TSM', 'ASML', 'SAP', 'NVO', 'COIN', 'MSTR', 'PLTR', 'ARM', 'SMCI']
  const sources = ['Reuters', 'Bloomberg', 'WSJ', 'CNBC', 'Financial Times', 'Barrons', 
                   'MarketWatch', 'Yahoo Finance', 'Benzinga', 'Seeking Alpha', 'CNN Business',
                   'Fox Business', 'Caixin', 'Nikkei', 'Handelsblatt', 'The Economist']
  const categories = ['Earnings', 'M&A', 'FDA', 'Fed', 'Macro', 'Tech', 'Crypto', 'Options Flow', 'Insider', 'Analyst']
  const regions = ['US', 'EU', 'Asia', 'Global']
  
  const headlines = [
    { 
      text: '{ticker} beats Q4 earnings expectations by 15%', 
      sentiment: 0.75,
      summary: '{ticker} reported quarterly earnings that significantly exceeded analyst expectations, with revenue up 23% year-over-year and earnings per share beating estimates by 15%. Management cited strong demand and successful cost optimization initiatives.',
      keyPoints: ['EPS beat by 15%', 'Revenue up 23% YoY', 'Raised full-year guidance', 'Strong demand in core segments'],
      priceImpact: 'Historically, earnings beats of this magnitude lead to 3-5% stock gains in the following week.'
    },
    { 
      text: '{ticker} announces $10B share buyback program', 
      sentiment: 0.68,
      summary: '{ticker} board has authorized a new $10 billion share repurchase program, signaling confidence in the company\'s future prospects. The buyback will be executed over the next 2 years through open market purchases.',
      keyPoints: ['$10B buyback authorized', '2-year execution timeline', 'Signals management confidence', 'Reduces share count'],
      priceImpact: 'Share buybacks typically provide 1-2% annual EPS accretion and support stock price.'
    },
    { 
      text: 'Breaking: {ticker} in talks for major acquisition', 
      sentiment: 0.55,
      summary: 'Sources familiar with the matter report that {ticker} is in advanced discussions to acquire a competitor, which could significantly expand its market share and product offerings. Deal value is estimated at $5-8 billion.',
      keyPoints: ['Major acquisition talks', 'Estimated $5-8B deal', 'Strategic market expansion', 'Due diligence ongoing'],
      priceImpact: 'Acquisition announcements can be volatile; initial reaction depends on deal terms and synergy expectations.'
    },
    { 
      text: '{ticker} receives FDA approval for new drug', 
      sentiment: 0.82,
      summary: 'The FDA has granted approval for {ticker}\'s new therapeutic drug, opening a potential $3 billion annual market opportunity. This marks a significant milestone in the company\'s pipeline development.',
      keyPoints: ['FDA approval granted', '$3B market opportunity', 'First-to-market advantage', 'Launch expected Q2'],
      priceImpact: 'FDA approvals for major drugs typically result in 5-15% stock appreciation.'
    },
    { 
      text: 'Analyst upgrades {ticker} to Strong Buy, raises PT to $500', 
      sentiment: 0.71,
      summary: 'A prominent Wall Street analyst has upgraded {ticker} to Strong Buy from Hold, raising the price target to $500 (40% upside). The upgrade cites improving fundamentals and sector tailwinds.',
      keyPoints: ['Upgraded to Strong Buy', 'New PT: $500 (40% upside)', 'Improving fundamentals', 'Sector tailwinds noted'],
      priceImpact: 'Analyst upgrades from major firms typically drive 1-3% immediate gains.'
    },
    { 
      text: '{ticker} CEO sells $50M in stock (scheduled sale)', 
      sentiment: -0.15,
      summary: 'The CEO of {ticker} has sold $50 million worth of shares as part of a pre-planned 10b5-1 trading plan. This is a routine, scheduled sale and does not indicate any change in outlook.',
      keyPoints: ['Pre-planned 10b5-1 sale', '$50M shares sold', 'Routine executive transaction', 'No change in outlook'],
      priceImpact: 'Scheduled insider sales rarely impact stock price significantly.'
    },
    { 
      text: '{ticker} faces regulatory scrutiny in EU', 
      sentiment: -0.45,
      summary: 'European regulators have opened an investigation into {ticker}\'s business practices, citing potential antitrust concerns. The company could face fines up to 10% of annual revenue if violations are found.',
      keyPoints: ['EU antitrust investigation', 'Potential 10% revenue fine', 'Investigation may take 18+ months', 'Company denies wrongdoing'],
      priceImpact: 'Regulatory investigations create uncertainty and typically pressure stocks 3-8%.'
    },
    { 
      text: '{ticker} warns of supply chain disruptions', 
      sentiment: -0.52,
      summary: '{ticker} issued a warning about ongoing supply chain challenges affecting production capacity. The company expects Q2 revenue to be impacted by approximately 5-8% due to component shortages.',
      keyPoints: ['Supply chain disruptions', '5-8% Q2 revenue impact', 'Component shortages', 'Seeking alternative suppliers'],
      priceImpact: 'Supply chain warnings typically result in 5-10% stock declines.'
    },
    { 
      text: '{ticker} lowers full-year guidance', 
      sentiment: -0.68,
      summary: '{ticker} has revised its full-year guidance downward, citing softer demand and margin pressure. Revenue expectations have been lowered by 8-10% from previous guidance.',
      keyPoints: ['Guidance lowered 8-10%', 'Softer demand cited', 'Margin pressure continues', 'Cost cuts announced'],
      priceImpact: 'Guidance cuts of this magnitude typically result in 10-15% stock declines.'
    },
    { 
      text: 'Unusual options activity detected in {ticker}', 
      sentiment: 0.35,
      summary: 'Market data shows significant unusual options activity in {ticker}, with call volume 5x normal levels. Large block trades suggest institutional positioning ahead of potential catalyst.',
      keyPoints: ['Call volume 5x normal', 'Large block trades detected', 'Institutional activity', 'Possible catalyst ahead'],
      priceImpact: 'Unusual options activity often precedes significant stock moves by 1-5 days.'
    },
    { 
      text: '{ticker} partners with tech giant on AI initiative', 
      sentiment: 0.62,
      summary: '{ticker} has announced a strategic partnership with a major technology company to develop AI solutions. The multi-year deal includes joint R&D and go-to-market initiatives.',
      keyPoints: ['Strategic AI partnership', 'Multi-year agreement', 'Joint R&D efforts', 'Expanded market reach'],
      priceImpact: 'AI partnership announcements have driven 3-8% gains in the current market.'
    },
    { 
      text: 'Hedge funds increase positions in {ticker}', 
      sentiment: 0.48,
      summary: 'Latest 13F filings reveal that major hedge funds have significantly increased their positions in {ticker} during the quarter. Total institutional ownership has risen to 78%.',
      keyPoints: ['Hedge fund accumulation', '78% institutional ownership', 'Smart money buying', 'Bullish positioning'],
      priceImpact: 'Increased institutional ownership provides support and often precedes outperformance.'
    },
    { 
      text: '{ticker} launches new product line ahead of schedule', 
      sentiment: 0.58,
      summary: '{ticker} has successfully launched its new product line two months ahead of schedule, demonstrating strong execution. Early customer feedback has been overwhelmingly positive.',
      keyPoints: ['Early launch success', 'Strong execution', 'Positive customer feedback', 'Revenue ramp ahead'],
      priceImpact: 'Successful product launches typically drive 2-5% stock appreciation.'
    },
    { 
      text: 'Short interest in {ticker} drops 20%', 
      sentiment: 0.42,
      summary: 'Short interest in {ticker} has declined 20% over the past two weeks, suggesting bears are covering their positions. This reduction in short selling pressure is a bullish technical signal.',
      keyPoints: ['Short interest down 20%', 'Bears covering positions', 'Reduced selling pressure', 'Bullish technical signal'],
      priceImpact: 'Declining short interest often precedes stock appreciation as covering continues.'
    },
    { 
      text: '{ticker} expands into emerging markets', 
      sentiment: 0.38,
      summary: '{ticker} announced expansion plans into key emerging markets including India, Brazil, and Southeast Asia. The company expects these markets to contribute 15% of revenue within 3 years.',
      keyPoints: ['Emerging market expansion', 'India, Brazil, SE Asia focus', '15% revenue target', '3-year timeline'],
      priceImpact: 'Geographic expansion provides long-term growth runway and multiple expansion.'
    },
    { 
      text: 'Fed comments boost outlook for {ticker} sector', 
      sentiment: 0.45,
      summary: 'Federal Reserve officials made dovish comments suggesting rate cuts may be on the horizon, boosting sectors sensitive to interest rates including {ticker}\'s industry.',
      keyPoints: ['Dovish Fed comments', 'Rate cuts possible', 'Sector boost', 'Multiple expansion potential'],
      priceImpact: 'Dovish Fed commentary typically drives 2-4% sector-wide gains.'
    },
    { 
      text: '{ticker} reports record revenue growth', 
      sentiment: 0.78,
      summary: '{ticker} has reported record quarterly revenue, exceeding $50 billion for the first time. The milestone reflects strong demand across all business segments and geographic regions.',
      keyPoints: ['Record revenue milestone', '$50B+ quarterly revenue', 'Strong across segments', 'All regions contributing'],
      priceImpact: 'Record revenue reports typically drive significant stock appreciation.'
    },
    { 
      text: 'Insider buying detected at {ticker}', 
      sentiment: 0.55,
      summary: 'Multiple executives at {ticker} have purchased shares on the open market totaling $2.3 million. Insider buying is typically viewed as a bullish signal of management confidence.',
      keyPoints: ['$2.3M insider purchases', 'Multiple executives buying', 'Management confidence signal', 'Open market purchases'],
      priceImpact: 'Cluster insider buying is one of the most reliable bullish indicators.'
    },
    { 
      text: '{ticker} stock split announced', 
      sentiment: 0.32,
      summary: '{ticker} has announced a 10-for-1 stock split to improve accessibility for retail investors. While splits don\'t change fundamental value, they often attract increased retail interest.',
      keyPoints: ['10-for-1 split announced', 'Improved retail accessibility', 'No fundamental change', 'Often boosts trading volume'],
      priceImpact: 'Stock splits typically result in 5-10% gains in the weeks following announcement.'
    },
    { 
      text: 'Major investor takes stake in {ticker}', 
      sentiment: 0.65,
      summary: 'A prominent activist investor has disclosed a 5% stake in {ticker}, signaling potential for corporate changes. The investor is known for driving operational improvements and shareholder returns.',
      keyPoints: ['5% stake disclosed', 'Activist investor involved', 'Potential corporate changes', 'Track record of improvements'],
      priceImpact: 'Activist stakes typically drive 5-15% initial appreciation on the news.'
    },
  ]

  const news: NewsItem[] = []
  const now = new Date()

  for (let i = 0; i < count; i++) {
    const ticker = tickers[Math.floor(Math.random() * tickers.length)]
    const template = headlines[Math.floor(Math.random() * headlines.length)]
    const minutesAgo = i * 3 + Math.floor(Math.random() * 5)
    const timestamp = new Date(now.getTime() - minutesAgo * 60000)
    const source = sources[Math.floor(Math.random() * sources.length)]
    
    const sentimentVariance = (Math.random() - 0.5) * 0.2
    const sentiment = Math.max(-1, Math.min(1, template.sentiment + sentimentVariance))
    
    // Generate related tickers
    const relatedTickers = tickers
      .filter(t => t !== ticker)
      .sort(() => Math.random() - 0.5)
      .slice(0, 3)

    news.push({
      id: `news-${i}`,
      time: timestamp.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      timestamp,
      ticker,
      sentiment,
      headline: template.text.replace('{ticker}', ticker),
      source,
      url: sourceUrls[source] || 'https://www.google.com/finance',
      category: categories[Math.floor(Math.random() * categories.length)],
      region: regions[Math.floor(Math.random() * regions.length)],
      summary: template.summary?.replace(/{ticker}/g, ticker),
      keyPoints: template.keyPoints,
      priceImpact: template.priceImpact,
      relatedTickers,
    })
  }

  return news.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
}

// Field definitions for filtering
const newsFields: FieldDefinition[] = [
  { key: 'ticker', label: 'Ticker', type: 'string', sortable: true, filterable: true },
  { key: 'headline', label: 'Headline', type: 'string', sortable: false, filterable: true },
  { key: 'sentiment', label: 'Sentiment', type: 'number', sortable: true, filterable: true },
  { key: 'source', label: 'Source', type: 'string', sortable: true, filterable: true },
  { 
    key: 'category', 
    label: 'Category', 
    type: 'select', 
    sortable: true, 
    filterable: true,
    options: [
      { value: 'Earnings', label: 'Earnings' },
      { value: 'M&A', label: 'M&A' },
      { value: 'FDA', label: 'FDA' },
      { value: 'Fed', label: 'Fed' },
      { value: 'Macro', label: 'Macro' },
      { value: 'Tech', label: 'Tech' },
      { value: 'Crypto', label: 'Crypto' },
      { value: 'Options Flow', label: 'Options Flow' },
      { value: 'Insider', label: 'Insider' },
      { value: 'Analyst', label: 'Analyst' },
    ]
  },
  { 
    key: 'region', 
    label: 'Region', 
    type: 'select', 
    sortable: true, 
    filterable: true,
    options: [
      { value: 'US', label: 'US' },
      { value: 'EU', label: 'Europe' },
      { value: 'Asia', label: 'Asia' },
      { value: 'Global', label: 'Global' },
    ]
  },
  { key: 'time', label: 'Time', type: 'string', sortable: true, filterable: false },
]

// Quick filter presets
const quickFilterOptions = [
  { label: '🟢 Bullish', filter: { field: 'sentiment', operator: 'gt' as const, value: 0.2 } },
  { label: '🔴 Bearish', filter: { field: 'sentiment', operator: 'lt' as const, value: -0.2 } },
  { label: '📊 Earnings', filter: { field: 'category', operator: 'eq' as const, value: 'Earnings' } },
  { label: '🤝 M&A', filter: { field: 'category', operator: 'eq' as const, value: 'M&A' } },
  { label: '💊 FDA', filter: { field: 'category', operator: 'eq' as const, value: 'FDA' } },
  { label: '🏛️ Fed', filter: { field: 'category', operator: 'eq' as const, value: 'Fed' } },
  { label: '🇺🇸 US', filter: { field: 'region', operator: 'eq' as const, value: 'US' } },
  { label: '🇪🇺 EU', filter: { field: 'region', operator: 'eq' as const, value: 'EU' } },
  { label: '🌏 Asia', filter: { field: 'region', operator: 'eq' as const, value: 'Asia' } },
]

export function NewsFeed({ maxItems = 100, itemsPerPage = 10 }: NewsFeedProps) {
  const [allNews, setAllNews] = useState<NewsItem[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [selectedNews, setSelectedNews] = useState<NewsItem | null>(null)
  const [showSentimentHelp, setShowSentimentHelp] = useState(false)
  
  // Auto-update feature
  const [autoUpdate, setAutoUpdate] = useState(false)
  const [autoUpdateInterval, setAutoUpdateInterval] = useState(30) // seconds
  const autoUpdateRef = useRef<ReturnType<typeof setInterval> | null>(null)
  
  // Audio readout feature
  const [isReadingNews, setIsReadingNews] = useState(false)

  // Use the data filters hook
  const {
    filteredData,
    searchQuery,
    setSearchQuery,
    sort,
    toggleSort,
    filters,
    addFilter,
    removeFilter,
    clearFilters,
    totalCount,
    filteredCount
  } = useDataFilters(allNews, newsFields)

  useEffect(() => {
    loadNews()
  }, [])
  
  // Auto-update effect
  useEffect(() => {
    if (autoUpdate) {
      autoUpdateRef.current = setInterval(() => {
        loadNews()
      }, autoUpdateInterval * 1000)
    }
    return () => {
      if (autoUpdateRef.current) {
        clearInterval(autoUpdateRef.current)
        autoUpdateRef.current = null
      }
    }
  }, [autoUpdate, autoUpdateInterval])

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery, filters, sort])

  const loadNews = () => {
    setLoading(true)
    setTimeout(() => {
      setAllNews(generateMockNews(maxItems))
      setLastUpdate(new Date())
      setLoading(false)
      setCurrentPage(1)
    }, 500)
  }

  // Pagination
  const totalPages = Math.ceil(filteredData.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const displayedNews = filteredData.slice(startIndex, startIndex + itemsPerPage)

  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0.3) return 'text-profit'
    if (sentiment < -0.3) return 'text-loss'
    return 'text-yellow-500'
  }

  const getSentimentBg = (sentiment: number) => {
    if (sentiment > 0.3) return 'bg-profit/10'
    if (sentiment < -0.3) return 'bg-loss/10'
    return 'bg-yellow-500/10'
  }

  const getSentimentIcon = (sentiment: number) => {
    if (sentiment > 0.2) return <TrendingUp className="h-4 w-4 text-profit" />
    if (sentiment < -0.2) return <TrendingDown className="h-4 w-4 text-loss" />
    return <Minus className="h-4 w-4 text-yellow-500" />
  }

  const getSentimentLabel = (sentiment: number) => {
    if (sentiment >= 0.7) return 'Very Bullish'
    if (sentiment >= 0.4) return 'Bullish'
    if (sentiment >= 0.1) return 'Slightly Bullish'
    if (sentiment >= -0.1) return 'Neutral'
    if (sentiment >= -0.4) return 'Slightly Bearish'
    if (sentiment >= -0.7) return 'Bearish'
    return 'Very Bearish'
  }

  const openArticle = (url: string) => {
    openExternalUrl(url)
  }

  const handleQuickFilter = (filter: FilterConfig) => {
    const existingIndex = filters.findIndex(f => f.field === filter.field && f.value === filter.value)
    if (existingIndex >= 0) {
      removeFilter(existingIndex)
    } else {
      // Remove other filters on the same field for sentiment
      const newFilters = filters.filter(f => f.field !== filter.field)
      newFilters.forEach((_, i) => removeFilter(i))
      addFilter(filter)
    }
  }
  
  // Audio readout of news headlines
  const readNewsAloud = () => {
    if (!isSpeechSynthesisSupported()) {
      alert('Text-to-speech is not supported in this browser')
      return
    }
    
    if (isReadingNews) {
      stopSpeaking()
      setIsReadingNews(false)
      return
    }
    
    const topNews = displayedNews.slice(0, 5) // Read top 5 headlines
    const newsText = topNews.map((news, i) => {
      const sentiment = news.sentiment > 0.2 ? 'bullish' : news.sentiment < -0.2 ? 'bearish' : 'neutral'
      return `Headline ${i + 1}. ${news.ticker}. ${news.headline}. Sentiment is ${sentiment}.`
    }).join(' ... ')
    
    const intro = `Here are the top ${topNews.length} news headlines. `
    
    setIsReadingNews(true)
    speak(intro + newsText, {
      rate: 0.95,
      onEnd: () => setIsReadingNews(false),
      onError: () => setIsReadingNews(false)
    })
  }

  return (
    <div className="space-y-3">
      {/* Filter Bar */}
      <FilterBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        sort={sort}
        onSortChange={toggleSort}
        filters={filters}
        onRemoveFilter={removeFilter}
        onClearAll={clearFilters}
        fields={newsFields}
        onAddFilter={addFilter}
        totalCount={totalCount}
        filteredCount={filteredCount}
        placeholder="Search headlines, tickers, sources..."
      />

      {/* Quick Filters */}
      <QuickFilters
        options={quickFilterOptions}
        activeFilters={filters}
        onToggle={handleQuickFilter}
      />

      {/* Header Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Globe className="h-3 w-3" />
          <span>Global Sources ({filteredCount} articles)</span>
          <span className="text-muted-foreground/50">•</span>
          <button
            onClick={() => setShowSentimentHelp(!showSentimentHelp)}
            className="flex items-center gap-1 hover:text-foreground transition-colors"
            title="What is sentiment score?"
          >
            <Info className="h-3 w-3" />
            <span>What is sentiment?</span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>Updated: {lastUpdate.toLocaleTimeString()}</span>
          </div>
          
          {/* Audio Readout Button */}
          <button
            onClick={readNewsAloud}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              isReadingNews 
                ? 'bg-violet-500/20 text-violet-400 border border-violet-500/30' 
                : 'bg-secondary hover:bg-secondary/80 text-muted-foreground'
            }`}
            title={isReadingNews ? 'Stop reading' : 'Read headlines aloud'}
          >
            {isReadingNews ? <VolumeX className="h-3 w-3" /> : <Volume2 className="h-3 w-3" />}
            <span>{isReadingNews ? 'Stop' : '🔊'}</span>
          </button>
          
          {/* Auto-Update Toggle */}
          <button
            onClick={() => setAutoUpdate(!autoUpdate)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              autoUpdate 
                ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                : 'bg-secondary hover:bg-secondary/80 text-muted-foreground'
            }`}
            title={autoUpdate ? `Live updates every ${autoUpdateInterval}s` : 'Enable live updates'}
          >
            <Radio className={`h-3 w-3 ${autoUpdate ? 'animate-pulse' : ''}`} />
            <span>{autoUpdate ? 'LIVE' : 'Auto'}</span>
          </button>
          
          {/* Auto-Update Interval Selector (shown when auto-update is on) */}
          {autoUpdate && (
            <select
              value={autoUpdateInterval}
              onChange={(e) => setAutoUpdateInterval(Number(e.target.value))}
              className="px-2 py-1 rounded-lg bg-secondary text-xs text-muted-foreground border border-border"
            >
              <option value={15}>15s</option>
              <option value={30}>30s</option>
              <option value={60}>1m</option>
              <option value={120}>2m</option>
              <option value={300}>5m</option>
            </select>
          )}
          
          <button
            onClick={loadNews}
            disabled={loading}
            className="p-2 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors"
            title="Refresh news"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Sentiment Help Panel */}
      {showSentimentHelp && (
        <div className="p-4 rounded-lg bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <BarChart3 className="h-5 w-5 text-blue-400 mt-0.5" />
              <div>
                <h4 className="font-medium text-foreground mb-2">Understanding Sentiment Scores</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  The sentiment score (e.g., <span className="text-profit font-mono">+0.62</span>) is an 
                  <strong> AI-analyzed measure</strong> of how positive or negative the news is for the stock, 
                  ranging from <span className="text-loss font-mono">-1.0</span> (very bearish) to 
                  <span className="text-profit font-mono"> +1.0</span> (very bullish).
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-profit" />
                    <span>+0.7 to +1.0: Very Bullish</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-profit/60" />
                    <span>+0.3 to +0.7: Bullish</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500" />
                    <span>-0.3 to +0.3: Neutral</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-loss" />
                    <span>-0.3 to -1.0: Bearish</span>
                  </div>
                </div>
              </div>
            </div>
            <button
              onClick={() => setShowSentimentHelp(false)}
              className="p-1 hover:bg-secondary rounded"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* News List */}
      <div className="space-y-2">
        {displayedNews.map((news) => (
          <button
            key={news.id}
            onClick={() => setSelectedNews(news)}
            className={`w-full flex items-center gap-3 rounded-lg px-3 py-2.5 border border-border/50 hover:border-xfactor-teal/50 hover:shadow-lg hover:shadow-xfactor-teal/5 transition-all cursor-pointer ${getSentimentBg(news.sentiment)}`}
          >
            {/* Time */}
            <span className="text-xs text-muted-foreground w-14 shrink-0 text-left">
              [{news.time}]
            </span>
            
            {/* Ticker */}
            <span className="font-bold text-foreground w-14 shrink-0 text-left">
              {news.ticker}
            </span>
            
            {/* Sentiment */}
            <div 
              className={`flex items-center gap-1 w-16 shrink-0 ${getSentimentColor(news.sentiment)}`}
              title={`Sentiment: ${getSentimentLabel(news.sentiment)}`}
            >
              {getSentimentIcon(news.sentiment)}
              <span className="text-sm font-medium">
                {news.sentiment > 0 ? '+' : ''}{news.sentiment.toFixed(2)}
              </span>
            </div>
            
            {/* Category badge */}
            <span className="text-xs px-2 py-0.5 rounded bg-secondary text-muted-foreground shrink-0">
              {news.category}
            </span>
            
            {/* Headline */}
            <span className="flex-1 text-sm truncate text-left" title="Click for details">
              "{news.headline}"
            </span>
            
            {/* Source & Region */}
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs text-muted-foreground">
                {news.source}
              </span>
              <span className="text-xs px-1.5 py-0.5 rounded bg-xfactor-teal/20 text-xfactor-teal">
                {news.region}
              </span>
              <ExternalLink className="h-3 w-3 text-muted-foreground/50" />
            </div>
          </button>
        ))}

        {displayedNews.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No news matching your filters
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div className="text-sm text-muted-foreground">
            Showing {startIndex + 1}-{Math.min(startIndex + itemsPerPage, filteredData.length)} of {filteredData.length}
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-2 rounded-lg bg-secondary hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum: number
                if (totalPages <= 5) {
                  pageNum = i + 1
                } else if (currentPage <= 3) {
                  pageNum = i + 1
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i
                } else {
                  pageNum = currentPage - 2 + i
                }
                
                return (
                  <button
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    className={`w-8 h-8 rounded-lg text-sm transition-colors ${
                      currentPage === pageNum
                        ? 'bg-xfactor-teal text-white'
                        : 'bg-secondary hover:bg-secondary/80'
                    }`}
                  >
                    {pageNum}
                  </button>
                )
              })}
              {totalPages > 5 && currentPage < totalPages - 2 && (
                <>
                  <span className="text-muted-foreground">...</span>
                  <button
                    onClick={() => setCurrentPage(totalPages)}
                    className="w-8 h-8 rounded-lg text-sm bg-secondary hover:bg-secondary/80 transition-colors"
                  >
                    {totalPages}
                  </button>
                </>
              )}
            </div>
            
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-2 rounded-lg bg-secondary hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* News Detail Modal */}
      {selectedNews && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-card rounded-xl border border-border max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl animate-in fade-in zoom-in duration-200">
            {/* Modal Header */}
            <div className={`p-5 border-b border-border ${getSentimentBg(selectedNews.sentiment)}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-bold text-lg">{selectedNews.ticker}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-secondary text-muted-foreground">
                      {selectedNews.category}
                    </span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-xfactor-teal/20 text-xfactor-teal">
                      {selectedNews.region}
                    </span>
                  </div>
                  <h2 className="text-lg font-medium text-foreground leading-tight">
                    {selectedNews.headline}
                  </h2>
                </div>
                <button
                  onClick={() => setSelectedNews(null)}
                  className="p-2 rounded hover:bg-secondary shrink-0"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              
              {/* Sentiment Badge */}
              <div className="flex items-center gap-4 mt-4">
                <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${getSentimentBg(selectedNews.sentiment)} border ${
                  selectedNews.sentiment > 0.3 ? 'border-profit/30' : 
                  selectedNews.sentiment < -0.3 ? 'border-loss/30' : 'border-yellow-500/30'
                }`}>
                  {getSentimentIcon(selectedNews.sentiment)}
                  <div>
                    <div className={`font-bold ${getSentimentColor(selectedNews.sentiment)}`}>
                      {selectedNews.sentiment > 0 ? '+' : ''}{selectedNews.sentiment.toFixed(2)}
                    </div>
                    <div className="text-[10px] text-muted-foreground">
                      {getSentimentLabel(selectedNews.sentiment)}
                    </div>
                  </div>
                </div>
                
                <div className="text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Building2 className="h-3 w-3" />
                    {selectedNews.source}
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {selectedNews.timestamp.toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
            
            {/* Modal Body */}
            <div className="p-5 space-y-5">
              {/* Summary */}
              {selectedNews.summary && (
                <div>
                  <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                    <Newspaper className="h-4 w-4" />
                    Summary
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {selectedNews.summary}
                  </p>
                </div>
              )}
              
              {/* Key Points */}
              {selectedNews.keyPoints && selectedNews.keyPoints.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    Key Points
                  </h3>
                  <ul className="space-y-1">
                    {selectedNews.keyPoints.map((point, i) => (
                      <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                        <span className="text-xfactor-teal mt-1">•</span>
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Price Impact */}
              {selectedNews.priceImpact && (
                <div className="p-3 rounded-lg bg-gradient-to-r from-violet-500/10 to-indigo-500/10 border border-violet-500/20">
                  <h3 className="text-sm font-medium text-violet-300 mb-1 flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" />
                    Potential Price Impact
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {selectedNews.priceImpact}
                  </p>
                </div>
              )}
              
              {/* Related Tickers */}
              {selectedNews.relatedTickers && selectedNews.relatedTickers.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-foreground mb-2">Related Stocks</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedNews.relatedTickers.map((ticker) => (
                      <span 
                        key={ticker}
                        className="px-2 py-1 rounded bg-secondary text-sm font-mono"
                      >
                        {ticker}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            {/* Modal Footer */}
            <div className="flex justify-between gap-3 p-4 border-t border-border bg-secondary/30">
              <button
                onClick={() => setSelectedNews(null)}
                className="px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-sm transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => openArticle(selectedNews.url)}
                className="px-4 py-2 rounded-lg bg-xfactor-teal text-white font-medium hover:bg-xfactor-teal/90 text-sm transition-colors flex items-center gap-2"
              >
                <ExternalLink className="h-4 w-4" />
                Read Full Article at {selectedNews.source}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
