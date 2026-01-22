import { useState, useRef, useEffect } from 'react';
import { X, HelpCircle, Zap, Bot, LineChart, Shield, Settings, Cpu, Globe, Calendar, Book, TrendingUp, TrendingDown, BarChart3, Activity, Target, Layers, Search, ChevronDown, ChevronUp, Mic, MicOff, Volume2, AlertTriangle } from 'lucide-react';
import { createSpeechRecognition, speak, isSpeechRecognitionSupported, isSpeechSynthesisSupported, stopSpeaking } from '../utils/audio';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Version is injected from package.json via Vite at build time
const VERSION = __APP_VERSION__;

const features = [
  // Core Trading
  {
    icon: Bot,
    title: '40+ Trading Bots',
    description: 'Pre-configured bots for stocks, options, futures, crypto, forex, and commodities. Numbered list with customizable strategies.'
  },
  {
    icon: Activity,
    title: 'Multi-Broker Support',
    description: 'Connect to IBKR, Alpaca, Schwab, Tradier, and NinjaTrader 8. OAuth, API keys, or username/password auth.'
  },
  // AI & Forecasting
  {
    icon: Zap,
    title: '🔮 AI Market Forecasting',
    description: 'Auto-populating trending symbols, catalysts, AI hypotheses, viral alerts. Pattern predictions with score breakdowns and formulas.'
  },
  {
    icon: Cpu,
    title: '🧠 Agentic Tuning (ATRWAC)',
    description: 'AI-powered auto-tuning with Anthropic, OpenAI, or Ollama. Automatic strategy optimization and parameter adjustment.'
  },
  // Analysis Panels
  {
    icon: LineChart,
    title: '📊 Stock Analyzer',
    description: 'Comprehensive time-series analysis with inflection points, golden/death crosses, analyst targets, and fundamental metrics.'
  },
  {
    icon: Target,
    title: '📹 Video Platforms Intelligence',
    description: 'Track 50+ finance influencers on YouTube, TikTok, Instagram. Viral alerts, trending videos, clickable profiles.'
  },
  // Asset Classes
  {
    icon: Globe,
    title: '💱 Forex Trading',
    description: 'Major pairs, Asia-Pacific FX, Euro crosses. Live rates, pip calculator, session times, and currency strength.'
  },
  {
    icon: Layers,
    title: '₿ Cryptocurrency Trading',
    description: 'Bitcoin, Ethereum, altcoins, DeFi, meme coins. Fear & Greed index, whale alerts with blockchain links.'
  },
  {
    icon: BarChart3,
    title: '⛏️ Commodities & Resources',
    description: 'Gold, oil, agriculture, uranium, lithium, rare earth metals. Commodity ETFs with news and price tracking.'
  },
  // Risk & Strategy
  {
    icon: Shield,
    title: '🛡️ Bot Risk Management',
    description: 'Risk scoring 0-100, Sharpe/Sortino ratios, VaR, max drawdown protection, VIX-based circuit breakers.'
  },
  {
    icon: Settings,
    title: 'Strategy Controls',
    description: 'Enable/disable strategies globally. Disabled strategies blocked in Create Bot. 10+ strategy templates.'
  },
  // Intelligence
  {
    icon: TrendingUp,
    title: 'Top Traders & Insider Activity',
    description: 'Track insider trades, top Reddit/Twitter traders, Finviz signals, earnings, press releases, AInvest AI.'
  },
  {
    icon: Activity,
    title: '📰 Live News & Sentiment',
    description: '100+ news sources, NLP sentiment analysis, real-time feed with clickable article links.'
  },
  // Help & Reference
  {
    icon: Book,
    title: '📚 900+ Trading Glossary',
    description: 'Visual SVG diagrams for RSI, MACD, patterns. Searchable terms with formulas and XFactor usage tips.'
  }
];

const quickStart = [
  { step: 1, title: 'Connect Broker', description: 'Go to Admin Panel > Broker Config and connect your trading account (IBKR, Alpaca, Schwab, Tradier, or NinjaTrader 8).' },
  { step: 2, title: 'Select Trading Mode', description: 'Choose Demo (simulated with fake data), Paper (broker paper trading), or Live mode for real trading.' },
  { step: 3, title: 'Configure Bots', description: 'Enable desired bots from the Bot Manager panel (40+ available). Filter by asset type: stocks, options, futures, crypto, or forex.' },
  { step: 4, title: 'Enable Agentic Tuning', description: 'Set up AI auto-tuning with your preferred provider (Anthropic, OpenAI, or Ollama). Let AI optimize your strategy parameters.' },
  { step: 5, title: 'Explore Market Intelligence', description: 'Check Video Platforms for influencer activity, Trader Insights for insider trades, and Forecasting for AI predictions.' },
  { step: 6, title: 'Monitor All Asset Classes', description: 'Track Forex pairs, Crypto with whale alerts, and Commodities. Each panel has real-time data and clickable references.' },
  { step: 7, title: 'Set Risk Controls', description: 'Configure Bot Risk Management for risk scoring, position limits, ATR-based stops, and VIX circuit breakers.' },
  { step: 8, title: 'Use the Glossary', description: 'Access 900+ trading terms with visual diagrams. Search or filter by category to learn indicators, patterns, and strategies.' },
  { step: 9, title: 'Start Trading', description: 'Click Start on individual bots or use Start All to begin automated trading. Monitor performance in the Dashboard.' }
];

const changelog = [
  {
    version: '2.1.10',
    date: 'January 22, 2026',
    changes: [
      '📚 Massively Expanded Trading Glossary (900+ terms)',
      '',
      '• Expanded from 500+ to 900+ trading terms',
      '• 200+ new options terms: Greeks, strategies, exotics',
      '• 50+ crypto/DeFi: Layer 2, rollups, MEV, yield farming',
      '• 100+ technical indicators: Ichimoku, breadth, vol surface',
      '• 80+ chart patterns: wedges, triangles, candlesticks',
      '• 50+ fundamental metrics: DCF, DuPont, quality scores',
      '• 50+ forex terms: carry trade, central banks, pips',
      '• 40+ futures: contango, roll yield, spreads',
      '• 30+ trading regulations: Reg T, margin rules, violations',
      '',
      '🔧 Bug Fixes',
      '• Fixed duplicate Prometheus metrics error on startup',
      '• MetricsCollector now uses singleton pattern',
      '• PyInstaller: Added --paths for src package discovery',
    ]
  },
  {
    version: '2.1.9',
    date: 'January 21, 2026',
    changes: [
      '🌐 Network Error Handling',
      '',
      '• Smart network outage detection across the system',
      '• Single "NETWORK DOWN" warning instead of log spam',
      '• Pauses trading automatically when network fails',
      '• "NETWORK RESTORED" notification when connectivity returns',
      '• Reduces hundreds of error logs to a few clean warnings',
      '',
      '🔧 Bug Fixes',
      '• Fixed BotManager "bots" attribute error on shutdown',
      '• Fixed stop_all() method call in cleanup',
    ]
  },
  {
    version: '2.1.8',
    date: 'January 21, 2026',
    changes: [
      '🛡️ Sell Order Validation',
      '',
      '• Comprehensive validation before every sell order',
      '• Verifies position exists on broker before selling',
      '• Prevents selling stocks you don\'t own',
      '• Fresh position check (not cached) before each sell',
      '• Quantity adjustment if selling more than available',
      '',
      '🔍 Multi-Broker Position Check',
      '• GET /api/positions/multi-broker/{symbol} endpoint',
      '• Check where a position exists across all brokers',
      '• POST /api/positions/validate-sell endpoint',
      '• Pre-validate sell orders before execution',
      '• Identifies "wrong broker" configuration issues',
    ]
  },
  {
    version: '2.1.7',
    date: 'January 20, 2026',
    changes: [
      '🛡️ Margin Safety System',
      '',
      '• Monitors margin cushion % above maintenance requirement',
      '• Blocks new buys when margin < 20%',
      '• Auto-reduces positions when margin < 15%',
      '• Emergency sell when margin < 12%',
      '• Configurable thresholds in bot settings',
      '',
      '📊 Position Bot Tracking',
      '• Open Positions now shows which bot opened each position',
      '• Displays bot_id, bot_name, and opened_at timestamp',
      '',
      '🔧 Agentic Tuning Fix',
      '• Fixed 24-hour delay before first evaluation',
      '• Now evaluates immediately on start',
    ]
  },
  {
    version: '2.1.6',
    date: 'January 20, 2026',
    changes: [
      '⏱️ Bot Rate Limiting',
      '',
      '• Configurable delays between orders to prevent broker throttling',
      '• order_delay_seconds: 2.0s delay between orders',
      '• symbol_delay_seconds: 0.5s delay between analyzing symbols',
      '• max_orders_per_minute: 10 orders/minute limit per bot',
      '• min_order_interval_seconds: 1.0s minimum between orders',
      '• Automatic waiting when rate limits are approached',
      '• Clear logging shows when rate limiting is active',
    ]
  },
  {
    version: '2.1.5',
    date: 'January 20, 2026',
    changes: [
      '✨ IBKR Extended Hours Trading',
      '',
      '• Pre-market trading: 4:00 AM - 9:30 AM ET',
      '• After-hours trading: 4:00 PM - 8:00 PM ET',
      '• Market orders auto-convert to limit orders in extended hours',
      '• Limit price = current price ± 0.5% buffer',
      '• outsideRth=True flag enables extended hours execution',
      '',
      '📊 Order Limit Tracking (15 per symbol/side)',
      '• Tracks orders per symbol per side over 24h window',
      '• Prevents exceeding IBKR order limits',
      '• get_order_counts() shows current order usage',
    ]
  },
  {
    version: '2.1.4',
    date: 'January 20, 2026',
    changes: [
      '🐛 IBKR Fractional Shares - Complete Fix',
      '',
      '• Fixed IBKR error 10243: "Fractional-sized order cannot be placed via API"',
      '• Added supports_fractional_shares property to broker interface',
      '• Bots now check broker capability before calculating order quantities',
      '• Two-level protection: bot-level + broker-level rounding',
      '• Sell orders also respect broker fractional share support',
    ]
  },
  {
    version: '2.1.3',
    date: 'January 17, 2026',
    changes: [
      '🐛 IBKR Fractional Shares Fix',
      '',
      '• IBKR does not support fractional shares for most symbols',
      '• Orders now automatically round down to whole numbers',
      '• If rounded quantity is 0, order is rejected with clear error',
      '• Prevents cryptic broker-level failures',
      '',
      '🔧 Top Traders API Fix',
      '• Fixed missing _ensure_insider_data function',
      '• /api/market/top-traders now works correctly',
      '',
      '🔧 yfinance NoneType Fix',
      '• Fixed NoneType not subscriptable errors',
      '• Added null checks when yfinance returns None',
    ]
  },
  {
    version: '2.1.2',
    date: 'January 17, 2026',
    changes: [
      '🐛 Bug Fixes & Multi-Broker Improvements',
      '',
      '🔧 Bot Manager UI Fix',
      '• Removed duplicate nested "Bot Manager" header',
      '• Now displays actual bot count correctly',
      '',
      '💰 P&L Tracking Fixed',
      '• Bots now properly track daily/total P&L when trades execute',
      '• Previously showed +$0.00 even after trades',
      '',
      '🔄 Bot Details Auto-Refresh',
      '• Performance chart refreshes bot details every 30 seconds',
      '',
      '📊 Trade Rejection Tracking',
      '• Track rejections by reason (buying power, position limit, etc.)',
      '• View blocked_by_* counters and recent rejections in bot status',
      '',
      '🔗 Multi-Broker Mode by Default',
      '• New bots trade on ALL connected brokers simultaneously',
      '• Ensures trades go to both IBKR and Alpaca',
      '',
      '⚙️ Bot-Level Limit Overrides',
      '• override_global_limits: Bot limits take precedence',
      '• ignore_vix_limits: Don\'t reduce position size during VIX spikes',
      '• ignore_sector_limits: Skip sector concentration checks',
      '',
      '🛠️ Technical Fixes',
      '• Fixed FastAPI regex deprecation warnings',
      '• Fixed pandas timezone parsing warnings',
      '• Added Alpaca crypto symbol normalization (BTC-USD → BTC/USD)',
    ]
  },
  {
    version: '2.1.1',
    date: 'January 7, 2026',
    changes: [
      '🐛 IBKR Broker Event Loop Fix',
      '',
      '• Fixed asyncio.Lock bound to different event loop error',
      '• Occurred when multiple bots accessed IBKR concurrently',
      '• Async lock now detects event loop changes automatically',
    ]
  },
  {
    version: '2.1.0',
    date: 'January 7, 2026',
    changes: [
      '✨ Manual Trading Feature',
      '',
      '📝 Manual Trading API',
      '• Submit manual buy/sell orders through the platform',
      '• Quick buy/sell with dollar amounts or share quantities',
      '• Close positions with percentage control',
      '• Trade history with filtering by source',
      '',
      '📊 Bot vs Manual Performance Comparison',
      '• Track performance of manual trades vs automated bots',
      '• Compare win rates, P&L, and trade volume',
      '• AI-powered recommendations based on performance',
      '• Best/worst trade tracking for each source',
      '',
      '🖥️ Manual Trading Frontend Component',
      '• Trade Tab: Buy/sell order form with symbol, quantity, order type',
      '• History Tab: Filterable trade history (all/manual/bot)',
      '• Comparison Tab: Visual bot vs manual performance analytics',
      '• Support for paper and live trading modes',
      '',
      '🔧 Trade Source Tracking',
      '• All trades categorized: manual, bot, tradingview, api',
      '• Bot trades include reasoning, confidence, indicators',
      '• Thread-safe trade history storage',
    ]
  },
  {
    version: '2.0.0',
    date: 'January 7, 2026',
    changes: [
      '🚨 MAJOR RELEASE - Critical Bug Fix & Bot Intelligence Overhaul',
      '',
      '🐛 CRITICAL FIX: Asyncio Semaphore Event Loop Bug',
      '• All bots were failing with "Semaphore bound to different event loop"',
      '• Result: ZERO signals generated since startup',
      '• Root cause: asyncio.Semaphore cannot be shared across threads',
      '• Fix: Changed to threading.Semaphore for cross-thread compatibility',
      '',
      '🎯 Bot-Specific Signal Thresholds',
      '• Added SignalPreset class with 8 strategy profiles',
      '• Each bot now has strategy-appropriate thresholds:',
      '  - CONSERVATIVE (1.5/3.0): Dividend, S&P ETFs',
      '  - MODERATE (2.0/4.0): Swing traders, Forex',
      '  - AGGRESSIVE (2.5/4.8): Momentum, Leveraged ETFs',
      '  - ULTRA_AGGRESSIVE (1.0/2.5): Scalping, 0DTE, Meme coins',
      '  - NEWS_DRIVEN (1.5/3.5): China ADRs, Biotech, News bots',
      '  - INCOME (1.2/2.5): Dividend, Bond ETFs',
      '  - CRYPTO (1.8/3.5): BTC, ETH, DeFi tokens',
      '  - COMMODITY (1.5/3.5): Gold, Oil, Industrial metals',
      '',
      '📊 All 50 Default Bots Updated',
      '• Dividend Growth: INCOME preset (easy entry, reluctant to sell)',
      '• China Tech ADRs: NEWS_DRIVEN (quick reaction to geopolitical)',
      '• 0DTE Scalper: ULTRA_AGGRESSIVE (very sensitive, 15s checks)',
      '• Bond ETF Rotator: INCOME (conservative, 10 min checks)',
      '• Meme Coin Scalper: ULTRA_AGGRESSIVE (quick entries/exits)',
      '',
      '🛠️ Auto Version Bump Script',
      '• scripts/auto_version_bump.py for automated versioning',
      '• 8+ features → patch bump, 20+ features → minor bump',
    ],
  },
  {
    version: '1.2.4',
    date: 'January 5, 2026',
    changes: [
      '🚀 More Aggressive Trading Defaults',
      '• max_positions: 10 → 50 per bot',
      '• trade_frequency: 60s → 30s (2x faster checking)',
      '• strong_buy_threshold: 6 → 4.8 points',
      '• buy_signal_threshold: 3 → 2 points',
      '💰 Dynamic Position Sizing',
      '• Position size now based on % of broker buying power',
      '• max_position_pct: 10% of buying power per position',
      '• Auto-adjusts based on account size',
      '📊 Momentum Scanner Fixed',
      '• Leaderboard now shows sample data when no scans run',
      '• Social trending shows viral stocks with buzz scores',
      '• News hot shows stocks with news momentum',
      '🔌 Extended Hours & Fractional Trading',
      '• enable_extended_hours: pre-market (4AM) and after-hours (8PM)',
      '• enable_fractional_shares: support for 0.000001 quantities',
      '• Broker-dependent (Alpaca supports fractional)',
      '📈 Pareto Performance Analysis',
      '• GET /api/bots/performance/pareto - 80/20 analysis',
      '• Shows which bots contribute most to P&L',
      '🔍 Analyst Ratings & Predictions',
      '• GET /api/market/analyst-ratings - consensus ratings',
      '• GET /api/market/analyst-actions - upgrades/downgrades',
      '🛡️ Bot Risk Management Fixed',
      '• /api/bots/risk/all now auto-scores all active bots',
      '🌐 Free Web Scraping Providers (No API Keys)',
      '• Removed Alpha Vantage (required API key)',
      '• Added CNBC, Google Finance, MarketWatch scrapers',
      '🔧 Broker Selector',
      '• Filter portfolio by broker when multiple connected',
    ],
  },
  {
    version: '1.2.3',
    date: 'January 4, 2026',
    changes: [
      '📊 22+ Indicators Across 7 Categories',
      '• Momentum: RSI, Stochastic Oscillator, Williams %R',
      '• Trend: MA Stack (20/50/200), Golden/Death Cross, MACD, ADX',
      '• Volatility: Bollinger Bands + Squeeze, Keltner Channels, ATR',
      '• Volume: Volume Ratio, OBV, VWAP above/below',
      '• Technical: Pivot Points (S1/S2, R1/R2), Donchian Channels, ROC',
      '• Sentiment: News sentiment, Social buzz, Top trader momentum',
      '📐 14 Chart Pattern Recognition (NEW)',
      '• Bullish: Double Bottom, Inverted H&S, Falling Wedge, Bullish Flag, Ascending Triangle, Cup & Handle',
      '• Bearish: Double Top, Head & Shoulders, Rising Wedge, Bearish Flag, Descending Triangle, Expanding Triangle',
      '• Neutral: Symmetrical Triangle, Pennant',
      '💰 Enhanced Positions Display',
      '• Open Positions tab with Buy Price vs Current Price comparison',
      '• "If Sold" column showing potential profit/loss',
      '• Percent change since purchase with trend icons',
      '• NEW: Closed Trades tab with full P&L history',
      '• Trade statistics: Win rate, Total realized P&L',
      '📝 Trade Reasoning Tracking',
      '• Every trade logs detailed reasoning (which indicators triggered)',
      '• API endpoints: /api/bots/trades, /api/positions/completed-trades',
      '🔢 Scoring System Update',
      '• Max 22 points per side (bullish/bearish)',
      '• Strong Buy/Sell threshold: ≥6 points',
      '• Buy/Sell threshold: ≥3 points',
    ],
  },
  {
    version: '1.2.2',
    date: 'January 3, 2026',
    changes: [
      '📈 ETF Overview Widget (NEW)',
      '• Top ETFs: S&P 500, Growth, Value, Dividend, Sector',
      '• International: Developed Markets, Emerging Markets, China, Europe, Japan',
      '• Leveraged/Inverse: Bull 3x, Bear 3x, Volatility ETFs (TQQQ, SQQQ, etc.)',
      '• Real-time quotes with price, change%, and volume',
      '🤖 10 New Trading Bots (50 Total)',
      '• Top S&P 500 ETFs (VOO, SPY, IVV)',
      '• Inverse/Leveraged ETFs (TQQQ, SQQQ, SOXL, SOXS)',
      '• International Developed Markets (EFA, VEA, VGK)',
      '• Emerging Markets ETFs (EEM, VWO, FXI)',
      '• Thematic Growth ETFs (ARKK, ICLN, BOTZ)',
      '• ADR Blue Chips (TSM, ASML, NVO)',
      '• China Tech ADRs (BABA, JD, PDD)',
      '• European Luxury Brands (LVMUY, RACE)',
      '• Bond ETF Rotator (AGG, TLT, HYG)',
      '• Volatility ETF Trader (VXX, UVXY)',
      '🔗 Multi-Broker UI Integration',
      '• Target Broker dropdown: Route orders to specific broker',
      '• Multi-Broker Mode checkbox: Execute on ALL connected brokers',
      '🔍 Symbol Autocomplete Search',
      '• Search 12,000+ symbols with instant autocomplete',
      '📊 Momentum Dashboard on Main Dashboard',
      '• Leaderboard, Sectors, Social, and News tabs',
    ]
  },
  {
    version: '1.2.1',
    date: 'January 3, 2026',
    changes: [
      '📊 Full Momentum Suite',
      '• Tiered Universe Scanner: Hot 100 (15m), Active 1000 (1h), Full 12k+ (2x/day)',
      '• 25 sector/sub-sector definitions with ETF proxies',
      '• Unified MomentumScore combining price, volume, social, news',
      '🔥 4 Momentum Bot Templates',
      '• Sector Rotation Bot: Rotates into top stocks from hottest sectors',
      '• Social Momentum Bot: Trades viral/trending stocks from social buzz',
      '• News Momentum Bot: News-driven catalyst trades',
      '• Composite Momentum Bot: Only trades when all signals align',
      '📈 Momentum Dashboard',
      '• Leaderboard: Top stocks by composite momentum score',
      '• Sector heatmap with momentum rankings',
      '• Social trending feed with buzz scores',
      '• News momentum with catalyst detection',
      '🔄 Background Scanning',
      '• MomentumScanScheduler for automated tiered scanning',
      '• Scans during market hours with configurable intervals',
      '• Full universe scans pre-market and after-hours',
      '🎯 API Endpoints',
      '• /api/momentum/* for all momentum data',
      '• /api/momentum/bots/create/{template} for one-click bot creation',
    ]
  },
  {
    version: '1.2.0',
    date: 'January 3, 2026',
    changes: [
      '🔗 Multi-Broker Bot Routing',
      '• Assign bots to specific brokers (Alpaca, IBKR, etc.)',
      '• Multi-broker mode: execute on ALL connected brokers simultaneously',
      '• Failover broker support: automatic fallback if primary disconnects',
      '🚀 Background Service & Auto-Start',
      '• Standalone bot service runs independently of desktop app',
      '• macOS launchd integration for auto-start on login',
      '• Bots continue running even after closing the app',
      '• python scripts/install_service.py to install',
      '📊 12,000+ Symbol Universe',
      '• Full NASDAQ, NYSE, and AMEX symbol database',
      '• Fast symbol search with autocomplete',
      '• ETF categories: Leveraged, Vanguard, iShares, Sector, Commodities, Crypto',
      '📈 Growth Screener',
      '• Find top growth stocks by timeframe (1m, 1d, 1w, 1M)',
      '• Volume surge detection and momentum scoring',
      '• /api/screener/top-growth endpoint',
      '🏷️ Quick ETF Presets in Bot Creation',
      '• One-click add: Leveraged (SOXL, TQQQ), Vanguard (VOO, VTI)',
      '• iShares (IVV, IWM), Sector (XLK, XLF), Commodities (GLD, USO)',
      '• Crypto ETFs (IBIT, FBTC, GBTC)',
    ]
  },
  {
    version: '1.1.9',
    date: 'January 3, 2026',
    changes: [
      '🔧 Critical Event Loop Fix',
      '• Fixed "asyncio.Lock bound to different event loop" errors',
      '• Bots now work correctly with Alpaca across all threads',
      '• Replaced asyncio.Lock with threading.Lock for cross-thread safety',
      '📰 SSL Certificate Fix for News Feeds',
      '• Fixed SSL certificate verification errors on macOS',
      '• News feeds now work correctly on all platforms',
    ]
  },
  {
    version: '1.1.8',
    date: 'January 2, 2026',
    changes: [
      '🦙 Alpaca Connection Fix',
      'Fixed API key/secret mapping between frontend and backend',
      'Added api_secret alias for backwards compatibility',
      'Better credential validation with descriptive error messages',
      '💾 Saved Broker Connections',
      'Save broker credentials securely after successful connection',
      'Auto-connect to saved brokers on app startup',
      'Encrypted credential storage with machine-specific key',
      '/api/integrations/brokers/saved - List saved connections',
      '/api/integrations/brokers/saved/connect - Quick reconnect',
      '📊 Account Limit Validation',
      'Validates expected account limits on connection',
      'Logs equity, cash, and buying power on connect',
      'Clarified Alpaca paper: $100k equity / $200k buying power (2x margin)',
      '🔄 Auto-Reconnection System',
      'Background health monitoring for all connected brokers',
      'Automatic reconnection with exponential backoff',
      'Handles TWS daily restarts gracefully',
      'Connection event history for auditing'
    ]
  },
  {
    version: '1.1.7',
    date: 'January 2, 2026',
    changes: [
      '🤖 Bot Trading Implementation Complete',
      'Implemented real signal generation using technical analysis',
      'RSI, MACD, Moving Average, Bollinger Bands indicators',
      'Multi-indicator confluence scoring for trade decisions',
      'Paper AND Live trading now execute real orders',
      '🔍 Comprehensive Bot Debug System',
      '/api/bots/debug - Full diagnostics for all bots',
      '/api/bots/activity - Activity log with filtering',
      '/api/bots/{id}/debug - Single bot diagnostics',
      '/api/bots/{id}/activity - Per-bot activity log',
      'Real-time logging of cycles, signals, orders, errors',
      'Issue detection: missing broker, no signals, order rejections',
      '📊 Enhanced Bot Statistics',
      'Cycles completed, signals generated, orders submitted/filled/rejected',
      'Last cycle time, last trade time tracking',
      'Symbols analyzed per cycle metrics'
    ]
  },
  {
    version: '1.1.6',
    date: 'December 24, 2025',
    changes: [
      '🔧 Dashboard & Equity Chart Fixes',
      'Portfolio Value now uses broker context as fallback',
      'Equity Chart generates data from broker when API fails',
      'Connect endpoint returns account data (portfolio_value)',
      'Added /api/integrations/broker/status endpoint',
      'Dashboard refreshes correctly on broker connection'
    ]
  },
  {
    version: '1.1.5',
    date: 'December 24, 2025',
    changes: [
      '🔧 IBKR Paper Trading Fixes',
      'Improved IBKR account data fetching from TWS',
      'Fallback to accountValues when accountSummary unavailable',
      'Fixed parsing of NetLiquidation, CashBalance, BuyingPower',
      'Added /api/positions/debug endpoint for diagnostics',
      'Enhanced logging for portfolio summary fetching'
    ]
  },
  {
    version: '1.1.4',
    date: 'December 22, 2025',
    changes: [
      '🔌 Broker Integration Improvements',
      'Fixed IBKR Docker networking with host.docker.internal',
      'Resolved async event loop issues with ib_insync library',
      'Schwab: API key auth with Client ID, Secret, Refresh Token',
      'Tradier: API token auth with Access Token and Account ID',
      'Improved connection error messages with actionable guidance',
      '🤖 AI Provider Integration Fixes',
      'Ollama Docker support: auto-detects environment for correct host',
      'Test Connection now tests entered API key, not saved one',
      'OpenAI/Claude buttons enable properly after saving config',
      'Default AI provider changed to Claude with Ollama fallback',
      '⚖️ Trading Compliance System',
      'Pattern Day Trader (PDT) rule monitoring',
      'Good Faith Violation detection for cash accounts',
      'Freeriding protection prevents buying with unsettled funds',
      '📚 Glossary: Regulations Category',
      '18+ new compliance terms: PDT, FINRA, Good Faith, Freeriding'
    ]
  },
  {
    version: '1.1.0',
    date: 'December 21, 2025',
    changes: [
      '⚙️ Settings Page & UI Restructuring',
      'Setup button in header opens dedicated Settings page',
      'Strategy Controls, Risk Management, Admin Panel moved to Settings',
      'Dashboard panels now full width for better space utilization',
      'Two-column responsive grid layout on larger screens',
      '🎤 Voice & Audio Features',
      'Audio readout for news headlines, AI responses, glossary terms',
      'Voice input for AI Assistant and glossary search',
      'Web Speech API integration for TTS and STT',
      '🔍 AI Forecasting - Name Search',
      'Search by company name (Apple, Microsoft) not just symbols',
      'Autocomplete dropdown with symbol, name, exchange info',
      '📰 Live News Auto-Update',
      'Enable automatic news refresh (15s to 5m intervals)',
      'LIVE indicator when auto-update is active',
      '📊 AI Pattern Prediction Charts',
      'Mini SVG charts for each pattern prediction',
      'Bullish/bearish color-coded visualizations',
      '📚 Glossary Encyclopedia Images',
      'Visual diagrams for RSI, MACD, Fibonacci, patterns',
      'Image support for key trading concepts'
    ]
  },
  {
    version: '1.0.8',
    date: 'December 19, 2025',
    changes: [
      '🔧 Strategy Controls Sync Fix',
      'Trading strategies in Create Bot now sync with Strategy Controls',
      'Strategy status re-fetches when Create Bot form opens',
      'StrategyPanel toggles update backend feature flags in real-time',
      'Fixed Yahoo Finance API boolean parameter error',
      '📚 Expanded Trading Glossary - 528 Terms',
      'Increased from 290 to 528 comprehensive trading terms',
      'Added 50+ financial acronyms: M&A, ATRWAC, FOMC, GDP, CPI, NFP',
      'Seasonal events: Summer Doldrums, Sell in May, October Effect',
      'Order types: Stop Limit, OCO, Bracket, GTC, IOC, FOK, MOC',
      'Bot config: Max Positions, Max Position Size, Daily Loss Limit',
      'Risk metrics: Tail Risk, Black Swan, Concentration Risk',
      'Whale tracking: Whale Alerts, Accumulation/Distribution'
    ]
  },
  {
    version: '1.0.7',
    date: 'December 19, 2025',
    changes: [
      '🔮 AI Market Forecasting Fully Operational',
      'Fixed API route ordering bug for /hypothesis/active and /catalysts/imminent',
      'All 4 tabs now populate: Trending, Catalysts, AI Hypotheses, Viral',
      '⚡ Auto-Fetch on Startup',
      'Forecasting data now auto-populates when server starts',
      'No manual Force Fetch required for initial data',
      '30 popular symbols fetched automatically (NVDA, AAPL, TSLA, etc.)',
      '📊 Enhanced Data Generation',
      'Lowered thresholds for more comprehensive coverage',
      'Synthetic catalysts generated when no earnings data available',
      '8+ AI hypotheses generated per fetch cycle',
      '15+ viral/buzz signals for market movers',
      '🛠️ Technical Improvements',
      'Static routes prioritized over dynamic routes in FastAPI',
      'Background task logging improvements',
      'Cache synchronization fixes for forecasting data'
    ]
  },
  {
    version: '1.0.6',
    date: 'December 19, 2025',
    changes: [
      '📊 AI Pattern Predictions in Market Forecasting',
      'Trend Continuation/Reversal detection with confidence scores',
      'Volatility Squeeze Breakout patterns',
      'Mean Reversion (Overbought/Oversold) signals',
      'Support/Resistance level testing alerts',
      'Analyst Divergence detection',
      'Momentum Divergence patterns',
      '📈 Visual Diagrams in Glossary',
      'SVG charts for RSI, MACD, Bollinger Bands',
      'Pattern diagrams: Head & Shoulders, Double Top/Bottom',
      'Risk diagrams: Stop Loss, Risk/Reward, Drawdown',
      'Fibonacci Retracement level visualization',
      'Support/Resistance and Trend line diagrams',
      '🔢 Score Breakdown with Formulas',
      'Full calculation formulas for each score component',
      'Live weighted score calculation display',
      'Contribution breakdown for speculation score',
      '📰 Fixed News Sources in Forecasting',
      'Updated yfinance API parsing for news articles',
      'Proper source attribution (Yahoo Finance, etc.)',
      '⛔ Strategy Disable Enforcement',
      'Disabled strategies now unselectable in Create Bot',
      'Visual indicators for disabled strategies',
      'Public API for strategy status checking',
      '🔢 Bot Numbering in Bot Manager',
      'Sequential numbers displayed for all 40 bots',
      '🔗 Clickable External References',
      'Influencer names link to social profiles',
      'News articles link to sources',
      'Whale alerts link to blockchain explorers',
      'Earnings/signals link to data sources'
    ]
  },
  {
    version: '1.0.5',
    date: 'December 19, 2025',
    changes: [
      '💱 Forex Trading Bots - 3 new currency trading bots',
      'Major Forex Pairs: EUR/USD, GBP/USD, USD/JPY, USD/CHF',
      'Asia-Pacific FX: AUD/USD, NZD/USD, USD/SGD, USD/HKD',
      'Euro Crosses: EUR/GBP, EUR/JPY, EUR/CHF, EUR/AUD',
      '🤖 Now 40+ Trading Bots across all asset classes',
      'Added FOREX instrument type support',
      '📚 Comprehensive Trading Glossary - 500+ terms',
      'Full-width glossary search with instant filtering',
      'Categorized terms: Basics, Technical, Strategies, Risk, Patterns, Regulations',
      'Expandable definitions with detailed explanations',
      '🔧 Dynamic version display from package.json',
      'Release date auto-pulled from changelog',
      'Bug fixes and stability improvements'
    ]
  },
  {
    version: '1.0.4',
    date: 'December 18, 2025',
    changes: [
      '📊 Stock Analyzer - Comprehensive Time Series Analysis',
      'Search any stock across all global exchanges',
      'Interactive candlestick chart with technical overlays',
      'Toggle SMA/EMA/RSI/Volume overlays independently',
      '🎯 Inflection Point Detection (peaks, troughs, crossovers)',
      'Golden Cross & Death Cross visual markers',
      '📈 Analyst Price Targets with projection lines',
      'Target Meeting Analysis with confidence levels',
      'Earnings history with surprise tracking',
      'Future EPS estimates visualization',
      'Fundamental metrics: P/E, PEG, profit margin, beta'
    ]
  },
  {
    version: '1.0.3',
    date: 'December 17, 2025',
    changes: [
      '🔮 AI-Powered Market Forecasting Engine',
      '📹 Video Platform Analysis (YouTube, TikTok, Instagram)',
      '🛡️ Bot Risk Management System (0-100 scoring)',
      'Track FinTok & YouTube finance influencers',
      'Viral content alerts across all platforms',
      'Risk-Adjusted Metrics: Sharpe, Sortino, VaR',
      'Social Sentiment (Twitter/X, Reddit, StockTwits)',
      'Speculation Scoring Algorithm',
      'Catalyst Tracker & AI Hypothesis Generator',
      '50+ Known Financial Influencer Database'
    ]
  },
  {
    version: '1.0.2',
    date: 'December 17, 2025',
    changes: [
      '🌍 Comprehensive Forex Trading',
      '60+ Currency Pairs with pip calculator',
      'Currency Strength Meter',
      'Economic Calendar',
      'MT5 & OANDA Integration'
    ]
  },
  {
    version: '1.0.1',
    date: 'December 17, 2025',
    changes: [
      '🎉 Quantvue-Inspired Features',
      'Volatility-Adaptive SL/TP with ATR-based dynamic stops',
      'TradingView Webhook Integration',
      'Market Regime Detection',
      'Martingale Position Sizing',
      'Strategy Templates Library (10+ strategies)',
      'NinjaTrader 8 Integration',
      'Visual Strategy Builder',
      'Social Trading Platform'
    ]
  },
  {
    version: '0.9.8',
    date: 'December 17, 2025',
    changes: [
      'Platform-specific fixes for Windows and Linux releases',
      'Exclude uvloop on Windows (Unix-only library)',
      'Enhanced zombie process cleanup with fallback commands',
      'Comprehensive debug logging for connection troubleshooting',
      'Fixed WebSocket connection loops (stable refs, no dependency loops)'
    ]
  },
  {
    version: '0.9.7',
    date: 'December 16, 2025',
    changes: [
      'Offline admin login - works even when backend is down',
      'Enhanced debug logging for "Failed to fetch bots" errors',
      'Fixed CSP to allow 127.0.0.1 connections in desktop app',
      'Improved API URL handling for Tauri desktop',
      'Added agentic tuning algorithm (ATRWAC) for bot optimization',
      'Zombie process cleanup scripts for macOS/Linux/Windows'
    ]
  },
  {
    version: '0.9.6',
    date: 'December 16, 2025',
    changes: [
      'Rebuilt x64 backend with all dependencies properly bundled',
      'Fixed Gatekeeper blocking on Intel Macs',
      'ChromeOS support via Linux .deb package',
      'Manual DMG creation fallback for reliable builds',
      'Version sync across all config files'
    ]
  },
  {
    version: '0.9.5',
    date: 'December 15, 2025',
    changes: [
      'Help popup with features, quick start, and changelog',
      'API-based LLM support (OpenAI, Anthropic, Ollama)',
      'Replaced pandas-ta with ta library for NumPy compatibility',
      'Cross-platform desktop builds (macOS ARM64/Intel, Windows, Linux)',
      'Added hypothesis testing framework'
    ]
  },
  {
    version: '0.9.4',
    date: 'December 13, 2025',
    changes: [
      'Fixed sidecar binary bundling for desktop app',
      'Backend auto-launch improvements'
    ]
  },
  {
    version: '0.9.3',
    date: 'December 13, 2025',
    changes: [
      'Auto-Tune UI for automatic strategy optimization',
      'Seasonal Events UI in Strategy Controls',
      'Enhanced bot details with Win Rate, Uptime, Error tracking'
    ]
  },
  {
    version: '0.9.0',
    date: 'December 12, 2025',
    changes: [
      'Desktop application with Tauri',
      'Multiple broker authentication methods',
      '37 pre-configured trading bots',
      'Global stock exchange support (40+ exchanges)'
    ]
  }
];

// ============================================================================
// GLOSSARY DATA - Trading Terminology Encyclopedia
// ============================================================================

interface GlossaryTerm {
  term: string;
  category: 'basics' | 'indicators' | 'strategies' | 'risk' | 'fundamentals' | 'patterns' | 'regulations';
  shortDef: string;
  fullExplanation: string;
  whyUseful: string;
  whyNotUseful?: string;
  formula?: string;
  example?: string;
  xfactorUsage?: string;
  relatedTerms?: string[];
  visualType?: 'chart' | 'diagram' | 'formula' | 'table';
  // Image support for encyclopedia-style visuals
  imageUrl?: string; // External image URL (from Investopedia, Wikipedia, etc.)
  imageCaption?: string; // Caption for the image
  imageCredit?: string; // Attribution for the image
  diagram?: 'rsi' | 'macd' | 'sma' | 'ema' | 'bollinger' | 'volume' | 'candlestick' | 
            'support-resistance' | 'trend' | 'double-top' | 'double-bottom' | 'head-shoulders' |
            'triangle' | 'wedge' | 'flag' | 'cup-handle' | 'fibonacci' | 'atr' | 'stochastic' |
            'obv' | 'vwap' | 'ichimoku' | 'pivot' | 'doji' | 'hammer' | 'engulfing' |
            'momentum' | 'mean-reversion' | 'breakout' | 'risk-reward' | 'position-size' |
            'stop-loss' | 'trailing-stop' | 'var' | 'sharpe' | 'drawdown';
}

// ============================================================================
// DIAGRAM COMPONENTS - SVG Mini Charts for Visual Learning
// ============================================================================

const DiagramRSI = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    {/* Background */}
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Overbought zone */}
    <rect fill="#ef444420" x="0" y="0" width="200" height="30" />
    <text x="5" y="15" fill="#ef4444" fontSize="8">Overbought (70+)</text>
    {/* Oversold zone */}
    <rect fill="#22c55e20" x="0" y="70" width="200" height="30" />
    <text x="5" y="95" fill="#22c55e" fontSize="8">Oversold (30-)</text>
    {/* RSI Line */}
    <path d="M10,50 Q30,20 50,35 T90,25 T130,60 T170,80 T190,45" fill="none" stroke="#8b5cf6" strokeWidth="2" />
    {/* 50 line */}
    <line x1="0" y1="50" x2="200" y2="50" stroke="#475569" strokeWidth="1" strokeDasharray="4" />
    <text x="180" y="48" fill="#475569" fontSize="7">50</text>
  </svg>
);

const DiagramMACD = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Zero line */}
    <line x1="0" y1="50" x2="200" y2="50" stroke="#475569" strokeWidth="1" />
    {/* MACD Line (blue) */}
    <path d="M10,60 Q30,70 50,55 T90,35 T130,45 T170,30 T190,40" fill="none" stroke="#3b82f6" strokeWidth="2" />
    {/* Signal Line (orange) */}
    <path d="M10,55 Q30,65 50,60 T90,40 T130,50 T170,35 T190,45" fill="none" stroke="#f97316" strokeWidth="2" />
    {/* Histogram */}
    <rect x="20" y="50" width="8" height="15" fill="#ef4444" opacity="0.7" />
    <rect x="35" y="50" width="8" height="10" fill="#ef4444" opacity="0.7" />
    <rect x="50" y="45" width="8" height="5" fill="#ef4444" opacity="0.7" />
    <rect x="65" y="40" width="8" height="10" fill="#22c55e" opacity="0.7" transform="rotate(180 69 45)" />
    <rect x="80" y="35" width="8" height="15" fill="#22c55e" opacity="0.7" transform="rotate(180 84 42.5)" />
    <text x="5" y="12" fill="#3b82f6" fontSize="7">MACD</text>
    <text x="35" y="12" fill="#f97316" fontSize="7">Signal</text>
  </svg>
);

const DiagramSMA = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Price candles (simplified) */}
    <path d="M10,70 L25,55 L40,60 L55,45 L70,50 L85,35 L100,40 L115,30 L130,35 L145,25 L160,30 L175,20 L190,25" fill="none" stroke="#94a3b8" strokeWidth="1" />
    {/* SMA 20 (smooth) */}
    <path d="M30,65 Q60,55 90,45 T150,30 T190,28" fill="none" stroke="#22c55e" strokeWidth="2" />
    {/* SMA 50 (smoother) */}
    <path d="M50,70 Q90,60 130,50 T190,40" fill="none" stroke="#eab308" strokeWidth="2" />
    <text x="5" y="12" fill="#94a3b8" fontSize="7">Price</text>
    <text x="35" y="12" fill="#22c55e" fontSize="7">SMA 20</text>
    <text x="75" y="12" fill="#eab308" fontSize="7">SMA 50</text>
  </svg>
);

const DiagramBollinger = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Upper band */}
    <path d="M10,25 Q50,15 90,20 T170,25 T190,20" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="3" />
    {/* Middle band (SMA) */}
    <path d="M10,50 Q50,45 90,50 T170,48 T190,50" fill="none" stroke="#eab308" strokeWidth="2" />
    {/* Lower band */}
    <path d="M10,75 Q50,85 90,80 T170,75 T190,80" fill="none" stroke="#22c55e" strokeWidth="1.5" strokeDasharray="3" />
    {/* Price */}
    <path d="M10,55 Q30,35 50,60 T90,40 T130,70 T170,45 T190,55" fill="none" stroke="#8b5cf6" strokeWidth="2" />
    {/* Fill between bands */}
    <path d="M10,25 Q50,15 90,20 T170,25 T190,20 L190,80 Q170,75 130,75 T50,85 T10,75 Z" fill="#3b82f620" />
    <text x="5" y="12" fill="#ef4444" fontSize="7">Upper Band (+2σ)</text>
    <text x="130" y="12" fill="#22c55e" fontSize="7">Lower Band (-2σ)</text>
  </svg>
);

const DiagramCandlestick = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Green candle */}
    <line x1="30" y1="20" x2="30" y2="80" stroke="#22c55e" strokeWidth="1" />
    <rect x="22" y="35" width="16" height="30" fill="#22c55e" />
    <text x="20" y="95" fill="#22c55e" fontSize="7">Bullish</text>
    {/* Red candle */}
    <line x1="80" y1="20" x2="80" y2="80" stroke="#ef4444" strokeWidth="1" />
    <rect x="72" y="35" width="16" height="30" fill="#ef4444" />
    <text x="70" y="95" fill="#ef4444" fontSize="7">Bearish</text>
    {/* Doji */}
    <line x1="130" y1="25" x2="130" y2="75" stroke="#eab308" strokeWidth="1" />
    <rect x="122" y="48" width="16" height="4" fill="#eab308" />
    <text x="122" y="95" fill="#eab308" fontSize="7">Doji</text>
    {/* Hammer */}
    <line x1="175" y1="30" x2="175" y2="80" stroke="#3b82f6" strokeWidth="1" />
    <rect x="167" y="30" width="16" height="10" fill="#3b82f6" />
    <text x="163" y="95" fill="#3b82f6" fontSize="7">Hammer</text>
  </svg>
);

const DiagramSupportResistance = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Resistance line */}
    <line x1="0" y1="25" x2="200" y2="25" stroke="#ef4444" strokeWidth="2" strokeDasharray="5" />
    <text x="5" y="20" fill="#ef4444" fontSize="8">Resistance</text>
    {/* Support line */}
    <line x1="0" y1="75" x2="200" y2="75" stroke="#22c55e" strokeWidth="2" strokeDasharray="5" />
    <text x="5" y="90" fill="#22c55e" fontSize="8">Support</text>
    {/* Price bouncing */}
    <path d="M10,50 Q30,75 50,70 T90,25 T130,30 T150,75 T180,70 T195,30" fill="none" stroke="#8b5cf6" strokeWidth="2" />
    {/* Bounce arrows */}
    <polygon points="50,75 45,68 55,68" fill="#22c55e" />
    <polygon points="90,25 85,32 95,32" fill="#ef4444" />
  </svg>
);

const DiagramTrend = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Uptrend */}
    <path d="M10,80 L65,40" stroke="#22c55e" strokeWidth="2" />
    <path d="M10,85 Q20,70 35,75 T55,50 T65,45" fill="none" stroke="#94a3b8" strokeWidth="1" />
    <text x="20" y="95" fill="#22c55e" fontSize="7">Uptrend</text>
    {/* Downtrend */}
    <path d="M135,30 L190,70" stroke="#ef4444" strokeWidth="2" />
    <path d="M135,25 Q145,35 155,30 T175,55 T190,65" fill="none" stroke="#94a3b8" strokeWidth="1" />
    <text x="145" y="95" fill="#ef4444" fontSize="7">Downtrend</text>
    {/* Higher highs/lows markers */}
    <circle cx="25" cy="70" r="3" fill="#22c55e" />
    <circle cx="45" cy="55" r="3" fill="#22c55e" />
    <text x="70" y="50" fill="#475569" fontSize="6">Higher Highs</text>
  </svg>
);

const DiagramDoubleTop = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Pattern */}
    <path d="M10,80 Q30,80 50,30 T90,70 T130,30 T170,80 T190,85" fill="none" stroke="#ef4444" strokeWidth="2" />
    {/* Neckline */}
    <line x1="70" y1="70" x2="150" y2="70" stroke="#eab308" strokeWidth="1.5" strokeDasharray="4" />
    {/* Peak markers */}
    <circle cx="50" cy="30" r="4" fill="none" stroke="#ef4444" strokeWidth="2" />
    <circle cx="130" cy="30" r="4" fill="none" stroke="#ef4444" strokeWidth="2" />
    <text x="40" y="20" fill="#ef4444" fontSize="7">Top 1</text>
    <text x="120" y="20" fill="#ef4444" fontSize="7">Top 2</text>
    <text x="85" y="85" fill="#eab308" fontSize="7">Neckline</text>
  </svg>
);

const DiagramDoubleBottom = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Pattern - W shape */}
    <path d="M10,20 Q30,20 50,70 T90,30 T130,70 T170,20 T190,15" fill="none" stroke="#22c55e" strokeWidth="2" />
    {/* Neckline */}
    <line x1="70" y1="30" x2="150" y2="30" stroke="#eab308" strokeWidth="1.5" strokeDasharray="4" />
    {/* Bottom markers */}
    <circle cx="50" cy="70" r="4" fill="none" stroke="#22c55e" strokeWidth="2" />
    <circle cx="130" cy="70" r="4" fill="none" stroke="#22c55e" strokeWidth="2" />
    <text x="35" y="85" fill="#22c55e" fontSize="7">Bottom 1</text>
    <text x="115" y="85" fill="#22c55e" fontSize="7">Bottom 2</text>
    <text x="85" y="20" fill="#eab308" fontSize="7">Neckline</text>
  </svg>
);

const DiagramHeadShoulders = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Pattern */}
    <path d="M10,70 Q25,70 40,45 T60,65 T100,20 T140,65 T160,45 T190,70" fill="none" stroke="#ef4444" strokeWidth="2" />
    {/* Neckline */}
    <line x1="50" y1="65" x2="150" y2="65" stroke="#eab308" strokeWidth="1.5" strokeDasharray="4" />
    {/* Labels */}
    <text x="30" y="40" fill="#94a3b8" fontSize="6">L.Shoulder</text>
    <text x="85" y="15" fill="#ef4444" fontSize="7">Head</text>
    <text x="145" y="40" fill="#94a3b8" fontSize="6">R.Shoulder</text>
  </svg>
);

const DiagramFibonacci = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Fib levels */}
    <line x1="0" y1="10" x2="200" y2="10" stroke="#22c55e" strokeWidth="1" />
    <text x="5" y="17" fill="#22c55e" fontSize="6">0% (High)</text>
    <line x1="0" y1="33" x2="200" y2="33" stroke="#3b82f6" strokeWidth="1" />
    <text x="5" y="40" fill="#3b82f6" fontSize="6">23.6%</text>
    <line x1="0" y1="48" x2="200" y2="48" stroke="#8b5cf6" strokeWidth="1" />
    <text x="5" y="55" fill="#8b5cf6" fontSize="6">38.2%</text>
    <line x1="0" y1="55" x2="200" y2="55" stroke="#eab308" strokeWidth="1.5" />
    <text x="5" y="62" fill="#eab308" fontSize="6">50%</text>
    <line x1="0" y1="72" x2="200" y2="72" stroke="#f97316" strokeWidth="1" />
    <text x="5" y="79" fill="#f97316" fontSize="6">61.8%</text>
    <line x1="0" y1="90" x2="200" y2="90" stroke="#ef4444" strokeWidth="1" />
    <text x="5" y="97" fill="#ef4444" fontSize="6">100% (Low)</text>
    {/* Price retracement */}
    <path d="M30,90 Q60,30 80,10 T120,55 T160,30 T190,20" fill="none" stroke="#94a3b8" strokeWidth="2" />
  </svg>
);

const DiagramRiskReward = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Entry line */}
    <line x1="0" y1="50" x2="200" y2="50" stroke="#3b82f6" strokeWidth="2" />
    <text x="5" y="47" fill="#3b82f6" fontSize="7">Entry $100</text>
    {/* Stop loss */}
    <rect x="0" y="50" width="200" height="25" fill="#ef444420" />
    <line x1="0" y1="75" x2="200" y2="75" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="4" />
    <text x="5" y="85" fill="#ef4444" fontSize="7">Stop Loss $95 (-$5 Risk)</text>
    {/* Take profit */}
    <rect x="0" y="20" width="200" height="30" fill="#22c55e20" />
    <line x1="0" y1="20" x2="200" y2="20" stroke="#22c55e" strokeWidth="1.5" strokeDasharray="4" />
    <text x="5" y="17" fill="#22c55e" fontSize="7">Target $115 (+$15 Reward)</text>
    {/* Ratio */}
    <text x="140" y="60" fill="#eab308" fontSize="9" fontWeight="bold">R:R = 1:3</text>
  </svg>
);

const DiagramStopLoss = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Price going down */}
    <path d="M10,30 Q40,25 60,35 T100,45 T140,70 T190,85" fill="none" stroke="#94a3b8" strokeWidth="2" />
    {/* Entry point */}
    <circle cx="60" cy="35" r="4" fill="#3b82f6" />
    <text x="45" y="28" fill="#3b82f6" fontSize="7">Entry</text>
    {/* Stop loss trigger */}
    <line x1="0" y1="55" x2="200" y2="55" stroke="#ef4444" strokeWidth="2" strokeDasharray="5" />
    <text x="5" y="52" fill="#ef4444" fontSize="7">Stop Loss Level</text>
    {/* X where stopped */}
    <circle cx="110" cy="55" r="5" fill="none" stroke="#ef4444" strokeWidth="2" />
    <text x="115" y="48" fill="#ef4444" fontSize="6">Triggered!</text>
  </svg>
);

const DiagramDrawdown = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Equity curve */}
    <path d="M10,60 Q30,40 50,35 T90,20 T110,45 T130,70 T150,50 T170,35 T190,30" fill="none" stroke="#3b82f6" strokeWidth="2" />
    {/* Peak line */}
    <line x1="90" y1="20" x2="150" y2="20" stroke="#22c55e" strokeWidth="1" strokeDasharray="3" />
    <text x="95" y="17" fill="#22c55e" fontSize="6">Peak</text>
    {/* Trough */}
    <line x1="90" y1="70" x2="150" y2="70" stroke="#ef4444" strokeWidth="1" strokeDasharray="3" />
    <text x="95" y="80" fill="#ef4444" fontSize="6">Trough</text>
    {/* Drawdown arrow */}
    <line x1="120" y1="20" x2="120" y2="70" stroke="#ef4444" strokeWidth="2" />
    <polygon points="120,70 115,60 125,60" fill="#ef4444" />
    <text x="125" y="50" fill="#ef4444" fontSize="8">-25%</text>
  </svg>
);

const DiagramVolume = () => (
  <svg viewBox="0 0 200 100" className="w-full h-24">
    <rect fill="#1e293b" width="200" height="100" rx="4" />
    {/* Price line */}
    <path d="M10,50 Q30,45 50,40 T90,35 T130,30 T170,25 T190,20" fill="none" stroke="#94a3b8" strokeWidth="1.5" />
    {/* Volume bars */}
    <rect x="15" y="75" width="12" height="15" fill="#22c55e" opacity="0.7" />
    <rect x="35" y="70" width="12" height="20" fill="#22c55e" opacity="0.7" />
    <rect x="55" y="65" width="12" height="25" fill="#22c55e" opacity="0.7" />
    <rect x="75" y="55" width="12" height="35" fill="#22c55e" opacity="0.8" />
    <rect x="95" y="45" width="12" height="45" fill="#22c55e" opacity="0.9" />
    <rect x="115" y="50" width="12" height="40" fill="#22c55e" opacity="0.8" />
    <rect x="135" y="60" width="12" height="30" fill="#ef4444" opacity="0.7" />
    <rect x="155" y="65" width="12" height="25" fill="#ef4444" opacity="0.7" />
    <rect x="175" y="70" width="12" height="20" fill="#ef4444" opacity="0.7" />
    <text x="5" y="12" fill="#94a3b8" fontSize="7">Price ↑</text>
    <text x="70" y="98" fill="#22c55e" fontSize="7">High Volume = Confirmation</text>
  </svg>
);

// Diagram selector component
const GlossaryDiagram = ({ type }: { type: string }) => {
  const diagrams: Record<string, JSX.Element> = {
    'rsi': <DiagramRSI />,
    'macd': <DiagramMACD />,
    'sma': <DiagramSMA />,
    'ema': <DiagramSMA />,
    'bollinger': <DiagramBollinger />,
    'candlestick': <DiagramCandlestick />,
    'support-resistance': <DiagramSupportResistance />,
    'trend': <DiagramTrend />,
    'double-top': <DiagramDoubleTop />,
    'double-bottom': <DiagramDoubleBottom />,
    'head-shoulders': <DiagramHeadShoulders />,
    'fibonacci': <DiagramFibonacci />,
    'risk-reward': <DiagramRiskReward />,
    'stop-loss': <DiagramStopLoss />,
    'trailing-stop': <DiagramStopLoss />,
    'drawdown': <DiagramDrawdown />,
    'volume': <DiagramVolume />,
    'obv': <DiagramVolume />,
    'vwap': <DiagramVolume />,
  };

  const diagram = diagrams[type];
  if (!diagram) return null;

  return (
    <div className="mt-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
      <h4 className="text-xs font-medium text-cyan-400 uppercase mb-2 flex items-center gap-1">
        <BarChart3 className="w-3 h-3" /> Visual Representation
      </h4>
      {diagram}
    </div>
  );
};

const glossaryTerms: GlossaryTerm[] = [
  // ===== BASICS =====
  {
    term: 'Bullish',
    category: 'basics',
    shortDef: 'Expecting prices to rise',
    fullExplanation: 'A bullish outlook means expecting the price of a security to increase. The term comes from how a bull attacks—thrusting its horns upward. When someone is "bullish" on a stock, they believe it will go up in value.',
    whyUseful: 'Understanding market sentiment helps you align your trades with the overall direction. Trading with the trend (bullish in an uptrend) typically has higher success rates than fighting it.',
    example: 'If NVDA is trading at $130 and you believe it will reach $150, you are bullish on NVDA. You might buy shares or call options.',
    xfactorUsage: 'XFactor displays bullish/bearish sentiment in the Market Forecasting panel based on social media analysis and technical indicators.',
    relatedTerms: ['Bearish', 'Trend', 'Long Position'],
  },
  {
    term: 'Bearish',
    category: 'basics',
    shortDef: 'Expecting prices to fall',
    fullExplanation: 'A bearish outlook means expecting the price to decrease. The term comes from how a bear attacks—swiping its paws downward. Bearish traders profit from falling prices through short selling or put options.',
    whyUseful: 'Recognizing bearish conditions helps you avoid buying at tops and potentially profit from downtrends. Bear markets present opportunities for short sellers.',
    whyNotUseful: 'Being overly bearish in a strong bull market can cause you to miss significant gains. Markets have historically trended upward over long periods.',
    example: 'If you think a company will miss earnings and drop from $100 to $80, you are bearish and might buy put options or short the stock.',
    relatedTerms: ['Bullish', 'Short Position', 'Put Option'],
  },
  {
    term: 'P&L (Profit & Loss)',
    category: 'basics',
    shortDef: 'The net gain or loss from trades',
    fullExplanation: 'P&L represents the total profit or loss from your trading activities. It can be calculated as "realized" (closed trades) or "unrealized" (open positions). Understanding P&L is fundamental to evaluating trading performance.',
    whyUseful: 'Tracking P&L helps you understand your actual trading performance, identify which strategies work, and make informed decisions about position sizing.',
    formula: 'P&L = (Exit Price - Entry Price) × Quantity × (1 if Long, -1 if Short) - Fees',
    example: 'Buy 100 shares at $50, sell at $55. P&L = ($55 - $50) × 100 = $500 profit (before fees)',
    xfactorUsage: 'XFactor tracks P&L for each bot in real-time, displaying daily, weekly, and all-time P&L in the dashboard.',
    relatedTerms: ['ROI', 'Win Rate', 'Drawdown'],
  },
  {
    term: 'Long Position',
    category: 'basics',
    shortDef: 'Buying an asset expecting it to rise',
    fullExplanation: 'Going "long" means buying a security with the expectation that its price will increase. You profit when the price goes up and lose when it goes down. This is the most common type of trade.',
    whyUseful: 'Long positions are straightforward and align with the natural upward bias of equity markets over time. No borrowing costs or short-selling restrictions.',
    example: 'You buy 50 shares of AAPL at $180. If the price rises to $200, your profit is $1,000. If it falls to $160, your loss is $1,000.',
    relatedTerms: ['Short Position', 'Bullish', 'Buy and Hold'],
  },
  {
    term: 'Short Position',
    category: 'basics',
    shortDef: 'Selling borrowed shares expecting price to fall',
    fullExplanation: 'Short selling involves borrowing shares from your broker and selling them immediately, hoping to buy them back later at a lower price. You profit from price declines but have unlimited loss potential if prices rise.',
    whyUseful: 'Shorting allows you to profit in bearish markets and hedge long positions. It provides opportunities regardless of market direction.',
    whyNotUseful: 'Short positions have unlimited loss potential (price can rise infinitely), borrowing costs, and short squeezes can cause rapid losses.',
    example: 'You borrow and sell 100 shares at $50. If the price drops to $40, you buy back (cover) for $4,000, keeping the $1,000 difference. If it rises to $70, you lose $2,000.',
    relatedTerms: ['Long Position', 'Short Squeeze', 'Margin'],
  },
  {
    term: 'Spread',
    category: 'basics',
    shortDef: 'The difference between bid and ask prices',
    fullExplanation: 'The spread is the difference between the highest price a buyer is willing to pay (bid) and the lowest price a seller is willing to accept (ask). Tighter spreads indicate more liquidity.',
    whyUseful: 'Understanding spreads helps you calculate true trading costs. In highly liquid markets, spreads are minimal; in illiquid markets, they can significantly impact profits.',
    formula: 'Spread = Ask Price - Bid Price',
    example: 'If AAPL bid is $179.95 and ask is $180.00, the spread is $0.05. Buying 1000 shares costs you $50 just in spread.',
    relatedTerms: ['Bid', 'Ask', 'Liquidity', 'Slippage'],
  },
  {
    term: 'Volume',
    category: 'basics',
    shortDef: 'Number of shares traded in a period',
    fullExplanation: 'Volume represents the total number of shares or contracts traded during a specific time period. High volume confirms price movements, while low volume may indicate weak trends.',
    whyUseful: 'Volume confirms trend strength—rising prices on high volume suggest strong buying interest. Breakouts on high volume are more reliable than those on low volume.',
    whyNotUseful: 'Volume alone doesn\'t indicate direction. High volume can occur during both advances and declines.',
    example: 'A stock breaks above resistance with 3x normal volume—this is a strong bullish signal. The same breakout on 0.5x volume might be a false breakout.',
    xfactorUsage: 'XFactor displays volume overlays on charts and uses volume analysis in breakout detection strategies.',
    relatedTerms: ['OBV', 'Volume Profile', 'Liquidity'],
    diagram: 'volume',
  },
  {
    term: 'Volatility',
    category: 'basics',
    shortDef: 'The degree of price variation over time',
    fullExplanation: 'Volatility measures how much a price fluctuates. High volatility means larger price swings (more risk and opportunity); low volatility means smaller, steadier movements. Implied volatility reflects expected future volatility.',
    whyUseful: 'Volatility helps determine position sizing, stop-loss distances, and option pricing. Adaptive strategies adjust to volatility conditions.',
    formula: 'Historical Volatility = Standard Deviation of Returns × √252 (annualized)',
    example: 'A stock with 40% annual volatility might swing ±2.5% daily on average. A 20% volatility stock might only move ±1.25% daily.',
    xfactorUsage: 'XFactor uses ATR (Average True Range) for volatility-adaptive stop losses and position sizing. VIX-based circuit breakers pause trading in extreme volatility.',
    relatedTerms: ['ATR', 'VIX', 'Standard Deviation', 'Beta'],
  },

  // ===== TECHNICAL INDICATORS =====
  {
    term: 'SMA (Simple Moving Average)',
    category: 'indicators',
    shortDef: 'Average price over a specific period',
    fullExplanation: 'SMA calculates the arithmetic mean of prices over N periods. Common periods are 20 (short-term), 50 (medium-term), and 200 (long-term). It smooths out price noise to identify trend direction.',
    whyUseful: 'SMAs identify trend direction, provide dynamic support/resistance levels, and generate crossover signals. The 200 SMA is widely watched by institutions.',
    whyNotUseful: 'SMAs lag price action because they use historical data. They work poorly in choppy, sideways markets and can generate many false signals.',
    formula: 'SMA = (P₁ + P₂ + ... + Pₙ) / n',
    example: '20 SMA: Add the last 20 closing prices, divide by 20. If prices are above the SMA, the short-term trend is up.',
    xfactorUsage: 'XFactor offers SMA 20, 50, and 200 as chart overlays. The trend_ma_crossover strategy uses SMA crossovers for entry signals.',
    relatedTerms: ['EMA', 'Golden Cross', 'Death Cross', 'Moving Average'],
    visualType: 'chart',
    diagram: 'sma',
  },
  {
    term: 'EMA (Exponential Moving Average)',
    category: 'indicators',
    shortDef: 'Weighted moving average favoring recent prices',
    fullExplanation: 'EMA gives more weight to recent prices, making it more responsive to new information than SMA. The weighting decreases exponentially. Common periods are 12 and 26 for MACD, or 9 for short-term trading.',
    whyUseful: 'EMAs react faster to price changes, catching trend reversals earlier. They\'re preferred by short-term traders who need quicker signals.',
    whyNotUseful: 'The increased sensitivity means more false signals in choppy markets. May whipsaw more than SMA during consolidation.',
    formula: 'EMA = (Price × k) + (Previous EMA × (1-k)), where k = 2/(n+1)',
    example: '12 EMA crossing above 26 EMA is a bullish signal (MACD crossover). Crossing below is bearish.',
    xfactorUsage: 'XFactor offers EMA 12 and EMA 26 overlays, used in trend_adx_macd and momentum strategies.',
    relatedTerms: ['SMA', 'MACD', 'Moving Average'],
    visualType: 'chart',
    diagram: 'ema',
  },
  {
    term: 'RSI (Relative Strength Index)',
    category: 'indicators',
    shortDef: 'Momentum oscillator measuring overbought/oversold conditions',
    fullExplanation: 'RSI measures the speed and magnitude of price changes on a 0-100 scale. Readings above 70 suggest overbought conditions (potential pullback), while below 30 suggests oversold (potential bounce). The standard period is 14.',
    whyUseful: 'RSI helps identify potential reversal points and confirm trend strength. Divergences between RSI and price often precede reversals.',
    whyNotUseful: 'In strong trends, RSI can remain overbought/oversold for extended periods. Using it alone for entries can result in fighting the trend.',
    formula: 'RSI = 100 - (100 / (1 + RS)), where RS = Avg Gain / Avg Loss over n periods',
    example: 'RSI drops to 25 while price makes a new low—this oversold condition might signal a buying opportunity. RSI divergence (price makes lower low, RSI makes higher low) is a bullish signal.',
    xfactorUsage: 'XFactor displays RSI as an overlay and uses it in reversion_rsi_bb and momentum_rsi_divergence strategies.',
    relatedTerms: ['Oversold', 'Overbought', 'Divergence', 'Momentum'],
    visualType: 'chart',
    diagram: 'rsi',
    imageUrl: 'https://www.investopedia.com/thmb/8SjpwVFxrDq5NlXlGxfBpJBjWHQ=/750x0/filters:no_upscale():max_bytes(150000):strip_icc():format(webp)/dotdash_Final_Relative_Strength_Index_RSI_Sep_2020-01-89c34f6a71db4d2a83f84d68f0f4a0d4.jpg',
    imageCaption: 'RSI oscillator showing overbought (above 70) and oversold (below 30) levels with price chart.',
    imageCredit: 'Investopedia',
  },
  {
    term: 'MACD (Moving Average Convergence Divergence)',
    category: 'indicators',
    shortDef: 'Trend-following momentum indicator',
    fullExplanation: 'MACD shows the relationship between two EMAs (typically 12 and 26). The MACD line is the difference between these EMAs. A 9-period EMA of MACD (signal line) triggers buy/sell signals when crossed.',
    imageUrl: 'https://www.investopedia.com/thmb/L0CpO_1DnF0J5H4UxqP5sJEWBao=/750x0/filters:no_upscale():max_bytes(150000):strip_icc():format(webp)/dotdash_Final_Moving_Average_Convergence_Divergence_MACD_Sep_2020-01-7a09cc6f2b0d4e7cb7c2a0f2b8b3e0a8.jpg',
    imageCaption: 'MACD indicator with signal line and histogram showing bullish and bearish crossovers.',
    imageCredit: 'Investopedia',
    whyUseful: 'MACD captures both trend direction and momentum. Crossovers, divergences, and histogram patterns provide multiple signal types.',
    whyNotUseful: 'As a lagging indicator, MACD often signals after moves have begun. It can produce many false signals in ranging markets.',
    formula: 'MACD Line = 12 EMA - 26 EMA; Signal Line = 9 EMA of MACD Line; Histogram = MACD - Signal',
    example: 'MACD crosses above signal line = bullish. Histogram expanding above zero = strengthening bullish momentum.',
    xfactorUsage: 'XFactor uses MACD in the trend_adx_macd strategy template for trend confirmation.',
    relatedTerms: ['EMA', 'Crossover', 'Divergence', 'Histogram'],
    visualType: 'chart',
    diagram: 'macd',
  },
  {
    term: 'Bollinger Bands',
    category: 'indicators',
    shortDef: 'Volatility bands around a moving average',
    fullExplanation: 'Bollinger Bands consist of a 20-period SMA (middle band) with upper and lower bands set at 2 standard deviations. Bands widen during high volatility and narrow during low volatility (squeeze).',
    whyUseful: 'Bands provide dynamic support/resistance and identify volatility conditions. Squeezes often precede large moves. Price touching bands can signal reversals.',
    whyNotUseful: 'In strong trends, price can "walk the band" staying at extremes. Using bands alone for mean reversion can be dangerous in trending markets.',
    formula: 'Upper Band = 20 SMA + (2 × StdDev); Lower Band = 20 SMA - (2 × StdDev)',
    example: 'Bollinger squeeze (bands narrowing) followed by expansion often signals a breakout. Price hitting lower band in uptrend might be a buy-the-dip opportunity.',
    xfactorUsage: 'XFactor uses Bollinger Bands in reversion_rsi_bb and breakout_squeeze strategies. The stdDev parameter controls band width.',
    relatedTerms: ['Standard Deviation', 'Squeeze', 'Volatility', 'Mean Reversion'],
    visualType: 'chart',
    imageUrl: 'https://www.investopedia.com/thmb/OJxnXxd2a4B3OMaT6p2_j0x5b_E=/750x0/filters:no_upscale():max_bytes(150000):strip_icc():format(webp)/dotdash_Final_Bollinger_Bands_Sep_2020-01-f3a2d8f2e7b94f35a1c0b9a8e5c8d8d8.jpg',
    imageCaption: 'Bollinger Bands showing volatility squeeze and expansion, with price touching upper and lower bands.',
    imageCredit: 'Investopedia',
    diagram: 'bollinger',
  },
  {
    term: 'ATR (Average True Range)',
    category: 'indicators',
    shortDef: 'Measures market volatility',
    fullExplanation: 'ATR calculates the average of "true ranges" over a period (typically 14). True range is the greatest of: current high minus low, absolute value of high minus previous close, or absolute value of low minus previous close.',
    whyUseful: 'ATR is essential for position sizing and setting stop-losses that adapt to current volatility. A 2 ATR stop gives your trade room to breathe.',
    whyNotUseful: 'ATR doesn\'t indicate direction—only volatility magnitude. It can\'t tell you if price will go up or down.',
    formula: 'True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|); ATR = 14-period average of TR',
    example: 'If ATR is $5, a 2 ATR stop-loss would be $10 from entry. This adapts automatically—in calm markets ATR shrinks, in volatile markets it expands.',
    xfactorUsage: 'XFactor uses ATR for volatility-adaptive stop losses. The ATR multiplier setting controls how many ATRs away stops are placed.',
    relatedTerms: ['Volatility', 'Stop Loss', 'Position Sizing'],
    visualType: 'formula',
  },
  {
    term: 'ADX (Average Directional Index)',
    category: 'indicators',
    shortDef: 'Measures trend strength (not direction)',
    fullExplanation: 'ADX measures how strong a trend is on a 0-100 scale, regardless of direction. Readings above 25 indicate a strong trend; below 20 indicates a weak or ranging market. It\'s derived from +DI and -DI directional indicators.',
    whyUseful: 'ADX helps you decide whether to use trend-following or mean-reversion strategies. High ADX = trend strategies; Low ADX = range strategies.',
    whyNotUseful: 'ADX doesn\'t indicate direction—you need +DI/-DI or price action for that. It also lags, so trends may be ending when ADX peaks.',
    formula: 'ADX = 14-period smoothed average of DX, where DX = |(+DI - -DI)| / (+DI + -DI) × 100',
    example: 'ADX at 35 with +DI > -DI = strong uptrend. ADX at 15 = ranging market, use range-bound strategies instead.',
    xfactorUsage: 'XFactor uses ADX in Market Regime Detection. ADX > 25 triggers trend-following mode; ADX < 20 triggers range mode.',
    relatedTerms: ['Trend', 'DMI', 'Market Regime'],
    visualType: 'chart',
  },
  {
    term: 'Fibonacci Retracement',
    category: 'indicators',
    shortDef: 'Key price levels based on Fibonacci ratios',
    fullExplanation: 'Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%, 78.6%) are horizontal lines indicating potential support/resistance based on the Fibonacci sequence. They\'re drawn from swing high to swing low (or vice versa).',
    whyUseful: 'Many traders watch Fibonacci levels, creating self-fulfilling prophecies. The 61.8% "golden ratio" level is particularly significant for pullback entries.',
    whyNotUseful: 'Fibonacci levels are subjective—different traders draw them differently. They don\'t always hold and work better in trending markets.',
    example: 'In an uptrend from $100 to $150, the 61.8% retracement is $119 (38.2% pullback). Buying near this level offers a potential bounce with defined risk.',
    xfactorUsage: 'XFactor displays Fibonacci levels in the Stock Analyzer chart for identifying key support/resistance zones.',
    relatedTerms: ['Support', 'Resistance', 'Retracement', 'Golden Ratio'],
    visualType: 'chart',
    diagram: 'fibonacci',
    imageUrl: 'https://www.investopedia.com/thmb/w5Vy7m2vXSJH0XzHU_9X5b_0vRs=/750x0/filters:no_upscale():max_bytes(150000):strip_icc():format(webp)/dotdash_Final_Fibonacci_Retracement_Levels_Sep_2020-01-5c8af5e4f0a54f52ba4b33a1a8b0b2fb.jpg',
    imageCaption: 'Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%, 78.6%) drawn from swing low to swing high, showing potential support levels during pullbacks.',
    imageCredit: 'Investopedia',
  },
  {
    term: 'VWAP (Volume Weighted Average Price)',
    category: 'indicators',
    shortDef: 'Average price weighted by volume',
    fullExplanation: 'VWAP calculates the average price weighted by volume for the day. Institutional traders use it as a benchmark—buying below VWAP is considered "good" execution. It resets each trading day.',
    whyUseful: 'VWAP provides dynamic intraday support/resistance. Price above VWAP is bullish; below is bearish. Institutions often target VWAP for large orders.',
    whyNotUseful: 'VWAP is primarily an intraday tool—less useful for swing or position traders. It loses meaning after the first hour of trading.',
    formula: 'VWAP = Σ(Price × Volume) / Σ(Volume)',
    example: 'A stock opens at $100, rises to $105 on high volume, then drifts. If VWAP is $103, buying near $103 might find support.',
    xfactorUsage: 'XFactor uses VWAP in the scalp_vwap_reversion strategy for intraday mean reversion trades.',
    relatedTerms: ['Volume', 'Intraday', 'Mean Reversion'],
    visualType: 'chart',
  },
  {
    term: 'Stochastic Oscillator',
    category: 'indicators',
    shortDef: 'Momentum indicator comparing close to price range',
    fullExplanation: 'Stochastic measures where the current close is relative to the high-low range over a period (typically 14). %K is the main line; %D is a 3-period SMA of %K. Readings above 80 are overbought; below 20 are oversold.',
    whyUseful: 'Stochastic is more sensitive than RSI, catching turns earlier. It works well in ranging markets for identifying reversal points.',
    whyNotUseful: 'In strong trends, Stochastic can remain overbought/oversold for extended periods, generating premature reversal signals.',
    formula: '%K = (Current Close - Lowest Low) / (Highest High - Lowest Low) × 100',
    example: 'Stochastic %K crosses above %D from below 20 = bullish reversal signal. Works best when confirmed by price action.',
    relatedTerms: ['RSI', 'Overbought', 'Oversold', 'Momentum'],
    visualType: 'chart',
  },

  // ===== STRATEGIES =====
  {
    term: 'Trend Following',
    category: 'strategies',
    shortDef: 'Trading in the direction of the prevailing trend',
    fullExplanation: 'Trend following strategies buy when prices are rising and sell when prices are falling. They use indicators like moving averages, ADX, or price action to identify and follow trends until they reverse.',
    whyUseful: 'Trends tend to persist longer than expected. "The trend is your friend" captures the idea that trading with momentum increases win probability.',
    whyNotUseful: 'Trend following suffers during ranging/choppy markets with frequent whipsaws. It also means buying after prices have already moved up.',
    example: 'Buy when price crosses above 50 SMA and RSI > 50. Hold until price closes below 50 SMA. This captures trending moves while avoiding chop.',
    xfactorUsage: 'XFactor offers trend_ma_crossover, trend_adx_macd, and trend_supertrend strategy templates.',
    relatedTerms: ['Moving Average', 'ADX', 'Breakout', 'Momentum'],
  },
  {
    term: 'Mean Reversion',
    category: 'strategies',
    shortDef: 'Trading based on price returning to average',
    fullExplanation: 'Mean reversion assumes prices oscillate around a central value (mean) and will eventually return to it. Traders buy when price is "too low" and sell when "too high" relative to this mean.',
    whyUseful: 'Works well in range-bound markets where prices oscillate between support and resistance. Many statistical arbitrage strategies are mean-reverting.',
    whyNotUseful: 'Can be disastrous in trending markets—"catching a falling knife." What seems oversold can become more oversold.',
    example: 'Buy when RSI < 30 and price touches lower Bollinger Band. Sell when RSI > 70 or price touches upper band.',
    xfactorUsage: 'XFactor offers reversion_rsi_bb and reversion_zscore strategy templates for mean reversion trading.',
    relatedTerms: ['RSI', 'Bollinger Bands', 'Oversold', 'Statistical Arbitrage'],
  },
  {
    term: 'Breakout Trading',
    category: 'strategies',
    shortDef: 'Entering when price breaks key levels',
    fullExplanation: 'Breakout trading involves entering positions when price moves beyond established support/resistance levels with conviction (usually confirmed by volume). The idea is that breaking a level often leads to continued momentum.',
    whyUseful: 'Breakouts can capture the beginning of new trends. When combined with volume confirmation, they offer defined entry points with clear invalidation levels.',
    whyNotUseful: 'Many breakouts fail (false breakouts), leading to losses. Breakouts often occur at extremes, making stop placement challenging.',
    example: 'Stock consolidates between $95-$100 for weeks. Buy when it closes above $100 on 2x average volume, with stop at $98.',
    xfactorUsage: 'XFactor offers breakout_donchian and breakout_squeeze strategy templates.',
    relatedTerms: ['Support', 'Resistance', 'Volume', 'False Breakout'],
  },
  {
    term: 'Scalping',
    category: 'strategies',
    shortDef: 'Very short-term trading for small profits',
    fullExplanation: 'Scalping involves making many trades throughout the day to capture small price movements. Positions are held for seconds to minutes. Success requires tight spreads, fast execution, and strict discipline.',
    whyUseful: 'Scalping can generate consistent small profits with limited overnight risk. High frequency means many opportunities per day.',
    whyNotUseful: 'Transaction costs can eat into profits. Requires constant attention and fast execution. Stressful and time-intensive.',
    example: 'Buy at VWAP support, sell when price moves 10 cents (0.1%). Do this 50 times per day for $500 profit.',
    xfactorUsage: 'XFactor offers scalp_vwap_reversion for intraday scalping strategies.',
    relatedTerms: ['VWAP', 'Day Trading', 'Spread', 'Slippage'],
  },
  {
    term: 'Momentum Trading',
    category: 'strategies',
    shortDef: 'Trading based on the strength of price movement',
    fullExplanation: 'Momentum trading bets that stocks with strong recent performance will continue performing well, and weak performers will continue underperforming. It\'s based on behavioral finance—investors tend to herd.',
    whyUseful: 'Momentum is one of the most documented anomalies in finance. Strong momentum stocks often continue rising due to institutional buying and FOMO.',
    whyNotUseful: 'Momentum can reverse suddenly, especially in high-flying stocks. Buying high hoping for higher is psychologically difficult.',
    example: 'Screen for stocks up 20%+ in the past month with positive RSI. Buy the strongest, sell when momentum fades (RSI divergence).',
    xfactorUsage: 'XFactor uses momentum_rsi_divergence strategy and includes momentum scoring in the speculation algorithm.',
    relatedTerms: ['RSI', 'Relative Strength', 'Trend', 'FOMO'],
  },
  {
    term: 'Golden Cross',
    category: 'strategies',
    shortDef: 'Bullish signal when short MA crosses above long MA',
    fullExplanation: 'A Golden Cross occurs when a shorter-term moving average (typically 50 SMA) crosses above a longer-term one (typically 200 SMA). It signals a potential shift from bearish to bullish trend.',
    whyUseful: 'Golden Crosses often mark the beginning of major bull runs. The 50/200 crossover is widely watched by institutions.',
    whyNotUseful: 'Golden Crosses lag significantly—by the time it triggers, much of the move may be over. False signals occur in choppy markets.',
    example: 'S&P 500\'s 50 SMA crosses above 200 SMA. Historically, this has preceded major bull markets, though not always immediately.',
    xfactorUsage: 'XFactor detects Golden Crosses in the Stock Analyzer inflection point detection.',
    relatedTerms: ['Death Cross', 'SMA', 'Trend Reversal'],
    visualType: 'chart',
  },
  {
    term: 'Death Cross',
    category: 'strategies',
    shortDef: 'Bearish signal when short MA crosses below long MA',
    fullExplanation: 'A Death Cross occurs when a shorter-term moving average crosses below a longer-term one. It suggests potential trend reversal from bullish to bearish.',
    whyUseful: 'Death Crosses can signal the start of bear markets, helping you reduce exposure or hedge.',
    whyNotUseful: 'Like Golden Crosses, Death Crosses lag. They often trigger near market bottoms after much of the decline has occurred.',
    example: 'SPY\'s 50 SMA crosses below 200 SMA. This triggered in 2008 and 2022, preceding further declines—but also in 2015 which was a false signal.',
    xfactorUsage: 'XFactor detects Death Crosses in the Stock Analyzer inflection point detection.',
    relatedTerms: ['Golden Cross', 'SMA', 'Bear Market'],
    visualType: 'chart',
  },
  {
    term: 'Martingale',
    category: 'strategies',
    shortDef: 'Doubling down after losses',
    fullExplanation: 'Martingale involves doubling position size after each loss, so that one win recovers all losses plus original profit. It\'s derived from gambling theory and is extremely risky.',
    whyUseful: 'In theory, a single win recovers all previous losses. Can work in mean-reverting markets with high win rates.',
    whyNotUseful: 'EXTREMELY DANGEROUS. A losing streak can exponentially increase position size until account is blown. Even small losing streaks require huge capital.',
    example: 'Bet $100, lose. Bet $200, lose. Bet $400, lose. Bet $800, win $800. Net: -$100-$200-$400+$800 = +$100. But what if you lost 10 times?',
    xfactorUsage: 'XFactor offers Martingale position sizing as an OPTIONAL feature with strict limits. Use with extreme caution.',
    relatedTerms: ['Position Sizing', 'Risk Management', 'Drawdown'],
  },

  // ===== RISK MANAGEMENT =====
  {
    term: 'Stop Loss',
    category: 'risk',
    shortDef: 'Order to exit position at a predetermined loss level',
    fullExplanation: 'A stop loss is an order that automatically closes a position when price reaches a specified level, limiting potential losses. It\'s the most fundamental risk management tool.',
    whyUseful: 'Stop losses protect capital, remove emotion from exit decisions, and define risk before entering trades. "Cut your losses short."',
    whyNotUseful: 'Stops can be triggered by volatility spikes before price reverses in your favor (stop hunting). Very tight stops increase false exits.',
    example: 'Buy AAPL at $180 with stop at $175. Maximum loss is $5 per share (2.8%). If AAPL drops to $175, position closes automatically.',
    xfactorUsage: 'XFactor uses ATR-based dynamic stop losses that adapt to volatility. Configured via ATR multiplier setting.',
    relatedTerms: ['ATR', 'Risk/Reward', 'Trailing Stop', 'Take Profit'],
    diagram: 'stop-loss',
  },
  {
    term: 'Take Profit',
    category: 'risk',
    shortDef: 'Order to exit position at a predetermined profit level',
    fullExplanation: 'A take profit order automatically closes a position when price reaches a target level, locking in gains. It removes the temptation to hold too long or close too early.',
    whyUseful: 'Take profits ensure you capture gains rather than watching them evaporate. Helps maintain disciplined exit strategy.',
    whyNotUseful: 'In trending markets, fixed take profits can exit too early, missing larger moves. Consider trailing stops for trending strategies.',
    example: 'Buy at $100 with take profit at $110. When price hits $110, position closes with $10 profit regardless of how high it might go.',
    xfactorUsage: 'XFactor uses ATR-based dynamic take profits. The TP is typically 1.5-2x the ATR stop distance for positive risk/reward.',
    relatedTerms: ['Stop Loss', 'Risk/Reward', 'Trailing Stop'],
  },
  {
    term: 'Risk/Reward Ratio',
    category: 'risk',
    shortDef: 'Potential profit divided by potential loss',
    fullExplanation: 'Risk/Reward (R:R) compares how much you could lose versus how much you could gain on a trade. A 1:3 ratio means risking $1 to potentially make $3. Higher ratios allow lower win rates to be profitable.',
    whyUseful: 'Understanding R:R helps you take only trades where the potential payoff justifies the risk. Even 40% win rate is profitable with 1:3 R:R.',
    formula: 'R:R = (Target Price - Entry) / (Entry - Stop Loss) for longs',
    example: 'Entry $100, Stop $95, Target $115. Risk = $5, Reward = $15. R:R = 1:3. You need only 25% win rate to break even.',
    xfactorUsage: 'XFactor calculates and displays R:R for trade setups. The TP/SL multiplier settings control the ratio.',
    relatedTerms: ['Stop Loss', 'Take Profit', 'Win Rate', 'Expected Value'],
    diagram: 'risk-reward',
  },
  {
    term: 'Drawdown',
    category: 'risk',
    shortDef: 'Peak-to-trough decline in account value',
    fullExplanation: 'Drawdown measures the decline from a portfolio\'s peak value to its lowest point before a new peak. Maximum drawdown is the largest such decline ever recorded. It indicates worst-case scenario.',
    whyUseful: 'Drawdown measures psychological and financial pain. A 50% drawdown requires 100% gain to recover. Understanding worst-case helps with position sizing.',
    formula: 'Drawdown = (Peak Value - Trough Value) / Peak Value × 100%',
    example: 'Account peaks at $100,000, drops to $80,000. Drawdown = 20%. If this is your max drawdown, you\'ve only ever lost 20% from peak.',
    xfactorUsage: 'XFactor tracks max drawdown in bot performance metrics and can pause trading when drawdown exceeds limits.',
    relatedTerms: ['Risk Management', 'Recovery', 'Max Loss'],
    diagram: 'drawdown',
  },
  {
    term: 'Position Sizing',
    category: 'risk',
    shortDef: 'Determining how much capital to allocate to a trade',
    fullExplanation: 'Position sizing determines how many shares/contracts to trade based on account size and risk tolerance. Proper sizing ensures no single trade can significantly damage the account.',
    whyUseful: 'Position sizing is arguably the most important factor in long-term success. It determines if you survive losing streaks.',
    formula: 'Position Size = (Account × Risk %) / (Entry - Stop); e.g., $100,000 × 1% / $5 stop = 200 shares',
    example: '$100,000 account, risk 1% ($1,000) per trade. With a $5 stop loss, buy 200 shares. Win or lose, you only risk $1,000.',
    xfactorUsage: 'XFactor calculates position sizes based on risk % per trade and ATR-based stops in the Risk Controls panel.',
    relatedTerms: ['Risk Management', 'Stop Loss', 'Kelly Criterion'],
  },
  {
    term: 'VaR (Value at Risk)',
    category: 'risk',
    shortDef: 'Maximum expected loss at a confidence level',
    fullExplanation: 'VaR estimates the maximum loss expected over a time period at a given confidence level. 95% daily VaR of $10,000 means there\'s only a 5% chance of losing more than $10,000 in a day.',
    whyUseful: 'VaR provides a single number to communicate portfolio risk. It\'s used by institutions and regulators for risk management.',
    whyNotUseful: 'VaR doesn\'t capture tail risks—what happens in the 5% worst cases. The 2008 crisis showed VaR\'s limitations.',
    formula: 'VaR = Portfolio Value × σ × Z-score × √time; e.g., $100,000 × 2% × 1.65 × √1 = $3,300 (95% daily)',
    example: '95% daily VaR of $5,000 means on 95% of days, you won\'t lose more than $5,000. But 5% of days could be worse.',
    xfactorUsage: 'XFactor calculates and displays real-time VaR in the Risk Management panel.',
    relatedTerms: ['Risk Management', 'Standard Deviation', 'Confidence Interval'],
  },
  {
    term: 'Sharpe Ratio',
    category: 'risk',
    shortDef: 'Risk-adjusted return measure',
    fullExplanation: 'Sharpe Ratio measures return per unit of risk (volatility). A ratio of 1 means 1% excess return for each 1% of volatility. Higher is better. Above 1 is good, above 2 is excellent.',
    whyUseful: 'Sharpe Ratio allows comparing strategies with different return/risk profiles. A 10% return with 5% volatility beats 15% with 20% volatility.',
    whyNotUseful: 'Sharpe assumes returns are normally distributed—doesn\'t capture tail risks. Also penalizes upside volatility equally with downside.',
    formula: 'Sharpe = (Strategy Return - Risk-Free Rate) / Strategy Volatility',
    example: 'Strategy: 15% return, 10% volatility. Risk-free: 5%. Sharpe = (15-5)/10 = 1.0',
    xfactorUsage: 'XFactor displays Sharpe Ratio in bot performance metrics and uses it in risk scoring.',
    relatedTerms: ['Sortino Ratio', 'Risk-Adjusted Return', 'Volatility'],
  },
  {
    term: 'Sortino Ratio',
    category: 'risk',
    shortDef: 'Like Sharpe but only penalizes downside volatility',
    fullExplanation: 'Sortino Ratio is similar to Sharpe but uses downside deviation instead of total volatility. This is more meaningful because upside volatility is desirable.',
    whyUseful: 'Sortino better captures what investors care about—avoiding losses while welcoming gains. More accurate for asymmetric return distributions.',
    formula: 'Sortino = (Strategy Return - Risk-Free Rate) / Downside Deviation',
    example: 'A strategy that\'s up 20% half the time and flat half the time has high Sharpe volatility but zero downside, so excellent Sortino.',
    xfactorUsage: 'XFactor calculates Sortino Ratio in bot risk metrics for more nuanced risk assessment.',
    relatedTerms: ['Sharpe Ratio', 'Downside Risk', 'Risk-Adjusted Return'],
  },

  // ===== FUNDAMENTALS =====
  {
    term: 'P/E Ratio (Price-to-Earnings)',
    category: 'fundamentals',
    shortDef: 'Stock price divided by earnings per share',
    fullExplanation: 'P/E Ratio measures how much investors pay for each dollar of earnings. A P/E of 20 means investors pay $20 for $1 of annual earnings. It\'s the most common valuation metric.',
    whyUseful: 'P/E allows comparing valuations across companies. Low P/E may indicate undervaluation or problems; high P/E suggests growth expectations.',
    whyNotUseful: 'P/E doesn\'t work for unprofitable companies. It can be manipulated by accounting. Doesn\'t account for growth or quality of earnings.',
    formula: 'P/E = Share Price / Earnings Per Share (EPS)',
    example: 'Stock at $100, EPS of $5. P/E = 20. If competitor has P/E of 15 with similar growth, this stock might be overvalued.',
    xfactorUsage: 'XFactor displays P/E ratio in the Stock Analyzer and tracks P/E history over time.',
    relatedTerms: ['EPS', 'PEG Ratio', 'Valuation', 'Earnings'],
  },
  {
    term: 'EPS (Earnings Per Share)',
    category: 'fundamentals',
    shortDef: 'Net income divided by shares outstanding',
    fullExplanation: 'EPS represents the portion of a company\'s profit allocated to each outstanding share. It\'s the foundation of P/E ratio and a key metric for company profitability.',
    whyUseful: 'EPS growth drives stock prices over the long term. Comparing actual EPS to estimates (earnings surprise) often causes significant price moves.',
    formula: 'EPS = (Net Income - Preferred Dividends) / Weighted Average Shares Outstanding',
    example: 'Company earns $1B with 100M shares. EPS = $10. If analysts expected $9 (11% beat), stock might jump 5-10%.',
    xfactorUsage: 'XFactor displays EPS history and estimates in Stock Analyzer. Tracks earnings surprises (beats/misses).',
    relatedTerms: ['P/E Ratio', 'Earnings', 'Net Income'],
  },
  {
    term: 'PEG Ratio',
    category: 'fundamentals',
    shortDef: 'P/E ratio adjusted for growth',
    fullExplanation: 'PEG divides P/E by expected earnings growth rate. A PEG of 1 is "fairly valued." Below 1 may be undervalued relative to growth; above 1 may be overvalued.',
    whyUseful: 'PEG accounts for growth—a high P/E might be justified by high growth. Allows apples-to-apples comparison of growth stocks.',
    whyNotUseful: 'Relies on growth estimates which are often wrong. Doesn\'t work for declining earnings or very low growth.',
    formula: 'PEG = P/E Ratio / Annual EPS Growth Rate',
    example: 'Stock has P/E of 30, expected to grow EPS 30% annually. PEG = 1. A P/E 30 stock growing 15% has PEG of 2 (overvalued).',
    xfactorUsage: 'XFactor displays PEG ratio in Stock Analyzer fundamental metrics.',
    relatedTerms: ['P/E Ratio', 'EPS', 'Growth Investing'],
  },
  {
    term: 'Market Cap',
    category: 'fundamentals',
    shortDef: 'Total market value of all shares',
    fullExplanation: 'Market capitalization is the total value of a company\'s outstanding shares. It determines company size classification: micro (<$300M), small ($300M-$2B), mid ($2B-$10B), large ($10B-$200B), mega (>$200B).',
    whyUseful: 'Market cap indicates company size, risk profile, and liquidity. Larger caps are typically less volatile but slower growing.',
    formula: 'Market Cap = Current Share Price × Total Shares Outstanding',
    example: 'Apple at $180 with 15.5B shares = $2.79T market cap (mega cap). A $10 stock with 50M shares = $500M (small cap).',
    xfactorUsage: 'XFactor displays market cap and tracks market cap history in Stock Analyzer.',
    relatedTerms: ['Share Price', 'Valuation', 'Large Cap', 'Small Cap'],
  },
  {
    term: 'Dividend Yield',
    category: 'fundamentals',
    shortDef: 'Annual dividend as percentage of stock price',
    fullExplanation: 'Dividend yield shows the cash return from dividends relative to stock price. A $100 stock paying $3 annual dividend has 3% yield. Higher yield provides income; lower yield suggests growth focus.',
    whyUseful: 'Dividend yield provides consistent income. Dividends have historically contributed ~40% of total stock returns. High yield can cushion drawdowns.',
    whyNotUseful: 'Very high yields may signal dividend cuts ahead. Focus on yield alone misses growth opportunities.',
    formula: 'Dividend Yield = Annual Dividend Per Share / Stock Price × 100%',
    example: 'AT&T at $20 pays $1.11 annual dividend. Yield = 5.55%. Apple at $180 pays $0.96. Yield = 0.53%.',
    xfactorUsage: 'XFactor displays dividend yield in Stock Analyzer and tracks historical dividend trends.',
    relatedTerms: ['Dividends', 'Income Investing', 'Payout Ratio'],
  },
  {
    term: 'Beta',
    category: 'fundamentals',
    shortDef: 'Stock\'s volatility relative to the market',
    fullExplanation: 'Beta measures how much a stock moves relative to the broader market. Beta of 1 = moves with market. Beta > 1 = more volatile. Beta < 1 = less volatile. Negative beta = moves opposite.',
    whyUseful: 'Beta helps estimate how your portfolio will react to market moves. High beta for aggressive; low beta for defensive.',
    whyNotUseful: 'Beta is based on historical data and can change. Doesn\'t capture company-specific risks.',
    formula: 'Beta = Covariance(Stock, Market) / Variance(Market)',
    example: 'NVDA beta of 1.8 means if market rises 1%, NVDA typically rises 1.8%. If market drops 1%, NVDA typically drops 1.8%.',
    xfactorUsage: 'XFactor displays beta in Stock Analyzer fundamental metrics.',
    relatedTerms: ['Volatility', 'Correlation', 'Risk', 'Alpha'],
  },
  {
    term: 'Profit Margin',
    category: 'fundamentals',
    shortDef: 'Percentage of revenue that becomes profit',
    fullExplanation: 'Profit margin shows how much of each revenue dollar is profit. Net profit margin uses bottom-line income; gross margin uses revenue minus cost of goods. Higher margins indicate pricing power and efficiency.',
    whyUseful: 'High margins indicate competitive advantages (moat). Improving margins suggest operational improvements. Compare within industries.',
    formula: 'Net Profit Margin = Net Income / Revenue × 100%',
    example: 'Apple revenue $100B, net income $25B. Net margin = 25%. Grocery stores might have 2% margin. Software companies often 20%+.',
    xfactorUsage: 'XFactor displays profit margin in Stock Analyzer and tracks margin trends over time.',
    relatedTerms: ['Revenue', 'Net Income', 'Gross Margin'],
  },

  // ===== CHART PATTERNS =====
  {
    term: 'Support',
    category: 'patterns',
    shortDef: 'Price level where buying prevents further decline',
    fullExplanation: 'Support is a price level where buying interest is strong enough to prevent price from falling further. It often forms at previous lows, round numbers, or moving averages. Support becomes resistance when broken.',
    whyUseful: 'Support levels offer low-risk entry points with clear invalidation. Buying near support with stop just below creates favorable risk/reward.',
    example: 'Stock bounces off $100 three times over several months. $100 is strong support. Buying at $102 with stop at $98 risks $4 to potentially gain $10+.',
    xfactorUsage: 'XFactor identifies support levels in Stock Analyzer and uses them in breakout strategies.',
    relatedTerms: ['Resistance', 'Breakout', 'Technical Analysis'],
    visualType: 'chart',
    diagram: 'support-resistance',
  },
  {
    term: 'Resistance',
    category: 'patterns',
    shortDef: 'Price level where selling prevents further rise',
    fullExplanation: 'Resistance is a price level where selling pressure is strong enough to halt advances. It often forms at previous highs, round numbers, or moving averages. When broken convincingly, resistance becomes support.',
    whyUseful: 'Resistance levels offer targets for exits and potential short entry points. Breakouts above resistance often lead to momentum runs.',
    example: 'Stock fails at $150 multiple times. $150 is strong resistance. Breaking above on volume signals potential run to $160-$170.',
    xfactorUsage: 'XFactor identifies resistance levels in Stock Analyzer for target setting.',
    relatedTerms: ['Support', 'Breakout', 'Technical Analysis'],
    visualType: 'chart',
    diagram: 'support-resistance',
  },
  {
    term: 'Divergence',
    category: 'patterns',
    shortDef: 'When price and indicator move in opposite directions',
    fullExplanation: 'Divergence occurs when price makes a new high/low but an indicator (RSI, MACD) doesn\'t confirm. Bullish divergence: lower price low, higher indicator low. Bearish divergence: higher price high, lower indicator high.',
    whyUseful: 'Divergences often precede reversals—they show weakening momentum before price turns. A powerful early warning signal.',
    whyNotUseful: 'Divergences can persist through multiple new highs/lows before resolving. Not reliable timing signals alone.',
    example: 'Stock makes new high at $120 (previous high $110), but RSI at 65 (previous 75). Bearish divergence suggests weakening—potential top.',
    xfactorUsage: 'XFactor uses momentum_rsi_divergence strategy to detect and trade divergence patterns.',
    relatedTerms: ['RSI', 'MACD', 'Momentum', 'Reversal'],
    visualType: 'chart',
  },
  {
    term: 'Overbought',
    category: 'patterns',
    shortDef: 'When price has risen too fast and may pull back',
    fullExplanation: 'Overbought conditions suggest a security has risen too quickly and may be due for a pullback. Common thresholds: RSI > 70, Stochastic > 80. However, in strong uptrends, overbought can remain for extended periods.',
    whyUseful: 'Overbought warnings help avoid buying at tops. Can signal exit points for long positions or short entry for mean reversion.',
    whyNotUseful: 'In strong trends, RSI can stay above 70 for months. Selling purely on overbought readings can miss massive gains.',
    example: 'RSI hits 85 after 30% rally. Consider taking partial profits or tightening stops rather than outright selling.',
    xfactorUsage: 'XFactor displays overbought conditions in technical overlays and uses them in mean reversion strategies.',
    relatedTerms: ['RSI', 'Oversold', 'Mean Reversion'],
  },
  {
    term: 'Oversold',
    category: 'patterns',
    shortDef: 'When price has fallen too fast and may bounce',
    fullExplanation: 'Oversold conditions suggest a security has declined too quickly and may be due for a bounce. Common thresholds: RSI < 30, Stochastic < 20. In strong downtrends, oversold can persist.',
    whyUseful: 'Oversold readings can identify bounce opportunities in quality stocks. Good for mean reversion entries with defined risk.',
    whyNotUseful: 'In bear markets, stocks can stay oversold for months. "Catching a falling knife" is a real risk.',
    example: 'Quality stock drops 20% on market panic, RSI at 25. Might be buying opportunity—but use stops in case decline continues.',
    xfactorUsage: 'XFactor uses oversold conditions in reversion_rsi_bb strategy for bounce trades.',
    relatedTerms: ['RSI', 'Overbought', 'Mean Reversion', 'Support'],
  },
  
  // ===== ADDITIONAL BASICS =====
  { term: 'Bid', category: 'basics', shortDef: 'Highest price buyer will pay', fullExplanation: 'The bid is the maximum price a buyer is currently willing to pay for a security. When you sell at market, you receive the bid price.', whyUseful: 'Understanding bid helps you know your actual execution price when selling.', relatedTerms: ['Ask', 'Spread', 'Market Order'] },
  { term: 'Ask', category: 'basics', shortDef: 'Lowest price seller will accept', fullExplanation: 'The ask (or offer) is the minimum price a seller is willing to accept. When you buy at market, you pay the ask price.', whyUseful: 'Knowing the ask helps you understand entry costs and slippage.', relatedTerms: ['Bid', 'Spread', 'Limit Order'] },
  { term: 'Market Order', category: 'basics', shortDef: 'Order executed immediately at best price', fullExplanation: 'A market order executes immediately at the best available price. It guarantees execution but not price.', whyUseful: 'Use for fast execution when getting in/out quickly matters more than price.', whyNotUseful: 'Can result in poor fills in illiquid markets or during volatility.', relatedTerms: ['Limit Order', 'Slippage'] },
  { term: 'Limit Order', category: 'basics', shortDef: 'Order to buy/sell at specific price or better', fullExplanation: 'A limit order sets the maximum price you will pay (buy) or minimum you will accept (sell). It guarantees price but not execution.', whyUseful: 'Ensures you get your desired price, avoids slippage, good for patient entries.', whyNotUseful: 'May never execute if price doesn\'t reach your limit.', relatedTerms: ['Market Order', 'Stop Order'] },
  { term: 'Stop Order', category: 'basics', shortDef: 'Order triggered when price reaches a level', fullExplanation: 'A stop order becomes a market order when the stop price is reached. Stop-loss orders protect against losses; stop-limit combines stop trigger with limit price.', whyUseful: 'Essential for risk management and protecting profits.', formula: 'Stop Loss = Entry Price - (ATR × Multiplier)', relatedTerms: ['Stop Loss', 'Trailing Stop'] },
  { term: 'Margin', category: 'basics', shortDef: 'Borrowed money to trade larger positions', fullExplanation: 'Margin is money borrowed from your broker to buy securities. Margin accounts allow leverage but require minimum equity (maintenance margin).', whyUseful: 'Amplifies returns on winning trades, enables short selling.', whyNotUseful: 'Amplifies losses, margin calls can force liquidation at worst times.', relatedTerms: ['Leverage', 'Margin Call'] },
  { term: 'Equity', category: 'basics', shortDef: 'Total account value minus liabilities', fullExplanation: 'Account equity is the total value of your account including cash, positions, and unrealized P&L, minus any borrowed funds (margin).', whyUseful: 'True measure of your trading capital and performance.', formula: 'Equity = Cash + Market Value of Positions - Margin Debt', relatedTerms: ['P&L', 'Buying Power'] },
  { term: 'Buying Power', category: 'basics', shortDef: 'Maximum amount you can purchase', fullExplanation: 'Buying power is the total amount available to buy securities, including margin. Day traders get 4:1 intraday margin; overnight is typically 2:1.', whyUseful: 'Helps plan position sizes and avoid overtrading.', relatedTerms: ['Margin', 'Position Sizing'] },
  { term: 'Day Trade', category: 'regulations', shortDef: 'Buy and sell same security same day', fullExplanation: 'A day trade opens and closes a position within the same trading day. Under FINRA PDT rules, making 4+ day trades in 5 business days with < $25,000 equity flags your account.', whyUseful: 'No overnight risk, quick profits, many opportunities.', whyNotUseful: 'PDT rules, high activity, commission costs, requires focus.', relatedTerms: ['Pattern Day Trader', 'Swing Trade', 'Day Trading Buying Power'], example: '9:35 AM: Buy 100 AAPL at $150. 2:30 PM: Sell 100 AAPL at $153. This counts as 1 day trade. Do this 4 times in 5 days = PDT.' },
  { term: 'Pattern Day Trader', category: 'regulations', shortDef: 'Trader making 4+ day trades in 5 days', fullExplanation: 'FINRA Rule 4210 designates margin accounts making 4+ day trades in 5 business days as PDT. Requires $25,000 minimum equity to continue day trading. Falling below restricts the account.', whyUseful: 'Understand to plan trading frequency.', relatedTerms: ['Day Trade', 'Margin Account', 'Day Trading Buying Power'], example: 'Week 1: 2 day trades. Week 2: 2 day trades in first 3 days = 4 total in 5 business days. Account flagged as PDT. If equity < $25k, day trading restricted.' },
  { term: 'Swing Trade', category: 'basics', shortDef: 'Holding positions for days to weeks', fullExplanation: 'Swing trading captures short-to-medium term price moves, holding overnight or for several days. Less intense than day trading.', whyUseful: 'Captures larger moves, less screen time, avoids PDT rules.', whyNotUseful: 'Overnight gap risk, longer capital tie-up.', relatedTerms: ['Day Trade', 'Position Trade'] },
  { term: 'Position Trade', category: 'basics', shortDef: 'Holding for weeks to months', fullExplanation: 'Position trading focuses on larger trends over weeks or months, based on fundamentals and technical analysis.', whyUseful: 'Lower stress, bigger moves, fewer transactions.', relatedTerms: ['Swing Trade', 'Trend Following'] },
  { term: 'Ticker Symbol', category: 'basics', shortDef: 'Unique identifier for a security', fullExplanation: 'A ticker symbol is the abbreviation used to uniquely identify traded shares of a stock. AAPL for Apple, MSFT for Microsoft.', whyUseful: 'Essential for placing orders and researching securities.', example: 'NVDA, AMD, SPY, QQQ, TSLA' },
  { term: 'Exchange', category: 'basics', shortDef: 'Marketplace where securities are traded', fullExplanation: 'Exchanges like NYSE, NASDAQ, LSE are regulated marketplaces where stocks are bought and sold.', whyUseful: 'Understanding exchanges helps with order routing and market hours.', relatedTerms: ['NYSE', 'NASDAQ', 'Market Hours'] },
  { term: 'Market Hours', category: 'basics', shortDef: 'When exchanges are open for trading', fullExplanation: 'US markets: 9:30 AM - 4:00 PM ET. Pre-market: 4:00-9:30 AM, After-hours: 4:00-8:00 PM. Different rules apply.', whyUseful: 'Plan trades around market hours for best liquidity.', relatedTerms: ['Pre-Market', 'After-Hours'] },
  { term: 'Pre-Market', category: 'basics', shortDef: 'Trading before regular hours', fullExplanation: 'Pre-market trading occurs 4:00-9:30 AM ET. Lower volume, wider spreads, reacts to overnight news.', whyUseful: 'React to earnings or news before market open.', whyNotUseful: 'Thin liquidity, wider spreads, higher volatility.' },
  { term: 'After-Hours', category: 'basics', shortDef: 'Trading after market close', fullExplanation: 'After-hours trading occurs 4:00-8:00 PM ET. Allows reaction to late news and earnings releases.', whyUseful: 'Trade on earnings releases immediately.', whyNotUseful: 'Low liquidity, wide spreads, price gaps.' },
  { term: 'Gap', category: 'basics', shortDef: 'Price jump between sessions', fullExplanation: 'A gap is a price range where no trades occurred between one session\'s close and next session\'s open. Gap up is bullish; gap down is bearish.', whyUseful: 'Gaps often indicate strong sentiment and can be traded.', relatedTerms: ['Gap Fill', 'Breakaway Gap'] },
  { term: 'Gap Fill', category: 'basics', shortDef: 'Price returning to pre-gap level', fullExplanation: 'When price moves back to fill the gap between sessions. Common gaps often fill; breakaway gaps less likely.', whyUseful: 'Trade strategy: fade common gaps, respect breakaway gaps.', relatedTerms: ['Gap', 'Fade'] },
  { term: 'Liquidity', category: 'basics', shortDef: 'Ease of buying/selling without impacting price', fullExplanation: 'Liquidity measures how easily you can enter/exit positions. High liquidity = tight spreads, easy execution. Low liquidity = wide spreads, slippage.', whyUseful: 'Trade liquid markets for better execution and lower costs.', relatedTerms: ['Volume', 'Spread', 'Slippage'] },
  { term: 'Slippage', category: 'basics', shortDef: 'Difference between expected and actual price', fullExplanation: 'Slippage is the difference between your intended execution price and actual fill. Common in fast markets or illiquid securities.', whyUseful: 'Factor slippage into strategy backtests and risk calculations.', relatedTerms: ['Liquidity', 'Market Order'] },
  { term: 'Fill', category: 'basics', shortDef: 'Completion of an order', fullExplanation: 'A fill is the execution of your order. Partial fills occur when only part of your order executes.', whyUseful: 'Understanding fills helps manage order execution.', relatedTerms: ['Order', 'Execution'] },
  { term: 'Dividend', category: 'basics', shortDef: 'Company profit distribution to shareholders', fullExplanation: 'Dividends are cash payments from company profits to shareholders. Paid quarterly by most dividend-paying stocks.', whyUseful: 'Passive income stream, sign of company health.', relatedTerms: ['Dividend Yield', 'Ex-Dividend Date'] },
  { term: 'Ex-Dividend Date', category: 'basics', shortDef: 'Cutoff date to receive dividend', fullExplanation: 'To receive a dividend, you must own shares before the ex-dividend date. Stock typically drops by dividend amount on ex-date.', whyUseful: 'Plan positions around dividend dates.', relatedTerms: ['Dividend', 'Record Date'] },
  { term: 'Stock Split', category: 'basics', shortDef: 'Increasing shares while decreasing price proportionally', fullExplanation: 'A stock split increases share count while proportionally decreasing price. 2-for-1 split: 100 shares at $200 becomes 200 shares at $100.', whyUseful: 'Understand to avoid confusion when reviewing historical charts.', relatedTerms: ['Reverse Split'] },
  { term: 'IPO', category: 'basics', shortDef: 'Initial Public Offering', fullExplanation: 'When a private company first offers shares to the public. Often volatile with high retail interest.', whyUseful: 'High-profile IPOs can be trading opportunities.', whyNotUseful: 'Often overpriced, lock-up expiration can pressure stock.' },
  { term: 'Blue Chip', category: 'basics', shortDef: 'Large, stable, established company', fullExplanation: 'Blue chip stocks are large, well-known, financially stable companies like AAPL, MSFT, JNJ. Generally lower risk.', whyUseful: 'Safer for conservative portfolios.', relatedTerms: ['Market Cap', 'Dividend'] },
  { term: 'Penny Stock', category: 'basics', shortDef: 'Low-priced, small company stock', fullExplanation: 'Stocks trading under $5, often OTC. High volatility, low liquidity, prone to manipulation.', whyUseful: 'High reward potential for small accounts.', whyNotUseful: 'High risk, manipulation, poor liquidity, difficult to short.' },
  { term: 'ETF', category: 'basics', shortDef: 'Exchange-Traded Fund', fullExplanation: 'ETFs are baskets of securities trading like stocks. SPY tracks S&P 500, QQQ tracks NASDAQ 100.', whyUseful: 'Easy diversification, sector exposure, liquid, low fees.', relatedTerms: ['Index', 'Mutual Fund'] },
  { term: 'Index', category: 'basics', shortDef: 'Benchmark measuring market performance', fullExplanation: 'An index like S&P 500 or NASDAQ tracks performance of a group of stocks. Used as benchmarks.', whyUseful: 'Compare your performance to the market.', relatedTerms: ['S&P 500', 'NASDAQ', 'Dow Jones'] },
  { term: 'Sector', category: 'basics', shortDef: 'Group of related industries', fullExplanation: 'Sectors group similar companies: Technology, Healthcare, Financials, Energy, Consumer, etc. Sector rotation is a strategy.', whyUseful: 'Understand correlations and rotation strategies.', relatedTerms: ['Industry', 'Sector Rotation'] },
  { term: 'Float', category: 'basics', shortDef: 'Shares available for public trading', fullExplanation: 'Float is shares outstanding minus insider and restricted shares. Low float stocks are more volatile.', whyUseful: 'Low float + high volume = explosive moves.', relatedTerms: ['Short Interest', 'Shares Outstanding'] },
  { term: 'Short Interest', category: 'basics', shortDef: 'Shares currently sold short', fullExplanation: 'Short interest is the number of shares currently sold short. High short interest can lead to short squeezes.', whyUseful: 'High short interest signals potential squeeze opportunities.', relatedTerms: ['Short Squeeze', 'Days to Cover'] },
  { term: 'Short Squeeze', category: 'basics', shortDef: 'Rapid price rise forcing shorts to cover', fullExplanation: 'When a heavily shorted stock rises, short sellers are forced to buy back shares to cover losses, driving price higher.', whyUseful: 'Can create explosive upside moves.', example: 'GME in January 2021 squeezed from $20 to $483.', relatedTerms: ['Short Interest', 'Days to Cover'] },
  { term: 'Days to Cover', category: 'basics', shortDef: 'Days to close all short positions', fullExplanation: 'Short interest divided by average daily volume. Higher days to cover = more squeeze potential.', whyUseful: 'Identify squeeze candidates.', formula: 'Days to Cover = Short Interest / Avg Daily Volume' },
  { term: 'Catalyst', category: 'basics', shortDef: 'Event that triggers price movement', fullExplanation: 'Catalysts are news events, earnings, FDA approvals, etc. that cause significant price moves.', whyUseful: 'Trading around catalysts offers high reward opportunities.', whyNotUseful: 'Difficult to predict direction; often priced in.' },
  
  // ===== MORE INDICATORS =====
  { term: 'MACD', category: 'indicators', shortDef: 'Moving Average Convergence Divergence', fullExplanation: 'MACD measures the relationship between two EMAs (12 and 26). Signal line is 9 EMA of MACD. Crossovers generate signals.', whyUseful: 'Combines trend following and momentum. Good for identifying trend changes.', formula: 'MACD = 12 EMA - 26 EMA; Signal = 9 EMA of MACD', relatedTerms: ['EMA', 'Signal Line', 'Histogram'], xfactorUsage: 'XFactor uses MACD in trend_adx_macd strategy.', diagram: 'macd' },
  { term: 'ATR', category: 'indicators', shortDef: 'Average True Range - volatility measure', fullExplanation: 'ATR measures average volatility over N periods (typically 14). Used for stop placement and position sizing.', whyUseful: 'Volatility-adaptive stops adjust to market conditions.', formula: 'TR = Max(High-Low, |High-PrevClose|, |Low-PrevClose|); ATR = Avg(TR)', relatedTerms: ['Volatility', 'Stop Loss'], xfactorUsage: 'XFactor uses ATR for dynamic stop losses and take profits.' },
  { term: 'OBV', category: 'indicators', shortDef: 'On-Balance Volume', fullExplanation: 'OBV is cumulative volume indicator: adds volume on up days, subtracts on down days. Rising OBV confirms uptrend.', whyUseful: 'Volume precedes price. OBV divergence can signal reversals.', relatedTerms: ['Volume', 'Accumulation/Distribution'] },
  { term: 'VWAP', category: 'indicators', shortDef: 'Volume Weighted Average Price', fullExplanation: 'VWAP is average price weighted by volume, calculated intraday. Institutional benchmark. Price above = bullish, below = bearish.', whyUseful: 'Institutional traders buy below VWAP, sell above. Good for intraday support/resistance.', formula: 'VWAP = Σ(Price × Volume) / Σ(Volume)', xfactorUsage: 'XFactor offers scalp_vwap_reversion for intraday VWAP strategies.' },
  { term: 'ADX', category: 'indicators', shortDef: 'Average Directional Index - trend strength', fullExplanation: 'ADX measures trend strength (not direction) on 0-100 scale. >25 is trending, <20 is range-bound.', whyUseful: 'Determine whether to use trend or mean-reversion strategies.', formula: 'ADX = 100 × EMA(|+DI - -DI| / (+DI + -DI))', relatedTerms: ['+DI', '-DI', 'Trend'], xfactorUsage: 'XFactor uses ADX in trend_adx_macd and displays in Market Regime panel.' },
  { term: 'CCI', category: 'indicators', shortDef: 'Commodity Channel Index', fullExplanation: 'CCI measures price deviation from average. >100 overbought, <-100 oversold. Works on any timeframe.', whyUseful: 'Good for cyclical markets and mean reversion signals.', formula: 'CCI = (Typical Price - 20 SMA) / (0.015 × Mean Deviation)' },
  { term: 'Williams %R', category: 'indicators', shortDef: 'Momentum oscillator similar to Stochastic', fullExplanation: 'Williams %R compares close to high-low range on -100 to 0 scale. Below -80 is oversold, above -20 is overbought.', whyUseful: 'Faster than Stochastic, good for short-term trading.', formula: '%R = (Highest High - Close) / (Highest High - Lowest Low) × -100' },
  { term: 'Momentum', category: 'indicators', shortDef: 'Rate of price change', fullExplanation: 'Momentum measures the rate at which price is changing. Positive momentum = rising prices; negative = falling.', whyUseful: 'Trend confirmation, divergence signals.', formula: 'Momentum = Close - Close(n periods ago)', relatedTerms: ['ROC', 'Trend'] },
  { term: 'ROC', category: 'indicators', shortDef: 'Rate of Change - percentage momentum', fullExplanation: 'ROC is momentum expressed as percentage. Shows how much price changed over period.', whyUseful: 'Compare momentum across different-priced stocks.', formula: 'ROC = ((Close - Close[n]) / Close[n]) × 100' },
  { term: 'Parabolic SAR', category: 'indicators', shortDef: 'Stop and Reverse trend indicator', fullExplanation: 'Parabolic SAR places dots above (downtrend) or below (uptrend) price. Dot flip signals potential reversal.', whyUseful: 'Good for trailing stops and trend following.', relatedTerms: ['Trailing Stop', 'Trend'] },
  { term: 'Ichimoku Cloud', category: 'indicators', shortDef: 'Comprehensive trend indicator system', fullExplanation: 'Ichimoku has 5 lines: Tenkan, Kijun, Senkou A/B (cloud), Chikou. Price above cloud is bullish; below is bearish.', whyUseful: 'All-in-one: trend, momentum, support/resistance.', whyNotUseful: 'Complex for beginners, can clutter charts.' },
  { term: 'Pivot Points', category: 'indicators', shortDef: 'Key support/resistance levels', fullExplanation: 'Pivot points calculate support and resistance from prior period\'s high, low, close. Used by floor traders.', whyUseful: 'Pre-market planning for key levels.', formula: 'Pivot = (High + Low + Close) / 3' },
  { term: 'Fibonacci Extension', category: 'indicators', shortDef: 'Price targets beyond the original move', fullExplanation: 'Extensions project price targets beyond a move using Fibonacci ratios (127.2%, 161.8%, 261.8%).', whyUseful: 'Set profit targets for breakout trades.', relatedTerms: ['Fibonacci Retracement'] },
  { term: 'Volume Profile', category: 'indicators', shortDef: 'Volume distribution at each price', fullExplanation: 'Volume Profile shows volume traded at each price level. High volume nodes = support/resistance; low volume = gaps.', whyUseful: 'Identify true support/resistance based on actual trading.', relatedTerms: ['POC', 'Value Area'] },
  { term: 'POC', category: 'indicators', shortDef: 'Point of Control - highest volume price', fullExplanation: 'POC is the price with most volume traded in a profile. Acts as magnet and support/resistance.', whyUseful: 'Price often returns to POC.', relatedTerms: ['Volume Profile', 'Value Area'] },
  { term: 'Value Area', category: 'indicators', shortDef: '70% of volume range', fullExplanation: 'Value Area High (VAH) and Low (VAL) contain 70% of volume. Trading strategies involve fading moves outside.', whyUseful: 'Identify fair value range for mean reversion.', relatedTerms: ['Volume Profile', 'POC'] },
  { term: 'Delta', category: 'indicators', shortDef: 'Net buying vs selling volume', fullExplanation: 'Delta is the difference between buy and sell volume. Positive delta = more buying; negative = more selling.', whyUseful: 'Shows order flow imbalance and buyer/seller aggression.' },
  { term: 'Cumulative Delta', category: 'indicators', shortDef: 'Running total of delta', fullExplanation: 'Cumulative delta tracks running net volume. Divergence from price indicates hidden buying or selling.', whyUseful: 'Spot institutional accumulation or distribution.', relatedTerms: ['Delta', 'Order Flow'] },
  { term: 'Market Profile', category: 'indicators', shortDef: 'Time-price distribution chart', fullExplanation: 'Market Profile shows time spent at each price level in a distribution format. TPO (Time Price Opportunity) counts.', whyUseful: 'Understand market structure and fair value.', relatedTerms: ['Volume Profile', 'Value Area'] },
  { term: 'A/D Line', category: 'indicators', shortDef: 'Accumulation/Distribution Line', fullExplanation: 'A/D Line uses volume and close location within range to measure buying/selling pressure.', whyUseful: 'Divergence from price warns of potential reversal.', formula: 'CLV = ((Close - Low) - (High - Close)) / (High - Low)' },
  { term: 'MFI', category: 'indicators', shortDef: 'Money Flow Index', fullExplanation: 'MFI is volume-weighted RSI. Incorporates volume into overbought/oversold readings.', whyUseful: 'More reliable than RSI in high-volume situations.', formula: 'MFI = 100 - (100 / (1 + Money Ratio))' },
  { term: 'Chaikin Money Flow', category: 'indicators', shortDef: 'CMF - buying/selling pressure over time', fullExplanation: 'CMF measures buying and selling pressure over a period (typically 21). Positive = accumulation; negative = distribution.', whyUseful: 'Confirm trend strength with volume analysis.' },
  { term: 'Force Index', category: 'indicators', shortDef: 'Price change weighted by volume', fullExplanation: 'Force Index combines price change and volume. Large force = strong move; weak force = uncertain.', whyUseful: 'Identify strength of moves.', formula: 'Force = (Close - Prior Close) × Volume' },
  { term: 'Keltner Channel', category: 'indicators', shortDef: 'ATR-based price channel', fullExplanation: 'Keltner Channels are EMA ± ATR multiplier. Similar to Bollinger but uses ATR instead of standard deviation.', whyUseful: 'Smoother than Bollinger, good for trend following.', relatedTerms: ['ATR', 'Bollinger Bands'] },
  { term: 'Donchian Channel', category: 'indicators', shortDef: 'Highest high / lowest low channel', fullExplanation: 'Donchian Channel plots highest high and lowest low over N periods. Used in turtle trading system.', whyUseful: 'Simple breakout system.', relatedTerms: ['Breakout', 'Turtle Trading'] },
  { term: 'Supertrend', category: 'indicators', shortDef: 'ATR-based trend indicator', fullExplanation: 'Supertrend is ATR-based indicator showing trend direction. Line below price = uptrend; above = downtrend.', whyUseful: 'Simple trend-following system with built-in stops.' },
  { term: 'Standard Deviation', category: 'indicators', shortDef: 'Statistical measure of volatility', fullExplanation: 'Standard deviation measures how spread out prices are from the mean. Higher = more volatile.', whyUseful: 'Foundation for Bollinger Bands and volatility calculations.', formula: 'σ = √(Σ(x-μ)² / n)' },
  { term: 'Z-Score', category: 'indicators', shortDef: 'Standard deviations from mean', fullExplanation: 'Z-Score measures how many standard deviations price is from its mean. ±2 is statistically significant.', whyUseful: 'Mean reversion trading when Z-Score is extreme.', formula: 'Z = (Price - Mean) / σ', xfactorUsage: 'XFactor offers reversion_zscore strategy template.' },
  { term: 'Linear Regression', category: 'indicators', shortDef: 'Best-fit trend line', fullExplanation: 'Linear regression calculates best-fit line through price data. Channel uses ± deviations from this line.', whyUseful: 'Objective trend identification and mean reversion.', relatedTerms: ['Regression Channel'] },
  
  // ===== MORE STRATEGIES =====
  { term: 'Fade', category: 'strategies', shortDef: 'Trading against the move', fullExplanation: 'Fading means trading against recent direction—shorting rallies or buying dips. Contrarian approach.', whyUseful: 'Catch overextensions, good risk/reward.', whyNotUseful: 'Dangerous in strong trends, requires precise timing.', relatedTerms: ['Contrarian', 'Mean Reversion'] },
  { term: 'Arbitrage', category: 'strategies', shortDef: 'Profiting from price differences', fullExplanation: 'Arbitrage exploits price differences in related securities or markets. Usually requires speed and capital.', whyUseful: 'Low risk if executed properly.', whyNotUseful: 'Opportunities are rare and quickly eliminated.' },
  { term: 'Pairs Trading', category: 'strategies', shortDef: 'Trading relative value between correlated stocks', fullExplanation: 'Pairs trading goes long one stock and short a correlated stock, betting on convergence.', whyUseful: 'Market-neutral, profits from relationship not direction.', relatedTerms: ['Correlation', 'Hedge'] },
  { term: 'News Trading', category: 'strategies', shortDef: 'Trading around news events', fullExplanation: 'News trading reacts to earnings, economic data, company announcements. Can be reactive or anticipatory.', whyUseful: 'News creates volatility and opportunity.', whyNotUseful: 'Fast moves, slippage, often priced in.', xfactorUsage: 'XFactor integrates real-time news sentiment for trading signals.' },
  { term: 'Earnings Play', category: 'strategies', shortDef: 'Trading around earnings announcements', fullExplanation: 'Earnings plays trade the volatility around quarterly results. Pre-earnings run-ups, post-earnings drift.', whyUseful: 'Known catalyst dates, high volatility.', whyNotUseful: 'Binary event, expensive options, unpredictable.' },
  { term: 'Gap Trading', category: 'strategies', shortDef: 'Trading price gaps at open', fullExplanation: 'Gap trading strategies either fade gaps (expecting fill) or trade gap-and-go (continuation).', whyUseful: 'Regular morning opportunities.', relatedTerms: ['Gap', 'Gap Fill'] },
  { term: 'Sector Rotation', category: 'strategies', shortDef: 'Moving capital between sectors', fullExplanation: 'Sector rotation shifts investment between market sectors based on economic cycle or relative strength.', whyUseful: 'Capture outperforming sectors.', relatedTerms: ['Sector', 'Economic Cycle'] },
  { term: 'DCA', category: 'strategies', shortDef: 'Dollar Cost Averaging', fullExplanation: 'DCA invests fixed amounts at regular intervals regardless of price. Reduces timing risk.', whyUseful: 'Simple, removes emotion, good for accumulation.', whyNotUseful: 'Underperforms lump sum in rising markets.' },
  { term: 'Grid Trading', category: 'strategies', shortDef: 'Placing orders at set price intervals', fullExplanation: 'Grid trading places buy and sell orders at fixed intervals, profiting from oscillation.', whyUseful: 'Works in ranging markets.', whyNotUseful: 'Loses in trending markets with many open positions.' },
  { term: 'Anti-Martingale', category: 'strategies', shortDef: 'Increasing size after wins', fullExplanation: 'Anti-Martingale increases size when winning, decreases when losing. Opposite of Martingale.', whyUseful: 'Capitalizes on winning streaks, limits losing streaks.', relatedTerms: ['Martingale', 'Position Sizing'] },
  { term: 'Turtle Trading', category: 'strategies', shortDef: 'Classic trend-following breakout system', fullExplanation: 'Turtle Trading buys 20-day high breakouts, exits on 10-day low. ATR-based position sizing.', whyUseful: 'Proven system with clear rules.', relatedTerms: ['Donchian Channel', 'ATR'] },
  { term: 'CANSLIM', category: 'strategies', shortDef: 'Growth stock selection criteria', fullExplanation: 'CANSLIM by William O\'Neil: Current earnings, Annual earnings, New products, Supply/demand, Leader, Institutional, Market.', whyUseful: 'Systematic growth stock selection.', relatedTerms: ['Fundamental Analysis', 'Growth'] },
  { term: 'Covered Call', category: 'strategies', shortDef: 'Selling calls against stock position', fullExplanation: 'Own 100 shares, sell 1 call option. Collect premium but cap upside at strike price.', whyUseful: 'Generate income, reduce cost basis.', whyNotUseful: 'Miss big upside moves, still have downside risk.' },
  { term: 'Iron Condor', category: 'strategies', shortDef: 'Selling call and put spreads', fullExplanation: 'Iron condor sells OTM call spread and put spread, profiting if price stays within range.', whyUseful: 'Profit from low volatility, defined risk.', relatedTerms: ['Credit Spread', 'Theta'] },
  { term: 'Straddle', category: 'strategies', shortDef: 'Buy both call and put at same strike', fullExplanation: 'Straddle profits from large move in either direction. Buy before earnings or events.', whyUseful: 'Profit from volatility regardless of direction.', whyNotUseful: 'Expensive, needs big move to profit.' },
  { term: 'Strangle', category: 'strategies', shortDef: 'Buy OTM call and put', fullExplanation: 'Cheaper than straddle but needs bigger move. OTM call and OTM put.', whyUseful: 'Lower cost volatility play.', relatedTerms: ['Straddle', 'Volatility'] },
  { term: 'Credit Spread', category: 'strategies', shortDef: 'Selling spread for net credit', fullExplanation: 'Sell higher premium option, buy lower premium option. Receive credit. Profit if price stays favorable.', whyUseful: 'Collect premium, defined risk.', relatedTerms: ['Bull Put Spread', 'Bear Call Spread'] },
  { term: 'Debit Spread', category: 'strategies', shortDef: 'Buying spread for net debit', fullExplanation: 'Buy option, sell further OTM option. Pay net debit. Cheaper than outright purchase.', whyUseful: 'Lower cost directional play.', relatedTerms: ['Bull Call Spread', 'Bear Put Spread'] },
  { term: 'Wheel Strategy', category: 'strategies', shortDef: 'Selling puts then calls repeatedly', fullExplanation: 'Sell cash-secured puts until assigned, then sell covered calls until called away. Repeat.', whyUseful: 'Generate income on stocks you want to own.', relatedTerms: ['Covered Call', 'Cash-Secured Put'] },
  { term: 'Collar', category: 'strategies', shortDef: 'Protective put + covered call', fullExplanation: 'Own stock, buy put for protection, sell call to offset put cost. Limited upside and downside.', whyUseful: 'Low-cost protection for existing position.' },
  { term: 'Butterfly Spread', category: 'strategies', shortDef: 'Three-strike options strategy', fullExplanation: 'Buy 1 low strike, sell 2 middle strikes, buy 1 high strike. Max profit at middle strike at expiration.', whyUseful: 'Low cost, high reward if price pins.' },
  
  // ===== MORE RISK MANAGEMENT =====
  { term: 'Trailing Stop', category: 'risk', shortDef: 'Stop that follows price', fullExplanation: 'Trailing stop moves with price—locks in profits as position moves favorably. Fixed amount or percentage.', whyUseful: 'Let winners run while protecting profits.', relatedTerms: ['Stop Loss', 'Parabolic SAR'] },
  { term: 'Expected Value', category: 'risk', shortDef: 'Average profit per trade over time', fullExplanation: 'Expected value = (Win Rate × Avg Win) - (Loss Rate × Avg Loss). Positive EV = profitable system.', whyUseful: 'Determine if strategy is profitable long-term.', formula: 'EV = (P(win) × Avg Win) - (P(loss) × Avg Loss)' },
  { term: 'Max Drawdown', category: 'risk', shortDef: 'Largest peak-to-trough decline', fullExplanation: 'Maximum drawdown is the largest percentage drop from peak equity before new high. Critical risk metric.', whyUseful: 'Understand worst-case scenario.', formula: 'MDD = (Peak - Trough) / Peak × 100%', relatedTerms: ['Recovery Factor'] },
  { term: 'VaR', category: 'risk', shortDef: 'Value at Risk', fullExplanation: 'VaR estimates maximum loss at given confidence level. "95% VaR of $10K" means 95% chance loss won\'t exceed $10K.', whyUseful: 'Quantify potential losses.', xfactorUsage: 'XFactor calculates real-time VaR in Risk Management panel.' },
  { term: 'Alpha', category: 'risk', shortDef: 'Excess return over benchmark', fullExplanation: 'Alpha is return above what beta predicts. Positive alpha = outperformance; negative = underperformance.', whyUseful: 'Measure skill vs luck in returns.', formula: 'α = Actual Return - (β × Market Return)' },
  { term: 'Correlation', category: 'risk', shortDef: 'How assets move together', fullExplanation: 'Correlation ranges -1 to +1. +1 = move together; -1 = move opposite; 0 = no relationship.', whyUseful: 'Build diversified portfolios.', relatedTerms: ['Diversification', 'Pairs Trading'] },
  { term: 'Diversification', category: 'risk', shortDef: 'Spreading risk across investments', fullExplanation: 'Diversification reduces risk by holding uncorrelated assets. "Don\'t put all eggs in one basket."', whyUseful: 'Reduces portfolio volatility without sacrificing return.', relatedTerms: ['Correlation', 'Portfolio'] },
  { term: 'Hedge', category: 'risk', shortDef: 'Position to offset risk', fullExplanation: 'A hedge is an investment made to reduce risk of adverse price movements. E.g., buying puts to protect long stock.', whyUseful: 'Protect gains, reduce risk.', relatedTerms: ['Put Option', 'Protective Put'] },
  { term: 'Kill Switch', category: 'risk', shortDef: 'Emergency trading stop', fullExplanation: 'Kill switch immediately stops all trading activity. Used when something goes wrong.', whyUseful: 'Last line of defense against catastrophic losses.', xfactorUsage: 'XFactor\'s Kill Switch stops all bots and cancels pending orders.' },
  { term: 'Kelly Criterion', category: 'risk', shortDef: 'Optimal bet sizing formula', fullExplanation: 'Kelly Criterion calculates optimal position size based on win rate and payoff ratio. Often use half-Kelly for safety.', whyUseful: 'Mathematically optimal growth.', formula: 'Kelly % = W - (1-W)/R, where W = win rate, R = win/loss ratio', whyNotUseful: 'Full Kelly is volatile; use half-Kelly.' },
  { term: 'Win Rate', category: 'risk', shortDef: 'Percentage of winning trades', fullExplanation: 'Win rate is winning trades divided by total trades. Not meaningful alone—must consider risk/reward.', whyUseful: 'Part of expectancy calculation.', formula: 'Win Rate = Winning Trades / Total Trades' },
  { term: 'Profit Factor', category: 'risk', shortDef: 'Gross profits divided by gross losses', fullExplanation: 'Profit factor = total winning / total losing. >1 is profitable; >2 is very good.', whyUseful: 'Simple profitability measure.', formula: 'Profit Factor = Gross Profit / Gross Loss' },
  { term: 'Recovery Factor', category: 'risk', shortDef: 'Net profit divided by max drawdown', fullExplanation: 'Recovery factor measures how well system recovers from drawdowns. Higher is better.', whyUseful: 'Compare risk-adjusted performance.', formula: 'Recovery Factor = Net Profit / Max Drawdown' },
  { term: 'Calmar Ratio', category: 'risk', shortDef: 'Annual return over max drawdown', fullExplanation: 'Calmar Ratio = CAGR / Max Drawdown. Higher is better. Focuses on downside risk.', whyUseful: 'Compare strategies with different drawdown profiles.', formula: 'Calmar = CAGR / Max Drawdown' },
  
  // ===== MORE FUNDAMENTALS =====
  { term: 'EPS', category: 'fundamentals', shortDef: 'Earnings Per Share', fullExplanation: 'EPS is net income divided by shares outstanding. Higher EPS = more profitable. Watch quarterly growth.', whyUseful: 'Fundamental measure of profitability.', formula: 'EPS = Net Income / Shares Outstanding', xfactorUsage: 'XFactor displays EPS history and estimates in Stock Analyzer.' },
  { term: 'P/E Ratio', category: 'fundamentals', shortDef: 'Price to Earnings Ratio', fullExplanation: 'P/E = Stock Price / EPS. Higher P/E = investors expect growth. Compare to industry average.', whyUseful: 'Basic valuation metric.', formula: 'P/E = Price / EPS', xfactorUsage: 'XFactor shows P/E in fundamental metrics.' },
  { term: 'P/B Ratio', category: 'fundamentals', shortDef: 'Price to Book Ratio', fullExplanation: 'P/B = Stock Price / Book Value Per Share. Lower = potentially undervalued. Banks typically low P/B.', whyUseful: 'Value investing metric.', formula: 'P/B = Price / (Total Assets - Liabilities) / Shares' },
  { term: 'P/S Ratio', category: 'fundamentals', shortDef: 'Price to Sales Ratio', fullExplanation: 'P/S = Market Cap / Revenue. Useful for unprofitable companies. Lower is generally better.', whyUseful: 'Value companies without earnings.', formula: 'P/S = Market Cap / Revenue' },
  { term: 'ROE', category: 'fundamentals', shortDef: 'Return on Equity', fullExplanation: 'ROE = Net Income / Shareholder Equity. Measures how efficiently company uses equity. >15% is good.', whyUseful: 'Measure management efficiency.', formula: 'ROE = Net Income / Shareholders Equity' },
  { term: 'ROA', category: 'fundamentals', shortDef: 'Return on Assets', fullExplanation: 'ROA = Net Income / Total Assets. Shows how efficiently company uses assets. Compare within industry.', whyUseful: 'Measure asset efficiency.', formula: 'ROA = Net Income / Total Assets' },
  { term: 'ROIC', category: 'fundamentals', shortDef: 'Return on Invested Capital', fullExplanation: 'ROIC measures return generated on all invested capital (debt + equity). >WACC creates value.', whyUseful: 'Best measure of capital efficiency.', formula: 'ROIC = NOPAT / Invested Capital' },
  { term: 'Gross Margin', category: 'fundamentals', shortDef: 'Gross profit as percentage of revenue', fullExplanation: 'Gross margin = (Revenue - COGS) / Revenue. Higher = more room for operating expenses.', whyUseful: 'Measure production efficiency.', formula: 'Gross Margin = (Revenue - COGS) / Revenue' },
  { term: 'Operating Margin', category: 'fundamentals', shortDef: 'Operating income as percentage of revenue', fullExplanation: 'Operating margin = Operating Income / Revenue. Shows operational efficiency before interest and taxes.', whyUseful: 'Compare operational efficiency.', formula: 'Operating Margin = EBIT / Revenue' },
  { term: 'Revenue Growth', category: 'fundamentals', shortDef: 'Year-over-year sales increase', fullExplanation: 'Revenue growth measures how fast sales are growing. High growth commands higher valuations.', whyUseful: 'Key growth metric.', formula: 'Revenue Growth = (Current - Prior) / Prior × 100%' },
  { term: 'Free Cash Flow', category: 'fundamentals', shortDef: 'Cash available after capex', fullExplanation: 'FCF = Operating Cash Flow - Capital Expenditures. Cash available for dividends, buybacks, debt repayment.', whyUseful: 'Real cash generation ability.', formula: 'FCF = Operating CF - CapEx' },
  { term: 'Debt to Equity', category: 'fundamentals', shortDef: 'Total debt divided by equity', fullExplanation: 'D/E ratio measures financial leverage. Higher = more debt = more risk. Industry dependent.', whyUseful: 'Assess financial risk.', formula: 'D/E = Total Debt / Shareholders Equity' },
  { term: 'Current Ratio', category: 'fundamentals', shortDef: 'Current assets to current liabilities', fullExplanation: 'Current ratio measures short-term liquidity. >1 means can cover short-term obligations.', whyUseful: 'Assess short-term financial health.', formula: 'Current Ratio = Current Assets / Current Liabilities' },
  { term: 'Quick Ratio', category: 'fundamentals', shortDef: 'Liquid assets to current liabilities', fullExplanation: 'Quick ratio excludes inventory from current assets. More conservative liquidity measure.', whyUseful: 'Assess immediate liquidity.', formula: 'Quick Ratio = (Current Assets - Inventory) / Current Liabilities' },
  { term: 'Payout Ratio', category: 'fundamentals', shortDef: 'Dividends as percentage of earnings', fullExplanation: 'Payout ratio = Dividends / Net Income. High ratio may be unsustainable; low leaves room for growth.', whyUseful: 'Assess dividend sustainability.', formula: 'Payout = Dividends / Net Income' },
  { term: 'Book Value', category: 'fundamentals', shortDef: 'Net asset value per share', fullExplanation: 'Book value = (Total Assets - Total Liabilities) / Shares. What would be left if company liquidated.', whyUseful: 'Floor value for stock.', formula: 'Book Value = (Assets - Liabilities) / Shares' },
  { term: 'Intrinsic Value', category: 'fundamentals', shortDef: 'Calculated true worth of stock', fullExplanation: 'Intrinsic value is estimated fair value based on fundamentals, often using DCF analysis.', whyUseful: 'Buy below intrinsic value for margin of safety.', relatedTerms: ['DCF', 'Margin of Safety'] },
  { term: 'DCF', category: 'fundamentals', shortDef: 'Discounted Cash Flow analysis', fullExplanation: 'DCF values company by projecting future cash flows and discounting to present value.', whyUseful: 'Fundamental valuation method.', formula: 'DCF = Σ(FCF / (1 + r)^n) + Terminal Value' },
  { term: 'EBITDA', category: 'fundamentals', shortDef: 'Earnings before interest, taxes, depreciation, amortization', fullExplanation: 'EBITDA is operating profitability before non-operating items. Used in valuation multiples.', whyUseful: 'Compare profitability across companies.', formula: 'EBITDA = Revenue - COGS - Operating Expenses' },
  { term: 'Enterprise Value', category: 'fundamentals', shortDef: 'Total company value including debt', fullExplanation: 'EV = Market Cap + Debt - Cash. Total cost to acquire company.', whyUseful: 'Better valuation metric than market cap alone.', formula: 'EV = Market Cap + Total Debt - Cash' },
  { term: 'EV/EBITDA', category: 'fundamentals', shortDef: 'Enterprise Value to EBITDA multiple', fullExplanation: 'EV/EBITDA is valuation multiple. Lower = potentially cheaper. Compare within industry.', whyUseful: 'Compare valuations across capital structures.', formula: 'EV/EBITDA = Enterprise Value / EBITDA' },
  { term: 'Forward P/E', category: 'fundamentals', shortDef: 'P/E using future earnings estimates', fullExplanation: 'Forward P/E uses next 12 months earnings estimates. Reflects expected growth.', whyUseful: 'More relevant for growth stocks.', formula: 'Forward P/E = Price / Expected EPS' },
  { term: 'Earnings Surprise', category: 'fundamentals', shortDef: 'Actual vs expected earnings difference', fullExplanation: 'Positive surprise when actual EPS beats estimates. Often leads to price reaction.', whyUseful: 'Trade post-earnings drift.', formula: 'Surprise = (Actual EPS - Expected EPS) / |Expected EPS|', xfactorUsage: 'XFactor tracks earnings surprise in Stock Analyzer.' },
  { term: 'Guidance', category: 'fundamentals', shortDef: 'Company\'s future earnings forecast', fullExplanation: 'Management guidance projects future revenue and earnings. Raising/lowering guidance impacts stock.', whyUseful: 'Understand company\'s own expectations.' },
  { term: 'Analyst Rating', category: 'fundamentals', shortDef: 'Buy/hold/sell recommendations', fullExplanation: 'Wall Street analysts rate stocks Buy, Hold, Sell with price targets. Consensus matters.', whyUseful: 'Understand institutional sentiment.', xfactorUsage: 'XFactor displays analyst ratings and price targets.' },
  { term: 'Price Target', category: 'fundamentals', shortDef: 'Analyst projected price', fullExplanation: 'Analysts project where stock price should trade in 12-18 months based on their models.', whyUseful: 'Gauge upside/downside potential.', xfactorUsage: 'XFactor shows consensus and individual price targets.' },
  { term: 'Institutional Ownership', category: 'fundamentals', shortDef: 'Percentage owned by institutions', fullExplanation: 'Mutual funds, pension funds, hedge funds ownership. High = stability; changes indicate sentiment.', whyUseful: 'Track smart money positioning.' },
  { term: '13F Filing', category: 'fundamentals', shortDef: 'Quarterly institutional holdings report', fullExplanation: 'Institutions with >$100M must file quarterly holdings. Shows hedge fund positions with 45-day delay.', whyUseful: 'Follow famous investors.', whyNotUseful: 'Delayed, may already have sold.' },
  
  // ===== MORE PATTERNS =====
  { term: 'Trend Line', category: 'patterns', shortDef: 'Line connecting swing highs or lows', fullExplanation: 'Trend lines connect higher lows (uptrend) or lower highs (downtrend). Break signals potential reversal.', whyUseful: 'Visual trend definition and trading opportunities.', relatedTerms: ['Support', 'Resistance'] },
  { term: 'Channel', category: 'patterns', shortDef: 'Parallel trend lines', fullExplanation: 'Channel is two parallel trend lines containing price. Trade bounces within, watch for breakout.', whyUseful: 'Range trading and breakout setups.', relatedTerms: ['Trend Line', 'Range'] },
  { term: 'Head and Shoulders', category: 'patterns', shortDef: 'Reversal pattern with three peaks', fullExplanation: 'H&S has left shoulder, higher head, right shoulder. Neckline break confirms reversal. Target = head to neckline distance.', whyUseful: 'Classic reversal pattern.', relatedTerms: ['Inverse H&S', 'Neckline'], diagram: 'head-shoulders', imageUrl: 'https://www.investopedia.com/thmb/BdGkdHW2e7l3hDJpJxDqJJCvJDk=/750x0/filters:no_upscale():max_bytes(150000):strip_icc():format(webp)/head-and-shoulders-pattern.asp-final-5c3c0d5546e0fb0001e8d91a.png', imageCaption: 'Head and Shoulders pattern showing left shoulder, head, right shoulder, and neckline with price target.', imageCredit: 'Investopedia' },
  { term: 'Inverse Head and Shoulders', category: 'patterns', shortDef: 'Bullish reversal pattern', fullExplanation: 'Opposite of H&S at market bottoms. Three troughs with lower middle. Neckline break is buy signal.', whyUseful: 'Identify major bottoms.', relatedTerms: ['Head and Shoulders'] },
  { term: 'Double Top', category: 'patterns', shortDef: 'Bearish reversal pattern', fullExplanation: 'Two peaks at similar level forming "M" shape. Break below middle trough confirms reversal.', whyUseful: 'Identify trend reversals.', relatedTerms: ['Double Bottom', 'Resistance'], diagram: 'double-top', imageUrl: 'https://www.investopedia.com/thmb/aSE0HqYX1mDQKGxhv_vO9XqWsKc=/750x0/filters:no_upscale():max_bytes(150000):strip_icc():format(webp)/dotdash_Final_Double_Top_Pattern_Sep_2020-01-f3a2d8f2e7b94f35a1c0b9a8e5c8d8d8.jpg', imageCaption: 'Double Top "M" pattern showing two resistance peaks and the neckline breakdown.', imageCredit: 'Investopedia' },
  { term: 'Double Bottom', category: 'patterns', shortDef: 'Bullish reversal pattern', fullExplanation: 'Two troughs at similar level forming "W" shape. Break above middle peak confirms reversal.', whyUseful: 'Identify major bottoms.', relatedTerms: ['Double Top', 'Support'], diagram: 'double-bottom' },
  { term: 'Triple Top', category: 'patterns', shortDef: 'Three peaks at resistance', fullExplanation: 'Three unsuccessful attempts to break resistance. Stronger reversal signal than double top.', whyUseful: 'Strong reversal pattern.', relatedTerms: ['Triple Bottom', 'Resistance'] },
  { term: 'Triple Bottom', category: 'patterns', shortDef: 'Three troughs at support', fullExplanation: 'Three successful defenses of support. Break above peaks is strong buy signal.', whyUseful: 'Reliable bottom pattern.', relatedTerms: ['Triple Top', 'Support'] },
  { term: 'Cup and Handle', category: 'patterns', shortDef: 'Bullish continuation pattern', fullExplanation: 'Rounded bottom (cup) followed by small pullback (handle). Breakout above handle is buy signal.', whyUseful: 'William O\'Neil\'s favorite pattern.', relatedTerms: ['Breakout', 'CANSLIM'] },
  { term: 'Flag', category: 'patterns', shortDef: 'Short consolidation in trend', fullExplanation: 'Flag is rectangular consolidation against trend. Bull flag slopes down; bear flag slopes up. Continuation pattern.', whyUseful: 'High probability continuation trades.', relatedTerms: ['Pennant', 'Continuation'] },
  { term: 'Pennant', category: 'patterns', shortDef: 'Triangular consolidation in trend', fullExplanation: 'Pennant is small symmetrical triangle after sharp move. Breakout continues prior trend.', whyUseful: 'Quick continuation setups.', relatedTerms: ['Flag', 'Triangle'] },
  { term: 'Triangle', category: 'patterns', shortDef: 'Converging trend lines', fullExplanation: 'Ascending (flat top, rising bottom), Descending (flat bottom, falling top), or Symmetrical. Breakout signals direction.', whyUseful: 'Predict breakout direction.', relatedTerms: ['Wedge', 'Pennant'] },
  { term: 'Wedge', category: 'patterns', shortDef: 'Converging lines both sloping same direction', fullExplanation: 'Rising wedge is bearish; falling wedge is bullish. Both lines slope same direction unlike triangle.', whyUseful: 'Reliable reversal patterns.', relatedTerms: ['Triangle', 'Reversal'] },
  { term: 'Rectangle', category: 'patterns', shortDef: 'Horizontal consolidation', fullExplanation: 'Price bounces between horizontal support and resistance. Breakout in trend direction usually.', whyUseful: 'Clear support/resistance levels.', relatedTerms: ['Range', 'Consolidation'] },
  { term: 'Rounding Bottom', category: 'patterns', shortDef: 'Slow, curved reversal', fullExplanation: 'Gradual U-shaped bottom over weeks/months. Indicates slow sentiment shift from bearish to bullish.', whyUseful: 'Major trend reversal.', relatedTerms: ['Cup and Handle'] },
  { term: 'Doji', category: 'patterns', shortDef: 'Candlestick with same open/close', fullExplanation: 'Doji shows indecision—open equals close. At top = potential reversal; at bottom = potential bounce.', whyUseful: 'Signal potential reversals.', relatedTerms: ['Candlestick', 'Hammer'], diagram: 'candlestick' },
  { term: 'Hammer', category: 'patterns', shortDef: 'Bullish reversal candlestick', fullExplanation: 'Small body at top, long lower shadow. Shows buyers rejected lower prices. Bullish after downtrend.', whyUseful: 'Single-candle reversal signal.', relatedTerms: ['Shooting Star', 'Doji'], diagram: 'candlestick' },
  { term: 'Shooting Star', category: 'patterns', shortDef: 'Bearish reversal candlestick', fullExplanation: 'Small body at bottom, long upper shadow. Shows sellers rejected higher prices. Bearish after uptrend.', whyUseful: 'Single-candle reversal signal.', relatedTerms: ['Hammer', 'Doji'] },
  { term: 'Engulfing', category: 'patterns', shortDef: 'Candle engulfing prior candle', fullExplanation: 'Bullish engulfing: green candle fully covers prior red. Bearish engulfing: red covers prior green.', whyUseful: 'Strong reversal pattern.', relatedTerms: ['Hammer', 'Morning Star'] },
  { term: 'Morning Star', category: 'patterns', shortDef: 'Three-candle bullish reversal', fullExplanation: 'Large red, small body (star), large green. Shows reversal from selling to buying.', whyUseful: 'Reliable bottom pattern.', relatedTerms: ['Evening Star'] },
  { term: 'Evening Star', category: 'patterns', shortDef: 'Three-candle bearish reversal', fullExplanation: 'Large green, small body (star), large red. Shows reversal from buying to selling.', whyUseful: 'Reliable top pattern.', relatedTerms: ['Morning Star'] },
  { term: 'Three White Soldiers', category: 'patterns', shortDef: 'Three bullish candles in a row', fullExplanation: 'Three consecutive long green candles, each closing higher. Strong bullish continuation signal.', whyUseful: 'Confirms trend strength.', relatedTerms: ['Three Black Crows'] },
  { term: 'Three Black Crows', category: 'patterns', shortDef: 'Three bearish candles in a row', fullExplanation: 'Three consecutive long red candles, each closing lower. Strong bearish continuation signal.', whyUseful: 'Confirms downtrend strength.', relatedTerms: ['Three White Soldiers'] },
  { term: 'Harami', category: 'patterns', shortDef: 'Small candle inside prior candle', fullExplanation: 'Second candle contained within first. Bullish harami in downtrend; bearish harami in uptrend.', whyUseful: 'Potential reversal signal.', relatedTerms: ['Inside Bar', 'Engulfing'] },
  { term: 'Inside Bar', category: 'patterns', shortDef: 'Bar within prior bar\'s range', fullExplanation: 'High and low contained within prior bar. Breakout of range is trade signal.', whyUseful: 'Low-risk breakout setups.', relatedTerms: ['Harami', 'Consolidation'] },
  { term: 'Outside Bar', category: 'patterns', shortDef: 'Bar engulfing prior bar\'s range', fullExplanation: 'Higher high AND lower low than prior bar. Shows expansion of range and volatility.', whyUseful: 'Signals volatility expansion.', relatedTerms: ['Engulfing', 'Expansion'] },
  { term: 'Pin Bar', category: 'patterns', shortDef: 'Long wick showing rejection', fullExplanation: 'Candle with long wick (shadow) showing price rejection. Bullish pin has long lower wick; bearish has long upper.', whyUseful: 'Clear rejection levels.', relatedTerms: ['Hammer', 'Shooting Star'] },
  { term: 'Consolidation', category: 'patterns', shortDef: 'Tight range after move', fullExplanation: 'Period of tight price action after move, building energy for next move. Lower volume during consolidation.', whyUseful: 'Precedes breakouts.', relatedTerms: ['Squeeze', 'Flag'] },
  { term: 'Squeeze', category: 'patterns', shortDef: 'Bollinger Bands inside Keltner Channels', fullExplanation: 'When Bollinger Bands contract inside Keltner Channels, indicating low volatility before expansion.', whyUseful: 'Anticipate volatility breakouts.', relatedTerms: ['Bollinger Bands', 'Keltner Channel'], xfactorUsage: 'XFactor includes breakout_squeeze strategy.' },
  { term: 'Climax', category: 'patterns', shortDef: 'Exhaustion at top or bottom', fullExplanation: 'Buying/selling climax shows exhaustion with high volume and wide range. Often marks turning points.', whyUseful: 'Identify potential reversals.', relatedTerms: ['Exhaustion', 'Volume'] },
  { term: 'Higher High', category: 'patterns', shortDef: 'Peak above prior peak', fullExplanation: 'New high surpassing previous high. Series of higher highs defines uptrend.', whyUseful: 'Confirm uptrend.', relatedTerms: ['Higher Low', 'Trend'] },
  { term: 'Higher Low', category: 'patterns', shortDef: 'Trough above prior trough', fullExplanation: 'Pullback stopping above previous low. Higher lows + higher highs = uptrend.', whyUseful: 'Confirm trend strength.', relatedTerms: ['Higher High', 'Trend'] },
  { term: 'Lower High', category: 'patterns', shortDef: 'Peak below prior peak', fullExplanation: 'Rally failing to reach previous high. Series of lower highs defines downtrend.', whyUseful: 'Confirm downtrend.', relatedTerms: ['Lower Low', 'Trend'] },
  { term: 'Lower Low', category: 'patterns', shortDef: 'Trough below prior trough', fullExplanation: 'New low breaking previous low. Lower lows + lower highs = downtrend.', whyUseful: 'Confirm downtrend.', relatedTerms: ['Lower High', 'Trend'] },
  
  // ===== MORE ADVANCED TERMS =====
  { term: 'Theta', category: 'strategies', shortDef: 'Options time decay', fullExplanation: 'Theta measures how much an option loses value each day due to time decay. Positive for sellers, negative for buyers.', whyUseful: 'Theta sellers profit from time passage.', formula: 'Θ = -∂V/∂t', relatedTerms: ['Greeks', 'Time Decay'] },
  { term: 'Gamma', category: 'strategies', shortDef: 'Rate of delta change', fullExplanation: 'Gamma measures how fast delta changes as stock price moves. Highest for at-the-money options near expiration.', whyUseful: 'Understand option acceleration.', formula: 'Γ = ∂Δ/∂S', relatedTerms: ['Delta', 'Greeks'] },
  { term: 'Vega', category: 'strategies', shortDef: 'Sensitivity to volatility', fullExplanation: 'Vega measures option price change for 1% change in implied volatility. Long options benefit from rising IV.', whyUseful: 'Trade volatility expectations.', formula: 'ν = ∂V/∂σ', relatedTerms: ['Implied Volatility', 'Greeks'] },
  { term: 'Implied Volatility', category: 'indicators', shortDef: 'Market\'s expected future volatility', fullExplanation: 'IV is volatility implied by option prices. High IV = expensive options. IV Rank and IV Percentile help assess levels.', whyUseful: 'Sell options when IV is high, buy when low.', relatedTerms: ['VIX', 'Vega'] },
  { term: 'VIX', category: 'indicators', shortDef: 'CBOE Volatility Index - "Fear Gauge"', fullExplanation: 'VIX measures expected S&P 500 volatility. >20 is elevated fear; <15 is complacent. Spikes during selloffs.', whyUseful: 'Gauge market fear and time entries.', xfactorUsage: 'XFactor uses VIX for circuit breakers.' },
  { term: 'IV Crush', category: 'strategies', shortDef: 'Volatility drop after event', fullExplanation: 'IV often spikes before earnings then drops sharply after. Options can lose value even with correct direction.', whyUseful: 'Avoid buying options before earnings.', relatedTerms: ['Implied Volatility', 'Earnings Play'] },
  { term: 'Skew', category: 'indicators', shortDef: 'Difference in IV across strikes', fullExplanation: 'Put skew shows higher IV for puts vs calls (fear of downside). Call skew shows higher IV for calls.', whyUseful: 'Understand market sentiment.', relatedTerms: ['Implied Volatility'] },
  { term: 'Term Structure', category: 'indicators', shortDef: 'IV across different expirations', fullExplanation: 'Usually IV increases with time (contango). Before events, near-term IV can exceed far-term (backwardation).', whyUseful: 'Choose optimal expiration.', relatedTerms: ['Contango', 'Backwardation'] },
  { term: 'Contango', category: 'basics', shortDef: 'Futures higher than spot', fullExplanation: 'When futures prices are higher than spot. Common in commodities due to storage costs. Creates drag in futures ETFs.', whyUseful: 'Understand ETF decay.', relatedTerms: ['Backwardation', 'VXX'] },
  { term: 'Backwardation', category: 'basics', shortDef: 'Futures lower than spot', fullExplanation: 'When futures prices are lower than spot. Indicates supply tightness or high demand now.', whyUseful: 'Bullish for commodity.', relatedTerms: ['Contango'] },
  { term: 'Open Interest', category: 'basics', shortDef: 'Outstanding option/futures contracts', fullExplanation: 'Open interest is total contracts not yet closed. High OI at strike = potential magnet. Changes show new money.', whyUseful: 'Identify key levels and liquidity.', relatedTerms: ['Volume', 'Max Pain'] },
  { term: 'Max Pain', category: 'strategies', shortDef: 'Strike where most options expire worthless', fullExplanation: 'Max pain is price where option holders have maximum losses. Theory: market makers push price to max pain.', whyUseful: 'Potential expiration target.', relatedTerms: ['Open Interest', 'Expiration'] },
  { term: 'Pin Risk', category: 'risk', shortDef: 'Uncertainty at expiration near strike', fullExplanation: 'When stock closes exactly at strike on expiration, uncertainty about assignment creates risk.', whyUseful: 'Manage positions near strikes on expiration.' },
  { term: 'Assignment', category: 'basics', shortDef: 'Obligation to buy/sell from option exercise', fullExplanation: 'Option sellers can be assigned when buyer exercises. American options can be assigned any time.', whyUseful: 'Understand option obligations.', relatedTerms: ['Exercise', 'Expiration'] },
  { term: 'Exercise', category: 'basics', shortDef: 'Executing option\'s right to buy/sell', fullExplanation: 'Buyer can exercise option to buy (call) or sell (put) shares at strike price.', whyUseful: 'Rare - usually close option instead.', relatedTerms: ['Assignment'] },
  { term: 'In-the-Money', category: 'basics', shortDef: 'Option with intrinsic value', fullExplanation: 'Call is ITM when stock > strike. Put is ITM when stock < strike. Has intrinsic value.', whyUseful: 'Higher delta, moves more with stock.', relatedTerms: ['Out-of-the-Money', 'At-the-Money'] },
  { term: 'Out-of-the-Money', category: 'basics', shortDef: 'Option with no intrinsic value', fullExplanation: 'Call is OTM when stock < strike. Put is OTM when stock > strike. All time value.', whyUseful: 'Cheaper, higher leverage, lower probability.', relatedTerms: ['In-the-Money', 'At-the-Money'] },
  { term: 'At-the-Money', category: 'basics', shortDef: 'Option at current stock price', fullExplanation: 'Strike equals current stock price. Maximum time value and gamma.', whyUseful: 'Highest theta decay.', relatedTerms: ['In-the-Money', 'Out-of-the-Money'] },
  { term: 'Intrinsic Value (Options)', category: 'basics', shortDef: 'Real value of ITM option', fullExplanation: 'Intrinsic value = how much option is in-the-money. Call: Stock - Strike. Put: Strike - Stock.', whyUseful: 'Floor value of option.', formula: 'Call IV = Max(0, Stock - Strike)' },
  { term: 'Time Value', category: 'basics', shortDef: 'Premium above intrinsic value', fullExplanation: 'Time value = Option Price - Intrinsic Value. Represents probability and time remaining.', whyUseful: 'What you pay for possibility.', formula: 'Time Value = Premium - Intrinsic Value' },
  { term: 'Roll', category: 'strategies', shortDef: 'Close and reopen option position', fullExplanation: 'Rolling closes current option and opens new one at different strike and/or expiration.', whyUseful: 'Manage losing trades, extend duration.' },
  { term: 'Wash Sale', category: 'regulations', shortDef: 'Buying back same security within 30 days', fullExplanation: 'IRS Section 1091: If you sell at a loss and repurchase the same or substantially identical security within 30 days before or after, the loss is disallowed for tax purposes. The disallowed loss is added to your new cost basis.', whyUseful: 'Critical for tax planning and loss harvesting.', relatedTerms: ['Tax Loss Harvesting', 'Capital Gains'], example: 'Dec 15: Sell 100 AAPL at $5,000 loss. Jan 10 (26 days later): Buy 100 AAPL. The $5,000 loss is disallowed but added to new cost basis.' },
  { term: 'Tax Loss Harvesting', category: 'strategies', shortDef: 'Selling losers to offset gains', fullExplanation: 'Sell losing positions to realize losses that offset capital gains. Mind wash sale rules.', whyUseful: 'Reduce tax bill.', relatedTerms: ['Wash Sale', 'Capital Gains'] },
  { term: 'Capital Gains', category: 'basics', shortDef: 'Profit from selling investments', fullExplanation: 'Short-term gains (<1 year) taxed as income. Long-term gains (>1 year) taxed at lower rate.', whyUseful: 'Hold over 1 year for tax benefit.' },
  { term: 'Cost Basis', category: 'basics', shortDef: 'Original value for tax purposes', fullExplanation: 'Cost basis is what you paid including fees. Determines capital gain/loss when sold.', whyUseful: 'Track for tax reporting.' },
  { term: 'FIFO', category: 'basics', shortDef: 'First In First Out', fullExplanation: 'Default tax accounting method: oldest shares sold first. Can choose specific lot ID for better tax result.', whyUseful: 'Optimize tax consequences.' },
  { term: 'Lot', category: 'basics', shortDef: 'Group of shares bought together', fullExplanation: 'A tax lot is shares purchased at same time/price. Each lot has its own cost basis and holding period.', whyUseful: 'Track for tax optimization.' },
  { term: 'Paper Trading', category: 'strategies', shortDef: 'Simulated trading without real money', fullExplanation: 'Paper trading practices strategies with fake money. Good for learning and testing.', whyUseful: 'Learn without risk.', whyNotUseful: 'No emotional pressure - doesn\'t replicate real trading psychology.', xfactorUsage: 'XFactor offers Demo mode for paper trading.' },
  { term: 'Backtesting', category: 'strategies', shortDef: 'Testing strategy on historical data', fullExplanation: 'Backtesting applies trading rules to past data to see how strategy would have performed.', whyUseful: 'Validate strategy before risking capital.', whyNotUseful: 'Past performance doesn\'t guarantee future results. Overfitting risk.' },
  { term: 'Forward Testing', category: 'strategies', shortDef: 'Testing strategy in real-time', fullExplanation: 'Forward testing (paper trading) runs strategy on live data without real money.', whyUseful: 'More realistic than backtesting.' },
  { term: 'Walk Forward', category: 'strategies', shortDef: 'Rolling backtest optimization', fullExplanation: 'Walk forward optimizes on past data, tests on next period, then rolls forward. Reduces overfitting.', whyUseful: 'More robust than single backtest.' },
  { term: 'Curve Fitting', category: 'risk', shortDef: 'Over-optimizing to past data', fullExplanation: 'Curve fitting creates rules that work perfectly on historical data but fail on new data.', whyUseful: 'Recognize and avoid overfitting.', relatedTerms: ['Overfitting', 'Backtesting'] },
  { term: 'Overfitting', category: 'risk', shortDef: 'Too many parameters for data', fullExplanation: 'Overfitting makes strategy too specific to historical data. Simpler strategies often more robust.', whyUseful: 'Keep strategies simple.', relatedTerms: ['Curve Fitting'] },
  { term: 'Robustness', category: 'risk', shortDef: 'Strategy works across conditions', fullExplanation: 'Robust strategies perform well across different time periods, markets, and conditions.', whyUseful: 'Seek robust over optimal.', relatedTerms: ['Walk Forward'] },
  { term: 'Regime', category: 'strategies', shortDef: 'Market phase or condition', fullExplanation: 'Market regimes: trending, ranging, volatile, calm. Different strategies work in different regimes.', whyUseful: 'Adapt strategy to current regime.', xfactorUsage: 'XFactor detects market regime in Forecasting panel.' },
  { term: 'Whipsaw', category: 'risk', shortDef: 'False signal causing loss', fullExplanation: 'Whipsaw happens when trade triggers then immediately reverses, causing loss. Common in choppy markets.', whyUseful: 'Recognize to avoid or use filters.', relatedTerms: ['False Breakout', 'Choppy'] },
  { term: 'False Breakout', category: 'patterns', shortDef: 'Breakout that fails and reverses', fullExplanation: 'Price breaks key level but quickly reverses back. Use volume confirmation to filter.', whyUseful: 'Fade false breakouts for profit.', relatedTerms: ['Breakout', 'Whipsaw'] },
  { term: 'Fakeout', category: 'patterns', shortDef: 'Same as false breakout', fullExplanation: 'Price briefly moves through level to trap traders then reverses. Common around round numbers.', whyUseful: 'Wait for confirmation.', relatedTerms: ['False Breakout'] },
  { term: 'Stop Hunt', category: 'patterns', shortDef: 'Move to trigger stops before reversing', fullExplanation: 'Price moves to obvious stop levels to trigger orders then reverses. Put stops in non-obvious places.', whyUseful: 'Don\'t put stops at obvious levels.', relatedTerms: ['Stop Loss'] },
  { term: 'Accumulation', category: 'patterns', shortDef: 'Smart money quietly buying', fullExplanation: 'Accumulation is when institutions buy large positions over time without moving price much. Precedes rally.', whyUseful: 'Spot early before breakout.', relatedTerms: ['Distribution', 'OBV'] },
  { term: 'Distribution', category: 'patterns', shortDef: 'Smart money quietly selling', fullExplanation: 'Distribution is when institutions sell into strength over time. Precedes decline.', whyUseful: 'Spot early before breakdown.', relatedTerms: ['Accumulation'] },
  { term: 'Smart Money', category: 'basics', shortDef: 'Institutional and informed traders', fullExplanation: 'Smart money refers to professional traders, hedge funds, institutions with information and resources.', whyUseful: 'Follow their footprints.', relatedTerms: ['Institutional', 'COT'] },
  { term: 'Dumb Money', category: 'basics', shortDef: 'Retail and uninformed traders', fullExplanation: 'Dumb money often buys tops and sells bottoms. Contrarian indicator when extreme.', whyUseful: 'Fade extreme retail sentiment.' },
  { term: 'COT Report', category: 'fundamentals', shortDef: 'Commitment of Traders report', fullExplanation: 'Weekly CFTC report showing futures positioning by commercials, large specs, and small specs.', whyUseful: 'Gauge institutional positioning.' },
  { term: 'Seasonality', category: 'strategies', shortDef: 'Recurring patterns by time of year', fullExplanation: '"Sell in May", Santa Rally, January Effect - historical patterns based on calendar.', whyUseful: 'Trade with historical tendencies.', whyNotUseful: 'Not reliable every year.' },
  { term: 'Santa Rally', category: 'patterns', shortDef: 'Year-end market rise', fullExplanation: 'Tendency for stocks to rise last 5 trading days of year through first 2 of January.', whyUseful: 'Historical bullish tendency.', relatedTerms: ['Seasonality'] },
  { term: 'January Effect', category: 'patterns', shortDef: 'Small caps outperform in January', fullExplanation: 'Historical tendency for small cap stocks to outperform large caps in January.', whyUseful: 'Sector rotation opportunity.', relatedTerms: ['Seasonality'] },
  { term: 'Triple Witching', category: 'basics', shortDef: 'Quarterly expiration of options and futures', fullExplanation: 'Third Friday of March, June, September, December when stock options, index options, and futures expire.', whyUseful: 'Often volatile - adjust position sizes.', relatedTerms: ['Expiration', 'Open Interest'] },
  { term: 'OPEX', category: 'basics', shortDef: 'Options expiration', fullExplanation: 'Standard monthly options expire third Friday. Weekly options expire every Friday. 0DTE expire same day.', whyUseful: 'Plan around expiration dates.' },
  { term: 'Front Running', category: 'risk', shortDef: 'Trading ahead of known orders', fullExplanation: 'Illegal practice of trading before executing customer orders. HFT front-runs in gray areas.', whyUseful: 'Understand market microstructure.' },
  { term: 'Dark Pool', category: 'basics', shortDef: 'Private trading venue', fullExplanation: 'Dark pools allow large orders to execute without public visibility. Hides institutional activity.', whyUseful: 'Large orders can execute without impact.', relatedTerms: ['Institutional'] },
  { term: 'PFOF', category: 'basics', shortDef: 'Payment for Order Flow', fullExplanation: 'Market makers pay brokers for retail order flow. How free brokers make money.', whyUseful: 'Understand execution quality.' },
  { term: 'Maker Taker', category: 'basics', shortDef: 'Exchange fee structure', fullExplanation: 'Makers (limit orders adding liquidity) get rebates. Takers (market orders removing liquidity) pay fees.', whyUseful: 'Understand trading costs.' },
  { term: 'HFT', category: 'basics', shortDef: 'High Frequency Trading', fullExplanation: 'Computer algorithms trading at microsecond speeds. Provides liquidity but can exacerbate volatility.', whyUseful: 'Understand market microstructure.' },
  { term: 'Algo Trading', category: 'strategies', shortDef: 'Automated computer trading', fullExplanation: 'Algorithm trading uses computer programs to execute trades based on rules. Removes emotion.', whyUseful: 'Consistent execution, no emotion.', xfactorUsage: 'XFactor is an algo trading platform.' },
  { term: 'Order Book', category: 'basics', shortDef: 'List of buy and sell orders', fullExplanation: 'Order book shows all limit orders at each price level. Level 2 data shows depth beyond best bid/ask.', whyUseful: 'See supply and demand at each level.', relatedTerms: ['Level 2', 'Depth'] },
  { term: 'Level 2', category: 'indicators', shortDef: 'Market depth data', fullExplanation: 'Level 2 shows order book with all bid and ask prices beyond best bid/ask. Shows market depth.', whyUseful: 'Gauge supply/demand imbalances.', relatedTerms: ['Order Book', 'Time and Sales'] },
  { term: 'Time and Sales', category: 'indicators', shortDef: 'Real-time trade feed', fullExplanation: 'Time and sales (tape) shows every trade: time, price, size. Green = at ask (buying), red = at bid (selling).', whyUseful: 'See actual trade flow.', relatedTerms: ['Tape Reading'] },
  { term: 'Tape Reading', category: 'strategies', shortDef: 'Analyzing time and sales', fullExplanation: 'Tape reading interprets trade flow to gauge buying/selling pressure and predict short-term moves.', whyUseful: 'Real-time order flow analysis.', relatedTerms: ['Time and Sales', 'Order Flow'] },
  { term: 'Order Flow', category: 'indicators', shortDef: 'Analysis of buying vs selling', fullExplanation: 'Order flow analyzes trades to determine if buyers or sellers are aggressive. Footprint charts visualize.', whyUseful: 'Leading indicator of price.', relatedTerms: ['Delta', 'Cumulative Delta'] },
  { term: 'Footprint Chart', category: 'indicators', shortDef: 'Volume at each price level', fullExplanation: 'Footprint charts show bid/ask volume at each price within each candle. Shows who is in control.', whyUseful: 'Detailed order flow analysis.', relatedTerms: ['Order Flow', 'Volume Profile'] },
  { term: 'Imbalance', category: 'indicators', shortDef: 'Large disparity between buyers and sellers', fullExplanation: 'Imbalances show when buying or selling volume far exceeds the other at a price level.', whyUseful: 'Signals aggressive participants.', relatedTerms: ['Order Flow', 'Delta'] },
  { term: 'Absorption', category: 'patterns', shortDef: 'Large orders consuming supply/demand', fullExplanation: 'Absorption shows large orders eating through opposing orders without moving price much.', whyUseful: 'Signals strong buyer/seller presence.', relatedTerms: ['Order Flow', 'Accumulation'] },
  { term: 'Iceberg Order', category: 'basics', shortDef: 'Large order hidden in small pieces', fullExplanation: 'Iceberg orders show small size in order book but automatically reload. Used to hide true size.', whyUseful: 'Spot hidden institutional orders.', relatedTerms: ['Dark Pool'] },
  { term: 'Reserve Order', category: 'basics', shortDef: 'Same as iceberg order', fullExplanation: 'Order showing partial size with remaining reserve hidden. Automatically replenishes.', whyUseful: 'Identify large players.' },
  { term: 'Value Area High', category: 'indicators', shortDef: 'Upper bound of 70% volume', fullExplanation: 'Upper boundary of price range containing 70% of volume. Resistance when approaching from below.', whyUseful: 'Key trading level.', relatedTerms: ['Value Area Low', 'Volume Profile'] },
  { term: 'Value Area Low', category: 'indicators', shortDef: 'Lower bound of 70% volume', fullExplanation: 'Lower boundary of price range containing 70% of volume. Support when approaching from above.', whyUseful: 'Key trading level.', relatedTerms: ['Value Area High', 'Volume Profile'] },
  { term: 'Initial Balance', category: 'indicators', shortDef: 'First hour\'s range', fullExplanation: 'The high-low range of the first trading hour. Often defines day\'s range in 70% of sessions.', whyUseful: 'Early reference for day trading.', relatedTerms: ['Opening Range'] },
  { term: 'Opening Range', category: 'indicators', shortDef: 'First 5-30 minutes\' range', fullExplanation: 'High and low of first 5, 15, or 30 minutes. Breakout from opening range is classic day trading setup.', whyUseful: 'Morning breakout strategy.', relatedTerms: ['Initial Balance', 'ORB'] },
  { term: 'ORB', category: 'strategies', shortDef: 'Opening Range Breakout', fullExplanation: 'Trade breakout above or below opening range. Classic day trading strategy with defined risk.', whyUseful: 'Simple morning strategy.', relatedTerms: ['Opening Range', 'Breakout'] },
  { term: 'Range Extension', category: 'patterns', shortDef: 'Price moving beyond initial range', fullExplanation: 'When price breaks out of initial balance or prior day\'s range. Signals trending day.', whyUseful: 'Identify trending days early.' },
  
  // ===== EVEN MORE TERMS TO REACH 300+ =====
  { term: 'Trend', category: 'basics', shortDef: 'Overall direction of price movement', fullExplanation: 'Trend is the general direction prices are moving. Uptrend = higher highs/lows. Downtrend = lower highs/lows.', whyUseful: 'Trade with the trend for higher probability.', relatedTerms: ['Higher High', 'Lower Low'] },
  { term: 'Range', category: 'basics', shortDef: 'Sideways price movement', fullExplanation: 'A range occurs when price bounces between support and resistance without trending.', whyUseful: 'Trade bounces or wait for breakout.', relatedTerms: ['Support', 'Resistance'] },
  { term: 'Reversal', category: 'patterns', shortDef: 'Change in trend direction', fullExplanation: 'Reversal is when uptrend turns to downtrend or vice versa. Major reversals occur at significant highs/lows.', whyUseful: 'Catch new trends early.', relatedTerms: ['Trend', 'Continuation'] },
  { term: 'Continuation', category: 'patterns', shortDef: 'Pattern showing trend will continue', fullExplanation: 'Continuation patterns (flags, pennants, triangles) suggest pause in trend before resumption.', whyUseful: 'Add to position during pause.', relatedTerms: ['Flag', 'Pennant'] },
  { term: 'Pullback', category: 'patterns', shortDef: 'Temporary move against trend', fullExplanation: 'Pullback is short-term decline in uptrend. Healthy pullbacks allow entry into existing trend.', whyUseful: 'Enter trends at better prices.', relatedTerms: ['Retracement', 'Buy the Dip'] },
  { term: 'Retracement', category: 'patterns', shortDef: 'Partial reversal of prior move', fullExplanation: 'Retracement is price moving back toward prior level before resuming trend. Fibonacci measures common.', whyUseful: 'Find entry points.', relatedTerms: ['Fibonacci', 'Pullback'] },
  { term: 'Buy the Dip', category: 'strategies', shortDef: 'Buying during pullbacks', fullExplanation: 'Strategy of buying during temporary price declines in uptrend. Works in bull markets.', whyUseful: 'Enter at better prices.', whyNotUseful: 'Dangerous in bear markets.' },
  { term: 'Sell the Rip', category: 'strategies', shortDef: 'Selling during rallies in downtrend', fullExplanation: 'Strategy of shorting temporary rallies in downtrend. Opposite of buying dips.', whyUseful: 'Enter shorts at better prices.' },
  { term: 'FOMO', category: 'risk', shortDef: 'Fear Of Missing Out', fullExplanation: 'Emotional state causing traders to chase moves after they\'ve happened. Often leads to buying tops.', whyUseful: 'Recognize to avoid.', relatedTerms: ['Emotional Trading'] },
  { term: 'FUD', category: 'basics', shortDef: 'Fear, Uncertainty, Doubt', fullExplanation: 'Negative sentiment often spread to manipulate prices lower. Common in crypto.', whyUseful: 'Recognize manipulation.' },
  { term: 'HODL', category: 'strategies', shortDef: 'Hold On for Dear Life', fullExplanation: 'Crypto slang for holding through volatility rather than trading. Long-term strategy.', whyUseful: 'Avoid panic selling.' },
  { term: 'Diamond Hands', category: 'strategies', shortDef: 'Holding through extreme volatility', fullExplanation: 'Trader who holds position through extreme moves. Meme stock culture term.', whyUseful: 'Conviction in thesis.', relatedTerms: ['Paper Hands'] },
  { term: 'Paper Hands', category: 'risk', shortDef: 'Selling too early', fullExplanation: 'Selling at first sign of loss or small profit. Misses big moves.', whyUseful: 'Develop conviction.', relatedTerms: ['Diamond Hands'] },
  { term: 'Bag Holder', category: 'risk', shortDef: 'Stuck holding losing position', fullExplanation: 'Trader holding position with large unrealized loss, hoping for recovery.', whyUseful: 'Use stops to avoid.', relatedTerms: ['Stop Loss'] },
  { term: 'Averaging Down', category: 'strategies', shortDef: 'Buying more as price falls', fullExplanation: 'Adding to losing position to lower average cost. Can work for quality stocks.', whyUseful: 'Lower cost basis.', whyNotUseful: 'Can compound losses in bad stocks.' },
  { term: 'Pyramiding', category: 'strategies', shortDef: 'Adding to winning positions', fullExplanation: 'Adding to position as it moves in your favor. Scales into winners.', whyUseful: 'Let winners run, add on strength.', relatedTerms: ['Scaling'] },
  { term: 'Scaling In', category: 'strategies', shortDef: 'Building position gradually', fullExplanation: 'Entering position over time rather than all at once. Reduces timing risk.', whyUseful: 'Better average entry.', relatedTerms: ['Scaling Out'] },
  { term: 'Scaling Out', category: 'strategies', shortDef: 'Exiting position gradually', fullExplanation: 'Selling position in parts at different prices. Locks in some profits while letting rest run.', whyUseful: 'Balance profit-taking with upside.', relatedTerms: ['Scaling In'] },
  { term: 'Position Trader', category: 'basics', shortDef: 'Long-term trend trader', fullExplanation: 'Position traders hold for weeks to months, riding major trends.', whyUseful: 'Lower stress, bigger moves.', relatedTerms: ['Swing Trader'] },
  { term: 'Swing Trader', category: 'basics', shortDef: 'Multi-day trader', fullExplanation: 'Swing traders hold for days to weeks, capturing short-term trends.', whyUseful: 'Balance of activity and flexibility.', relatedTerms: ['Day Trader'] },
  { term: 'Day Trader', category: 'basics', shortDef: 'Same-day trader', fullExplanation: 'Day traders close all positions before market close. No overnight risk.', whyUseful: 'No gap risk.', relatedTerms: ['Scalper'] },
  { term: 'Scalper', category: 'basics', shortDef: 'Quick in-and-out trader', fullExplanation: 'Scalpers hold for seconds to minutes, taking small profits many times.', whyUseful: 'Many opportunities.', relatedTerms: ['Day Trader'] },
  { term: 'Contrarian', category: 'strategies', shortDef: 'Trading against crowd', fullExplanation: 'Contrarians do opposite of crowd sentiment. Buy when others panic, sell when euphoric.', whyUseful: 'Catch turning points.', whyNotUseful: 'Can be early (wrong).' },
  { term: 'Sentiment', category: 'indicators', shortDef: 'Overall market mood', fullExplanation: 'Sentiment measures bullish vs bearish attitude. Extreme sentiment is contrarian signal.', whyUseful: 'Gauge crowd positioning.', xfactorUsage: 'XFactor tracks social sentiment.' },
  { term: 'Fear Greed Index', category: 'indicators', shortDef: 'CNN sentiment gauge', fullExplanation: 'Fear & Greed Index measures market sentiment on 0-100 scale. Extreme fear = buy signal; extreme greed = sell signal.', whyUseful: 'Contrarian indicator.', xfactorUsage: 'XFactor displays Fear & Greed in Crypto panel.' },
  { term: 'Put Call Ratio', category: 'indicators', shortDef: 'Put volume divided by call volume', fullExplanation: 'High put/call = bearish sentiment (contrarian bullish). Low = bullish sentiment (contrarian bearish).', whyUseful: 'Contrarian sentiment indicator.' },
  { term: 'VIX Put Call', category: 'indicators', shortDef: 'VIX options ratio', fullExplanation: 'Put/call ratio on VIX. High put ratio = traders expect volatility to drop.', whyUseful: 'Gauge volatility expectations.' },
  { term: 'AAII Sentiment', category: 'indicators', shortDef: 'Individual investor sentiment survey', fullExplanation: 'Weekly survey of retail investors. Extreme bullish/bearish is contrarian signal.', whyUseful: 'Gauge retail positioning.' },
  { term: 'Smart Money Indicator', category: 'indicators', shortDef: 'Institutional vs retail', fullExplanation: 'Tracks smart money (last hour) vs dumb money (first hour) positioning.', whyUseful: 'Follow smart money.' },
  { term: 'Advance Decline', category: 'indicators', shortDef: 'Rising vs falling stocks', fullExplanation: 'Advance/Decline line tracks stocks rising minus falling. Divergence from index warns of weakness.', whyUseful: 'Gauge market breadth.' },
  { term: 'Breadth', category: 'indicators', shortDef: 'Participation in market move', fullExplanation: 'Breadth measures how many stocks participate in a move. Narrow rallies (few stocks) are weak.', whyUseful: 'Confirm index moves.', relatedTerms: ['Advance Decline'] },
  { term: 'New Highs New Lows', category: 'indicators', shortDef: '52-week high/low counts', fullExplanation: 'Number of stocks making new 52-week highs minus new lows. Confirms index direction.', whyUseful: 'Gauge market health.' },
  { term: 'McClellan Oscillator', category: 'indicators', shortDef: 'Breadth momentum indicator', fullExplanation: 'Momentum oscillator based on advance/decline data. Overbought/oversold signals.', whyUseful: 'Short-term market timing.' },
  { term: 'Arms Index', category: 'indicators', shortDef: 'TRIN - trading index', fullExplanation: 'TRIN = (Advancing/Declining stocks) / (Advancing/Declining volume). >1 bearish, <1 bullish.', whyUseful: 'Intraday sentiment gauge.' },
  { term: 'Up Down Volume', category: 'indicators', shortDef: 'Volume in up vs down stocks', fullExplanation: 'Up/Down volume ratio shows where volume is flowing. Confirms price moves.', whyUseful: 'Volume confirms direction.' },
  { term: 'Sector ETF', category: 'basics', shortDef: 'ETF tracking market sector', fullExplanation: 'Sector ETFs like XLK (tech), XLF (financials), XLE (energy) track specific sectors.', whyUseful: 'Sector exposure without stock picking.' },
  { term: 'Leveraged ETF', category: 'basics', shortDef: 'ETF with daily leverage', fullExplanation: 'Leveraged ETFs like TQQQ (3x Nasdaq) amplify daily returns. Volatility decay over time.', whyUseful: 'Amplified short-term exposure.', whyNotUseful: 'Decay makes them unsuitable for holding.' },
  { term: 'Inverse ETF', category: 'basics', shortDef: 'ETF that profits from decline', fullExplanation: 'Inverse ETFs like SH (short S&P) profit when index falls. Alternative to shorting.', whyUseful: 'Hedge without margin account.' },
  { term: 'Crypto', category: 'basics', shortDef: 'Cryptocurrency assets', fullExplanation: 'Digital currencies like Bitcoin, Ethereum. Trade 24/7, high volatility.', whyUseful: 'Additional trading opportunities.', xfactorUsage: 'XFactor includes crypto trading bots.' },
  { term: 'DeFi', category: 'basics', shortDef: 'Decentralized Finance', fullExplanation: 'Financial services on blockchain without intermediaries. Lending, DEXs, yield farming.', whyUseful: 'New financial ecosystem.' },
  { term: 'NFT', category: 'basics', shortDef: 'Non-Fungible Token', fullExplanation: 'Unique digital assets on blockchain. Art, collectibles, gaming items.', whyUseful: 'Alternative asset class.' },
  { term: 'Whale', category: 'basics', shortDef: 'Large holder/trader with market-moving capital', fullExplanation: 'Whales are entities (institutional investors, hedge funds, or wealthy individuals) with holdings large enough to significantly impact market prices. In crypto, a whale might hold 1000+ BTC; in stocks, positions of $10M+. Their buying/selling creates visible price impact.', whyUseful: 'Following whale movements can signal major trend changes.', xfactorUsage: 'XFactor tracks whale alerts and large transaction monitoring.' },
  { term: 'Whale Alert', category: 'indicators', shortDef: 'Notification of large transactions', fullExplanation: 'Real-time alerts when whales move significant amounts. Tracks large transfers between wallets, exchanges, and cold storage. Often precedes major price moves.', whyUseful: 'Early warning for potential volatility.', xfactorUsage: 'XFactor integrates whale alert feeds in real-time.' },
  { term: 'Whale Accumulation', category: 'indicators', shortDef: 'Large players building positions', fullExplanation: 'Pattern where whales quietly accumulate assets over time, often during low volume periods. Detectable through on-chain analysis showing increasing wallet concentrations.', whyUseful: 'Bullish signal when whales accumulate.', xfactorUsage: 'XFactor detects accumulation patterns.' },
  { term: 'Whale Distribution', category: 'indicators', shortDef: 'Large players selling positions', fullExplanation: 'When whales begin selling their holdings, often distributing to smaller traders. Can signal market tops. Watch for large transfers to exchanges.', whyUseful: 'Bearish signal - smart money exiting.', xfactorUsage: 'XFactor monitors distribution patterns.' },
  { term: 'Whale Watching', category: 'strategies', shortDef: 'Tracking large holder activity', fullExplanation: 'Strategy of monitoring whale wallet addresses and transactions to gain insight into market direction. Includes tracking known institutional wallets, exchange flows, and large orders.', whyUseful: 'Trade alongside smart money.', xfactorUsage: 'XFactor provides whale tracking dashboard.' },
  { term: 'Dark Pool Activity', category: 'indicators', shortDef: 'Private exchange large orders', fullExplanation: 'Dark pools are private exchanges where institutional investors trade large blocks without public visibility. High dark pool activity can indicate whale positioning before major moves.', whyUseful: 'See where institutions are trading.', xfactorUsage: 'XFactor includes dark pool flow data.' },
  { term: 'Institutional Flow', category: 'indicators', shortDef: 'Smart money movement', fullExplanation: 'Tracking where institutional investors (mutual funds, pension funds, hedge funds) are moving capital. Includes 13F filings, options flow, and block trades.', whyUseful: 'Follow professional money managers.', xfactorUsage: 'XFactor tracks institutional order flow.' },
  { term: 'On-Chain', category: 'indicators', shortDef: 'Blockchain data analysis', fullExplanation: 'On-chain analysis examines blockchain data like transactions, wallet activity, supply.', whyUseful: 'Unique crypto data.', xfactorUsage: 'XFactor includes on-chain analysis.' },
  { term: 'Hash Rate', category: 'indicators', shortDef: 'Mining computing power', fullExplanation: 'Hash rate measures total mining power on blockchain. Rising = network strength.', whyUseful: 'Gauge network health.' },
  { term: 'Staking', category: 'strategies', shortDef: 'Locking crypto for rewards', fullExplanation: 'Staking locks tokens in proof-of-stake networks to earn yield.', whyUseful: 'Passive crypto income.' },
  { term: 'Yield Farming', category: 'strategies', shortDef: 'DeFi liquidity provision', fullExplanation: 'Providing liquidity to DeFi protocols in exchange for token rewards.', whyUseful: 'High yields.', whyNotUseful: 'Impermanent loss, smart contract risk.' },
  { term: 'Gas Fees', category: 'basics', shortDef: 'Blockchain transaction costs', fullExplanation: 'Gas fees pay for computation on blockchains like Ethereum. Vary with network congestion.', whyUseful: 'Factor into trading costs.' },
  { term: 'Slippage Tolerance', category: 'risk', shortDef: 'Acceptable price difference', fullExplanation: 'Maximum acceptable difference between expected and executed price. Important in DeFi.', whyUseful: 'Prevent failed transactions.' },

  // ============================================================================
  // EXPANDED GLOSSARY - 200+ MORE TERMS TO REACH 500+
  // ============================================================================

  // ===== ACRONYMS & ABBREVIATIONS =====
  { term: 'M&A', category: 'basics', shortDef: 'Mergers and Acquisitions', fullExplanation: 'M&A refers to corporate transactions where companies combine (merge) or one buys another (acquisition). Announcements typically cause significant stock price moves. Targets often jump 20-50%, while acquirers may drop slightly.', whyUseful: 'Major catalyst for price movement. Arbitrage opportunities exist between announcement and closing.', relatedTerms: ['Catalyst', 'Takeover', 'Arbitrage'] },
  { term: 'ATRWAC', category: 'strategies', shortDef: 'Agentic Tuning with Risk-Weighted Adaptive Control', fullExplanation: 'ATRWAC is XFactor\'s proprietary AI-powered optimization algorithm that automatically tunes trading bot parameters. It uses machine learning to adjust risk settings, position sizing, and strategy parameters based on market conditions and performance feedback.', whyUseful: 'Automatically optimizes bot performance without manual parameter tuning.', xfactorUsage: 'XFactor\'s core auto-tuning algorithm. Enable in Admin Panel > Agentic Tuning.' },
  { term: 'FOMC', category: 'fundamentals', shortDef: 'Federal Open Market Committee', fullExplanation: 'The FOMC is the Federal Reserve committee that sets U.S. monetary policy, including interest rates. Meetings occur 8 times per year. Rate decisions cause significant market volatility.', whyUseful: 'Major market-moving event. Plan trades around FOMC announcements.', example: 'Fed raises rates 25bps - markets typically sell off initially, then may rally on "certainty."' },
  { term: 'GDP', category: 'fundamentals', shortDef: 'Gross Domestic Product', fullExplanation: 'GDP measures the total value of goods and services produced in a country. Key economic indicator reported quarterly. Positive GDP = growing economy; negative = contraction (recession if two consecutive negative quarters).', whyUseful: 'Gauge overall economic health and market direction.', formula: 'GDP = C + I + G + (X-M) where C=consumption, I=investment, G=government, X=exports, M=imports' },
  { term: 'CPI', category: 'fundamentals', shortDef: 'Consumer Price Index - inflation measure', fullExplanation: 'CPI measures changes in prices paid by consumers for goods and services. Primary inflation gauge. Released monthly. Hot CPI = hawkish Fed = market selloff typically.', whyUseful: 'Major market mover. Plan around CPI release dates.', example: 'CPI comes in at 3.5% vs 3.0% expected - markets drop on higher-than-expected inflation.' },
  { term: 'PPI', category: 'fundamentals', shortDef: 'Producer Price Index', fullExplanation: 'PPI measures wholesale inflation - prices producers receive. Often leads CPI. Rising PPI suggests future consumer inflation.', whyUseful: 'Leading indicator for CPI and inflation expectations.' },
  { term: 'NFP', category: 'fundamentals', shortDef: 'Non-Farm Payrolls', fullExplanation: 'NFP is the monthly jobs report showing employment changes excluding farms. Released first Friday of each month at 8:30 AM ET. Major market mover. Strong jobs = hawkish Fed; weak = dovish.', whyUseful: 'Trade the volatility or avoid it. Major FX mover.' },
  { term: 'PCE', category: 'fundamentals', shortDef: 'Personal Consumption Expenditures', fullExplanation: 'PCE is the Fed\'s preferred inflation measure. Core PCE excludes food and energy. Released monthly. Directly influences Fed rate decisions.', whyUseful: 'Fed watches PCE more than CPI for policy decisions.' },
  { term: 'PMI', category: 'fundamentals', shortDef: 'Purchasing Managers Index', fullExplanation: 'PMI surveys manufacturing and services managers. Above 50 = expansion; below 50 = contraction. Leading economic indicator.', whyUseful: 'Early signal of economic direction.' },
  { term: 'ISM', category: 'fundamentals', shortDef: 'Institute for Supply Management', fullExplanation: 'ISM releases Manufacturing and Services PMI data. Key leading indicators for economic activity.', whyUseful: 'Leading economic indicator.', relatedTerms: ['PMI'] },
  { term: 'QE', category: 'basics', shortDef: 'Quantitative Easing', fullExplanation: 'QE is when central banks buy bonds to inject money into the economy. Increases liquidity, lowers interest rates. Generally bullish for stocks.', whyUseful: 'Central bank policy drives markets. QE = bullish; QT = bearish.', relatedTerms: ['QT', 'Fed'] },
  { term: 'QT', category: 'basics', shortDef: 'Quantitative Tightening', fullExplanation: 'QT is when central banks reduce their balance sheet by selling bonds or letting them mature. Removes liquidity. Generally bearish for stocks.', whyUseful: 'Understand macro environment.', relatedTerms: ['QE', 'Fed'] },
  { term: 'TINA', category: 'strategies', shortDef: 'There Is No Alternative', fullExplanation: 'TINA refers to the idea that stocks are the only attractive investment when bond yields are low. Drives money into equities even at high valuations.', whyUseful: 'Explains equity flows in low-rate environments.' },
  { term: 'FANG', category: 'basics', shortDef: 'Facebook, Amazon, Netflix, Google', fullExplanation: 'Original mega-cap tech stocks that dominated market performance. Now often "FAANG" including Apple. Evolved to "Magnificent 7" including MSFT, NVDA, TSLA.', whyUseful: 'These stocks drive market indices.' },
  { term: 'SPAC', category: 'basics', shortDef: 'Special Purpose Acquisition Company', fullExplanation: 'SPACs are blank-check companies that IPO to acquire a private company. Allows private companies to go public without traditional IPO process.', whyUseful: 'Can be traded pre-merger for speculation.', whyNotUseful: 'Many SPACs underperform. Dilution risk from warrants.' },
  { term: 'PIPE', category: 'basics', shortDef: 'Private Investment in Public Equity', fullExplanation: 'PIPE is private placement of stock in public company, often alongside SPAC mergers. Usually done at discount.', whyUseful: 'Watch for PIPE sales as overhang.' },
  { term: 'AUM', category: 'fundamentals', shortDef: 'Assets Under Management', fullExplanation: 'AUM is total market value of assets a fund manages. Larger AUM = more market impact and sometimes lower fees.', whyUseful: 'Gauge fund size and influence.' },
  { term: 'NAV', category: 'fundamentals', shortDef: 'Net Asset Value', fullExplanation: 'NAV is the per-share value of fund assets minus liabilities. ETFs trade close to NAV; closed-end funds can trade at premiums/discounts.', whyUseful: 'Identify arbitrage opportunities in CEFs.' },
  { term: 'TER', category: 'fundamentals', shortDef: 'Total Expense Ratio', fullExplanation: 'TER is annual cost of owning a fund. Lower = better for long-term returns. Index funds often 0.03-0.10%; active funds 0.5-2%.', whyUseful: 'Minimize costs for better returns.' },
  { term: 'YOY', category: 'fundamentals', shortDef: 'Year Over Year', fullExplanation: 'YOY compares current period to same period last year. Eliminates seasonality. YOY growth is key metric for earnings.', whyUseful: 'Standard comparison method.', example: 'Revenue grew 25% YOY means this quarter vs same quarter last year.' },
  { term: 'QOQ', category: 'fundamentals', shortDef: 'Quarter Over Quarter', fullExplanation: 'QOQ compares current quarter to previous quarter. Shows sequential growth. Important for seasonal businesses.', whyUseful: 'Track sequential trends.' },
  { term: 'MOM', category: 'fundamentals', shortDef: 'Month Over Month', fullExplanation: 'MOM compares current month to previous month. Used for economic data like CPI, retail sales.', whyUseful: 'Track recent changes.' },
  { term: 'TTM', category: 'fundamentals', shortDef: 'Trailing Twelve Months', fullExplanation: 'TTM is data from the past 12 months. Used for valuation metrics to capture full year without waiting for fiscal year end.', whyUseful: 'Current annualized metrics.' },
  { term: 'LTM', category: 'fundamentals', shortDef: 'Last Twelve Months', fullExplanation: 'LTM is same as TTM - trailing 12 months of financial data.', whyUseful: 'Standard for valuation analysis.' },
  { term: 'NTM', category: 'fundamentals', shortDef: 'Next Twelve Months', fullExplanation: 'NTM is forward-looking 12-month estimate. Used for forward P/E and growth projections.', whyUseful: 'Forward valuation metrics.' },
  { term: 'CAGR', category: 'fundamentals', shortDef: 'Compound Annual Growth Rate', fullExplanation: 'CAGR is smoothed annual return over multiple years. Better than average returns for comparing investments.', whyUseful: 'True measure of growth over time.', formula: 'CAGR = (Ending Value / Beginning Value)^(1/years) - 1' },
  { term: 'TAM', category: 'fundamentals', shortDef: 'Total Addressable Market', fullExplanation: 'TAM is the total market opportunity if a company captured 100% market share. Used to evaluate growth potential.', whyUseful: 'Assess growth runway.', relatedTerms: ['SAM', 'SOM'] },
  { term: 'SAM', category: 'fundamentals', shortDef: 'Serviceable Addressable Market', fullExplanation: 'SAM is portion of TAM that company can realistically target with current products/geography.', whyUseful: 'More realistic market size.' },
  { term: 'SOM', category: 'fundamentals', shortDef: 'Serviceable Obtainable Market', fullExplanation: 'SOM is portion of SAM company can realistically capture given competition and resources.', whyUseful: 'Most realistic revenue projection.' },
  { term: 'ARR', category: 'fundamentals', shortDef: 'Annual Recurring Revenue', fullExplanation: 'ARR is annualized value of subscription contracts. Key SaaS metric. ARR growth rate is crucial for valuation.', whyUseful: 'Predictable revenue stream.' },
  { term: 'MRR', category: 'fundamentals', shortDef: 'Monthly Recurring Revenue', fullExplanation: 'MRR is monthly subscription revenue. ARR = MRR × 12. Easier to track short-term growth.', whyUseful: 'Track subscription growth.' },
  { term: 'NRR', category: 'fundamentals', shortDef: 'Net Revenue Retention', fullExplanation: 'NRR measures revenue from existing customers including expansion and churn. >100% means customers spend more over time.', whyUseful: 'Key SaaS quality metric. >120% is excellent.' },
  { term: 'CAC', category: 'fundamentals', shortDef: 'Customer Acquisition Cost', fullExplanation: 'CAC is cost to acquire a new customer (marketing + sales). Compare to LTV for unit economics.', whyUseful: 'Measure marketing efficiency.' },
  { term: 'LTV', category: 'fundamentals', shortDef: 'Lifetime Value', fullExplanation: 'LTV is total revenue expected from a customer over their lifetime. LTV/CAC > 3 is healthy.', whyUseful: 'Unit economics foundation.' },
  { term: 'DAU', category: 'fundamentals', shortDef: 'Daily Active Users', fullExplanation: 'DAU is unique users engaging with product daily. Key engagement metric for consumer apps.', whyUseful: 'Track user engagement trends.' },
  { term: 'MAU', category: 'fundamentals', shortDef: 'Monthly Active Users', fullExplanation: 'MAU is unique users engaging monthly. DAU/MAU ratio shows engagement intensity.', whyUseful: 'User growth metric.' },
  { term: 'ARPU', category: 'fundamentals', shortDef: 'Average Revenue Per User', fullExplanation: 'ARPU is revenue divided by users. Track over time to see monetization improvement.', whyUseful: 'Monetization metric.', formula: 'ARPU = Total Revenue / Active Users' },
  { term: 'GMV', category: 'fundamentals', shortDef: 'Gross Merchandise Value', fullExplanation: 'GMV is total value of goods sold on a marketplace. E-commerce metric. Company takes a cut as revenue.', whyUseful: 'Measure marketplace scale.' },
  { term: 'AOV', category: 'fundamentals', shortDef: 'Average Order Value', fullExplanation: 'AOV is average amount per transaction. Important for e-commerce unit economics.', whyUseful: 'Track transaction size trends.' },
  { term: 'WACC', category: 'fundamentals', shortDef: 'Weighted Average Cost of Capital', fullExplanation: 'WACC is blended cost of debt and equity. Used as discount rate in DCF. Higher WACC = higher required return.', whyUseful: 'Foundation for valuation.', formula: 'WACC = (E/V × Re) + (D/V × Rd × (1-Tc))' },
  { term: 'IRR', category: 'fundamentals', shortDef: 'Internal Rate of Return', fullExplanation: 'IRR is discount rate that makes NPV = 0. Used by PE/VC to evaluate investments. Higher is better.', whyUseful: 'Standard return metric for private investments.' },
  { term: 'NPV', category: 'fundamentals', shortDef: 'Net Present Value', fullExplanation: 'NPV is present value of cash flows minus initial investment. Positive NPV = value-creating investment.', whyUseful: 'Investment decision tool.' },

  // ===== SEASONAL EVENTS & CALENDAR =====
  { term: 'Summer Doldrums', category: 'patterns', shortDef: 'Low volume period in late summer', fullExplanation: 'The Summer Doldrums typically occur in August when Wall Street traders take vacations. Volume drops significantly, leading to thin markets and potential for exaggerated moves on any news. Many traders reduce position sizes or go to cash.', whyUseful: 'Reduce trading activity in thin markets to avoid whipsaws.', example: 'August 2024 saw 30% lower volume than average, with flash crashes on minor news.', relatedTerms: ['Seasonality', 'Volume'] },
  { term: 'Sell in May', category: 'strategies', shortDef: 'Seasonal strategy to exit stocks in May', fullExplanation: '"Sell in May and Go Away" is based on historical underperformance of stocks from May to October compared to November to April. The six-month period November-April has historically outperformed May-October.', whyUseful: 'Historical seasonality edge.', whyNotUseful: 'Doesn\'t work every year. Missing dividends and potential rallies.', relatedTerms: ['Summer Doldrums', 'Santa Rally'] },
  { term: 'October Effect', category: 'patterns', shortDef: 'Historical volatility in October', fullExplanation: 'October has historical reputation for crashes (1929, 1987, 2008). While statistically not the worst month on average, it sees elevated volatility and investor anxiety.', whyUseful: 'Prepare for increased volatility in October.', whyNotUseful: 'Often a good buying opportunity after October lows.' },
  { term: 'Window Dressing', category: 'patterns', shortDef: 'End-of-quarter portfolio adjustments', fullExplanation: 'Fund managers buy recent winners and sell losers before quarter-end to make portfolios look good for reports. Creates predictable price pressure on extreme performers.', whyUseful: 'Trade with end-of-quarter flows.', example: 'In final week of quarter, beaten-down stocks face selling pressure as managers dump before reporting.' },
  { term: 'Tax Loss Selling', category: 'patterns', shortDef: 'Year-end selling of losers', fullExplanation: 'Investors sell losing positions in December to realize losses for tax purposes. Creates predictable selling pressure, especially in beaten-down stocks. Often reverses in January.', whyUseful: 'Buy depressed stocks in late December for January rebound.', relatedTerms: ['January Effect', 'Tax Loss Harvesting'] },
  { term: 'Earnings Season', category: 'patterns', shortDef: 'Quarterly reporting periods', fullExplanation: 'Earnings seasons occur 4 times per year, typically starting mid-January, April, July, and October. Most companies report within 3-4 weeks of quarter-end.', whyUseful: 'Plan trades around earnings dates.', xfactorUsage: 'XFactor tracks earnings dates in the calendar.' },
  { term: 'Quadruple Witching', category: 'patterns', shortDef: 'Four derivatives expire simultaneously', fullExplanation: 'Four types of contracts expire: stock options, stock index options, stock index futures, and single stock futures. Third Friday of March, June, September, December. High volume and volatility.', whyUseful: 'Expect unusual volume and potential pin risk.', relatedTerms: ['Triple Witching', 'OPEX'] },
  { term: 'FOMC Week', category: 'patterns', shortDef: 'Week of Federal Reserve meeting', fullExplanation: 'The week of FOMC announcements often sees compressed trading ranges before the announcement, then explosive moves after. Statement released Wednesday 2 PM ET.', whyUseful: 'Position for post-FOMC volatility or reduce size before.', xfactorUsage: 'XFactor marks FOMC dates in the economic calendar.' },
  { term: 'NFP Friday', category: 'patterns', shortDef: 'Non-Farm Payrolls release day', fullExplanation: 'First Friday of each month at 8:30 AM ET. Major market-moving event. Often creates the week\'s high or low. Forex and bond markets especially volatile.', whyUseful: 'Trade the move or avoid until volatility settles.' },
  { term: 'Fed Blackout Period', category: 'patterns', shortDef: 'FOMC members cannot speak', fullExplanation: 'The period before FOMC meetings when Fed officials cannot give speeches or interviews. Starts the Saturday before the meeting.', whyUseful: 'Reduced Fed-driven volatility during blackout.' },
  { term: 'Turnaround Tuesday', category: 'patterns', shortDef: 'Tendency for reversals on Tuesdays', fullExplanation: 'Historical tendency for markets to reverse direction on Tuesdays, especially after Monday selloffs.', whyUseful: 'Look for reversal setups Tuesday mornings.' },
  { term: 'End-of-Month Flows', category: 'patterns', shortDef: 'Portfolio rebalancing at month-end', fullExplanation: 'Pension funds and large institutions rebalance at month-end. Creates predictable buying of underweight assets, selling of overweight. Often bullish bias last few days.', whyUseful: 'Position for month-end rebalancing flows.' },
  { term: 'Monday Effect', category: 'patterns', shortDef: 'Historical Monday weakness', fullExplanation: 'Historically, Mondays have shown slightly negative returns on average. Weekend news digestion and position adjustments contribute.', whyUseful: 'Be cautious buying Friday into weekend.', whyNotUseful: 'Effect has weakened in recent years.' },
  { term: 'Pre-Holiday Drift', category: 'patterns', shortDef: 'Bullish bias before holidays', fullExplanation: 'Markets tend to drift higher in the days before major holidays as traders are reluctant to sell and short sellers cover.', whyUseful: 'Historical bullish edge before holidays.' },
  { term: 'Back to School Rally', category: 'patterns', shortDef: 'September retail bounce', fullExplanation: 'Retail stocks often rally in September as back-to-school spending data comes in and holiday inventory builds begin.', whyUseful: 'Sector-specific seasonal opportunity.' },
  { term: 'Black Friday Effect', category: 'patterns', shortDef: 'Retail sentiment after Thanksgiving', fullExplanation: 'Black Friday sales data often moves retail stocks. Strong sales = bullish; weak = bearish for holiday quarter.', whyUseful: 'Trade retail sector on sales data.' },
  { term: 'Super Bowl Indicator', category: 'patterns', shortDef: 'Quirky market predictor', fullExplanation: 'Theory that NFC win = bull market, AFC win = bear market. Historically 80%+ accurate but likely coincidence.', whyUseful: 'Fun trivia only - don\'t trade on it!' },

  // ===== ORDER TYPES & EXECUTION =====
  { term: 'Stop Limit Order', category: 'basics', shortDef: 'Stop that becomes limit order', fullExplanation: 'A stop-limit order triggers at the stop price but then becomes a limit order at the limit price. Unlike regular stops that become market orders, you control the execution price but risk non-execution.', whyUseful: 'Control entry/exit price even in volatile markets.', whyNotUseful: 'May not execute if price gaps through your limit.', example: 'Stop at $100, limit at $99.50. Triggers at $100 but only fills at $99.50 or better. If it gaps to $98, you don\'t get filled.' },
  { term: 'Daily Loss Limit', category: 'risk', shortDef: 'Maximum allowed loss per day', fullExplanation: 'A daily loss limit is a risk management rule that stops all trading once losses reach a predetermined amount. Essential for preserving capital and preventing emotional revenge trading after losses.', whyUseful: 'Prevents catastrophic single-day losses and emotional trading.', example: 'Daily loss limit of $500 or 2% of account. Once hit, all bots stop and no new trades until next day.', xfactorUsage: 'XFactor supports daily loss limits in Risk Controls panel.' },
  { term: 'Weekly Loss Limit', category: 'risk', shortDef: 'Maximum allowed loss per week', fullExplanation: 'A weekly loss limit caps total losses for the week. More relaxed than daily limits but still provides a safety net for bad weeks.', whyUseful: 'Prevents multi-day losing streaks from escalating.', xfactorUsage: 'Configure in XFactor Risk Controls.' },
  { term: 'Max Daily Trades', category: 'risk', shortDef: 'Limit on number of trades per day', fullExplanation: 'Maximum daily trades prevents overtrading. Once reached, no new positions can be opened until the next trading day.', whyUseful: 'Prevents overtrading and high commission costs.', xfactorUsage: 'Set in XFactor bot configuration.' },
  { term: 'OCO Order', category: 'basics', shortDef: 'One Cancels Other', fullExplanation: 'OCO is two orders linked together - when one executes, the other is automatically cancelled. Typically a profit target and stop loss.', whyUseful: 'Bracket positions with automatic exit management.' },
  { term: 'Bracket Order', category: 'basics', shortDef: 'Entry with profit target and stop loss', fullExplanation: 'A bracket order combines entry order with OCO exit orders (profit target and stop loss). Complete trade management in one order.', whyUseful: 'Set and forget trade management.' },
  { term: 'GTC Order', category: 'basics', shortDef: 'Good Till Cancelled', fullExplanation: 'GTC orders remain active until filled or manually cancelled. Unlike day orders that expire at market close.', whyUseful: 'Set limit orders for longer-term entries.' },
  { term: 'Day Order', category: 'basics', shortDef: 'Order that expires at market close', fullExplanation: 'Day orders automatically cancel at end of trading session if not filled. Default order type for most brokers.', whyUseful: 'No stale orders hanging around.' },
  { term: 'IOC Order', category: 'basics', shortDef: 'Immediate Or Cancel', fullExplanation: 'IOC orders execute immediately for whatever quantity is available, then cancel any unfilled portion. Used for urgent entries.', whyUseful: 'Get filled immediately without partial hangers.' },
  { term: 'FOK Order', category: 'basics', shortDef: 'Fill Or Kill', fullExplanation: 'FOK orders must be filled completely and immediately or are cancelled entirely. All-or-nothing execution.', whyUseful: 'Avoid partial fills for large orders.' },
  { term: 'AON Order', category: 'basics', shortDef: 'All Or None', fullExplanation: 'AON orders only execute if entire order can be filled. Unlike FOK, doesn\'t require immediate fill.', whyUseful: 'Avoid awkward partial positions.' },
  { term: 'MOC Order', category: 'basics', shortDef: 'Market On Close', fullExplanation: 'MOC orders execute at the closing auction price. Used for rebalancing and benchmark tracking.', whyUseful: 'Get official closing price.' },
  { term: 'LOC Order', category: 'basics', shortDef: 'Limit On Close', fullExplanation: 'LOC is limit order that only executes at close if price is at or better than limit.', whyUseful: 'Close price with price protection.' },
  { term: 'MOO Order', category: 'basics', shortDef: 'Market On Open', fullExplanation: 'MOO orders execute at the opening auction price. Used to catch overnight moves.', whyUseful: 'Get official opening price.' },
  { term: 'Pegged Order', category: 'basics', shortDef: 'Order that adjusts to market', fullExplanation: 'Pegged orders automatically adjust price relative to bid/ask. Maintains position in order book as market moves.', whyUseful: 'Stay competitive in order book without monitoring.' },
  { term: 'Trailing Stop Dollar', category: 'risk', shortDef: 'Stop that trails by fixed amount', fullExplanation: 'Trailing stop that follows price by fixed dollar amount. Stop moves up but never down for longs.', whyUseful: 'Lock in profits as price moves favorably.', example: 'Buy at $100 with $5 trailing stop. Price goes to $120, stop now at $115. Price reverses to $115, you exit.' },
  { term: 'Trailing Stop Percent', category: 'risk', shortDef: 'Stop that trails by percentage', fullExplanation: 'Trailing stop that follows price by fixed percentage. Better for different-priced stocks.', whyUseful: 'Percentage-based profit protection.', example: '10% trailing stop on $100 stock. Goes to $150, stop at $135 (10% below high).' },
  { term: 'Contingent Order', category: 'basics', shortDef: 'Order triggered by conditions', fullExplanation: 'Orders that only activate when certain conditions are met (price, time, indicator value).', whyUseful: 'Automate entry on specific conditions.' },
  { term: 'TWAP', category: 'strategies', shortDef: 'Time Weighted Average Price', fullExplanation: 'TWAP executes large orders in equal slices over time. Achieves average price over execution period.', whyUseful: 'Minimize market impact for large orders.' },
  { term: 'VWAP Order', category: 'strategies', shortDef: 'Volume Weighted Average Price order', fullExplanation: 'Executes order to achieve VWAP. Trades more when volume is high, less when low.', whyUseful: 'Benchmark execution for institutions.' },
  { term: 'Iceberg Execution', category: 'strategies', shortDef: 'Execute large order in hidden pieces', fullExplanation: 'Break large order into visible pieces to hide true size. Reduces market impact.', whyUseful: 'Hide large order intention from market.' },

  // ===== BOT CONFIGURATION & FEATURES =====
  { term: 'Max Positions', category: 'risk', shortDef: 'Maximum simultaneous open positions', fullExplanation: 'Max Positions limits how many different positions a bot can hold at once. Prevents over-diversification and ensures adequate attention to each position.', whyUseful: 'Manage concentration and attention bandwidth.', example: 'Max positions of 5 means the bot won\'t open a 6th position until one closes.', xfactorUsage: 'Configure in Bot Settings > Risk Controls.' },
  { term: 'Max Position Size', category: 'risk', shortDef: 'Maximum capital per position', fullExplanation: 'Max Position Size limits the dollar amount or share quantity for any single position. Prevents concentrated bets that could cause major losses.', whyUseful: 'Limit single-position risk.', formula: 'Max Position = Account × Max Position %', example: '$100k account with 10% max position = $10k maximum per trade.', xfactorUsage: 'Set in Bot Configuration or globally in Risk Controls.' },
  { term: 'Risk Per Trade', category: 'risk', shortDef: 'Maximum loss allowed per trade', fullExplanation: 'Risk per trade defines the maximum amount you\'re willing to lose on a single trade. Combined with stop distance to calculate position size. Professional traders typically risk 0.5-2% per trade.', whyUseful: 'Foundation of proper position sizing.', formula: 'Position Size = (Account × Risk %) / Stop Distance', xfactorUsage: 'Configure in Bot Risk Settings.' },
  { term: 'Cooldown Period', category: 'risk', shortDef: 'Delay after trade before next trade', fullExplanation: 'Cooldown period is enforced waiting time after a trade closes before the bot can enter a new trade. Prevents revenge trading and overtrading.', whyUseful: 'Reduce emotional trading and whipsaws.', xfactorUsage: 'Set cooldown in minutes/hours in Bot Settings.' },
  { term: 'Entry Delay', category: 'strategies', shortDef: 'Wait time before entering after signal', fullExplanation: 'Entry delay waits for signal confirmation before executing. Helps avoid false signals and fakeouts.', whyUseful: 'Filter out weak signals.', xfactorUsage: 'Configure in Advanced Bot Settings.' },
  { term: 'Signal Strength Threshold', category: 'strategies', shortDef: 'Minimum score for trade entry', fullExplanation: 'Signal strength threshold requires signals to meet a minimum confidence score before triggering trades. Higher threshold = fewer but higher quality trades.', whyUseful: 'Filter for high-conviction setups.', xfactorUsage: 'Set in Bot Strategy Parameters.' },
  { term: 'Volatility Filter', category: 'risk', shortDef: 'Avoid trading in extreme volatility', fullExplanation: 'Volatility filter pauses trading when VIX or ATR exceeds thresholds. Prevents trading in chaotic conditions.', whyUseful: 'Avoid whipsaws in volatile markets.', xfactorUsage: 'XFactor VIX-based circuit breakers use this.' },
  { term: 'Regime Filter', category: 'strategies', shortDef: 'Trade only in favorable market conditions', fullExplanation: 'Regime filter enables trading only when market is in specific state (trending, ranging, low vol). Different strategies work in different regimes.', whyUseful: 'Match strategy to market conditions.', xfactorUsage: 'XFactor Market Regime Detection panel.' },
  { term: 'Max Drawdown Limit', category: 'risk', shortDef: 'Maximum allowed peak-to-trough decline', fullExplanation: 'Max drawdown limit pauses trading when account drops a certain percentage from its peak. Prevents catastrophic losses during bad streaks.', whyUseful: 'Protect capital during bad periods.', example: '15% max drawdown: if account goes from $100k peak to $85k, all trading stops.', xfactorUsage: 'Configure in Risk Management panel.' },
  { term: 'Profit Target Mode', category: 'strategies', shortDef: 'How profit targets are calculated', fullExplanation: 'Profit target mode determines how TPs are set: fixed dollar, percentage, ATR multiple, resistance levels, or trailing.', whyUseful: 'Choose appropriate exit method for strategy.', xfactorUsage: 'Select in Bot Strategy Settings.' },
  { term: 'Stop Loss Mode', category: 'strategies', shortDef: 'How stop losses are calculated', fullExplanation: 'Stop loss mode determines how SLs are set: fixed dollar, percentage, ATR multiple, support levels, or trailing.', whyUseful: 'Choose appropriate risk management for strategy.', xfactorUsage: 'Select in Bot Strategy Settings.' },
  { term: 'Position Scaling', category: 'strategies', shortDef: 'Adding to positions based on conditions', fullExplanation: 'Position scaling rules for adding to winners (pyramiding) or losers (averaging down). Dangerous without strict limits.', whyUseful: 'Maximize exposure to winning trades.', xfactorUsage: 'Advanced Bot Configuration.' },
  { term: 'Trade Direction', category: 'strategies', shortDef: 'Long only, short only, or both', fullExplanation: 'Trade direction setting limits bot to long trades only, short trades only, or allows both directions.', whyUseful: 'Match strategy to market bias.', xfactorUsage: 'Set in Bot Configuration.' },
  { term: 'Trading Hours', category: 'risk', shortDef: 'When bot is allowed to trade', fullExplanation: 'Trading hours restrict when the bot can enter new positions. Some strategies work better at specific times (opening, closing, overnight).', whyUseful: 'Trade during optimal liquidity periods.', xfactorUsage: 'Configure in Bot Schedule Settings.' },
  { term: 'Instrument Filter', category: 'risk', shortDef: 'Which securities bot can trade', fullExplanation: 'Instrument filter limits which symbols the bot can trade. By price, volume, sector, or specific watchlist.', whyUseful: 'Focus on liquid, tradeable securities.', xfactorUsage: 'Set in Bot Watchlist Settings.' },
  { term: 'Min Volume Filter', category: 'risk', shortDef: 'Minimum volume required to trade', fullExplanation: 'Minimum volume filter prevents trading illiquid securities. Ensures adequate liquidity for entry and exit.', whyUseful: 'Avoid slippage in thin markets.', xfactorUsage: 'Configure in Bot Filters.' },
  { term: 'Min Price Filter', category: 'risk', shortDef: 'Minimum stock price to trade', fullExplanation: 'Minimum price filter excludes penny stocks and low-priced securities. Reduces manipulation risk.', whyUseful: 'Avoid highly volatile penny stocks.', xfactorUsage: 'Configure in Bot Filters.' },
  { term: 'Sector Exposure Limit', category: 'risk', shortDef: 'Maximum allocation to one sector', fullExplanation: 'Sector exposure limit caps how much capital can be in any single sector. Prevents concentration risk.', whyUseful: 'Maintain diversification.', xfactorUsage: 'Set in Portfolio Risk Controls.' },
  { term: 'Correlation Limit', category: 'risk', shortDef: 'Maximum correlation between positions', fullExplanation: 'Correlation limit prevents opening highly correlated positions. Ensures true diversification.', whyUseful: 'Avoid concentrated bets in correlated assets.' },
  { term: 'Max Open Risk', category: 'risk', shortDef: 'Total risk across all positions', fullExplanation: 'Max open risk limits total dollars at risk across all open positions. Sum of (position size × stop distance).', whyUseful: 'Cap total portfolio risk exposure.', formula: 'Total Risk = Σ(Position Size × Stop %)', xfactorUsage: 'Monitor in Risk Dashboard.' },
  { term: 'Equity Curve Trading', category: 'strategies', shortDef: 'Adjust trading based on performance', fullExplanation: 'Equity curve trading reduces size or pauses after losses, increases after wins. Trade with "hot hand."', whyUseful: 'Reduce exposure during losing streaks.', xfactorUsage: 'Advanced feature in Bot Settings.' },
  { term: 'Auto-Tuning', category: 'strategies', shortDef: 'Automatic parameter optimization', fullExplanation: 'Auto-tuning automatically adjusts bot parameters based on recent performance. Uses AI/ML to optimize settings.', whyUseful: 'Adapts to changing market conditions.', xfactorUsage: 'XFactor ATRWAC auto-tuning feature.' },
  { term: 'Bot Template', category: 'basics', shortDef: 'Pre-configured bot settings', fullExplanation: 'Bot templates are pre-configured strategy setups that can be quickly deployed. Includes parameters, filters, and risk settings.', whyUseful: 'Quick deployment of proven strategies.', xfactorUsage: 'XFactor includes 10+ strategy templates.' },
  { term: 'Paper Mode', category: 'basics', shortDef: 'Simulated trading without real money', fullExplanation: 'Paper mode runs bots with fake money against real market data. Used for testing strategies without risk.', whyUseful: 'Test before risking real capital.', xfactorUsage: 'Select Paper mode in Trading Mode.' },
  { term: 'Live Mode', category: 'basics', shortDef: 'Real money trading', fullExplanation: 'Live mode executes real trades with real money through your connected broker.', whyUseful: 'Actual trading.', xfactorUsage: 'Select Live mode after testing in Paper.' },
  { term: 'Demo Mode', category: 'basics', shortDef: 'Simulated trading with fake data', fullExplanation: 'Demo mode uses simulated market data and fake money. Useful for learning the interface without market connection.', whyUseful: 'Learn platform before connecting broker.', xfactorUsage: 'Default mode for new users.' },

  // ===== MORE TRADING CONCEPTS =====
  { term: 'Takeover Premium', category: 'fundamentals', shortDef: 'Premium paid in acquisition', fullExplanation: 'The amount above market price that an acquirer pays. Typically 20-50% premium to incentivize shareholders to tender.', whyUseful: 'Arbitrage opportunity between current price and offer.', relatedTerms: ['M&A', 'Merger Arbitrage'] },
  { term: 'Merger Arbitrage', category: 'strategies', shortDef: 'Trading the spread in M&A deals', fullExplanation: 'Merger arb buys target at discount to deal price, betting deal closes. Spread = risk of deal failure.', whyUseful: 'Market-neutral returns uncorrelated to market.', whyNotUseful: 'Deal breaks cause large losses.' },
  { term: 'Tender Offer', category: 'basics', shortDef: 'Public offer to buy shares', fullExplanation: 'A tender offer is public offer to buy shares directly from shareholders, usually at premium. Often used in acquisitions.', whyUseful: 'Opportunity to sell at premium.' },
  { term: 'Hostile Takeover', category: 'basics', shortDef: 'Acquisition against management\'s wishes', fullExplanation: 'Hostile takeover bypasses management and goes directly to shareholders. Can involve proxy fights and bidding wars.', whyUseful: 'Often leads to higher offers.' },
  { term: 'Poison Pill', category: 'basics', shortDef: 'Anti-takeover defense mechanism', fullExplanation: 'Poison pill allows existing shareholders to buy shares at discount if hostile acquirer buys too much, diluting the acquirer.', whyUseful: 'Understand takeover dynamics.' },
  { term: 'Proxy Fight', category: 'basics', shortDef: 'Battle for shareholder votes', fullExplanation: 'Activist investors seek to elect directors to influence company strategy. Can unlock value through changes.', whyUseful: 'Activist involvement often bullish.' },
  { term: 'Activist Investor', category: 'basics', shortDef: 'Investor pushing for changes', fullExplanation: 'Activists buy stakes and push for changes: spin-offs, buybacks, M&A, management changes. Often unlocks value.', whyUseful: 'Activist involvement is often bullish catalyst.', example: 'Carl Icahn takes stake and pushes for spin-off - stock rallies 20%.' },
  { term: 'Spin-Off', category: 'basics', shortDef: 'Creating independent company from division', fullExplanation: 'Spin-off distributes shares of subsidiary to parent company shareholders. Often unlocks hidden value.', whyUseful: 'Spin-offs often outperform as pure-play.', relatedTerms: ['Carve-Out'] },
  { term: 'Carve-Out', category: 'basics', shortDef: 'IPO of subsidiary while parent retains control', fullExplanation: 'Carve-out sells portion of subsidiary to public while parent keeps majority. Establishes market value.', whyUseful: 'Precursor to full spin-off.' },
  { term: 'Lock-Up Period', category: 'basics', shortDef: 'Period insiders cannot sell after IPO', fullExplanation: 'Lock-up period (usually 90-180 days) prevents insiders from selling after IPO. Expiration often creates selling pressure.', whyUseful: 'Short or avoid IPO stocks near lock-up expiration.' },
  { term: 'Secondary Offering', category: 'basics', shortDef: 'Additional share issuance', fullExplanation: 'Secondary offering sells new or existing shares. Dilutive if new shares. Often done at discount.', whyUseful: 'Be cautious of dilution.', whyNotUseful: 'Can be bullish if proceeds fund growth.' },
  { term: 'Buyback', category: 'fundamentals', shortDef: 'Company repurchasing its own shares', fullExplanation: 'Share buybacks reduce shares outstanding, increasing EPS. Signal that company believes stock is undervalued.', whyUseful: 'Bullish signal and EPS boost.', relatedTerms: ['EPS', 'Dividends'] },
  { term: 'Special Dividend', category: 'fundamentals', shortDef: 'One-time large dividend', fullExplanation: 'Special dividends are one-time payments, often from asset sales or excess cash. Stock typically drops by dividend amount.', whyUseful: 'Return of capital to shareholders.' },
  { term: 'Stock Dividend', category: 'fundamentals', shortDef: 'Dividend paid in additional shares', fullExplanation: 'Stock dividend issues additional shares instead of cash. Like small stock split. No cash leaves company.', whyUseful: 'Understand impact on position size.' },
  { term: 'ADR', category: 'basics', shortDef: 'American Depositary Receipt', fullExplanation: 'ADRs allow U.S. investors to buy foreign stocks. Trade on U.S. exchanges in dollars. Can have different voting rights.', whyUseful: 'Access foreign stocks easily.' },
  { term: 'GDR', category: 'basics', shortDef: 'Global Depositary Receipt', fullExplanation: 'GDRs trade on non-U.S. exchanges (like LSE) and represent foreign shares.', whyUseful: 'Access for international investors.' },
  { term: 'Statistical Arbitrage', category: 'strategies', shortDef: 'Quantitative mean reversion trading', fullExplanation: 'Stat arb uses quantitative models to identify mispricings between related securities. Pairs trading and market neutral.', whyUseful: 'Market-neutral returns.', relatedTerms: ['Pairs Trading', 'Mean Reversion'] },
  { term: 'Relative Value', category: 'strategies', shortDef: 'Trading price relationships', fullExplanation: 'Relative value strategies bet on convergence of related assets rather than outright direction.', whyUseful: 'Hedge away market risk.' },
  { term: 'Long/Short Equity', category: 'strategies', shortDef: 'Long winners, short losers', fullExplanation: 'L/S equity goes long best ideas, short worst. Reduces market exposure while capturing alpha.', whyUseful: 'Hedge fund style returns.' },
  { term: 'Market Neutral', category: 'strategies', shortDef: 'Equal long and short exposure', fullExplanation: 'Market neutral maintains roughly equal long and short exposure. Profits from stock selection, not market direction.', whyUseful: 'Returns uncorrelated to market.' },
  { term: 'Factor Investing', category: 'strategies', shortDef: 'Targeting specific return drivers', fullExplanation: 'Factor investing targets characteristics like value, momentum, quality, low vol that historically deliver premium returns.', whyUseful: 'Systematic source of returns.', relatedTerms: ['Smart Beta', 'Value', 'Momentum'] },
  { term: 'Smart Beta', category: 'strategies', shortDef: 'Rules-based factor exposure', fullExplanation: 'Smart beta ETFs use rules-based factor weighting rather than market cap. Value, momentum, low vol.', whyUseful: 'Factor exposure in ETF format.' },
  { term: 'Quality Factor', category: 'fundamentals', shortDef: 'High ROE, low debt companies', fullExplanation: 'Quality factor targets companies with high profitability, stable earnings, and strong balance sheets.', whyUseful: 'Defensive outperformance over time.' },
  { term: 'Value Factor', category: 'strategies', shortDef: 'Cheap stocks outperform', fullExplanation: 'Value factor bets that low P/E, P/B stocks outperform expensive stocks over time.', whyUseful: 'Historical risk premium.', whyNotUseful: 'Value has underperformed growth recently.' },
  { term: 'Size Factor', category: 'strategies', shortDef: 'Small caps outperform large caps', fullExplanation: 'Size premium suggests small cap stocks earn higher returns than large caps over long periods.', whyUseful: 'Historical risk premium.', whyNotUseful: 'More volatile and less liquid.' },
  { term: 'Low Volatility', category: 'strategies', shortDef: 'Low vol stocks outperform risk-adjusted', fullExplanation: 'Low volatility anomaly: low vol stocks have better risk-adjusted returns than high vol.', whyUseful: 'Better returns per unit of risk.' },
  { term: 'Carry Trade', category: 'strategies', shortDef: 'Borrow low yield, invest high yield', fullExplanation: 'Carry trade borrows in low-interest currency to invest in high-interest currency. Profits from rate differential.', whyUseful: 'Steady returns in calm markets.', whyNotUseful: 'Blows up during risk-off events.' },
  { term: 'Risk Parity', category: 'strategies', shortDef: 'Equal risk allocation across assets', fullExplanation: 'Risk parity allocates based on risk contribution not dollar amounts. Often means more bonds, less stocks.', whyUseful: 'Balanced risk exposure.' },
  { term: 'Tail Risk', category: 'risk', shortDef: 'Extreme unlikely events', fullExplanation: 'Tail risk is the risk of extreme moves that fall outside normal distributions. Black swan events. VaR underestimates.', whyUseful: 'Prepare for the unexpected.', relatedTerms: ['Black Swan', 'VaR'] },
  { term: 'Black Swan', category: 'risk', shortDef: 'Unpredictable extreme event', fullExplanation: 'Black swan events are highly improbable but have massive impact. 2008 crisis, COVID crash. Cannot be predicted but can hedge.', whyUseful: 'Maintain hedges and position limits.' },
  { term: 'Fat Tails', category: 'risk', shortDef: 'More extreme events than normal distribution', fullExplanation: 'Financial returns have "fat tails" - extreme moves happen more often than normal distribution predicts.', whyUseful: 'Understand true risk is higher than models suggest.' },
  { term: 'Kurtosis', category: 'indicators', shortDef: 'Measure of tail thickness', fullExplanation: 'Kurtosis measures how fat the tails are. Higher kurtosis = more extreme events. Financial returns have high kurtosis.', whyUseful: 'Understand distribution of returns.' },
  { term: 'Skewness', category: 'indicators', shortDef: 'Asymmetry of distribution', fullExplanation: 'Skewness measures distribution asymmetry. Negative skew = more downside outliers (typical for stocks).', whyUseful: 'Understand risk profile.' },
  { term: 'Mean-Variance Optimization', category: 'strategies', shortDef: 'Portfolio optimization method', fullExplanation: 'MVO maximizes return for given risk or minimizes risk for given return. Modern Portfolio Theory foundation.', whyUseful: 'Optimal portfolio construction.', whyNotUseful: 'Sensitive to input assumptions.' },
  { term: 'Efficient Frontier', category: 'strategies', shortDef: 'Optimal risk-return portfolios', fullExplanation: 'The efficient frontier is the set of portfolios offering highest return for each level of risk.', whyUseful: 'Benchmark for portfolio efficiency.' },
  { term: 'Risk Budget', category: 'risk', shortDef: 'Allocated risk across positions', fullExplanation: 'Risk budget divides total portfolio risk across positions. Ensures no position contributes disproportionate risk.', whyUseful: 'Balanced risk allocation.' },
  { term: 'Marginal Contribution', category: 'risk', shortDef: 'Position\'s contribution to portfolio risk', fullExplanation: 'Marginal contribution to risk (MCTR) measures how much each position adds to total portfolio risk.', whyUseful: 'Identify and manage risk concentrations.' },
  { term: 'Tracking Error', category: 'risk', shortDef: 'Deviation from benchmark', fullExplanation: 'Tracking error measures how closely a portfolio follows its benchmark. Lower = more index-like.', whyUseful: 'Understand active risk taken.' },
  { term: 'Information Ratio', category: 'risk', shortDef: 'Alpha per unit of tracking error', fullExplanation: 'Information ratio = Alpha / Tracking Error. Measures skill of active management.', whyUseful: 'Compare active managers.', formula: 'IR = (Portfolio Return - Benchmark Return) / Tracking Error' },
  { term: 'Treynor Ratio', category: 'risk', shortDef: 'Return per unit of beta', fullExplanation: 'Treynor ratio is excess return divided by beta. Measures return earned per unit of market risk.', whyUseful: 'Risk-adjusted performance.', formula: 'Treynor = (Return - Risk-Free) / Beta' },
  { term: 'Jensen\'s Alpha', category: 'risk', shortDef: 'Return above CAPM prediction', fullExplanation: 'Jensen\'s alpha measures return in excess of what CAPM predicts given the portfolio\'s beta.', whyUseful: 'Measure manager skill.', formula: 'α = Return - [Rf + β(Rm - Rf)]' },
  { term: 'CAPM', category: 'fundamentals', shortDef: 'Capital Asset Pricing Model', fullExplanation: 'CAPM predicts expected return based on risk-free rate and beta exposure to market. Foundation of finance theory.', whyUseful: 'Theoretical framework for expected returns.', formula: 'Expected Return = Rf + β(Rm - Rf)' },
  { term: 'R-Squared', category: 'indicators', shortDef: 'Correlation to benchmark squared', fullExplanation: 'R-squared shows what percentage of portfolio moves are explained by benchmark moves. High = index-like.', whyUseful: 'Understand portfolio behavior.' },
  { term: 'Regression', category: 'indicators', shortDef: 'Statistical relationship analysis', fullExplanation: 'Regression analyzes relationships between variables. Used for factor analysis and alpha generation.', whyUseful: 'Quantitative analysis foundation.' },
  { term: 'Monte Carlo', category: 'strategies', shortDef: 'Simulation using random sampling', fullExplanation: 'Monte Carlo simulations run thousands of random scenarios to estimate probability distributions of outcomes.', whyUseful: 'Stress test strategies and portfolios.' },
  { term: 'Bootstrapping', category: 'strategies', shortDef: 'Resampling for robust statistics', fullExplanation: 'Bootstrapping resamples historical data to estimate confidence intervals and test robustness.', whyUseful: 'More realistic backtesting.' },
  { term: 'Survivorship Bias', category: 'risk', shortDef: 'Only seeing winners', fullExplanation: 'Survivorship bias occurs when analysis only includes survivors, not failures. Makes past performance look better.', whyUseful: 'Use survivorship-bias-free data for backtests.' },
  { term: 'Look-Ahead Bias', category: 'risk', shortDef: 'Using future data in backtest', fullExplanation: 'Look-ahead bias uses information not available at the time. Invalidates backtest results.', whyUseful: 'Avoid to get realistic backtest results.' },
  { term: 'Data Snooping', category: 'risk', shortDef: 'Overfitting to historical data', fullExplanation: 'Data snooping tests many strategies on same data until one works by chance. Results don\'t hold out-of-sample.', whyUseful: 'Use out-of-sample testing.', relatedTerms: ['Overfitting', 'Curve Fitting'] },
  { term: 'Out-of-Sample', category: 'strategies', shortDef: 'Testing on unseen data', fullExplanation: 'Out-of-sample testing validates strategy on data not used for development. Essential for valid backtests.', whyUseful: 'Confirm strategy works on new data.' },
  { term: 'In-Sample', category: 'strategies', shortDef: 'Data used for strategy development', fullExplanation: 'In-sample data is used to develop and optimize the strategy. Should not be used for final testing.', whyUseful: 'Separate development and testing data.' },
  { term: 'Degrees of Freedom', category: 'risk', shortDef: 'Number of independent data points', fullExplanation: 'More parameters relative to data points increases overfitting risk. Need adequate degrees of freedom.', whyUseful: 'Keep strategies simple.' },
  { term: 'Parameter Sensitivity', category: 'risk', shortDef: 'How results change with parameters', fullExplanation: 'Robust strategies show similar results across nearby parameter values. Fragile ones are highly sensitive.', whyUseful: 'Test parameter sensitivity for robustness.' },
  { term: 'Stress Test', category: 'risk', shortDef: 'Testing under extreme conditions', fullExplanation: 'Stress testing applies extreme historical or hypothetical scenarios to see how strategy performs.', whyUseful: 'Understand worst-case behavior.' },
  { term: 'Scenario Analysis', category: 'risk', shortDef: 'Testing specific what-if scenarios', fullExplanation: 'Scenario analysis models specific events: recession, rate hike, sector crash. What happens to portfolio?', whyUseful: 'Prepare for specific risks.' },

  // ===== FOREX & CURRENCY =====
  { term: 'Pip', category: 'basics', shortDef: 'Smallest price move in forex', fullExplanation: 'A pip is 0.0001 for most pairs (0.01 for JPY pairs). Measures price changes in forex.', whyUseful: 'Calculate forex profit/loss.', formula: 'For EUR/USD, 1 pip = $10 per standard lot (100,000 units)' },
  { term: 'Lot Size', category: 'basics', shortDef: 'Forex position size unit', fullExplanation: 'Standard lot = 100,000 units. Mini lot = 10,000. Micro lot = 1,000.', whyUseful: 'Understand position sizing in forex.' },
  { term: 'Currency Pair', category: 'basics', shortDef: 'Two currencies quoted together', fullExplanation: 'Currency pairs show one currency\'s value relative to another. EUR/USD = euros per dollar. Base/Quote format.', whyUseful: 'Foundation of forex trading.' },
  { term: 'Base Currency', category: 'basics', shortDef: 'First currency in pair', fullExplanation: 'Base currency is the first in a pair. EUR in EUR/USD. Price shows how much quote you need to buy 1 base.', whyUseful: 'Understand pair direction.' },
  { term: 'Quote Currency', category: 'basics', shortDef: 'Second currency in pair', fullExplanation: 'Quote currency is the second in pair. USD in EUR/USD. Price expressed in quote currency units.', whyUseful: 'Understand P&L currency.' },
  { term: 'Major Pairs', category: 'basics', shortDef: 'Most traded currency pairs', fullExplanation: 'Major pairs include USD vs EUR, GBP, JPY, CHF, CAD, AUD, NZD. Most liquid, tightest spreads.', whyUseful: 'Best liquidity and lowest costs.' },
  { term: 'Minor Pairs', category: 'basics', shortDef: 'Crosses without USD', fullExplanation: 'Minor or cross pairs don\'t include USD. EUR/GBP, EUR/JPY, GBP/JPY. Less liquid, wider spreads.', whyUseful: 'More trading opportunities.' },
  { term: 'Exotic Pairs', category: 'basics', shortDef: 'Major + emerging market currency', fullExplanation: 'Exotic pairs combine major with emerging: USD/TRY, USD/ZAR. Very wide spreads, high volatility.', whyUseful: 'Higher volatility trading.', whyNotUseful: 'High costs, low liquidity.' },
  { term: 'Currency Strength', category: 'indicators', shortDef: 'Relative currency performance', fullExplanation: 'Currency strength meter ranks currencies by performance. Trade strongest vs weakest.', whyUseful: 'Find best pairs to trade.', xfactorUsage: 'XFactor displays currency strength meter.' },
  { term: 'Forex Session', category: 'basics', shortDef: 'Trading periods by timezone', fullExplanation: 'Three main sessions: Asian (Tokyo), European (London), American (New York). Overlaps have highest volume.', whyUseful: 'Trade during active sessions.' },
  { term: 'London Session', category: 'basics', shortDef: 'European trading hours', fullExplanation: 'London session 8 AM - 4 PM GMT is most liquid. Overlaps with Asian and US sessions.', whyUseful: 'Best forex trading hours.' },
  { term: 'Central Bank Intervention', category: 'fundamentals', shortDef: 'Government currency manipulation', fullExplanation: 'Central banks sometimes buy/sell currency to influence exchange rates. Can cause massive moves.', whyUseful: 'Be aware of intervention risk.' },
  { term: 'Interest Rate Differential', category: 'indicators', shortDef: 'Rate difference between currencies', fullExplanation: 'Currency with higher rates tends to appreciate due to carry trade flows. Drives forex trends.', whyUseful: 'Foundation of carry trade.' },
  { term: 'Safe Haven Currency', category: 'basics', shortDef: 'Currency that gains in risk-off', fullExplanation: 'Safe haven currencies (USD, JPY, CHF) appreciate during market stress as investors seek safety.', whyUseful: 'Hedge or trade risk sentiment.' },
  { term: 'Risk Currency', category: 'basics', shortDef: 'Currency that gains in risk-on', fullExplanation: 'Risk currencies (AUD, NZD, emerging markets) appreciate when markets are optimistic.', whyUseful: 'Trade risk sentiment.' },
  { term: 'Dollar Index', category: 'indicators', shortDef: 'DXY - dollar vs basket of currencies', fullExplanation: 'Dollar Index (DXY) measures USD against EUR, JPY, GBP, CAD, SEK, CHF. Benchmark for dollar strength.', whyUseful: 'Gauge overall dollar direction.', xfactorUsage: 'XFactor tracks DXY in Forex panel.' },

  // ===== COMMODITIES =====
  { term: 'Crude Oil', category: 'basics', shortDef: 'WTI and Brent petroleum', fullExplanation: 'Crude oil is the most traded commodity. WTI (West Texas Intermediate) is U.S. benchmark; Brent is international.', whyUseful: 'Impacts inflation, energy stocks, transport.' },
  { term: 'Gold', category: 'basics', shortDef: 'Traditional safe haven commodity', fullExplanation: 'Gold is inflation hedge and safe haven. Often rises when real rates fall or uncertainty increases.', whyUseful: 'Portfolio hedge and safe haven.' },
  { term: 'Silver', category: 'basics', shortDef: 'Industrial and precious metal', fullExplanation: 'Silver has both precious metal and industrial uses. More volatile than gold, higher beta to economic activity.', whyUseful: 'Leveraged gold play with industrial exposure.' },
  { term: 'Copper', category: 'basics', shortDef: 'Industrial metal - Dr. Copper', fullExplanation: 'Copper is called "Dr. Copper" because it predicts economic health. Used in construction, electronics.', whyUseful: 'Leading economic indicator.' },
  { term: 'Natural Gas', category: 'basics', shortDef: 'Heating and electricity fuel', fullExplanation: 'Natural gas is highly seasonal (winter heating demand) and weather-dependent. Very volatile.', whyUseful: 'Seasonal trading opportunities.' },
  { term: 'Agriculture', category: 'basics', shortDef: 'Farm commodities', fullExplanation: 'Ag commodities include corn, wheat, soybeans, sugar, coffee, cotton. Weather and supply-driven.', whyUseful: 'Diversification and inflation hedge.' },
  { term: 'Commodity Futures', category: 'basics', shortDef: 'Contracts for future commodity delivery', fullExplanation: 'Commodity futures are standardized contracts for future delivery. Used for hedging and speculation.', whyUseful: 'Leverage and directional exposure.' },
  { term: 'Spot Price', category: 'basics', shortDef: 'Current cash market price', fullExplanation: 'Spot price is for immediate delivery. Futures may trade at premium or discount to spot.', whyUseful: 'Reference price for commodities.' },
  { term: 'Roll Yield', category: 'indicators', shortDef: 'Return from futures rolling', fullExplanation: 'Roll yield is gain or loss from rolling futures. Positive in backwardation, negative in contango.', whyUseful: 'Impacts long-term commodity returns.' },

  // ===== RISK METRICS & PORTFOLIO =====
  { term: 'Beta-Adjusted Exposure', category: 'risk', shortDef: 'Position weighted by beta', fullExplanation: 'Beta-adjusted exposure accounts for position volatility relative to market. High beta counts for more.', whyUseful: 'True measure of market exposure.' },
  { term: 'Gross Exposure', category: 'risk', shortDef: 'Total long plus short exposure', fullExplanation: 'Gross exposure = |Long| + |Short|. 100% long + 50% short = 150% gross exposure.', whyUseful: 'Measure of leverage used.' },
  { term: 'Net Exposure', category: 'risk', shortDef: 'Long minus short exposure', fullExplanation: 'Net exposure = Long - Short. 100% long - 50% short = 50% net long.', whyUseful: 'Directional bias of portfolio.' },
  { term: 'Leverage', category: 'risk', shortDef: 'Using borrowed money', fullExplanation: 'Leverage amplifies returns and losses. 2:1 leverage means $1 controls $2 of assets.', whyUseful: 'Increase returns.', whyNotUseful: 'Also increases losses and risk of ruin.' },
  { term: 'Concentration Risk', category: 'risk', shortDef: 'Risk from large position weights', fullExplanation: 'Concentration risk occurs when few positions dominate portfolio. Single stock dropping can hurt badly.', whyUseful: 'Maintain diversification limits.' },
  { term: 'Liquidity Risk', category: 'risk', shortDef: 'Risk of not being able to exit', fullExplanation: 'Liquidity risk is inability to sell without major price impact. Worse in small caps, during stress.', whyUseful: 'Size positions appropriately for liquidity.' },
  { term: 'Counterparty Risk', category: 'risk', shortDef: 'Risk of other party defaulting', fullExplanation: 'Counterparty risk is risk that the other side of your trade defaults. Relevant for OTC derivatives.', whyUseful: 'Choose counterparties carefully.' },
  { term: 'Operational Risk', category: 'risk', shortDef: 'Risk from system or human error', fullExplanation: 'Operational risk includes technology failures, human error, fraud. Can cause major losses.', whyUseful: 'Implement proper controls.' },
  { term: 'Model Risk', category: 'risk', shortDef: 'Risk that model is wrong', fullExplanation: 'Model risk is the risk that your trading model has flaws or assumptions that don\'t hold.', whyUseful: 'Test and validate models thoroughly.' },
  { term: 'Execution Risk', category: 'risk', shortDef: 'Risk of poor trade execution', fullExplanation: 'Execution risk is the risk of not getting filled at expected price due to slippage, delays, etc.', whyUseful: 'Factor into strategy profitability.' },

  // ===== FINAL ADDITIONS TO REACH 500+ =====
  { term: 'Order Entry', category: 'basics', shortDef: 'Submitting a trade order', fullExplanation: 'Order entry is the process of submitting buy or sell orders to your broker for execution.', whyUseful: 'Foundation of trading.' },
  { term: 'Execution', category: 'basics', shortDef: 'Completing a trade', fullExplanation: 'Execution is when your order is filled and the trade is completed.', whyUseful: 'Understand execution quality.' },
  { term: 'Settlement', category: 'regulations', shortDef: 'Transfer of securities and cash', fullExplanation: 'Settlement is when securities and cash officially change hands. Since May 2024, stocks settle T+1 (next business day). Options also T+1. Cash accounts must wait for settlement before reusing funds.', whyUseful: 'Know when you can use proceeds and avoid violations.', example: 'Sell AAPL on Monday. Settlement is Tuesday. You cannot withdraw the cash until Tuesday. In cash accounts, you cannot reuse those funds until Tuesday.' },
  { term: 'Clearing', category: 'basics', shortDef: 'Processing trades between parties', fullExplanation: 'Clearing is the process of matching and reconciling trades between buyers and sellers.', whyUseful: 'Understand trade lifecycle.' },
  { term: 'Prime Broker', category: 'basics', shortDef: 'Full-service broker for hedge funds', fullExplanation: 'Prime brokers provide clearing, custody, financing, and securities lending to hedge funds.', whyUseful: 'Institutional trading infrastructure.' },
  { term: 'Custodian', category: 'basics', shortDef: 'Entity holding your securities', fullExplanation: 'A custodian holds and safeguards your securities. Separate from broker for protection.', whyUseful: 'Security of assets.' },
  { term: 'Trade Confirmation', category: 'basics', shortDef: 'Record of completed trade', fullExplanation: 'Trade confirmation is official record of your trade with price, quantity, commissions.', whyUseful: 'Verify trade details and keep records.' },
  { term: 'Account Statement', category: 'basics', shortDef: 'Periodic account summary', fullExplanation: 'Account statement shows positions, transactions, and performance for the period.', whyUseful: 'Track and verify account activity.' },
  { term: 'Buying on Margin', category: 'basics', shortDef: 'Using borrowed funds to buy', fullExplanation: 'Buying on margin uses broker-provided funds to purchase more securities than cash allows.', whyUseful: 'Increase buying power.', whyNotUseful: 'Interest costs and margin call risk.' },
  { term: 'Reg T', category: 'regulations', shortDef: 'Federal margin requirement', fullExplanation: 'Regulation T (Federal Reserve Board) sets initial margin at 50% for stock purchases. Brokers can require more but not less.', whyUseful: 'Understand regulatory framework.', example: 'To buy $10,000 of stock, you need at least $5,000 cash (50% initial margin). The other $5,000 can be borrowed from your broker.' },
  { term: 'FINRA', category: 'regulations', shortDef: 'Financial Industry Regulatory Authority', fullExplanation: 'FINRA is a self-regulatory organization that oversees broker-dealers and enforces rules like the Pattern Day Trader rule, margin requirements, and suitability standards.', whyUseful: 'Understand who regulates trading rules.', example: 'FINRA enforces the PDT rule requiring $25,000 minimum equity for day traders with 4+ trades in 5 days.' },
  { term: 'Good Faith Violation', category: 'regulations', shortDef: 'Selling before purchase settles', fullExplanation: 'In cash accounts, selling securities before the purchase settles (T+1) is a Good Faith Violation. Three violations in 12 months results in 90-day cash-upfront restriction where you must have settled funds before buying.', whyUseful: 'Critical for cash account traders.', whyNotUseful: 'Restricts trading flexibility.', relatedTerms: ['Settlement', 'Cash Account', 'Freeriding'], example: 'Monday: Buy $1,000 AAPL. Tuesday (before settlement): Sell AAPL. This triggers a GFV because you sold before the purchase settled.' },
  { term: 'Freeriding', category: 'regulations', shortDef: 'Buying and selling before paying', fullExplanation: 'Freeriding occurs when you buy securities with unsettled funds, sell them, and use those proceeds before paying for the original purchase. Results in 90-day cash-upfront restriction.', whyUseful: 'Avoid severe account restrictions.', relatedTerms: ['Good Faith Violation', 'Settlement', 'Cash Account'], example: 'Day 1: Sell MSFT for $5,000 (settles Day 2). Day 1: Buy TSLA with that $5,000. Day 1: Sell TSLA before Day 2. This is freeriding.' },
  { term: 'Day Trading Buying Power', category: 'regulations', shortDef: '4x margin for PDT accounts', fullExplanation: 'Pattern Day Traders get 4x their maintenance margin excess for intraday trades. Exceeding DTBP triggers a day trading margin call requiring immediate deposit within 5 business days.', whyUseful: 'Maximize intraday trading capacity.', whyNotUseful: 'Overuse can trigger margin calls.', relatedTerms: ['Pattern Day Trader', 'Margin'], example: 'With $30,000 equity, your DTBP might be $120,000 (4x). If you buy $150,000 of stock intraday, you exceed DTBP by $30,000.' },
  { term: 'T+1 Settlement', category: 'regulations', shortDef: 'One business day to settle', fullExplanation: 'As of May 28, 2024, stocks settle T+1 (one business day after trade). Previously T+2. SEC is considering T+0 (same-day settlement) for 2025/2026.', whyUseful: 'Know when cash/securities are available.', relatedTerms: ['Settlement', 'Good Faith Violation'], example: 'Trade Monday: Stock settles Tuesday. Trade Friday: Stock settles Monday. You can\'t withdraw sale proceeds until settlement.' },
  { term: 'Cash Account', category: 'regulations', shortDef: 'No margin, no borrowing', fullExplanation: 'Cash accounts only use available settled cash for purchases. No margin or borrowing, but subject to Good Faith and Freeriding violations. Not subject to PDT rule.', whyUseful: 'Simpler, no margin risk, no PDT rules.', whyNotUseful: 'Limited buying power, settlement restrictions.', relatedTerms: ['Margin Account', 'Good Faith Violation'], example: 'With $10,000 settled cash, you can only buy $10,000 of stock. You cannot day trade the same cash until it settles again (T+1).' },
  { term: 'Margin Account', category: 'regulations', shortDef: 'Can borrow to trade', fullExplanation: 'Margin accounts allow borrowing from broker to buy securities. Provides 2x buying power overnight, 4x intraday for PDT. Subject to PDT rules if making 4+ day trades in 5 days with < $25,000 equity.', whyUseful: 'Increased buying power.', whyNotUseful: 'Margin calls, interest, PDT restrictions.', relatedTerms: ['Cash Account', 'Pattern Day Trader'], example: 'With $25,000 cash in a margin account, you could buy up to $50,000 of stock (2x) overnight, or $100,000 intraday if PDT.' },
  { term: 'SEC', category: 'regulations', shortDef: 'Securities and Exchange Commission', fullExplanation: 'The SEC is the primary federal regulator of securities markets, enforcing securities laws, protecting investors, and maintaining fair, orderly, and efficient markets.', whyUseful: 'Understand the regulatory landscape.', example: 'The SEC enforces insider trading laws, requires company disclosures (10-K, 10-Q), and sets settlement rules like T+1.' },
  { term: 'Pattern Day Trader Rule', category: 'regulations', shortDef: '4+ day trades requires $25k', fullExplanation: 'FINRA Rule 4210: If you execute 4 or more day trades within 5 business days in a margin account, you are classified as a Pattern Day Trader. PDT accounts must maintain $25,000 minimum equity at all times. Falling below triggers restrictions.', whyUseful: 'Plan trading frequency to avoid restrictions.', whyNotUseful: 'Limits active trading for smaller accounts.', relatedTerms: ['Day Trade', 'Margin Account', 'FINRA'], example: 'Mon: Buy/sell AAPL, Tue: Buy/sell TSLA, Wed: Buy/sell NVDA, Thu: Buy/sell AMD = 4 day trades. If equity < $25k, account is restricted.' },
  { term: 'Wash Sale Rule', category: 'regulations', shortDef: 'No loss deduction if repurchased within 30 days', fullExplanation: 'IRS Section 1091: If you sell a security at a loss and repurchase the same or substantially identical security within 30 days (before or after), the loss is disallowed for tax purposes. The disallowed loss is added to your cost basis.', whyUseful: 'Critical for tax planning.', relatedTerms: ['Tax Loss Harvesting', 'Capital Gains'], example: 'Sell AAPL at $1,000 loss on Dec 15. Buy AAPL again on Jan 5 (21 days later). The $1,000 loss is disallowed, but added to new cost basis.' },
  { term: 'Margin Call', category: 'regulations', shortDef: 'Demand to deposit more funds', fullExplanation: 'A margin call occurs when your account equity falls below the maintenance margin requirement (typically 25%). You must deposit funds or securities, or your broker will liquidate positions to meet the requirement.', whyUseful: 'Avoid forced liquidations.', example: 'You buy $40,000 stock with $20,000 cash (50% margin). Stock drops 40% to $24,000. Your equity is now $4,000 (16.6%), below 25%. Margin call!' },
  { term: 'Maintenance Margin', category: 'regulations', shortDef: 'Minimum equity to hold position', fullExplanation: 'Maintenance margin is the minimum equity percentage required to maintain a margin position. FINRA requires 25% minimum, but brokers often require 30-40%. Falling below triggers a margin call.', whyUseful: 'Know your risk level.', example: 'With 30% maintenance requirement: On $100,000 position, you need at least $30,000 equity. If your equity drops to $25,000, you get a margin call.' },
  { term: 'Liquidation', category: 'regulations', shortDef: 'Forced selling of positions', fullExplanation: 'When you fail to meet a margin call, your broker can liquidate (forcibly sell) your positions without your consent to bring your account into compliance. They choose which positions to sell.', whyUseful: 'Understand the consequences of margin calls.', example: 'You receive a margin call for $5,000 and don\'t deposit. Your broker sells your NVDA shares worth $5,000 at market price to cover.' },
  { term: 'Day Trade Call', category: 'regulations', shortDef: 'PDT margin violation notice', fullExplanation: 'A day trade call occurs when a Pattern Day Trader exceeds their Day Trading Buying Power. You have 5 business days to deposit funds. Until met, DTBP is reduced and you may be limited to 2x leverage.', whyUseful: 'Avoid trading restrictions.', example: 'With $120,000 DTBP, you day trade $150,000 of stock. You receive a day trade call for $30,000. Must deposit within 5 days.' },
  { term: 'Equity Call', category: 'regulations', shortDef: 'PDT minimum equity notice', fullExplanation: 'An equity call occurs when a Pattern Day Trader\'s account falls below $25,000 minimum equity. You cannot day trade until equity is restored to $25,000.', whyUseful: 'Understand PDT equity requirements.', example: 'Your PDT account has $28,000. After losses, it drops to $23,000. You receive an equity call and cannot day trade until you deposit $2,000+.' },
  { term: 'Regulation SHO', category: 'regulations', shortDef: 'Short selling rules', fullExplanation: 'SEC Regulation SHO governs short sales, requiring brokers to locate shares before shorting and imposing price restrictions during significant price declines (circuit breakers).', whyUseful: 'Understand short selling rules.', example: 'Before shorting TSLA, your broker must confirm they can borrow the shares. If TSLA drops 10%+, short-sale price test triggers for rest of day and next day.' },
  { term: 'Circuit Breaker', category: 'regulations', shortDef: 'Market-wide trading halt', fullExplanation: 'SEC Rule 80B: Market-wide circuit breakers halt trading when S&P 500 drops 7% (Level 1), 13% (Level 2), or 20% (Level 3). Halts last 15 minutes except Level 3 (rest of day).', whyUseful: 'Know when markets may halt.', example: 'March 2020: S&P 500 dropped 7% at market open, triggering Level 1 circuit breaker. Trading halted 15 minutes.' },
  { term: 'LULD (Limit Up-Limit Down)', category: 'regulations', shortDef: 'Individual stock price bands', fullExplanation: 'LULD prevents extreme price swings in individual stocks. If price moves outside a calculated band (typically 5-20% from reference price), trading pauses for 5 minutes.', whyUseful: 'Understand why stocks might halt.', example: 'Stock XYZ trading at $100. LULD band is $95-$105. If price hits $105, trading pauses 5 minutes to let buyers/sellers recalibrate.' },
  { term: 'Accredited Investor', category: 'regulations', shortDef: 'Meets income/wealth requirements', fullExplanation: 'SEC definition: Individual with $200k+ income ($300k with spouse) for 2 years, or $1M+ net worth excluding primary residence. Accredited investors can access private placements and hedge funds.', whyUseful: 'Access more investment opportunities.', example: 'A pre-IPO startup only accepts investments from accredited investors. If your net worth is $1.2M (excluding home), you qualify.' },
  { term: 'Insider Trading', category: 'regulations', shortDef: 'Trading on non-public information', fullExplanation: 'SEC Rule 10b-5: It is illegal to trade securities based on material, non-public information. Applies to company insiders, their tippees, and anyone who misappropriates such information.', whyUseful: 'Avoid severe legal consequences.', example: 'A CFO tells her spouse about unannounced earnings beat. Spouse buys stock. Both can face criminal charges and civil penalties.' },
  { term: 'Form 4', category: 'regulations', shortDef: 'Insider trading disclosure', fullExplanation: 'SEC Form 4 must be filed within 2 business days when company insiders (officers, directors, 10%+ owners) buy or sell company stock. This is public information.', whyUseful: 'Track insider activity.', example: 'Elon Musk sells 1M Tesla shares. Within 2 days, a Form 4 is filed with SEC and becomes public. Traders analyze this for signals.' },
  { term: 'Suitability', category: 'regulations', shortDef: 'Investment must match investor profile', fullExplanation: 'FINRA suitability rules require that recommendations be suitable for the customer based on their investment profile, risk tolerance, and financial situation.', whyUseful: 'Protection from inappropriate recommendations.', example: 'A broker recommending highly leveraged options to a retiree seeking income could violate suitability rules.' },
  { term: 'Know Your Customer (KYC)', category: 'regulations', shortDef: 'Identity verification requirement', fullExplanation: 'Financial institutions must verify customer identities to prevent money laundering and fraud. Required information includes name, DOB, address, SSN, and employment.', whyUseful: 'Understand account opening requirements.', example: 'Opening a brokerage account requires uploading ID, verifying SSN, and answering questions about income and investment experience.' },
  // =========================================================================
  // Additional Trading Regulations & Restrictions (Added v2.1.10)
  // =========================================================================
  { term: 'Regulation T (Reg T)', category: 'regulations', shortDef: 'Initial margin requirement of 50%', fullExplanation: 'Federal Reserve Regulation T sets the initial margin requirement at 50% for purchasing securities on margin. You must deposit at least 50% of the purchase price in cash; the broker can lend the other 50%. This applies to the initial purchase only.', whyUseful: 'Understand minimum cash needed for margin purchases.', whyNotUseful: 'Restricts how much you can leverage on initial purchase.', relatedTerms: ['Margin Account', 'Initial Margin', 'Maintenance Margin'], example: 'To buy $10,000 of AAPL on margin, you need at least $5,000 cash (50%). The broker lends $5,000. This is Reg T initial margin.' },
  { term: 'Initial Margin', category: 'regulations', shortDef: '50% deposit required for margin trades', fullExplanation: 'Initial margin (set by Reg T at 50%) is the minimum equity percentage required when opening a new margin position. This is different from maintenance margin (typically 25%), which applies after the position is established.', whyUseful: 'Know upfront costs for margin trading.', relatedTerms: ['Reg T', 'Maintenance Margin', 'Margin Call'], example: 'Buying $20,000 of stock requires $10,000 initial margin (50%). Once purchased, you only need $5,000 (25% maintenance) to avoid a margin call.' },
  { term: 'Settled Funds', category: 'regulations', shortDef: 'Cleared cash available for trading', fullExplanation: 'Settled funds are cash that has completed the settlement process (T+1 for stocks since May 2024). In cash accounts, you can only buy with settled funds to avoid Good Faith Violations. Unsettled funds from a sale cannot be used immediately.', whyUseful: 'Avoid trading violations in cash accounts.', relatedTerms: ['T+1 Settlement', 'Good Faith Violation', 'Cash Account'], example: 'Monday: Sell $5,000 MSFT. The $5,000 is unsettled until Tuesday. In a cash account, you should not buy new stock with that $5,000 until Tuesday.' },
  { term: 'Unsettled Funds', category: 'regulations', shortDef: 'Cash from recent sale not yet cleared', fullExplanation: 'When you sell securities, the proceeds are unsettled until T+1. Using unsettled funds to buy new securities, then selling those before the original sale settles, can cause Good Faith Violations or Freeriding violations.', whyUseful: 'Avoid cash account violations.', relatedTerms: ['Settled Funds', 'Good Faith Violation', 'Freeriding'], example: 'You sell AAPL Monday for $3,000 (settles Tuesday). You buy NVDA Monday with that $3,000. If you sell NVDA before Tuesday, that\'s a violation.' },
  { term: 'Cash Liquidation Violation', category: 'regulations', shortDef: 'Selling before paying for purchase', fullExplanation: 'A Cash Liquidation Violation occurs in cash accounts when you buy securities and sell them before paying for the purchase with settled funds. Similar to Good Faith Violation but specifically when the sale proceeds are used to pay for the original purchase.', whyUseful: 'Avoid account restrictions.', relatedTerms: ['Good Faith Violation', 'Cash Account'], example: 'Monday: Buy $5,000 TSLA with unsettled funds. Monday: Sell TSLA for $5,100. You used sale proceeds to pay for the purchase = CLV.' },
  { term: '90-Day Restriction', category: 'regulations', shortDef: 'Cash-upfront penalty for violations', fullExplanation: 'After 3 Good Faith Violations or any Freeriding violation in 12 months, your cash account is restricted for 90 days. During this period, you can only buy securities if you have settled cash in the account at the time of purchase.', whyUseful: 'Understand consequences of violations.', relatedTerms: ['Good Faith Violation', 'Freeriding', 'Cash Account'], example: 'After 3 GFVs, you must have settled cash before any buy order for 90 days. No more same-day buying with sale proceeds.' },
  { term: 'Short Selling Restrictions', category: 'regulations', shortDef: 'Rules governing selling borrowed shares', fullExplanation: 'Short selling has multiple restrictions: locate requirement (broker must confirm shares available), uptick rule during 10%+ drops (can only short on uptick), Regulation SHO requirements, and some stocks may be hard-to-borrow or unavailable to short.', whyUseful: 'Understand when you can and cannot short.', relatedTerms: ['Regulation SHO', 'Hard to Borrow', 'Locate'], example: 'Stock XYZ drops 12% at open. Short-Sale Price Test triggers: you can only short at a price above the current best bid for the rest of today and tomorrow.' },
  { term: 'Hard to Borrow (HTB)', category: 'regulations', shortDef: 'Stocks difficult to locate for shorting', fullExplanation: 'Hard to Borrow stocks have limited shares available to borrow for short selling. HTB stocks incur higher borrow fees and may become impossible to short if no shares are available. Your broker provides a HTB list.', whyUseful: 'Know additional costs and limitations for shorting.', relatedTerms: ['Short Selling', 'Borrow Fee', 'Locate'], example: 'Shorting a HTB stock might cost 10-50% annualized borrow fee vs 0.25% for easy-to-borrow stocks. Meme stocks are often HTB.' },
  { term: 'Borrow Fee', category: 'regulations', shortDef: 'Cost to borrow shares for shorting', fullExplanation: 'When shorting, you pay a borrow fee to the share lender. Fees are quoted annualized and charged daily. Easy-to-borrow stocks might be 0.25-1% annually; hard-to-borrow can be 20-100%+ annually.', whyUseful: 'Factor into short-selling profit calculations.', relatedTerms: ['Hard to Borrow', 'Short Selling'], example: 'You short 1,000 shares of XYZ at $50 ($50,000). Borrow fee is 30% annually = $15,000/year or ~$41/day. Stock must drop enough to cover this cost.' },
  { term: 'Locate', category: 'regulations', shortDef: 'Confirming shares available to borrow', fullExplanation: 'Before executing a short sale, your broker must locate shares that can be borrowed. This is required by Regulation SHO. If no shares can be located, you cannot short the stock.', whyUseful: 'Understand why some shorts are rejected.', relatedTerms: ['Short Selling', 'Regulation SHO', 'Hard to Borrow'], example: 'You try to short 10,000 shares of a small-cap stock. Your broker\'s locate desk can only find 5,000. You can only short 5,000.' },
  { term: 'Options Level', category: 'regulations', shortDef: 'Broker approval for options strategies', fullExplanation: 'Brokers assign options trading levels based on your experience and risk tolerance. Level 1: Covered calls. Level 2: Long calls/puts. Level 3: Spreads. Level 4: Naked options. Each level requires additional approval.', whyUseful: 'Know which strategies you\'re approved for.', relatedTerms: ['Covered Call', 'Naked Option'], example: 'You want to sell naked puts but only have Level 2 approval. You must apply for Level 4, demonstrating experience and sufficient funds.' },
  { term: 'PDT Reset', category: 'regulations', shortDef: 'Resetting Pattern Day Trader status', fullExplanation: 'Once flagged as PDT, you can request a one-time PDT reset from your broker if you didn\'t intend to day trade. Alternatively, you can convert to a cash account (no margin, no PDT rules) or wait for equity to reach $25,000.', whyUseful: 'Options to escape PDT restrictions.', relatedTerms: ['Pattern Day Trader', 'Cash Account'], example: 'Accidentally flagged as PDT with $15,000 equity. Request one-time reset from broker, or convert to cash account to continue trading (with settlement restrictions).' },
  { term: 'Margin Interest', category: 'regulations', shortDef: 'Interest charged on borrowed funds', fullExplanation: 'When you borrow funds from your broker (margin), you pay interest on the borrowed amount. Rates vary by broker and loan amount, typically 5-13% annually. Interest accrues daily on your margin debit.', whyUseful: 'Factor into holding costs.', relatedTerms: ['Margin Account', 'Buying Power'], example: 'You borrow $10,000 on margin at 8% annual rate. Monthly interest = $10,000 × 8% / 12 = $67. Holding for a year costs $800 in interest.' },
  { term: 'Free Riding', category: 'regulations', shortDef: 'Trading with proceeds before settlement', fullExplanation: 'Free riding is buying securities with unsettled proceeds, selling them, and using those sale proceeds before the original trade settles. It violates Regulation T and results in a 90-day cash-upfront restriction.', whyUseful: 'Avoid severe account penalties.', relatedTerms: ['Freeriding', 'Good Faith Violation', 'Settled Funds'], example: 'Day 1: Sell ABC, buy XYZ with unsettled proceeds, sell XYZ. You profited using money you never actually had = free riding. 90-day restriction.' },
  { term: 'Concentrated Position', category: 'regulations', shortDef: 'Single stock exceeds portfolio threshold', fullExplanation: 'Many brokers restrict margin on concentrated positions (typically >30-50% of portfolio in one stock). The position may receive reduced margin or require additional equity. This is a risk management rule, not SEC regulation.', whyUseful: 'Understand margin restrictions on large positions.', relatedTerms: ['Margin', 'Position Sizing'], example: 'Your $100,000 portfolio is 60% in TSLA. Broker may only give 25% margin on TSLA position instead of 50%, or require you to reduce the position.' },
  { term: 'Excess Margin', category: 'regulations', shortDef: 'Equity above margin requirements', fullExplanation: 'Excess margin (or SMA - Special Memorandum Account) is the amount of equity you have above the margin requirement. This determines your buying power. Excess margin can be withdrawn or used to buy more securities.', whyUseful: 'Understand available trading capacity.', relatedTerms: ['Buying Power', 'Margin Account'], example: 'Account equity: $40,000. Margin requirement: $25,000. Excess margin: $15,000. You can buy up to $30,000 more stock (2x leverage) or withdraw the $15,000.' },
  { term: 'Overnight Margin', category: 'regulations', shortDef: '2x leverage for positions held overnight', fullExplanation: 'For positions held overnight, most brokers provide 2:1 margin (50% requirement per Reg T). This is less than the 4:1 intraday margin available to Pattern Day Traders. You must reduce positions or add funds if you exceed overnight limits.', whyUseful: 'Plan position sizes for overnight holds.', relatedTerms: ['Day Trading Buying Power', 'Reg T', 'Margin Account'], example: 'DTBP: $200,000 intraday. But to hold overnight, you can only keep $100,000 in positions (2:1 margin vs 4:1 intraday).' },
  { term: 'Anti-Money Laundering (AML)', category: 'regulations', shortDef: 'Preventing illicit fund flows', fullExplanation: 'AML regulations require financial institutions to detect and report suspicious activity, maintain records, and implement compliance programs to prevent money laundering.', whyUseful: 'Understand compliance requirements.', example: 'Depositing exactly $9,999 repeatedly to avoid $10,000 reporting threshold is called "structuring" and is illegal under AML laws.' },
  { term: 'SMA', category: 'basics', shortDef: 'Special Memorandum Account', fullExplanation: 'SMA tracks excess margin available. Can be used for additional purchases.', whyUseful: 'Maximize buying power.' },
  { term: 'House Call', category: 'basics', shortDef: 'Broker margin call', fullExplanation: 'House call is when broker requires additional funds because you\'re below their (not regulatory) limits.', whyUseful: 'Understand broker-specific requirements.' },
  { term: 'Sweep Account', category: 'basics', shortDef: 'Automatic cash management', fullExplanation: 'Sweep accounts automatically move idle cash into interest-bearing accounts.', whyUseful: 'Earn interest on cash balances.' },
  { term: 'Core Position', category: 'strategies', shortDef: 'Long-term portfolio holding', fullExplanation: 'Core positions are long-term holdings around which you trade tactical positions.', whyUseful: 'Anchor portfolio with conviction positions.' },
  { term: 'Trading Position', category: 'strategies', shortDef: 'Short-term tactical trade', fullExplanation: 'Trading positions are shorter-term trades around core positions.', whyUseful: 'Add value through active trading.' },
  { term: 'Watchlist', category: 'basics', shortDef: 'List of securities to monitor', fullExplanation: 'Watchlist is a saved list of securities you\'re tracking for potential trades.', whyUseful: 'Organize trading ideas.', xfactorUsage: 'XFactor includes watchlist features.' },
  { term: 'Scanner', category: 'basics', shortDef: 'Tool to find securities meeting criteria', fullExplanation: 'Scanners filter the market by criteria: volume, price, technical patterns, fundamentals.', whyUseful: 'Find trading candidates systematically.' },
  { term: 'Alert', category: 'basics', shortDef: 'Notification when condition is met', fullExplanation: 'Alerts notify you when price, volume, or other conditions are met. Don\'t need to watch constantly.', whyUseful: 'Monitor markets passively.', xfactorUsage: 'XFactor includes price and event alerts.' },
  { term: 'Hotkey', category: 'basics', shortDef: 'Keyboard shortcut for fast execution', fullExplanation: 'Hotkeys allow instant order entry with keyboard. Essential for day traders needing speed.', whyUseful: 'Faster execution for active traders.' },
  { term: 'Level 1 Data', category: 'basics', shortDef: 'Best bid and ask only', fullExplanation: 'Level 1 shows only the best bid and ask prices. Basic quote data included with most brokers.', whyUseful: 'Basic quote information.' },
  { term: 'Level 3 Data', category: 'indicators', shortDef: 'Full order book', fullExplanation: 'Level 3 shows full order book including all orders at all prices. Available to market makers.', whyUseful: 'Complete market visibility.' },
  { term: 'Total Return', category: 'fundamentals', shortDef: 'Price change plus dividends', fullExplanation: 'Total return includes both price appreciation and dividends reinvested. True measure of investment return.', whyUseful: 'Compare performance accurately.', formula: 'Total Return = (Ending Value - Starting Value + Dividends) / Starting Value' },
  { term: 'Price Return', category: 'fundamentals', shortDef: 'Return from price change only', fullExplanation: 'Price return only measures price appreciation, excluding dividends.', whyUseful: 'Understand components of return.' },
  { term: 'Excess Return', category: 'fundamentals', shortDef: 'Return above benchmark or risk-free', fullExplanation: 'Excess return is performance above a benchmark or risk-free rate.', whyUseful: 'Measure value added.' },
  { term: 'Benchmark', category: 'basics', shortDef: 'Standard for comparison', fullExplanation: 'A benchmark is the index or standard you compare performance against. S&P 500 is common.', whyUseful: 'Evaluate relative performance.' },
  { term: 'Index Fund', category: 'basics', shortDef: 'Fund that tracks an index', fullExplanation: 'Index funds passively track a market index like S&P 500. Low cost, market returns.', whyUseful: 'Simple, cheap market exposure.' },
  { term: 'Active Management', category: 'strategies', shortDef: 'Attempting to beat the market', fullExplanation: 'Active management tries to outperform through stock selection and timing. Higher fees.', whyUseful: 'Potential alpha.', whyNotUseful: 'Most underperform after fees.' },
  { term: 'Passive Management', category: 'strategies', shortDef: 'Tracking index returns', fullExplanation: 'Passive management tracks an index without trying to outperform. Lower costs, market returns.', whyUseful: 'Low-cost market exposure.' },
  { term: 'Rebalancing', category: 'strategies', shortDef: 'Returning portfolio to target weights', fullExplanation: 'Rebalancing sells winners and buys losers to return to target allocation. Forced discipline.', whyUseful: 'Maintain intended risk profile.' },
  { term: 'Tax-Advantaged', category: 'basics', shortDef: 'Accounts with tax benefits', fullExplanation: 'Tax-advantaged accounts like 401(k), IRA offer tax deferral or tax-free growth.', whyUseful: 'Maximize after-tax returns.' },
  { term: 'Tax Efficiency', category: 'strategies', shortDef: 'Minimizing tax impact', fullExplanation: 'Tax-efficient investing minimizes tax drag through location, holding period, loss harvesting.', whyUseful: 'Keep more of your returns.' },
  { term: 'Qualified Dividend', category: 'basics', shortDef: 'Dividend with lower tax rate', fullExplanation: 'Qualified dividends are taxed at lower long-term capital gains rates. Must meet holding period.', whyUseful: 'Tax-advantaged income.' },
  { term: 'Unrealized Gain', category: 'basics', shortDef: 'Paper profit not yet locked in', fullExplanation: 'Unrealized gain is profit on open position that hasn\'t been sold yet.', whyUseful: 'Not taxed until realized.' },
  { term: 'Realized Gain', category: 'basics', shortDef: 'Profit from closed position', fullExplanation: 'Realized gain is profit after selling. Creates tax event.', whyUseful: 'Taxable event.' },
  { term: 'Short-Term Gain', category: 'basics', shortDef: 'Gain on asset held less than 1 year', fullExplanation: 'Short-term capital gains are taxed as ordinary income. Higher rates.', whyUseful: 'Understand tax implications.' },
  { term: 'Long-Term Gain', category: 'basics', shortDef: 'Gain on asset held over 1 year', fullExplanation: 'Long-term capital gains have preferential tax rates: 0%, 15%, or 20% depending on income.', whyUseful: 'Hold over 1 year when possible.' },
  { term: 'Mark-to-Market', category: 'basics', shortDef: 'Valuing positions at current price', fullExplanation: 'Mark-to-market values all positions at current market price. Shows true portfolio value.', whyUseful: 'Real-time P&L accounting.' },
  { term: 'LIFO', category: 'basics', shortDef: 'Last In First Out', fullExplanation: 'LIFO sells most recently purchased shares first. Can manage tax consequences.', whyUseful: 'Tax management flexibility.' },
  { term: 'Specific ID', category: 'basics', shortDef: 'Choosing which shares to sell', fullExplanation: 'Specific identification lets you choose which tax lots to sell for optimal tax result.', whyUseful: 'Maximize tax efficiency.' },
  // =========================================================================
  // Extended Glossary v2.1.10 - Additional Terms to reach 1000+
  // =========================================================================
  // OPTIONS - Advanced Greeks and Strategies
  { term: 'Vanna', category: 'indicators', shortDef: 'Rate of change of delta with respect to volatility', fullExplanation: 'Vanna measures how delta changes when implied volatility changes. Important for options traders hedging volatility exposure.', whyUseful: 'Understand delta sensitivity to IV.' },
  { term: 'Charm', category: 'indicators', shortDef: 'Rate of change of delta over time', fullExplanation: 'Charm (delta decay) measures how delta changes as time passes. ATM options have highest charm as expiration approaches.', whyUseful: 'Predict delta changes as expiration nears.' },
  { term: 'Vomma', category: 'indicators', shortDef: 'Rate of change of vega with respect to volatility', fullExplanation: 'Vomma measures how vega changes when implied volatility changes. Higher for OTM options.', whyUseful: 'Second-order volatility exposure.' },
  { term: 'Zomma', category: 'indicators', shortDef: 'Rate of change of gamma with respect to volatility', fullExplanation: 'Zomma measures how gamma changes when implied volatility changes.', whyUseful: 'Third-order Greeks for complex hedging.' },
  { term: 'Color', category: 'indicators', shortDef: 'Rate of change of gamma over time', fullExplanation: 'Color measures how gamma changes as time passes. Important for gamma scalping strategies.', whyUseful: 'Track gamma decay.' },
  { term: 'Speed', category: 'indicators', shortDef: 'Rate of change of gamma with respect to price', fullExplanation: 'Speed (DgammaDspot) measures how gamma changes with underlying price movement.', whyUseful: 'Third-order price sensitivity.' },
  { term: 'Ultima', category: 'indicators', shortDef: 'Third derivative of option price to volatility', fullExplanation: 'Ultima measures sensitivity of vomma to changes in implied volatility.', whyUseful: 'Advanced volatility modeling.' },
  { term: 'Lambda', category: 'indicators', shortDef: 'Option elasticity/leverage', fullExplanation: 'Lambda measures percentage change in option price for 1% change in underlying. Shows effective leverage of options position.', whyUseful: 'Understand true leverage.' },
  { term: 'Butterfly Spread', category: 'strategies', shortDef: 'Low-cost neutral strategy', fullExplanation: 'A butterfly uses 4 options at 3 strikes. Long 1 lower, short 2 middle, long 1 higher. Profits if price stays at middle strike.', whyUseful: 'Cheap way to bet on low volatility.', formula: 'Max Profit at middle strike = Width - Net Debit' },
  { term: 'Condor Spread', category: 'strategies', shortDef: 'Wide-range neutral strategy', fullExplanation: 'Like butterfly but with 4 different strikes. Wider profit zone but lower max profit.', whyUseful: 'Bet on range-bound movement.' },
  { term: 'Calendar Spread', category: 'strategies', shortDef: 'Time decay strategy using different expirations', fullExplanation: 'Sell near-term option, buy longer-term at same strike. Profits from faster decay of short leg.', whyUseful: 'Harvest theta differential.' },
  { term: 'Diagonal Spread', category: 'strategies', shortDef: 'Calendar with different strikes', fullExplanation: 'Combines time and directional exposure. Sell short-term, buy long-term at different strikes.', whyUseful: 'Directional bias with time decay.' },
  { term: 'Ratio Spread', category: 'strategies', shortDef: 'Unequal number of long/short options', fullExplanation: 'Buy 1 option, sell 2 (or more) at different strike. Can be done for credit. Has unlimited risk on short side.', whyUseful: 'Income strategy with directional view.', whyNotUseful: 'Unlimited loss potential.' },
  { term: 'Backspread', category: 'strategies', shortDef: 'Sell fewer, buy more options', fullExplanation: 'Sell 1 ATM, buy 2 OTM. Profits from large moves in one direction. Limited risk, unlimited profit potential.', whyUseful: 'Cheap way to bet on big moves.' },
  { term: 'Jade Lizard', category: 'strategies', shortDef: 'Short put spread + naked short call', fullExplanation: 'Sell OTM put spread + sell OTM call. Collects premium on both sides with no upside risk if done for credit.', whyUseful: 'Enhanced premium collection.' },
  { term: 'Broken Wing Butterfly', category: 'strategies', shortDef: 'Asymmetric butterfly spread', fullExplanation: 'Butterfly with unequal wing widths. Can be done for credit with no risk on one side.', whyUseful: 'Directional butterfly variant.' },
  { term: 'Poor Man\'s Covered Call', category: 'strategies', shortDef: 'LEAPS + short-term calls', fullExplanation: 'Buy deep ITM LEAPS, sell short-term OTM calls against it. Synthetic covered call with less capital.', whyUseful: 'Capital-efficient covered call.' },
  { term: 'Skip Strike Butterfly', category: 'strategies', shortDef: 'Butterfly with gap between strikes', fullExplanation: 'Like butterfly but skips the middle strike. Creates two profit zones instead of one.', whyUseful: 'Modified payout structure.' },
  { term: 'Christmas Tree', category: 'strategies', shortDef: 'Increasing quantities at different strikes', fullExplanation: 'Buy 1, sell 2, buy 3 at progressively higher strikes. Creates unique risk profile.', whyUseful: 'Complex payout structure.' },
  { term: 'Seagull', category: 'strategies', shortDef: 'Collar with wider strikes', fullExplanation: 'Protective put + covered call with wider strikes. Like a collar but with more room to run.', whyUseful: 'Low-cost hedging with upside.' },
  { term: 'Fence', category: 'strategies', shortDef: 'Collar strategy alternative name', fullExplanation: 'Same as collar: long stock + protective put + covered call. Limits both upside and downside.', whyUseful: 'Hedging synonym.' },
  { term: 'Synthetic Long', category: 'strategies', shortDef: 'Options mimicking stock ownership', fullExplanation: 'Buy ATM call + sell ATM put = synthetic long stock. Same profit/loss profile as owning shares.', whyUseful: 'Stock exposure without buying shares.' },
  { term: 'Synthetic Short', category: 'strategies', shortDef: 'Options mimicking short stock', fullExplanation: 'Sell ATM call + buy ATM put = synthetic short stock. Same P/L as shorting shares.', whyUseful: 'Short exposure without borrowing shares.' },
  { term: 'Box Spread', category: 'strategies', shortDef: 'Arbitrage strategy with guaranteed return', fullExplanation: 'Combination of bull call spread + bear put spread. Creates risk-free position if done at discount to strike width.', whyUseful: 'Arbitrage opportunity.', whyNotUseful: 'Hard to find mispricing.' },
  { term: 'Conversion', category: 'strategies', shortDef: 'Arbitrage: long stock + synthetic short', fullExplanation: 'Buy stock + buy put + sell call (same strike). Should equal zero if options are fairly priced.', whyUseful: 'Arbitrage between stock and options.' },
  { term: 'Reversal', category: 'strategies', shortDef: 'Arbitrage: short stock + synthetic long', fullExplanation: 'Short stock + sell put + buy call (same strike). Opposite of conversion.', whyUseful: 'Arbitrage opportunity.' },
  { term: 'Jelly Roll', category: 'strategies', shortDef: 'Time spread arbitrage', fullExplanation: 'Synthetic long in one expiration + synthetic short in another. Exploits time value differences.', whyUseful: 'Calendar arbitrage.' },
  { term: 'Pin Risk', category: 'risk', shortDef: 'Risk when stock closes at strike', fullExplanation: 'When stock closes exactly at strike at expiration, assignment is uncertain. May be exercised on some but not all contracts.', whyUseful: 'Manage expiration positions.' },
  { term: 'Assignment Risk', category: 'risk', shortDef: 'Risk of being assigned on short options', fullExplanation: 'Short option holders can be assigned at any time (American style). ITM options near dividend or expiration have highest risk.', whyUseful: 'Prepare for potential assignment.' },
  { term: 'Early Exercise', category: 'basics', shortDef: 'Exercising option before expiration', fullExplanation: 'American options can be exercised early. Typically done for deep ITM calls before dividend or deep ITM puts when interest > remaining time value.', whyUseful: 'Understand when early exercise makes sense.' },
  { term: 'European Style', category: 'basics', shortDef: 'Exercise only at expiration', fullExplanation: 'European options can only be exercised at expiration. SPX, VIX options are European. No early assignment risk.', whyUseful: 'No early assignment risk.' },
  { term: 'American Style', category: 'basics', shortDef: 'Exercise any time before expiration', fullExplanation: 'American options can be exercised any time. Most stock options are American. Allows early exercise for dividends.', whyUseful: 'Flexibility to exercise early.' },
  { term: 'Cash Settlement', category: 'basics', shortDef: 'Options settle in cash not shares', fullExplanation: 'Cash-settled options pay the intrinsic value in cash at expiration. SPX, NDX, VIX options are cash-settled.', whyUseful: 'No need to buy/sell underlying.' },
  { term: 'Physical Settlement', category: 'basics', shortDef: 'Options settle with actual shares', fullExplanation: 'Physical settlement delivers actual shares. Equity options are typically physically settled.', whyUseful: 'Get actual shares on exercise.' },
  // CRYPTO/DEFI - Extended Terms
  { term: 'Layer 1', category: 'basics', shortDef: 'Base blockchain protocol', fullExplanation: 'Layer 1 is the base blockchain (Bitcoin, Ethereum). Provides consensus and security. L1s can be slow and expensive.', whyUseful: 'Understand blockchain hierarchy.' },
  { term: 'Layer 2', category: 'basics', shortDef: 'Scaling solution on top of L1', fullExplanation: 'Layer 2s (Arbitrum, Optimism, Polygon) process transactions off L1 for speed and cost, then settle to L1 for security.', whyUseful: 'Faster, cheaper transactions.' },
  { term: 'Rollup', category: 'basics', shortDef: 'L2 batching transactions', fullExplanation: 'Rollups bundle many L2 transactions into one L1 transaction. Optimistic rollups assume validity; ZK rollups prove validity.', whyUseful: 'Scalability solution.' },
  { term: 'Optimistic Rollup', category: 'basics', shortDef: 'Rollup assuming transaction validity', fullExplanation: 'Optimistic rollups assume transactions are valid. Anyone can challenge within a dispute period. Arbitrum, Optimism use this.', whyUseful: 'Faster than ZK with trade-offs.' },
  { term: 'ZK Rollup', category: 'basics', shortDef: 'Zero-knowledge proof rollup', fullExplanation: 'ZK rollups use cryptographic proofs to prove transaction validity. No dispute period needed but computationally intensive.', whyUseful: 'Mathematically guaranteed validity.' },
  { term: 'Bridge', category: 'basics', shortDef: 'Cross-chain asset transfer', fullExplanation: 'Bridges move assets between blockchains. Lock on source chain, mint on destination. Security varies; bridges are common attack targets.', whyUseful: 'Multi-chain trading.', whyNotUseful: 'Bridge hacks are common.' },
  { term: 'Wrapped Token', category: 'basics', shortDef: 'Token representing asset on another chain', fullExplanation: 'Wrapped tokens (WBTC, WETH) represent assets from other chains. Backed 1:1 by original asset held in custody.', whyUseful: 'Use BTC on Ethereum.' },
  { term: 'Oracle', category: 'basics', shortDef: 'External data feed for smart contracts', fullExplanation: 'Oracles (Chainlink) bring off-chain data on-chain. Price feeds, weather, events. Critical for DeFi price discovery.', whyUseful: 'Enable smart contracts to use real-world data.' },
  { term: 'Flash Loan', category: 'strategies', shortDef: 'Uncollateralized loan repaid in same transaction', fullExplanation: 'Flash loans borrow any amount without collateral, as long as repaid within the same transaction. Used for arbitrage.', whyUseful: 'Capital-free arbitrage.', whyNotUseful: 'Complex execution.' },
  { term: 'Impermanent Loss', category: 'risk', shortDef: 'LP loss vs holding', fullExplanation: 'When providing liquidity, if asset prices diverge, LP tokens may be worth less than simply holding. Called impermanent because it reverses if prices converge.', whyUseful: 'Understand LP risks.', formula: 'IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1' },
  { term: 'TVL', category: 'indicators', shortDef: 'Total Value Locked', fullExplanation: 'TVL measures total assets deposited in a DeFi protocol. Key metric for protocol health and adoption.', whyUseful: 'Gauge protocol adoption.' },
  { term: 'APY', category: 'indicators', shortDef: 'Annual Percentage Yield', fullExplanation: 'APY includes compound interest effect. Higher than APR for same rate. DeFi protocols often show APY.', whyUseful: 'Compare yield opportunities.', formula: 'APY = (1 + APR/n)^n - 1' },
  { term: 'APR', category: 'indicators', shortDef: 'Annual Percentage Rate', fullExplanation: 'APR is simple interest rate without compounding. Multiply daily/weekly rate by periods to get APR.', whyUseful: 'Simple rate calculation.' },
  { term: 'Liquidity Pool', category: 'basics', shortDef: 'Paired tokens for DEX trading', fullExplanation: 'Liquidity pools contain paired tokens (ETH/USDC). AMMs use pools for trading. LPs earn trading fees.', whyUseful: 'Enable decentralized trading.' },
  { term: 'AMM', category: 'basics', shortDef: 'Automated Market Maker', fullExplanation: 'AMMs use algorithms instead of order books. Most common: x*y=k constant product formula. Uniswap pioneered this.', whyUseful: 'Understand DEX mechanics.', formula: 'x * y = k' },
  { term: 'Slippage Tolerance', category: 'basics', shortDef: 'Acceptable price deviation', fullExplanation: 'Maximum price difference you accept between quote and execution. Higher slippage needed for large trades or illiquid pairs.', whyUseful: 'Protect against bad fills.' },
  { term: 'MEV', category: 'risk', shortDef: 'Maximal Extractable Value', fullExplanation: 'MEV is profit miners/validators can extract by reordering transactions. Includes frontrunning, sandwich attacks, arbitrage.', whyUseful: 'Understand hidden trading costs.' },
  { term: 'Frontrunning', category: 'risk', shortDef: 'Trading before known order', fullExplanation: 'Seeing pending transaction, placing order ahead of it to profit. Bots monitor mempool for opportunities.', whyUseful: 'Understand MEV risks.' },
  { term: 'Sandwich Attack', category: 'risk', shortDef: 'Front and back running victim', fullExplanation: 'Attacker buys before victim, then sells after. Victim gets worse price; attacker profits from price impact.', whyUseful: 'Protect against MEV.' },
  { term: 'Gas Fee', category: 'basics', shortDef: 'Transaction cost on blockchain', fullExplanation: 'Gas fees pay for computation on Ethereum. Higher during network congestion. Measured in gwei (10^-9 ETH).', whyUseful: 'Factor into trade costs.' },
  { term: 'Gwei', category: 'basics', shortDef: 'Ethereum gas unit', fullExplanation: 'Gwei is 0.000000001 ETH. Gas prices quoted in gwei. Typical range 10-500 gwei depending on network activity.', whyUseful: 'Understand gas pricing.' },
  { term: 'Staking', category: 'strategies', shortDef: 'Locking tokens for rewards', fullExplanation: 'Staking locks tokens to support network operations. Earn rewards for securing the network. ETH staking earns ~4% APY.', whyUseful: 'Passive crypto income.' },
  { term: 'Validator', category: 'basics', shortDef: 'Node verifying transactions', fullExplanation: 'Validators stake tokens to process and verify transactions. Earn rewards for honest work; lose stake for misbehavior.', whyUseful: 'Network security.' },
  { term: 'Slashing', category: 'risk', shortDef: 'Penalty for validator misbehavior', fullExplanation: 'Validators lose staked tokens for double-signing or extended downtime. Security mechanism.', whyUseful: 'Understand staking risks.' },
  { term: 'Governance Token', category: 'basics', shortDef: 'Token granting voting rights', fullExplanation: 'Governance tokens (UNI, AAVE) allow voting on protocol changes. More tokens = more voting power. Some also share protocol fees.', whyUseful: 'Participate in protocol decisions.' },
  { term: 'DAO', category: 'basics', shortDef: 'Decentralized Autonomous Organization', fullExplanation: 'DAOs are blockchain-based organizations governed by token holders. Treasury controlled by smart contracts and votes.', whyUseful: 'New organizational structure.' },
  { term: 'NFT', category: 'basics', shortDef: 'Non-Fungible Token', fullExplanation: 'NFTs are unique tokens representing ownership of digital or physical items. Art, collectibles, gaming items.', whyUseful: 'Digital ownership.' },
  { term: 'Mint', category: 'basics', shortDef: 'Creating new tokens', fullExplanation: 'Minting creates new tokens or NFTs. Can refer to initial creation or reward emissions.', whyUseful: 'Understand token issuance.' },
  { term: 'Burn', category: 'basics', shortDef: 'Permanently destroying tokens', fullExplanation: 'Burning sends tokens to irretrievable address. Reduces supply. Used to increase scarcity or reduce inflation.', whyUseful: 'Token economics.' },
  { term: 'Airdrop', category: 'basics', shortDef: 'Free token distribution', fullExplanation: 'Airdrops distribute free tokens to wallet holders. Often for marketing or rewarding early users.', whyUseful: 'Free tokens opportunity.' },
  { term: 'Vesting', category: 'regulations', shortDef: 'Gradual token unlock schedule', fullExplanation: 'Vesting releases tokens gradually over time. Prevents team/investor dumps. Typical: 1-4 year vesting with cliff.', whyUseful: 'Understand sell pressure.' },
  { term: 'Cliff', category: 'regulations', shortDef: 'Initial lockup before vesting starts', fullExplanation: 'Cliff period where no tokens unlock. After cliff, remaining tokens vest over time. Typical: 6-12 month cliff.', whyUseful: 'Predict unlock events.' },
  { term: 'Tokenomics', category: 'fundamentals', shortDef: 'Token economic model', fullExplanation: 'Tokenomics covers supply, distribution, utility, and incentive structure of a token. Critical for fundamental analysis.', whyUseful: 'Evaluate token value.' },
  { term: 'Fully Diluted Value', category: 'fundamentals', shortDef: 'Market cap if all tokens released', fullExplanation: 'FDV = Price × Max Supply. Shows theoretical max market cap. Compare to current market cap for dilution.', whyUseful: 'Assess future dilution.', formula: 'FDV = Price × Max Supply' },
  { term: 'Circulating Supply', category: 'fundamentals', shortDef: 'Tokens currently tradeable', fullExplanation: 'Circulating supply is tokens actually available for trading. Excludes locked, vesting, or unreleased tokens.', whyUseful: 'Real market cap calculation.' },
  { term: 'Max Supply', category: 'fundamentals', shortDef: 'Maximum tokens ever', fullExplanation: 'Max supply is hard cap on total tokens. Bitcoin: 21M. Some tokens have no max supply (inflationary).', whyUseful: 'Understand scarcity.' },
  // TECHNICAL ANALYSIS - More Indicators
  { term: 'CCI', category: 'indicators', shortDef: 'Commodity Channel Index', fullExplanation: 'CCI measures price deviation from average. +100 overbought, -100 oversold. Originally for commodities, works on all.', whyUseful: 'Cyclical overbought/oversold.', formula: 'CCI = (Typical Price - 20 SMA) / (0.015 × Mean Deviation)' },
  { term: 'MFI', category: 'indicators', shortDef: 'Money Flow Index', fullExplanation: 'MFI is RSI but volume-weighted. 80+ overbought, 20- oversold. Shows volume conviction in moves.', whyUseful: 'Volume-confirmed momentum.' },
  { term: 'CMF', category: 'indicators', shortDef: 'Chaikin Money Flow', fullExplanation: 'CMF measures buying/selling pressure using volume and close location within range. Positive = accumulation.', whyUseful: 'Institutional flow detection.' },
  { term: 'A/D Line', category: 'indicators', shortDef: 'Accumulation/Distribution Line', fullExplanation: 'A/D Line cumulates volume-weighted price moves. Rising A/D with price = confirmation. Divergence = warning.', whyUseful: 'Volume-price confirmation.' },
  { term: 'Force Index', category: 'indicators', shortDef: 'Price change × volume', fullExplanation: 'Force Index combines price change and volume to measure strength. Large force = strong conviction.', whyUseful: 'Measure move strength.' },
  { term: 'Keltner Channel', category: 'indicators', shortDef: 'ATR-based envelope', fullExplanation: 'Keltner Channels use ATR for band width instead of standard deviation (Bollinger). 20 EMA center, 2 ATR bands.', whyUseful: 'Volatility-adaptive bands.' },
  { term: 'Donchian Channel', category: 'indicators', shortDef: 'Highest high/lowest low bands', fullExplanation: 'Donchian Channels plot N-period high and low. Breakouts above high = buy signal. Used in Turtle trading.', whyUseful: 'Breakout trading.' },
  { term: 'Ichimoku Cloud', category: 'indicators', shortDef: 'Multi-component Japanese indicator', fullExplanation: 'Ichimoku has 5 components: Tenkan, Kijun, Senkou A, Senkou B, Chikou. Cloud (Kumo) shows support/resistance.', whyUseful: 'Comprehensive trend/S&R system.' },
  { term: 'Tenkan-Sen', category: 'indicators', shortDef: 'Ichimoku conversion line', fullExplanation: 'Tenkan = (9-period High + 9-period Low) / 2. Fast signal line in Ichimoku system.', whyUseful: 'Short-term trend.' },
  { term: 'Kijun-Sen', category: 'indicators', shortDef: 'Ichimoku base line', fullExplanation: 'Kijun = (26-period High + 26-period Low) / 2. Base line, slower than Tenkan. Crossovers generate signals.', whyUseful: 'Medium-term trend.' },
  { term: 'Kumo', category: 'indicators', shortDef: 'Ichimoku cloud', fullExplanation: 'Kumo (cloud) is area between Senkou A and B. Price above cloud = bullish. Thick cloud = strong S/R.', whyUseful: 'Visual support/resistance.' },
  { term: 'TRIX', category: 'indicators', shortDef: 'Triple exponential average', fullExplanation: 'TRIX is rate of change of triple-smoothed EMA. Filters noise. Zero-line crossovers are signals.', whyUseful: 'Smooth momentum.' },
  { term: 'ROC', category: 'indicators', shortDef: 'Rate of Change', fullExplanation: 'ROC measures percent change from N periods ago. Simple momentum indicator.', whyUseful: 'Price momentum.', formula: 'ROC = (Close - Close N ago) / Close N ago × 100' },
  { term: 'Ultimate Oscillator', category: 'indicators', shortDef: 'Multi-timeframe momentum', fullExplanation: 'Ultimate Oscillator averages momentum across 3 timeframes. Reduces false signals from single timeframe.', whyUseful: 'Multi-period confirmation.' },
  { term: 'Aroon', category: 'indicators', shortDef: 'Time since high/low', fullExplanation: 'Aroon measures periods since 25-period high (Aroon Up) and low (Aroon Down). Crossovers signal trend changes.', whyUseful: 'Trend timing.' },
  { term: 'Chande Momentum', category: 'indicators', shortDef: 'Modified momentum oscillator', fullExplanation: 'CMO similar to RSI but ranges from -100 to +100. No smoothing applied.', whyUseful: 'Unsmoothed momentum.' },
  { term: 'Accumulation Swing Index', category: 'indicators', shortDef: 'Cumulative swing index', fullExplanation: 'ASI accumulates swing index values. Confirms trendline breakouts when ASI breaks first.', whyUseful: 'Breakout confirmation.' },
  { term: 'Coppock Curve', category: 'indicators', shortDef: 'Long-term momentum', fullExplanation: 'Coppock adds 11 and 14 month ROC, then smoothes. Designed for monthly charts. Buy when turns up from below zero.', whyUseful: 'Long-term buy signal.' },
  { term: 'Ease of Movement', category: 'indicators', shortDef: 'Price change vs volume', fullExplanation: 'EOM shows relationship between price range and volume. High EOM = easy movement on low volume.', whyUseful: 'Volume efficiency.' },
  { term: 'Mass Index', category: 'indicators', shortDef: 'Range reversal predictor', fullExplanation: 'Mass Index identifies reversals based on range expansion/contraction. Bulge above 27 then fall below 26.5 = reversal.', whyUseful: 'Volatility reversal signal.' },
  { term: 'Negative Volume Index', category: 'indicators', shortDef: 'Price action on down volume', fullExplanation: 'NVI only changes on lower-volume days. Smart money trades on quiet days. NVI above 255-day MA = bullish.', whyUseful: 'Institutional activity.' },
  { term: 'Positive Volume Index', category: 'indicators', shortDef: 'Price action on up volume', fullExplanation: 'PVI only changes on higher-volume days. Retail trades on busy days. Compare to NVI for confirmation.', whyUseful: 'Retail activity.' },
  { term: 'Price Zone Oscillator', category: 'indicators', shortDef: 'Range-based momentum', fullExplanation: 'PZO measures where close falls within the day\'s range. Above 60 = bullish momentum.', whyUseful: 'Close location analysis.' },
  { term: 'Qstick', category: 'indicators', shortDef: 'Candle body oscillator', fullExplanation: 'Qstick averages (Close - Open) over N periods. Positive = bullish candles dominating.', whyUseful: 'Candle pattern strength.' },
  { term: 'Range Action Verification Index', category: 'indicators', shortDef: 'Range momentum', fullExplanation: 'RAVI measures SMA divergence as percentage. Shows strength of trend.', whyUseful: 'Trend strength.' },
  { term: 'Relative Vigor Index', category: 'indicators', shortDef: 'Close location in range', fullExplanation: 'RVI assumes closes near highs in uptrends, lows in downtrends. Signal line crossovers for entries.', whyUseful: 'Trend confirmation.' },
  { term: 'Schaff Trend Cycle', category: 'indicators', shortDef: 'Fast MACD-based oscillator', fullExplanation: 'STC applies stochastic to MACD. Faster than MACD. Range 0-100, 75 overbought, 25 oversold.', whyUseful: 'Fast trend signals.' },
  { term: 'SMI', category: 'indicators', shortDef: 'Stochastic Momentum Index', fullExplanation: 'SMI measures where close is relative to midpoint of high-low range. Range -100 to +100.', whyUseful: 'Refined stochastic.' },
  { term: 'True Strength Index', category: 'indicators', shortDef: 'Double-smoothed momentum', fullExplanation: 'TSI applies double exponential smoothing to price momentum. Reduces noise. Ranges -100 to +100.', whyUseful: 'Smooth momentum reading.' },
  { term: 'Vortex Indicator', category: 'indicators', shortDef: 'Trend direction and strength', fullExplanation: 'VI has positive and negative lines. Crossovers signal trend changes. Based on true range concepts.', whyUseful: 'Trend identification.' },
  { term: 'Wave Trend', category: 'indicators', shortDef: 'Smooth momentum oscillator', fullExplanation: 'WaveTrend smoothes price and creates oscillator. Popular in crypto. Divergences and overbought/oversold levels.', whyUseful: 'Clean momentum signals.' },
  { term: 'Know Sure Thing', category: 'indicators', shortDef: 'Multi-period ROC', fullExplanation: 'KST combines 4 ROC periods with smoothing. Signal line crossovers and zero-line crosses for signals.', whyUseful: 'Multi-timeframe momentum.' },
  // CHART PATTERNS - Extended
  { term: 'Rising Wedge', category: 'patterns', shortDef: 'Bearish continuation/reversal pattern', fullExplanation: 'Rising wedge has converging trendlines sloping up. Usually breaks down. Bearish at top of uptrend.', whyUseful: 'Anticipate breakdowns.' },
  { term: 'Falling Wedge', category: 'patterns', shortDef: 'Bullish continuation/reversal pattern', fullExplanation: 'Falling wedge has converging trendlines sloping down. Usually breaks up. Bullish at bottom of downtrend.', whyUseful: 'Anticipate breakouts.' },
  { term: 'Ascending Triangle', category: 'patterns', shortDef: 'Bullish pattern with flat resistance', fullExplanation: 'Ascending triangle has flat top resistance and rising support. Usually breaks up. Measure move = height.', whyUseful: 'Bullish breakout setup.' },
  { term: 'Descending Triangle', category: 'patterns', shortDef: 'Bearish pattern with flat support', fullExplanation: 'Descending triangle has flat bottom support and falling resistance. Usually breaks down.', whyUseful: 'Bearish breakdown setup.' },
  { term: 'Symmetrical Triangle', category: 'patterns', shortDef: 'Consolidation with neutral bias', fullExplanation: 'Symmetrical triangle has converging trendlines from both sides. Breaks in direction of prior trend.', whyUseful: 'Continuation pattern.' },
  { term: 'Rectangle', category: 'patterns', shortDef: 'Sideways consolidation', fullExplanation: 'Rectangle is horizontal channel between support and resistance. Breakout direction determines trend.', whyUseful: 'Range-bound trading.' },
  { term: 'Bull Pennant', category: 'patterns', shortDef: 'Small triangle after sharp move up', fullExplanation: 'Bull pennant is small symmetrical triangle after strong up move. Continuation pattern. Breaks up.', whyUseful: 'Quick continuation trade.' },
  { term: 'Bear Pennant', category: 'patterns', shortDef: 'Small triangle after sharp move down', fullExplanation: 'Bear pennant is small symmetrical triangle after strong down move. Continuation pattern. Breaks down.', whyUseful: 'Short continuation setup.' },
  { term: 'Bull Flag', category: 'patterns', shortDef: 'Downward channel after up move', fullExplanation: 'Bull flag is slight downward sloping channel after strong up move. Continuation. Target = flagpole height.', whyUseful: 'Momentum continuation.' },
  { term: 'Bear Flag', category: 'patterns', shortDef: 'Upward channel after down move', fullExplanation: 'Bear flag is slight upward sloping channel after strong down move. Continuation. Breaks down.', whyUseful: 'Short continuation.' },
  { term: 'Triple Top', category: 'patterns', shortDef: 'Three peaks at same level', fullExplanation: 'Triple top has three peaks at similar price, separated by pullbacks. Bearish reversal. Breaks neckline.', whyUseful: 'Major reversal pattern.' },
  { term: 'Triple Bottom', category: 'patterns', shortDef: 'Three troughs at same level', fullExplanation: 'Triple bottom has three lows at similar price. Bullish reversal. Breaks above neckline.', whyUseful: 'Major bullish reversal.' },
  { term: 'Rounding Bottom', category: 'patterns', shortDef: 'Saucer-shaped reversal', fullExplanation: 'Rounding bottom (saucer) shows gradual shift from selling to buying. Long-term bullish reversal.', whyUseful: 'Long-term bottom.' },
  { term: 'Rounding Top', category: 'patterns', shortDef: 'Inverse saucer reversal', fullExplanation: 'Rounding top shows gradual shift from buying to selling. Long-term bearish reversal pattern.', whyUseful: 'Long-term top.' },
  { term: 'Diamond Top', category: 'patterns', shortDef: 'Diamond-shaped reversal', fullExplanation: 'Diamond forms from broadening then narrowing range. Rare but reliable reversal pattern at tops.', whyUseful: 'Rare reversal signal.' },
  { term: 'Bump and Run', category: 'patterns', shortDef: 'Trend acceleration and reversal', fullExplanation: 'Bump and Run has lead-in trend, steep bump phase, then reversal. Bump exceeds normal trend angle.', whyUseful: 'Blow-off top identification.' },
  { term: 'Island Reversal', category: 'patterns', shortDef: 'Gap-isolated price action', fullExplanation: 'Island reversal has gaps on both sides isolating price action. Strong reversal signal.', whyUseful: 'Strong reversal signal.' },
  { term: 'Three Line Break', category: 'patterns', shortDef: 'Trend following chart type', fullExplanation: 'Three line break draws new line only if it exceeds prior 3 lines. Filters noise.', whyUseful: 'Trend clarity.' },
  { term: 'Renko', category: 'patterns', shortDef: 'Price-only chart type', fullExplanation: 'Renko charts draw bricks only when price moves a set amount. Ignores time. Shows pure trend.', whyUseful: 'Noise-free trend view.' },
  { term: 'Point and Figure', category: 'patterns', shortDef: 'X and O chart type', fullExplanation: 'P&F charts show Xs for up moves, Os for down. Column changes on reversal. Ignores time.', whyUseful: 'Price action only.' },
  { term: 'Heikin Ashi', category: 'patterns', shortDef: 'Smoothed candlestick', fullExplanation: 'Heikin Ashi averages price data for smoother candles. Trend direction clearer but lags actual price.', whyUseful: 'Trend identification.' },
  // CANDLESTICK PATTERNS - Extended
  { term: 'Morning Doji Star', category: 'patterns', shortDef: 'Bullish reversal with doji', fullExplanation: 'Morning star with middle candle as doji. Stronger signal than regular morning star.', whyUseful: 'Strong bottom signal.' },
  { term: 'Evening Doji Star', category: 'patterns', shortDef: 'Bearish reversal with doji', fullExplanation: 'Evening star with middle candle as doji. Stronger signal than regular evening star.', whyUseful: 'Strong top signal.' },
  { term: 'Abandoned Baby', category: 'patterns', shortDef: 'Rare reversal with gaps', fullExplanation: 'Doji that gaps away from prior and next candle. Very rare, very reliable reversal.', whyUseful: 'Rare strong signal.' },
  { term: 'Three White Soldiers', category: 'patterns', shortDef: 'Three consecutive bullish candles', fullExplanation: 'Three long bullish candles opening within prior body. Strong bullish continuation/reversal.', whyUseful: 'Bullish momentum.' },
  { term: 'Three Black Crows', category: 'patterns', shortDef: 'Three consecutive bearish candles', fullExplanation: 'Three long bearish candles opening within prior body. Strong bearish signal.', whyUseful: 'Bearish momentum.' },
  { term: 'Three Inside Up', category: 'patterns', shortDef: 'Bullish harami confirmation', fullExplanation: 'Bearish candle, inside bullish candle, confirmation bullish close above first candle.', whyUseful: 'Confirmed reversal.' },
  { term: 'Three Inside Down', category: 'patterns', shortDef: 'Bearish harami confirmation', fullExplanation: 'Bullish candle, inside bearish candle, confirmation bearish close below first candle.', whyUseful: 'Confirmed top.' },
  { term: 'Three Outside Up', category: 'patterns', shortDef: 'Bullish engulfing confirmation', fullExplanation: 'Bearish candle, bullish engulfing, then continuation higher.', whyUseful: 'Confirmed bullish.' },
  { term: 'Three Outside Down', category: 'patterns', shortDef: 'Bearish engulfing confirmation', fullExplanation: 'Bullish candle, bearish engulfing, then continuation lower.', whyUseful: 'Confirmed bearish.' },
  { term: 'Rising Three Methods', category: 'patterns', shortDef: 'Bullish continuation', fullExplanation: 'Long bullish, 3 small bearish within range, long bullish breaking high. Continuation.', whyUseful: 'Trend continuation.' },
  { term: 'Falling Three Methods', category: 'patterns', shortDef: 'Bearish continuation', fullExplanation: 'Long bearish, 3 small bullish within range, long bearish breaking low. Continuation.', whyUseful: 'Downtrend continuation.' },
  { term: 'Tweezer Top', category: 'patterns', shortDef: 'Two candles with same high', fullExplanation: 'Two candles with matching highs (tweezers). Suggests resistance. More significant at tops.', whyUseful: 'Resistance confirmation.' },
  { term: 'Tweezer Bottom', category: 'patterns', shortDef: 'Two candles with same low', fullExplanation: 'Two candles with matching lows. Suggests support. More significant at bottoms.', whyUseful: 'Support confirmation.' },
  { term: 'Piercing Line', category: 'patterns', shortDef: 'Bullish reversal closing into prior', fullExplanation: 'After bearish candle, bullish candle opens lower but closes above midpoint of prior body.', whyUseful: 'Bullish reversal.' },
  { term: 'Dark Cloud Cover', category: 'patterns', shortDef: 'Bearish reversal closing into prior', fullExplanation: 'After bullish candle, bearish candle opens higher but closes below midpoint of prior body.', whyUseful: 'Bearish reversal.' },
  { term: 'Kicker', category: 'patterns', shortDef: 'Strong reversal with gap', fullExplanation: 'Complete reversal: opposite candle that gaps in opposite direction. Very strong signal.', whyUseful: 'Strongest candle signal.' },
  { term: 'Marubozu', category: 'patterns', shortDef: 'Candle with no wicks', fullExplanation: 'Marubozu has no shadows (wicks). Shows complete dominance by bulls (white) or bears (black).', whyUseful: 'Strong conviction candle.' },
  { term: 'Spinning Top', category: 'patterns', shortDef: 'Small body with long wicks', fullExplanation: 'Spinning top has small body with wicks on both sides. Shows indecision. Neutral pattern.', whyUseful: 'Identify consolidation.' },
  { term: 'Belt Hold', category: 'patterns', shortDef: 'Opening on extreme with strong close', fullExplanation: 'Bullish belt hold opens on low, closes near high. Bearish opens on high, closes near low.', whyUseful: 'Strong single-bar signal.' },
  { term: 'Counterattack', category: 'patterns', shortDef: 'Opposite candles closing at same price', fullExplanation: 'Two opposite colored candles closing at same price. Suggests reversal momentum.', whyUseful: 'Momentum shift signal.' },
  { term: 'On Neck', category: 'patterns', shortDef: 'Bearish continuation pattern', fullExplanation: 'After bearish candle, small bullish candle closes near low of prior candle. Continuation.', whyUseful: 'Weak bounce = continuation.' },
  { term: 'In Neck', category: 'patterns', shortDef: 'Slightly stronger on-neck', fullExplanation: 'Like on-neck but closes slightly into prior candle body. Still bearish continuation.', whyUseful: 'Continuation variant.' },
  { term: 'Thrusting', category: 'patterns', shortDef: 'Closes into prior body', fullExplanation: 'After bearish candle, bullish candle closes halfway into prior body. Not strong enough reversal.', whyUseful: 'Weak reversal attempt.' },
  // FUNDAMENTALS - Extended
  { term: 'Enterprise Value', category: 'fundamentals', shortDef: 'Total company value including debt', fullExplanation: 'EV = Market Cap + Debt - Cash. Better than market cap for comparing companies with different capital structures.', whyUseful: 'Acquisition cost metric.', formula: 'EV = Market Cap + Total Debt - Cash' },
  { term: 'EV/EBITDA', category: 'fundamentals', shortDef: 'Enterprise value to EBITDA', fullExplanation: 'EV/EBITDA is valuation ratio comparing total company value to operating earnings. Lower = cheaper.', whyUseful: 'Compare across capital structures.', formula: 'EV/EBITDA = Enterprise Value / EBITDA' },
  { term: 'EV/Revenue', category: 'fundamentals', shortDef: 'Enterprise value to sales', fullExplanation: 'EV/Revenue (EV/Sales) used for unprofitable growth companies. 1-3x typical; 10x+ for high growth.', whyUseful: 'Value growth companies.' },
  { term: 'EV/FCF', category: 'fundamentals', shortDef: 'Enterprise value to free cash flow', fullExplanation: 'EV/FCF measures value relative to cash generation. Lower = better value. Alternative to P/E.', whyUseful: 'Cash-based valuation.' },
  { term: 'Price-to-Book', category: 'fundamentals', shortDef: 'Stock price vs book value', fullExplanation: 'P/B compares market price to book value per share. <1 = trading below asset value (value trap or opportunity).', whyUseful: 'Asset-based valuation.', formula: 'P/B = Price / Book Value per Share' },
  { term: 'Price-to-Sales', category: 'fundamentals', shortDef: 'Stock price vs revenue', fullExplanation: 'P/S compares market cap to revenue. Useful for unprofitable companies. Lower = cheaper.', whyUseful: 'Value unprofitable growth.', formula: 'P/S = Market Cap / Revenue' },
  { term: 'Price-to-Cash-Flow', category: 'fundamentals', shortDef: 'Stock price vs operating cash', fullExplanation: 'P/CF compares price to operating cash flow. Less manipulable than earnings. Lower = better.', whyUseful: 'Cash-based P/E alternative.' },
  { term: 'Earnings Yield', category: 'fundamentals', shortDef: 'Inverse of P/E', fullExplanation: 'Earnings yield = EPS / Price = 1/PE. Compare to bond yields for relative value.', whyUseful: 'Compare stocks to bonds.', formula: 'Earnings Yield = EPS / Price × 100%' },
  { term: 'FCF Yield', category: 'fundamentals', shortDef: 'Free cash flow as percentage of price', fullExplanation: 'FCF yield = FCF per share / Price. Higher = more cash generation relative to price.', whyUseful: 'Cash-based yield.', formula: 'FCF Yield = FCF per Share / Price × 100%' },
  { term: 'WACC', category: 'fundamentals', shortDef: 'Weighted Average Cost of Capital', fullExplanation: 'WACC is blended cost of debt and equity capital. Used as discount rate in DCF.', whyUseful: 'DCF discount rate.', formula: 'WACC = (E/V × Re) + (D/V × Rd × (1-T))' },
  { term: 'Gordon Growth Model', category: 'fundamentals', shortDef: 'Dividend discount model', fullExplanation: 'GGM values stock based on perpetually growing dividends. Simple but limited to stable dividend payers.', whyUseful: 'Value dividend stocks.', formula: 'Value = D1 / (r - g)' },
  { term: 'Terminal Value', category: 'fundamentals', shortDef: 'Value beyond projection period', fullExplanation: 'Terminal value captures value after explicit forecast period in DCF. Often 70-80% of total value.', whyUseful: 'Complete DCF valuation.' },
  { term: 'Comparable Analysis', category: 'fundamentals', shortDef: 'Valuation using peer multiples', fullExplanation: 'Comp analysis values company using multiples of similar companies. Apply peer average P/E to target EPS.', whyUseful: 'Relative valuation.' },
  { term: 'Sum of Parts', category: 'fundamentals', shortDef: 'Valuing each segment separately', fullExplanation: 'SOTP values each business segment individually, then adds together. Used for conglomerates.', whyUseful: 'Value diversified companies.' },
  { term: 'NAV', category: 'fundamentals', shortDef: 'Net Asset Value', fullExplanation: 'NAV = Total Assets - Total Liabilities. Per share NAV for closed-end funds and REITs.', whyUseful: 'Asset-based valuation.' },
  { term: 'Tangible Book Value', category: 'fundamentals', shortDef: 'Book value minus intangibles', fullExplanation: 'Tangible BV excludes goodwill and intangibles. More conservative asset measure.', whyUseful: 'Conservative asset value.' },
  { term: 'Goodwill', category: 'fundamentals', shortDef: 'Premium paid over fair value in acquisition', fullExplanation: 'Goodwill is excess purchase price over fair value of acquired assets. Can be impaired if overpaid.', whyUseful: 'Acquisition accounting.' },
  { term: 'Impairment', category: 'fundamentals', shortDef: 'Write-down of asset value', fullExplanation: 'Impairment charges reduce asset value when fair value drops below carrying value. Common for goodwill.', whyUseful: 'Balance sheet adjustment.' },
  { term: 'Accruals', category: 'fundamentals', shortDef: 'Non-cash accounting entries', fullExplanation: 'Accruals are revenues/expenses recorded before cash changes hands. High accruals may signal earnings manipulation.', whyUseful: 'Earnings quality check.' },
  { term: 'Altman Z-Score', category: 'fundamentals', shortDef: 'Bankruptcy prediction model', fullExplanation: 'Z-Score uses 5 ratios to predict bankruptcy. Below 1.8 = high risk. Above 3.0 = safe.', whyUseful: 'Financial distress warning.', formula: 'Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E' },
  { term: 'Piotroski F-Score', category: 'fundamentals', shortDef: 'Value stock quality score', fullExplanation: 'F-Score rates value stocks 0-9 based on 9 financial criteria. Higher = higher quality value.', whyUseful: 'Filter value traps.' },
  { term: 'Beneish M-Score', category: 'fundamentals', shortDef: 'Earnings manipulation detection', fullExplanation: 'M-Score predicts likelihood of earnings manipulation. Above -1.78 suggests manipulation.', whyUseful: 'Detect fraud risk.' },
  { term: 'DuPont Analysis', category: 'fundamentals', shortDef: 'ROE decomposition', fullExplanation: 'DuPont breaks ROE into profit margin × asset turnover × leverage. Shows source of returns.', whyUseful: 'Understand ROE drivers.', formula: 'ROE = Profit Margin × Asset Turnover × Equity Multiplier' },
  { term: 'Asset Turnover', category: 'fundamentals', shortDef: 'Revenue per dollar of assets', fullExplanation: 'Asset turnover = Revenue / Total Assets. Measures efficiency of asset utilization.', whyUseful: 'Efficiency metric.', formula: 'Asset Turnover = Revenue / Total Assets' },
  { term: 'Inventory Turnover', category: 'fundamentals', shortDef: 'How fast inventory sells', fullExplanation: 'Inventory turnover = COGS / Avg Inventory. Higher = faster-selling inventory. Industry dependent.', whyUseful: 'Inventory efficiency.' },
  { term: 'Days Sales Outstanding', category: 'fundamentals', shortDef: 'Days to collect receivables', fullExplanation: 'DSO = (AR / Revenue) × 365. Days to collect customer payments. Lower = faster collection.', whyUseful: 'Cash flow timing.' },
  { term: 'Days Payable Outstanding', category: 'fundamentals', shortDef: 'Days to pay suppliers', fullExplanation: 'DPO = (AP / COGS) × 365. Days company takes to pay bills. Higher = better cash position.', whyUseful: 'Cash flow management.' },
  { term: 'Cash Conversion Cycle', category: 'fundamentals', shortDef: 'Days cash is tied up', fullExplanation: 'CCC = DIO + DSO - DPO. Days between paying suppliers and collecting from customers.', whyUseful: 'Working capital efficiency.', formula: 'CCC = DIO + DSO - DPO' },
  { term: 'Quick Ratio', category: 'fundamentals', shortDef: 'Liquid assets to liabilities', fullExplanation: 'Quick ratio = (Current Assets - Inventory) / Current Liabilities. More conservative than current ratio.', whyUseful: 'Short-term liquidity.', formula: 'Quick = (Cash + AR + ST Investments) / Current Liabilities' },
  { term: 'Current Ratio', category: 'fundamentals', shortDef: 'Current assets to liabilities', fullExplanation: 'Current ratio = Current Assets / Current Liabilities. Above 1 = can cover short-term obligations.', whyUseful: 'Basic liquidity measure.' },
  { term: 'Debt-to-Equity', category: 'fundamentals', shortDef: 'Leverage ratio', fullExplanation: 'D/E = Total Debt / Shareholders Equity. Higher = more leveraged. Industry dependent.', whyUseful: 'Leverage assessment.' },
  { term: 'Interest Coverage', category: 'fundamentals', shortDef: 'Earnings to interest expense', fullExplanation: 'Interest coverage = EBIT / Interest Expense. Above 2.5 generally safe. Below 1.5 = risky.', whyUseful: 'Debt service ability.' },
  { term: 'Debt Service Coverage', category: 'fundamentals', shortDef: 'Cash flow to debt payments', fullExplanation: 'DSCR = Operating Income / Debt Service. Banks want 1.25x+ for loans.', whyUseful: 'Loan covenant metric.' },
  // RISK MANAGEMENT - Extended
  { term: 'Expected Shortfall', category: 'risk', shortDef: 'Average loss beyond VaR', fullExplanation: 'Expected Shortfall (CVaR) is average loss when VaR is exceeded. Better captures tail risk.', whyUseful: 'Tail risk measure.' },
  { term: 'Tail Risk', category: 'risk', shortDef: 'Risk of extreme outcomes', fullExplanation: 'Tail risk is probability of extreme moves beyond normal distribution. Fat tails = higher tail risk.', whyUseful: 'Understand crash risk.' },
  { term: 'Black Swan', category: 'risk', shortDef: 'Unexpected extreme event', fullExplanation: 'Black swan events are rare, unpredictable, high-impact. 2008 crisis, COVID crash examples.', whyUseful: 'Prepare for unexpected.' },
  { term: 'Correlation', category: 'risk', shortDef: 'How assets move together', fullExplanation: 'Correlation ranges -1 to +1. +1 = move together. -1 = opposite. 0 = unrelated. Key for diversification.', whyUseful: 'Portfolio diversification.' },
  { term: 'Covariance', category: 'risk', shortDef: 'Joint variability of returns', fullExplanation: 'Covariance measures how two assets move together. Positive = same direction. Used in portfolio math.', whyUseful: 'Portfolio construction.' },
  { term: 'Tracking Error', category: 'risk', shortDef: 'Deviation from benchmark', fullExplanation: 'Tracking error measures how closely portfolio follows benchmark. Lower = more similar to index.', whyUseful: 'Evaluate index funds.' },
  { term: 'Information Ratio', category: 'risk', shortDef: 'Active return per unit of active risk', fullExplanation: 'IR = Active Return / Tracking Error. Higher = better risk-adjusted active management.', whyUseful: 'Evaluate active managers.' },
  { term: 'Treynor Ratio', category: 'risk', shortDef: 'Return per unit of beta', fullExplanation: 'Treynor = (Portfolio Return - Risk-free) / Beta. Like Sharpe but uses beta instead of std dev.', whyUseful: 'Risk-adjusted return.' },
  { term: 'Calmar Ratio', category: 'risk', shortDef: 'Return per unit of drawdown', fullExplanation: 'Calmar = CAGR / Max Drawdown. Higher = better return relative to worst decline.', whyUseful: 'Drawdown-adjusted return.' },
  { term: 'Sterling Ratio', category: 'risk', shortDef: 'Return vs average drawdown', fullExplanation: 'Sterling uses average drawdown instead of max. Less sensitive to single worst period.', whyUseful: 'Smoothed drawdown metric.' },
  { term: 'Ulcer Index', category: 'risk', shortDef: 'Depth and duration of drawdowns', fullExplanation: 'Ulcer Index measures both depth and duration of underwater periods. Name reflects investor stress.', whyUseful: 'Comprehensive drawdown measure.' },
  { term: 'Omega Ratio', category: 'risk', shortDef: 'Gains vs losses above threshold', fullExplanation: 'Omega compares probability-weighted gains to losses above threshold. >1 is good.', whyUseful: 'Full return distribution.' },
  { term: 'Kappa', category: 'risk', shortDef: 'Generalized Sharpe ratio', fullExplanation: 'Kappa generalizes Sharpe to consider higher moments of distribution. Better for non-normal returns.', whyUseful: 'Non-normal risk measure.' },
  { term: 'Skewness', category: 'risk', shortDef: 'Asymmetry of returns', fullExplanation: 'Skewness measures return asymmetry. Positive = more upside. Negative = more downside (fat left tail).', whyUseful: 'Tail behavior.' },
  { term: 'Kurtosis', category: 'risk', shortDef: 'Fat tails in distribution', fullExplanation: 'Kurtosis measures tail fatness. High kurtosis = more extreme outcomes than normal distribution.', whyUseful: 'Extreme event probability.' },
  { term: 'Monte Carlo Simulation', category: 'risk', shortDef: 'Random scenario generation', fullExplanation: 'Monte Carlo generates thousands of random scenarios to estimate probability distributions of outcomes.', whyUseful: 'Portfolio stress testing.' },
  { term: 'Stress Testing', category: 'risk', shortDef: 'Testing against adverse scenarios', fullExplanation: 'Stress tests apply extreme but plausible scenarios to portfolio. 2008 replay, rate shock, etc.', whyUseful: 'Understand worst cases.' },
  { term: 'Scenario Analysis', category: 'risk', shortDef: 'Testing specific scenarios', fullExplanation: 'Scenario analysis evaluates portfolio under specific hypothetical conditions.', whyUseful: 'Plan for possibilities.' },
  { term: 'Factor Exposure', category: 'risk', shortDef: 'Sensitivity to risk factors', fullExplanation: 'Factor exposure measures sensitivity to factors like value, momentum, size, volatility.', whyUseful: 'Understand portfolio drivers.' },
  { term: 'Risk Parity', category: 'strategies', shortDef: 'Equal risk from each asset', fullExplanation: 'Risk parity allocates so each asset contributes equal risk. Usually means more bonds than stocks.', whyUseful: 'Balanced risk approach.' },
  { term: 'Maximum Drawdown', category: 'risk', shortDef: 'Largest peak-to-trough decline', fullExplanation: 'Max drawdown is biggest decline from high to subsequent low. Key risk metric for investors.', whyUseful: 'Worst case measure.' },
  { term: 'Recovery Time', category: 'risk', shortDef: 'Time to return to prior high', fullExplanation: 'Recovery time is how long to get back to previous peak after drawdown. Can be years.', whyUseful: 'Time cost of losses.' },
  { term: 'Rolling Returns', category: 'risk', shortDef: 'Returns over rolling periods', fullExplanation: 'Rolling returns show performance over overlapping periods. 3-year rolling shows all 3-year results.', whyUseful: 'Consistency of returns.' },
  { term: 'Win/Loss Ratio', category: 'risk', shortDef: 'Average win vs average loss', fullExplanation: 'Win/loss ratio = Average Winning Trade / Average Losing Trade. Combined with win rate for expectancy.', whyUseful: 'Trade quality metric.' },
  { term: 'Profit Factor', category: 'risk', shortDef: 'Gross profit vs gross loss', fullExplanation: 'Profit factor = Gross Profit / Gross Loss. >1 = profitable. >2 = good strategy.', whyUseful: 'Strategy profitability.' },
  { term: 'Expectancy', category: 'risk', shortDef: 'Expected value per trade', fullExplanation: 'Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss). Positive = profitable edge.', whyUseful: 'Trading edge measure.', formula: 'E = (W% × AvgW) - (L% × AvgL)' },
  { term: 'Kelly Criterion', category: 'risk', shortDef: 'Optimal bet sizing', fullExplanation: 'Kelly = (bp - q) / b where b=odds, p=win prob, q=loss prob. Maximizes long-term growth. Full Kelly is aggressive.', whyUseful: 'Optimal position size.', formula: 'Kelly = (bp - q) / b' },
  { term: 'Half Kelly', category: 'risk', shortDef: 'Conservative Kelly sizing', fullExplanation: 'Half Kelly uses 50% of Kelly size. Reduces volatility while capturing most growth benefit.', whyUseful: 'Practical position sizing.' },
  // ADDITIONAL TERMS TO REACH 1000+
  // Market Structure
  { term: 'Market Maker', category: 'basics', shortDef: 'Firm providing bid/ask quotes', fullExplanation: 'Market makers continuously quote bid and ask prices, providing liquidity. Profit from spread. Obligated to maintain orderly markets.', whyUseful: 'Understand liquidity providers.' },
  { term: 'Specialist', category: 'basics', shortDef: 'NYSE designated market maker', fullExplanation: 'Specialists (now DMMs) are assigned to specific stocks on NYSE. Maintain fair and orderly markets.', whyUseful: 'NYSE market structure.' },
  { term: 'Dark Pool', category: 'basics', shortDef: 'Private trading venue', fullExplanation: 'Dark pools are alternative trading systems where orders are not displayed. Used for large institutional trades.', whyUseful: 'Understand hidden liquidity.' },
  { term: 'Order Flow', category: 'basics', shortDef: 'Stream of customer orders', fullExplanation: 'Order flow is aggregate of buy/sell orders. Firms pay for order flow (PFOF) to execute retail trades.', whyUseful: 'Understand trade routing.' },
  { term: 'PFOF', category: 'basics', shortDef: 'Payment for Order Flow', fullExplanation: 'Market makers pay brokers for retail order flow. Controversial practice enabling commission-free trading.', whyUseful: 'Understand broker revenue.' },
  { term: 'Best Execution', category: 'regulations', shortDef: 'Duty to get best price', fullExplanation: 'Brokers must seek best execution for customer orders considering price, speed, and likelihood of execution.', whyUseful: 'Know your rights.' },
  { term: 'NBBO', category: 'basics', shortDef: 'National Best Bid and Offer', fullExplanation: 'NBBO is best bid and ask across all exchanges. Regulation NMS requires trades execute at NBBO or better.', whyUseful: 'Price benchmark.' },
  { term: 'Regulation NMS', category: 'regulations', shortDef: 'National Market System rules', fullExplanation: 'Reg NMS governs order routing and trade-through protection. Requires routing to best available price.', whyUseful: 'Market structure rules.' },
  { term: 'Odd Lot', category: 'basics', shortDef: 'Less than standard trading unit', fullExplanation: 'Odd lots are orders for less than 100 shares. Historically got worse execution. Now more common with fractional.', whyUseful: 'Understand order types.' },
  { term: 'Round Lot', category: 'basics', shortDef: 'Standard 100 share unit', fullExplanation: 'Round lots are 100 shares. Standard trading unit. Orders displayed on NBBO.', whyUseful: 'Standard order size.' },
  { term: 'Tape', category: 'basics', shortDef: 'Record of trades', fullExplanation: 'The tape (from ticker tape) is stream of all trades. Tape A (NYSE), B (regional), C (NASDAQ).', whyUseful: 'Historical term.' },
  { term: 'Level 1', category: 'basics', shortDef: 'Best bid/ask only', fullExplanation: 'Level 1 data shows only best bid and ask prices with sizes. Basic market data.', whyUseful: 'Basic price data.' },
  { term: 'Level 2', category: 'basics', shortDef: 'Full order book depth', fullExplanation: 'Level 2 shows all bid and ask quotes at various prices. Reveals order book depth and market makers.', whyUseful: 'See market depth.' },
  { term: 'Time and Sales', category: 'basics', shortDef: 'List of executed trades', fullExplanation: 'Time and sales shows every trade with price, size, and time. Track block trades and aggressor side.', whyUseful: 'See trade flow.' },
  { term: 'Block Trade', category: 'basics', shortDef: 'Large institutional trade', fullExplanation: 'Block trades are large orders typically 10,000+ shares. Often executed off-exchange to minimize impact.', whyUseful: 'Institutional activity.' },
  { term: 'Iceberg Order', category: 'basics', shortDef: 'Hidden size order', fullExplanation: 'Iceberg orders show only small portion of total size. Rest is hidden. Reduces market impact.', whyUseful: 'Hide large orders.' },
  { term: 'Reserve Order', category: 'basics', shortDef: 'Partially displayed order', fullExplanation: 'Reserve orders display a portion and automatically replenish as displayed portion fills.', whyUseful: 'Reduce market impact.' },
  { term: 'All or None', category: 'basics', shortDef: 'Order must fill completely', fullExplanation: 'AON orders must fill entirely or not at all. No partial fills. May take longer to execute.', whyUseful: 'Guarantee full size.' },
  { term: 'Fill or Kill', category: 'basics', shortDef: 'Immediate full fill or cancel', fullExplanation: 'FOK orders must fill immediately and completely, or are cancelled. No partial fills, no waiting.', whyUseful: 'Immediate certainty.' },
  { term: 'Immediate or Cancel', category: 'basics', shortDef: 'Fill what you can immediately', fullExplanation: 'IOC orders execute immediately for available quantity, cancel unfilled portion. No waiting.', whyUseful: 'Partial OK, no waiting.' },
  { term: 'Good Till Cancelled', category: 'basics', shortDef: 'Order stays open until filled/cancelled', fullExplanation: 'GTC orders remain active until executed or cancelled. Usually limited to 90-180 days by brokers.', whyUseful: 'Persistent orders.' },
  { term: 'Day Order', category: 'basics', shortDef: 'Order expires end of day', fullExplanation: 'Day orders cancel at market close if not filled. Default order duration at most brokers.', whyUseful: 'No overnight surprises.' },
  { term: 'Extended Hours Order', category: 'basics', shortDef: 'Order active in pre/post market', fullExplanation: 'Extended hours orders can execute in pre-market and after-hours sessions. Must be limit orders.', whyUseful: 'Trade outside regular hours.' },
  { term: 'Stop Limit Order', category: 'basics', shortDef: 'Stop that becomes limit order', fullExplanation: 'Stop limit triggers at stop price but becomes limit order. May not fill if price gaps through limit.', whyUseful: 'Control execution price.' },
  { term: 'Trailing Stop', category: 'basics', shortDef: 'Stop that follows price', fullExplanation: 'Trailing stop adjusts as price moves favorably. Locks in profits while giving room to run.', whyUseful: 'Protect gains dynamically.' },
  { term: 'Bracket Order', category: 'basics', shortDef: 'Entry with profit target and stop', fullExplanation: 'Bracket order places entry with OCO orders for take profit and stop loss. Complete trade setup.', whyUseful: 'Automated risk management.' },
  { term: 'OCO Order', category: 'basics', shortDef: 'One Cancels Other', fullExplanation: 'OCO pairs two orders where filling one cancels the other. Use for profit target + stop loss.', whyUseful: 'Linked exit orders.' },
  { term: 'OTO Order', category: 'basics', shortDef: 'One Triggers Other', fullExplanation: 'OTO order places second order only after first fills. Use for entry + stop loss setup.', whyUseful: 'Conditional orders.' },
  // MORE STRATEGIES
  { term: 'Pairs Trading', category: 'strategies', shortDef: 'Long one, short correlated stock', fullExplanation: 'Pairs trading goes long underperforming stock, short outperforming one. Profit when spread reverts.', whyUseful: 'Market-neutral strategy.' },
  { term: 'Statistical Arbitrage', category: 'strategies', shortDef: 'Quantitative pairs/basket trading', fullExplanation: 'Stat arb uses quantitative models to find mispricings across many securities. High-frequency pairs trading.', whyUseful: 'Systematic alpha.' },
  { term: 'Merger Arbitrage', category: 'strategies', shortDef: 'Trading acquisition spreads', fullExplanation: 'Merger arb buys target, shorts acquirer (stock deals) to capture spread between current and deal price.', whyUseful: 'Event-driven strategy.' },
  { term: 'Convertible Arbitrage', category: 'strategies', shortDef: 'Long convert, short stock', fullExplanation: 'Conv arb buys convertible bond, shorts underlying stock to isolate cheap optionality or credit.', whyUseful: 'Fixed income + equity strategy.' },
  { term: 'Index Arbitrage', category: 'strategies', shortDef: 'Exploit index vs constituents', fullExplanation: 'Index arb trades price differences between index (ETF/futures) and underlying basket of stocks.', whyUseful: 'Pure arbitrage.' },
  { term: 'Risk Arbitrage', category: 'strategies', shortDef: 'Event-driven trading', fullExplanation: 'Risk arb captures spreads in corporate events: mergers, spin-offs, restructurings. Not risk-free.', whyUseful: 'Event premium capture.' },
  { term: 'Sector Rotation', category: 'strategies', shortDef: 'Shifting between sectors', fullExplanation: 'Sector rotation moves capital between sectors based on economic cycle. Overweight cyclicals in expansion.', whyUseful: 'Cycle-based allocation.' },
  { term: 'Factor Investing', category: 'strategies', shortDef: 'Targeting return drivers', fullExplanation: 'Factor investing targets return drivers like value, momentum, size, quality, low volatility.', whyUseful: 'Systematic tilts.' },
  { term: 'Smart Beta', category: 'strategies', shortDef: 'Rules-based factor ETFs', fullExplanation: 'Smart beta ETFs weight by factors instead of market cap. Value-weighted, equal-weighted, low-vol, etc.', whyUseful: 'Passive factor exposure.' },
  { term: 'Tactical Asset Allocation', category: 'strategies', shortDef: 'Short-term allocation shifts', fullExplanation: 'TAA adjusts allocation based on short-term views. Overweight assets expected to outperform.', whyUseful: 'Dynamic allocation.' },
  { term: 'Strategic Asset Allocation', category: 'strategies', shortDef: 'Long-term target mix', fullExplanation: 'SAA sets long-term target allocation based on risk tolerance and goals. Rebalance to targets.', whyUseful: 'Core portfolio structure.' },
  { term: 'Dollar Cost Averaging', category: 'strategies', shortDef: 'Regular fixed-dollar investing', fullExplanation: 'DCA invests fixed dollar amount regularly regardless of price. Buys more when cheap, less when expensive.', whyUseful: 'Remove timing risk.' },
  { term: 'Value Averaging', category: 'strategies', shortDef: 'Adjust contributions to meet target', fullExplanation: 'Value averaging adjusts contribution to hit portfolio value target. Buy more in down markets.', whyUseful: 'Enhanced DCA.' },
  { term: 'Lump Sum', category: 'strategies', shortDef: 'Invest all at once', fullExplanation: 'Lump sum investing puts all capital in immediately. Historically outperforms DCA 2/3 of time.', whyUseful: 'Time in market.' },
  { term: 'Buy and Hold', category: 'strategies', shortDef: 'Long-term passive investing', fullExplanation: 'Buy and hold purchases and holds regardless of market conditions. Minimizes costs and taxes.', whyUseful: 'Simple, tax-efficient.' },
  { term: 'Core-Satellite', category: 'strategies', shortDef: 'Passive core, active satellites', fullExplanation: 'Core-satellite uses passive index funds for bulk of portfolio, active strategies for alpha.', whyUseful: 'Blended approach.' },
  { term: 'Barbell Strategy', category: 'strategies', shortDef: 'Extreme allocations, no middle', fullExplanation: 'Barbell invests in extremes: very safe + very risky, avoiding middle. Taleb advocates this.', whyUseful: 'Convex payoff.' },
  { term: 'All Weather', category: 'strategies', shortDef: 'Ray Dalio\'s balanced portfolio', fullExplanation: 'All Weather portfolio designed to perform in any economic environment. Stocks, bonds, gold, commodities.', whyUseful: 'Robust allocation.' },
  { term: 'Permanent Portfolio', category: 'strategies', shortDef: 'Harry Browne\'s 4-asset mix', fullExplanation: 'Permanent Portfolio: 25% stocks, bonds, gold, cash. Designed for all economic conditions.', whyUseful: 'Simple diversification.' },
  { term: 'CANSLIM', category: 'strategies', shortDef: 'William O\'Neil\'s growth criteria', fullExplanation: 'CANSLIM: Current earnings, Annual earnings, New product, Supply/demand, Leader, Institutional, Market.', whyUseful: 'Growth stock selection.' },
  { term: 'Magic Formula', category: 'strategies', shortDef: 'Greenblatt value strategy', fullExplanation: 'Magic Formula ranks stocks by earnings yield and return on capital. Buy top ranked, hold 1 year.', whyUseful: 'Systematic value.' },
  { term: 'Dogs of the Dow', category: 'strategies', shortDef: 'Highest yield Dow stocks', fullExplanation: 'Dogs strategy buys 10 highest dividend yield Dow stocks. Rebalance annually.', whyUseful: 'Simple dividend strategy.' },
  { term: 'January Effect', category: 'strategies', shortDef: 'Small caps outperform in January', fullExplanation: 'January Effect: small caps tend to outperform in January, possibly due to tax-loss selling recovery.', whyUseful: 'Seasonal pattern.' },
  { term: 'Sell in May', category: 'strategies', shortDef: 'Seasonal weakness May-October', fullExplanation: 'Sell in May and go away: stocks historically weaker May-October. Buy November-April.', whyUseful: 'Seasonal timing.' },
  { term: 'Santa Rally', category: 'strategies', shortDef: 'Year-end bullish tendency', fullExplanation: 'Santa Claus Rally: stocks tend to rise last 5 trading days + first 2 of new year.', whyUseful: 'Holiday pattern.' },
  { term: 'Triple Witching', category: 'basics', shortDef: 'Quarterly options/futures expiry', fullExplanation: 'Triple witching: quarterly expiration of stock options, stock index futures, and stock index options. High volume.', whyUseful: 'Expect volatility.' },
  { term: 'Quad Witching', category: 'basics', shortDef: 'Triple witching + single stock futures', fullExplanation: 'Quad witching adds single stock futures to triple witching. Third Friday of March, June, Sept, Dec.', whyUseful: 'Maximum expiration activity.' },
  { term: 'OPEX', category: 'basics', shortDef: 'Options expiration', fullExplanation: 'OPEX is options expiration, typically third Friday monthly. Large OPEX can move markets.', whyUseful: 'Key calendar date.' },
  { term: 'Gamma Exposure', category: 'indicators', shortDef: 'Dealer hedging impact', fullExplanation: 'GEX measures aggregate dealer gamma. Positive GEX = dealers stabilize. Negative = amplify moves.', whyUseful: 'Predict market behavior.' },
  { term: 'DIX', category: 'indicators', shortDef: 'Dark pool buying indicator', fullExplanation: 'Dark Index measures net buying in dark pools. High DIX = institutional accumulation.', whyUseful: 'Institutional sentiment.' },
  { term: 'GEX', category: 'indicators', shortDef: 'Gamma Exposure Index', fullExplanation: 'GEX shows aggregate dealer gamma. Flip from positive to negative can trigger volatility.', whyUseful: 'Options market structure.' },
  { term: 'Put/Call Ratio', category: 'indicators', shortDef: 'Put volume vs call volume', fullExplanation: 'P/C ratio shows sentiment. High = bearish (contrarian bullish). Low = bullish (contrarian bearish).', whyUseful: 'Contrarian indicator.' },
  { term: 'VIX Term Structure', category: 'indicators', shortDef: 'VIX futures curve', fullExplanation: 'VIX term structure shows futures prices across expirations. Contango = normal. Backwardation = fear.', whyUseful: 'Volatility expectations.' },
  { term: 'SKEW Index', category: 'indicators', shortDef: 'Tail risk indicator', fullExplanation: 'CBOE SKEW measures perceived tail risk from S&P 500 options. Higher = more tail risk priced.', whyUseful: 'Black swan indicator.' },
  { term: 'MOVE Index', category: 'indicators', shortDef: 'Bond market volatility', fullExplanation: 'MOVE is VIX equivalent for Treasury market. High MOVE = bond market stress.', whyUseful: 'Fixed income volatility.' },
  { term: 'AAII Sentiment', category: 'indicators', shortDef: 'Retail investor sentiment', fullExplanation: 'AAII surveys retail investors on market outlook. Extreme readings are contrarian indicators.', whyUseful: 'Contrarian signal.' },
  { term: 'Fear and Greed Index', category: 'indicators', shortDef: 'CNN composite sentiment', fullExplanation: 'CNN Fear & Greed aggregates 7 indicators. Extreme greed = overbought. Extreme fear = oversold.', whyUseful: 'Sentiment gauge.' },
  { term: 'Investor Intelligence', category: 'indicators', shortDef: 'Newsletter writer sentiment', fullExplanation: 'Investor Intelligence tracks newsletter writer bullishness. High bulls = contrarian bearish.', whyUseful: 'Professional sentiment.' },
  { term: 'Commitment of Traders', category: 'indicators', shortDef: 'Futures positioning report', fullExplanation: 'COT shows futures positions by type: commercials (hedgers), large speculators, small speculators.', whyUseful: 'Smart money positioning.' },
  { term: 'Advance Decline Line', category: 'indicators', shortDef: 'Cumulative breadth', fullExplanation: 'A/D Line = Advances - Declines, cumulated. Divergence from index warns of weakness.', whyUseful: 'Market breadth.' },
  { term: 'McClellan Oscillator', category: 'indicators', shortDef: 'Breadth momentum', fullExplanation: 'McClellan Oscillator is MACD of advance-decline data. Overbought/oversold readings at extremes.', whyUseful: 'Breadth momentum.' },
  { term: 'McClellan Summation', category: 'indicators', shortDef: 'Cumulative McClellan', fullExplanation: 'Summation Index cumulates McClellan Oscillator. Longer-term breadth trend.', whyUseful: 'Intermediate breadth.' },
  { term: 'New Highs New Lows', category: 'indicators', shortDef: '52-week highs minus lows', fullExplanation: 'NH-NL counts stocks at new 52-week highs minus new lows. Confirms or diverges from index.', whyUseful: 'Breadth confirmation.' },
  { term: 'Percent Above 200 MA', category: 'indicators', shortDef: 'Stocks above long-term average', fullExplanation: 'Percentage of stocks above 200-day MA. Low readings = oversold market. High = overbought.', whyUseful: 'Breadth gauge.' },
  { term: 'Percent Above 50 MA', category: 'indicators', shortDef: 'Stocks above medium-term average', fullExplanation: 'Percentage above 50-day MA. More sensitive than 200 MA. Extremes signal reversals.', whyUseful: 'Medium-term breadth.' },
  { term: 'Arms Index (TRIN)', category: 'indicators', shortDef: 'Volume-weighted breadth', fullExplanation: 'TRIN = (Advances/Declines) / (Up Volume/Down Volume). Below 1 = bullish. Above 1 = bearish.', whyUseful: 'Intraday breadth.' },
  { term: 'Tick Index', category: 'indicators', shortDef: 'Uptick minus downtick stocks', fullExplanation: 'TICK counts stocks on uptick minus downtick. Extreme readings (>1000 or <-1000) signal exhaustion.', whyUseful: 'Short-term sentiment.' },
  { term: 'Baltic Dry Index', category: 'indicators', shortDef: 'Shipping costs index', fullExplanation: 'BDI tracks dry bulk shipping costs. Leading indicator for global trade and commodity demand.', whyUseful: 'Economic indicator.' },
  { term: 'Copper-Gold Ratio', category: 'indicators', shortDef: 'Risk-on/risk-off gauge', fullExplanation: 'Copper/Gold ratio rises when economy is strong (copper demand) vs fear (gold demand).', whyUseful: 'Economic sentiment.' },
  { term: 'Yield Curve', category: 'indicators', shortDef: 'Bond yields across maturities', fullExplanation: 'Yield curve plots yields from short to long maturities. Inverted curve historically predicts recession.', whyUseful: 'Recession indicator.' },
  { term: '10-2 Spread', category: 'indicators', shortDef: '10-year minus 2-year yield', fullExplanation: '10-2 spread is most watched yield curve measure. Inversion (negative) precedes recessions.', whyUseful: 'Key recession indicator.' },
  { term: 'TED Spread', category: 'indicators', shortDef: 'Credit risk indicator', fullExplanation: 'TED spread = 3-month LIBOR - 3-month T-bill. High spread = bank stress. Spiked in 2008.', whyUseful: 'Financial stress gauge.' },
  { term: 'High Yield Spread', category: 'indicators', shortDef: 'Junk bond premium', fullExplanation: 'HY spread = junk bond yield - Treasury yield. Widening spreads signal credit stress.', whyUseful: 'Credit market health.' },
  { term: 'Investment Grade Spread', category: 'indicators', shortDef: 'IG corporate premium', fullExplanation: 'IG spread measures premium for investment grade bonds over Treasuries. Widens in stress.', whyUseful: 'Corporate credit health.' },
  // FOREX TERMS
  { term: 'Pip', category: 'basics', shortDef: 'Forex price increment', fullExplanation: 'Pip is smallest price move, typically 0.0001 for most pairs. Yen pairs use 0.01.', whyUseful: 'Forex pricing unit.', formula: 'Pip value = (Pip / Rate) × Lot Size' },
  { term: 'Lot', category: 'basics', shortDef: 'Forex trade size', fullExplanation: 'Standard lot = 100,000 units. Mini = 10,000. Micro = 1,000. Nano = 100 units.', whyUseful: 'Position sizing.' },
  { term: 'Cross Rate', category: 'basics', shortDef: 'Non-USD currency pair', fullExplanation: 'Cross rates are pairs not involving USD like EUR/GBP, EUR/JPY. Calculated from USD rates.', whyUseful: 'Direct currency exposure.' },
  { term: 'Base Currency', category: 'basics', shortDef: 'First currency in pair', fullExplanation: 'In EUR/USD, EUR is base. Quote shows how much USD (quote currency) to buy 1 EUR.', whyUseful: 'Read forex quotes.' },
  { term: 'Quote Currency', category: 'basics', shortDef: 'Second currency in pair', fullExplanation: 'In EUR/USD, USD is quote. A rate of 1.10 means 1 EUR = 1.10 USD.', whyUseful: 'Understand pair notation.' },
  { term: 'Carry Trade', category: 'strategies', shortDef: 'Borrow low yield, buy high yield', fullExplanation: 'Carry trade borrows low interest currency, invests in high yield. Profits from interest differential.', whyUseful: 'Interest rate strategy.' },
  { term: 'Interest Rate Differential', category: 'indicators', shortDef: 'Difference between country rates', fullExplanation: 'IRD is difference in interest rates between two countries. Drives currency direction over time.', whyUseful: 'Long-term currency driver.' },
  { term: 'Swap Rate', category: 'basics', shortDef: 'Overnight holding cost/credit', fullExplanation: 'Swap (rollover) is interest paid/received for holding positions overnight. Based on rate differential.', whyUseful: 'Cost of holding positions.' },
  { term: 'Tom-Next', category: 'basics', shortDef: 'Tomorrow-next day swap', fullExplanation: 'Tom-next is swap from tomorrow to next day. Used to calculate retail forex rollovers.', whyUseful: 'Rollover mechanics.' },
  { term: 'Central Bank Intervention', category: 'fundamentals', shortDef: 'Official currency buying/selling', fullExplanation: 'Central banks intervene by buying/selling currency to influence exchange rates. Japan notable for this.', whyUseful: 'Major price driver.' },
  { term: 'BOJ', category: 'fundamentals', shortDef: 'Bank of Japan', fullExplanation: 'BOJ sets Japan monetary policy. Known for ultra-low rates and currency intervention.', whyUseful: 'Yen driver.' },
  { term: 'ECB', category: 'fundamentals', shortDef: 'European Central Bank', fullExplanation: 'ECB sets eurozone monetary policy. Key for EUR pairs. Frankfurt-based.', whyUseful: 'Euro driver.' },
  { term: 'FOMC', category: 'fundamentals', shortDef: 'Federal Open Market Committee', fullExplanation: 'FOMC sets US interest rates. 8 meetings per year. Most important forex calendar event.', whyUseful: 'USD driver.' },
  { term: 'NFP', category: 'fundamentals', shortDef: 'Non-Farm Payrolls', fullExplanation: 'NFP is monthly US employment report. Major market mover. Released first Friday of month.', whyUseful: 'Key economic release.' },
  { term: 'PMI', category: 'fundamentals', shortDef: 'Purchasing Managers Index', fullExplanation: 'PMI surveys business activity. Above 50 = expansion. Below 50 = contraction. Leading indicator.', whyUseful: 'Economic health check.' },
  { term: 'CPI', category: 'fundamentals', shortDef: 'Consumer Price Index', fullExplanation: 'CPI measures inflation. Fed targets 2%. High CPI = rate hike expectations = USD bullish.', whyUseful: 'Inflation gauge.' },
  { term: 'GDP', category: 'fundamentals', shortDef: 'Gross Domestic Product', fullExplanation: 'GDP measures total economic output. Quarterly releases move markets. Negative = recession.', whyUseful: 'Economic growth measure.' },
  { term: 'Quantitative Easing', category: 'fundamentals', shortDef: 'Central bank asset purchases', fullExplanation: 'QE is central bank buying bonds to inject money. Generally currency negative, asset positive.', whyUseful: 'Monetary policy tool.' },
  { term: 'Quantitative Tightening', category: 'fundamentals', shortDef: 'Central bank asset reduction', fullExplanation: 'QT reduces central bank balance sheet. Drains liquidity. Generally currency positive.', whyUseful: 'Policy normalization.' },
  { term: 'Hawkish', category: 'fundamentals', shortDef: 'Favoring rate hikes', fullExplanation: 'Hawkish monetary policy prioritizes inflation fighting. Rate hikes = currency bullish.', whyUseful: 'Central bank stance.' },
  { term: 'Dovish', category: 'fundamentals', shortDef: 'Favoring rate cuts', fullExplanation: 'Dovish policy prioritizes growth/employment. Rate cuts = currency bearish.', whyUseful: 'Policy direction.' },
  { term: 'Forward Guidance', category: 'fundamentals', shortDef: 'Central bank policy signaling', fullExplanation: 'Forward guidance communicates future policy intentions. Moves markets before actual changes.', whyUseful: 'Anticipate policy.' },
  { term: 'Dot Plot', category: 'fundamentals', shortDef: 'Fed rate projections', fullExplanation: 'Dot plot shows FOMC members\' rate projections. Released quarterly. Median is market focus.', whyUseful: 'Rate path expectations.' },
  // FUTURES TERMS
  { term: 'Contango', category: 'basics', shortDef: 'Futures above spot price', fullExplanation: 'Contango is when futures trade above spot. Normal for storable commodities. Creates roll cost.', whyUseful: 'Understand roll impact.' },
  { term: 'Backwardation', category: 'basics', shortDef: 'Futures below spot price', fullExplanation: 'Backwardation is futures below spot. Indicates supply shortage. Roll earns money.', whyUseful: 'Supply/demand signal.' },
  { term: 'Basis', category: 'basics', shortDef: 'Spot minus futures price', fullExplanation: 'Basis = Spot - Futures. Positive in backwardation, negative in contango. Converges to zero at expiry.', whyUseful: 'Spread trading.' },
  { term: 'Roll', category: 'basics', shortDef: 'Moving to next contract', fullExplanation: 'Rolling closes expiring contract and opens next month. Roll cost/yield depends on curve shape.', whyUseful: 'Continuous exposure.' },
  { term: 'Roll Yield', category: 'basics', shortDef: 'Return from rolling contracts', fullExplanation: 'Roll yield is profit/loss from rolling. Positive in backwardation (sell high, buy low). Negative in contango.', whyUseful: 'Total return component.' },
  { term: 'Front Month', category: 'basics', shortDef: 'Nearest expiration contract', fullExplanation: 'Front month is most actively traded futures contract. Most liquid but requires frequent rolling.', whyUseful: 'Primary trading contract.' },
  { term: 'Back Month', category: 'basics', shortDef: 'Further expiration contract', fullExplanation: 'Back months are contracts expiring later. Less liquid but longer time to expiry.', whyUseful: 'Longer duration.' },
  { term: 'Open Interest', category: 'indicators', shortDef: 'Outstanding contracts', fullExplanation: 'Open interest is total open positions. Rising OI with price = strong trend. Falling OI = weakening.', whyUseful: 'Trend strength.' },
  { term: 'Volume', category: 'indicators', shortDef: 'Contracts traded', fullExplanation: 'Volume is number of contracts traded in period. Confirms price moves. High volume = conviction.', whyUseful: 'Confirm moves.' },
  { term: 'Contract Specs', category: 'basics', shortDef: 'Futures contract details', fullExplanation: 'Contract specs define multiplier, tick size, expiry, delivery. ES = $50/point, CL = 1000 barrels.', whyUseful: 'Know what you trade.' },
  { term: 'Tick Size', category: 'basics', shortDef: 'Minimum price increment', fullExplanation: 'Tick size is smallest price move. ES = 0.25 points = $12.50. CL = $0.01 = $10.', whyUseful: 'Calculate P&L.' },
  { term: 'Multiplier', category: 'basics', shortDef: 'Dollar value per point', fullExplanation: 'Multiplier converts points to dollars. ES = $50, NQ = $20, CL = $1000 per point.', whyUseful: 'Position sizing.' },
  { term: 'E-mini', category: 'basics', shortDef: 'Electronically traded mini contract', fullExplanation: 'E-minis are smaller versions of full futures. ES (S&P 500) is 1/5 of full. Popular with retail.', whyUseful: 'Accessible futures.' },
  { term: 'Micro', category: 'basics', shortDef: 'Even smaller futures contract', fullExplanation: 'Micro futures are 1/10 of E-mini. MES = $5/point. Very accessible for smaller accounts.', whyUseful: 'Small account trading.' },
  { term: 'Limit Up', category: 'regulations', shortDef: 'Maximum daily price increase', fullExplanation: 'Limit up is maximum allowed daily price increase. Trading halts at limit. Expanded limits next day.', whyUseful: 'Price protection.' },
  { term: 'Limit Down', category: 'regulations', shortDef: 'Maximum daily price decrease', fullExplanation: 'Limit down is maximum allowed daily decrease. Triggers trading halt. Protects against crashes.', whyUseful: 'Crash protection.' },
  { term: 'Lock Limit', category: 'regulations', shortDef: 'Price stuck at limit', fullExplanation: 'Lock limit occurs when price hits limit and stays there. No trading possible until limit expands.', whyUseful: 'Understand trading halts.' },
  { term: 'First Notice Day', category: 'regulations', shortDef: 'Delivery notice begins', fullExplanation: 'FND is first day long holders may be assigned delivery notice. Close positions before to avoid delivery.', whyUseful: 'Avoid delivery.' },
  { term: 'Last Trading Day', category: 'regulations', shortDef: 'Final day to trade contract', fullExplanation: 'LTD is last day to trade before expiry. Must close or roll before this date.', whyUseful: 'Avoid settlement issues.' },
  { term: 'Cash Settlement', category: 'regulations', shortDef: 'Settle in cash not delivery', fullExplanation: 'Cash-settled futures pay difference in cash. No physical delivery. Stock indices are cash-settled.', whyUseful: 'No delivery risk.' },
  { term: 'Physical Delivery', category: 'regulations', shortDef: 'Actual commodity delivered', fullExplanation: 'Physical delivery means actually receiving commodity. Oil, grains, metals can require delivery.', whyUseful: 'Know your obligations.' },
  { term: 'Delivery Month', category: 'basics', shortDef: 'Contract expiration month', fullExplanation: 'Futures are named by delivery month. ESZ24 = S&P December 2024. Letter codes for months.', whyUseful: 'Read contract names.' },
  { term: 'Spread Trading', category: 'strategies', shortDef: 'Long one contract short another', fullExplanation: 'Spread trading goes long one contract, short related one. Calendar spreads, inter-commodity spreads.', whyUseful: 'Reduced risk trading.' },
  { term: 'Calendar Spread', category: 'strategies', shortDef: 'Different expirations same commodity', fullExplanation: 'Calendar spread is long one month, short another. Profits from changes in time spread.', whyUseful: 'Trade time premium.' },
  { term: 'Inter-Commodity Spread', category: 'strategies', shortDef: 'Related commodities', fullExplanation: 'Trade related commodities: gold/silver, crude/heating oil. Profit from relative moves.', whyUseful: 'Relative value.' },
  { term: 'Crush Spread', category: 'strategies', shortDef: 'Soybean processing margin', fullExplanation: 'Crush spread = soybean meal + oil - soybeans. Tracks processing margin.', whyUseful: 'Ag sector trading.' },
  { term: 'Crack Spread', category: 'strategies', shortDef: 'Oil refining margin', fullExplanation: 'Crack spread = refined products (gas + heating oil) - crude oil. Refinery profit margin.', whyUseful: 'Energy sector trading.' },
  { term: 'Spark Spread', category: 'strategies', shortDef: 'Power plant margin', fullExplanation: 'Spark spread = electricity price - natural gas cost. Power generation profitability.', whyUseful: 'Utility trading.' },
  // FINAL BATCH TO REACH 1000+
  { term: 'Synthetic Put', category: 'strategies', shortDef: 'Short stock + long call', fullExplanation: 'Synthetic put = short stock + long call. Same payoff as long put. Useful when puts unavailable.', whyUseful: 'Put alternative.' },
  { term: 'Synthetic Call', category: 'strategies', shortDef: 'Long stock + long put', fullExplanation: 'Synthetic call = long stock + long put. Same payoff as long call. Protective put = synthetic call.', whyUseful: 'Call alternative.' },
  { term: 'Split Strike Synthetic', category: 'strategies', shortDef: 'Stock with different strike options', fullExplanation: 'Split strike uses put and call at different strikes. Creates modified payoff structure.', whyUseful: 'Modified synthetic.' },
  { term: 'Risk Reversal', category: 'strategies', shortDef: 'Sell put, buy call', fullExplanation: 'Risk reversal sells OTM put, buys OTM call. Zero cost bullish exposure. Opposite of collar.', whyUseful: 'Leveraged bullish bet.' },
  { term: 'Combo', category: 'strategies', shortDef: 'Synthetic stock with options', fullExplanation: 'Combo is synthetic long (buy call, sell put) or short (sell call, buy put) stock.', whyUseful: 'Stock replacement.' },
  { term: 'Married Put', category: 'strategies', shortDef: 'Stock purchase with put', fullExplanation: 'Married put buys stock and put simultaneously. Insurance from day one.', whyUseful: 'Immediate protection.' },
  { term: 'Fiduciary Call', category: 'strategies', shortDef: 'Call + cash for exercise', fullExplanation: 'Fiduciary call = call + PV of strike in cash. Replicates protective put by put-call parity.', whyUseful: 'Parity relationship.' },
  { term: 'Gamma Scalping', category: 'strategies', shortDef: 'Trading gamma by hedging delta', fullExplanation: 'Gamma scalping buys options, then trades stock to neutralize delta. Profits from realized volatility.', whyUseful: 'Trade volatility.' },
  { term: 'Delta Neutral', category: 'strategies', shortDef: 'No directional exposure', fullExplanation: 'Delta neutral position has zero delta. Not directional. Isolates other Greeks.', whyUseful: 'Volatility trading.' },
  { term: 'Vega Neutral', category: 'strategies', shortDef: 'No volatility exposure', fullExplanation: 'Vega neutral eliminates sensitivity to IV changes. Pure directional or theta play.', whyUseful: 'Remove vol risk.' },
  { term: 'Gamma Neutral', category: 'strategies', shortDef: 'Stable delta', fullExplanation: 'Gamma neutral means delta won\'t change as price moves. Requires selling options.', whyUseful: 'Stable hedge.' },
  { term: 'Theta Gang', category: 'strategies', shortDef: 'Selling options for decay', fullExplanation: 'Theta gang strategies sell options to collect time decay. Covered calls, cash-secured puts, spreads.', whyUseful: 'Income generation.' },
  { term: 'Vol Crush', category: 'risk', shortDef: 'IV collapse after event', fullExplanation: 'Vol crush is IV drop after anticipated event (earnings). Hurts long options even if direction right.', whyUseful: 'Avoid overpaying.' },
  { term: 'IV Percentile', category: 'indicators', shortDef: 'Current IV vs historical', fullExplanation: 'IV percentile = % of days in past year with lower IV. 80% = IV higher than 80% of days.', whyUseful: 'Is IV high or low?' },
  { term: 'IV Rank', category: 'indicators', shortDef: 'IV position in 52-week range', fullExplanation: 'IV Rank = (Current IV - 52w Low) / (52w High - 52w Low). 100% = at 52-week high.', whyUseful: 'IV context.' },
  { term: 'Realized Volatility', category: 'indicators', shortDef: 'Actual price movement', fullExplanation: 'RV is actual historical volatility. Compare to IV: RV > IV = IV was cheap.', whyUseful: 'IV vs reality.' },
  { term: 'Volatility Risk Premium', category: 'indicators', shortDef: 'IV minus realized volatility', fullExplanation: 'VRP = IV - RV. Usually positive (IV > RV) as options are priced for risk. Selling captures VRP.', whyUseful: 'Option selling edge.' },
  { term: 'Term Structure', category: 'indicators', shortDef: 'Volatility across expirations', fullExplanation: 'Vol term structure shows IV for different expirations. Upward slope normal. Inverted = near-term fear.', whyUseful: 'Volatility expectations.' },
  { term: 'Volatility Smile', category: 'indicators', shortDef: 'IV across strikes', fullExplanation: 'Vol smile shows higher IV for OTM puts and calls vs ATM. Reflects fat tail expectations.', whyUseful: 'Strike selection.' },
  { term: 'Volatility Skew', category: 'indicators', shortDef: 'IV difference by strike', fullExplanation: 'Skew shows IV varies by strike. Equity skew: puts have higher IV than calls (downside fear).', whyUseful: 'Understand pricing.' },
  { term: 'Volatility Surface', category: 'indicators', shortDef: '3D view of vol across strikes and time', fullExplanation: 'Vol surface combines smile and term structure. Full picture of option market expectations.', whyUseful: 'Complete vol view.' },
  { term: 'VIX Futures', category: 'basics', shortDef: 'Futures on VIX index', fullExplanation: 'VIX futures trade expectations of future VIX. Not directly tradeable VIX spot.', whyUseful: 'Vol trading vehicle.' },
  { term: 'VXX', category: 'basics', shortDef: 'Short-term VIX ETN', fullExplanation: 'VXX tracks short-term VIX futures. Decays in contango. For short-term hedging only.', whyUseful: 'Short-term vol exposure.' },
  { term: 'UVXY', category: 'basics', shortDef: 'Leveraged VIX ETF', fullExplanation: 'UVXY is 1.5x leveraged VIX. Amplified decay in contango. Extreme short-term only.', whyUseful: 'Aggressive vol long.' },
  { term: 'SVXY', category: 'basics', shortDef: 'Short VIX ETF', fullExplanation: 'SVXY profits when VIX falls. Benefits from contango roll. Risks blow-up in vol spike.', whyUseful: 'Short volatility.' },
  { term: 'Volatility Arbitrage', category: 'strategies', shortDef: 'Trade IV vs expected RV', fullExplanation: 'Vol arb sells options when IV > expected RV, buys when IV < expected RV. Delta hedged.', whyUseful: 'Pure volatility trade.' },
  { term: 'Dispersion Trading', category: 'strategies', shortDef: 'Index vol vs component vol', fullExplanation: 'Dispersion sells index options, buys component options. Profits when correlation is low.', whyUseful: 'Correlation trade.' },
  { term: 'Variance Swap', category: 'strategies', shortDef: 'Trade realized variance', fullExplanation: 'Variance swaps pay based on realized variance vs strike. OTC product for pure volatility.', whyUseful: 'Pure variance exposure.' },
  { term: 'Volatility Swap', category: 'strategies', shortDef: 'Trade realized volatility', fullExplanation: 'Vol swap pays based on realized vol vs strike. Less convex than variance swap.', whyUseful: 'Direct vol exposure.' },
  { term: 'Expiration Value', category: 'basics', shortDef: 'Option worth at expiry', fullExplanation: 'Expiration value = intrinsic value only. Time value = 0 at expiry.', whyUseful: 'Final settlement.' },
  { term: 'Extrinsic Value', category: 'basics', shortDef: 'Value above intrinsic', fullExplanation: 'Extrinsic = Premium - Intrinsic. Time value + volatility premium. Decays to zero.', whyUseful: 'What you pay for time.' },
  { term: 'Intrinsic Value', category: 'basics', shortDef: 'Option\'s in-the-money amount', fullExplanation: 'Intrinsic value = |Stock - Strike| for ITM options. Zero for OTM.', whyUseful: 'Minimum option value.' },
  { term: 'At-the-Money', category: 'basics', shortDef: 'Strike equals stock price', fullExplanation: 'ATM options have strike near current stock price. Highest theta and vega.', whyUseful: 'Maximum time value.' },
  { term: 'In-the-Money', category: 'basics', shortDef: 'Option has intrinsic value', fullExplanation: 'ITM calls: strike < stock. ITM puts: strike > stock. Has intrinsic value.', whyUseful: 'Has immediate value.' },
  { term: 'Out-of-the-Money', category: 'basics', shortDef: 'Option has no intrinsic value', fullExplanation: 'OTM calls: strike > stock. OTM puts: strike < stock. Only extrinsic value.', whyUseful: 'Cheaper, higher leverage.' },
  { term: 'Deep ITM', category: 'basics', shortDef: 'Far in-the-money', fullExplanation: 'Deep ITM options have delta near 1 (calls) or -1 (puts). Move almost like stock.', whyUseful: 'Stock replacement.' },
  { term: 'Deep OTM', category: 'basics', shortDef: 'Far out-of-the-money', fullExplanation: 'Deep OTM options have very low delta. Cheap but low probability of profit.', whyUseful: 'Lottery tickets.' },
  { term: 'Strike Price', category: 'basics', shortDef: 'Exercise price of option', fullExplanation: 'Strike is price at which option can be exercised. Call buyer can buy at strike; put buyer can sell.', whyUseful: 'Core option parameter.' },
  { term: 'Expiration Date', category: 'basics', shortDef: 'When option expires', fullExplanation: 'Expiration is last day option can be exercised. Typically third Friday for monthly options.', whyUseful: 'Time limit.' },
  { term: 'Weekly Options', category: 'basics', shortDef: 'Short-dated options', fullExplanation: 'Weeklies expire every Friday. Higher theta decay. Popular for earnings and short-term trades.', whyUseful: 'Short-term trading.' },
  { term: 'LEAPS', category: 'basics', shortDef: 'Long-term options', fullExplanation: 'LEAPS are options with 1+ year to expiration. Lower theta, act more like stock.', whyUseful: 'Long-term exposure.' },
  { term: 'Mini Options', category: 'basics', shortDef: '10-share options', fullExplanation: 'Mini options control 10 shares instead of 100. Available on select high-priced stocks.', whyUseful: 'Smaller position size.' },
  { term: 'Flex Options', category: 'basics', shortDef: 'Customizable options', fullExplanation: 'FLEX options allow custom strikes, expirations, exercise style. OTC-like on exchange.', whyUseful: 'Custom hedging.' },
  { term: 'Binary Option', category: 'basics', shortDef: 'All-or-nothing payout', fullExplanation: 'Binary options pay fixed amount if ITM at expiry, zero otherwise. High-risk, often fraudulent offshore.', whyUseful: 'Avoid scams.', whyNotUseful: 'Often scams.' },
  { term: 'Barrier Option', category: 'basics', shortDef: 'Activates/deactivates at price', fullExplanation: 'Barrier options knock-in or knock-out when underlying hits barrier. OTC exotic option.', whyUseful: 'Exotic products.' },
  { term: 'Asian Option', category: 'basics', shortDef: 'Average price option', fullExplanation: 'Asian options use average price over period instead of spot at expiry. Lower vol, cheaper.', whyUseful: 'Reduce timing risk.' },
  { term: 'Lookback Option', category: 'basics', shortDef: 'Best price during period', fullExplanation: 'Lookback options let you exercise at best price during option life. Very expensive.', whyUseful: 'Eliminate timing regret.' },
  { term: 'Chooser Option', category: 'basics', shortDef: 'Choose call or put later', fullExplanation: 'Chooser option lets holder decide if it\'s a call or put at a future date.', whyUseful: 'Flexible directional bet.' },
  { term: 'Compound Option', category: 'basics', shortDef: 'Option on an option', fullExplanation: 'Compound option is right to buy another option. Used for staged investment decisions.', whyUseful: 'Staged exposure.' },
  { term: 'Rainbow Option', category: 'basics', shortDef: 'Multiple underlying assets', fullExplanation: 'Rainbow options have payoff based on multiple assets. Best of, worst of, spread on basket.', whyUseful: 'Multi-asset exposure.' },
  { term: 'Quanto Option', category: 'basics', shortDef: 'Fixed currency conversion', fullExplanation: 'Quanto options eliminate FX risk by fixing exchange rate. Underlying in foreign currency, payout in domestic.', whyUseful: 'Remove FX exposure.' },
];

// Glossary categories for filtering

// Glossary categories for filtering
const glossaryCategories = [
  { id: 'all', label: 'All Terms', icon: Book },
  { id: 'basics', label: 'Basics', icon: Activity },
  { id: 'indicators', label: 'Indicators', icon: BarChart3 },
  { id: 'strategies', label: 'Strategies', icon: Target },
  { id: 'risk', label: 'Risk Mgmt', icon: Shield },
  { id: 'fundamentals', label: 'Fundamentals', icon: TrendingUp },
  { id: 'patterns', label: 'Patterns', icon: Layers },
  { id: 'regulations', label: 'Regulations', icon: AlertTriangle },
];

interface GlossaryTermCardProps {
  term: GlossaryTerm;
  isExpanded: boolean;
  onToggle: () => void;
  onReadAloud?: (term: GlossaryTerm) => void;
}

function GlossaryTermCard({ term, isExpanded, onToggle, onReadAloud }: GlossaryTermCardProps) {
  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      basics: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      indicators: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      strategies: 'bg-green-500/20 text-green-400 border-green-500/30',
      risk: 'bg-red-500/20 text-red-400 border-red-500/30',
      fundamentals: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      patterns: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    };
    return colors[category] || colors.basics;
  };

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700/50 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700/30 transition-colors"
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className={`px-2 py-0.5 text-xs rounded border flex-shrink-0 ${getCategoryColor(term.category)}`}>
            {term.category.charAt(0).toUpperCase() + term.category.slice(1)}
          </span>
          <span className="font-semibold text-white flex-shrink-0">{term.term}</span>
          <span className="text-sm text-slate-400 hidden md:inline truncate">— {term.shortDef}</span>
        </div>
        <div className="flex items-center gap-2">
          {onReadAloud && (
            <button
              onClick={(e) => { e.stopPropagation(); onReadAloud(term); }}
              className="p-1.5 rounded-lg bg-slate-700/50 text-slate-400 hover:text-violet-400 hover:bg-slate-700 transition-colors"
              title="Read aloud"
            >
              <Volume2 className="w-4 h-4" />
            </button>
          )}
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>
      
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-slate-700/50 pt-4">
          {/* Full Explanation */}
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase mb-2">What is it?</h4>
            <p className="text-sm text-slate-300">{term.fullExplanation}</p>
          </div>
          
          {/* Formula */}
          {term.formula && (
            <div className="p-3 bg-slate-900/50 rounded-lg border border-slate-700/50">
              <h4 className="text-xs font-medium text-violet-400 uppercase mb-2">Formula</h4>
              <code className="text-sm text-green-400 font-mono">{term.formula}</code>
            </div>
          )}
          
          {/* Why Useful */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 bg-green-500/5 rounded-lg border border-green-500/20">
              <h4 className="text-xs font-medium text-green-400 uppercase mb-2 flex items-center gap-1">
                <TrendingUp className="w-3 h-3" /> Why It's Useful
              </h4>
              <p className="text-sm text-slate-300">{term.whyUseful}</p>
            </div>
            
            {term.whyNotUseful && (
              <div className="p-3 bg-red-500/5 rounded-lg border border-red-500/20">
                <h4 className="text-xs font-medium text-red-400 uppercase mb-2 flex items-center gap-1">
                  <TrendingDown className="w-3 h-3" /> Limitations
                </h4>
                <p className="text-sm text-slate-300">{term.whyNotUseful}</p>
              </div>
            )}
          </div>
          
          {/* Example */}
          {term.example && (
            <div className="p-3 bg-blue-500/5 rounded-lg border border-blue-500/20">
              <h4 className="text-xs font-medium text-blue-400 uppercase mb-2">Example</h4>
              <p className="text-sm text-slate-300">{term.example}</p>
            </div>
          )}
          
          {/* XFactor Usage */}
          {term.xfactorUsage && (
            <div className="p-3 bg-violet-500/5 rounded-lg border border-violet-500/20">
              <h4 className="text-xs font-medium text-violet-400 uppercase mb-2 flex items-center gap-1">
                <Zap className="w-3 h-3" /> Used in XFactor
              </h4>
              <p className="text-sm text-slate-300">{term.xfactorUsage}</p>
            </div>
          )}
          
          {/* Related Terms */}
          {term.relatedTerms && term.relatedTerms.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-slate-500 uppercase mb-2">Related Terms</h4>
              <div className="flex flex-wrap gap-2">
                {term.relatedTerms.map((related, i) => (
                  <span key={i} className="px-2 py-1 text-xs bg-slate-700/50 text-slate-400 rounded">
                    {related}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* External Image (Encyclopedia-style) */}
          {term.imageUrl && (
            <div className="mt-4 rounded-lg overflow-hidden border border-slate-700/50">
              <img 
                src={term.imageUrl} 
                alt={term.term}
                className="w-full max-h-64 object-contain bg-white"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
              {(term.imageCaption || term.imageCredit) && (
                <div className="px-3 py-2 bg-slate-900/50 text-xs">
                  {term.imageCaption && <p className="text-slate-400">{term.imageCaption}</p>}
                  {term.imageCredit && <p className="text-slate-500 mt-1">Source: {term.imageCredit}</p>}
                </div>
              )}
            </div>
          )}
          
          {/* Visual Diagram (SVG) */}
          {term.diagram && (
            <GlossaryDiagram type={term.diagram} />
          )}
        </div>
      )}
    </div>
  );
}

export default function HelpModal({ isOpen, onClose }: HelpModalProps) {
  const [activeTab, setActiveTab] = useState<'features' | 'quickstart' | 'glossary' | 'changelog'>('features');
  const [glossaryCategory, setGlossaryCategory] = useState<string>('all');
  const [glossarySearch, setGlossarySearch] = useState('');
  const [expandedTerms, setExpandedTerms] = useState<Set<string>>(new Set());
  
  // Voice search state
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const recognitionRef = useRef<any>(null);
  
  useEffect(() => {
    setVoiceSupported(isSpeechRecognitionSupported());
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      stopSpeaking();
    };
  }, []);
  
  // Toggle voice search
  const toggleVoiceSearch = () => {
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
    } else {
      recognitionRef.current = createSpeechRecognition({
        continuous: false,
        interimResults: true,
        onResult: (transcript, isFinal) => {
          setGlossarySearch(transcript);
        },
        onEnd: () => setIsListening(false),
        onError: () => setIsListening(false)
      });
      
      if (recognitionRef.current) {
        recognitionRef.current.start();
        setIsListening(true);
      }
    }
  };
  
  // Read term aloud
  const readTermAloud = (term: GlossaryTerm) => {
    if (!isSpeechSynthesisSupported()) return;
    
    const text = `${term.term}. ${term.shortDef}. ${term.fullExplanation}. ${term.whyUseful ? `Why it's useful: ${term.whyUseful}` : ''}`;
    speak(text, { rate: 0.95 });
  };

  if (!isOpen) return null;

  const toggleTerm = (term: string) => {
    const newExpanded = new Set(expandedTerms);
    if (newExpanded.has(term)) {
      newExpanded.delete(term);
    } else {
      newExpanded.add(term);
    }
    setExpandedTerms(newExpanded);
  };

  const filteredGlossaryTerms = glossaryTerms.filter(term => {
    const matchesCategory = glossaryCategory === 'all' || term.category === glossaryCategory;
    const matchesSearch = glossarySearch === '' || 
      term.term.toLowerCase().includes(glossarySearch.toLowerCase()) ||
      term.shortDef.toLowerCase().includes(glossarySearch.toLowerCase()) ||
      term.fullExplanation.toLowerCase().includes(glossarySearch.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden border border-slate-700">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700 bg-gradient-to-r from-blue-600/20 to-purple-600/20">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <HelpCircle className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">XFactor Bot Help</h2>
              <p className="text-sm text-slate-400">Version {VERSION} • {changelog[0]?.date || 'Latest'}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-700">
          {[
            { id: 'features', label: 'Features', icon: Zap },
            { id: 'quickstart', label: 'Quick Start', icon: Activity },
            { id: 'glossary', label: 'Glossary', icon: Book },
            { id: 'changelog', label: 'Changelog', icon: Calendar }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2 ${
                activeTab === tab.id
                  ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-500/10'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[65vh]">
          {activeTab === 'features' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {features.map((feature, index) => (
                <div
                  key={index}
                  className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-blue-500/50 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-blue-500/20 rounded-lg shrink-0">
                      <feature.icon className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white mb-1">{feature.title}</h3>
                      <p className="text-sm text-slate-400">{feature.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'quickstart' && (
            <div className="space-y-4">
              <p className="text-slate-300 mb-6">
                Get started with XFactor Bot in 5 simple steps:
              </p>
              {quickStart.map((item) => (
                <div
                  key={item.step}
                  className="flex items-start gap-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700"
                >
                  <div className="w-8 h-8 flex items-center justify-center bg-blue-500 rounded-full text-white font-bold shrink-0">
                    {item.step}
                  </div>
                  <div>
                    <h3 className="font-semibold text-white mb-1">{item.title}</h3>
                    <p className="text-sm text-slate-400">{item.description}</p>
                  </div>
                </div>
              ))}

              <div className="mt-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                <h4 className="font-semibold text-amber-400 mb-2">⚠️ Important Notes</h4>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Always start with Paper trading mode to test strategies</li>
                  <li>• Set appropriate risk limits before enabling Live trading</li>
                  <li>• Monitor bot performance regularly using the Performance Charts</li>
                  <li>• Use Auto-Tune to optimize bot parameters automatically</li>
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'glossary' && (
            <div className="space-y-4">
              {/* Header */}
              <div className="flex flex-col md:flex-row gap-4 mb-6">
                <p className="text-slate-300 flex-1">
                  <span className="text-2xl mr-2">📚</span>
                  <strong>{glossaryTerms.length} terms</strong> covering trading basics, technical indicators, strategies, risk management, and chart patterns used in XFactor.
                </p>
              </div>
              
              {/* Search - Full Width Row with Voice */}
              <div className="relative w-full flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 pointer-events-none" />
                  <input
                    type="text"
                    placeholder={isListening ? "Listening... say a term" : "Search 500+ trading terms, indicators, strategies..."}
                    value={glossarySearch}
                    onChange={(e) => setGlossarySearch(e.target.value)}
                    className={`w-full pl-12 pr-4 py-3 bg-slate-800/50 border rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 text-lg ${
                      isListening ? 'border-red-500' : 'border-slate-700'
                    }`}
                  />
                </div>
                {/* Voice Search Button */}
                {voiceSupported && (
                  <button
                    onClick={toggleVoiceSearch}
                    className={`px-4 py-3 rounded-xl transition-all flex items-center gap-2 ${
                      isListening 
                        ? 'bg-red-500 text-white animate-pulse' 
                        : 'bg-slate-700/50 text-slate-400 hover:text-white hover:bg-slate-600'
                    }`}
                    title={isListening ? 'Stop listening' : 'Voice search'}
                  >
                    {isListening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
                    <span className="hidden md:inline text-sm">{isListening ? 'Stop' : 'Voice'}</span>
                  </button>
                )}
              </div>
              
              {/* Voice Status */}
              {isListening && (
                <div className="flex items-center gap-2 text-xs text-red-400">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                  Listening... speak a trading term
                </div>
              )}
              
              {/* Category Filters - Separate Row */}
              <div className="flex flex-wrap gap-2">
                {glossaryCategories.map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setGlossaryCategory(cat.id)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                      glossaryCategory === cat.id
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700'
                    }`}
                  >
                    <cat.icon className="w-3 h-3" />
                    {cat.label}
                  </button>
                ))}
              </div>
              
              {/* Results count */}
              <div className="text-sm text-slate-500">
                Showing {filteredGlossaryTerms.length} of {glossaryTerms.length} terms
              </div>
              
              {/* Terms List */}
              <div className="space-y-2">
                {filteredGlossaryTerms.map((term) => (
                  <GlossaryTermCard
                    key={term.term}
                    term={term}
                    isExpanded={expandedTerms.has(term.term)}
                    onToggle={() => toggleTerm(term.term)}
                    onReadAloud={isSpeechSynthesisSupported() ? readTermAloud : undefined}
                  />
                ))}
              </div>
              
              {filteredGlossaryTerms.length === 0 && (
                <div className="text-center py-12 text-slate-500">
                  <Book className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No terms found matching your search.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'changelog' && (
            <div className="space-y-6">
              {changelog.map((release) => (
                <div key={release.version} className="border-l-2 border-blue-500 pl-4">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-sm font-mono rounded">
                      v{release.version}
                    </span>
                    <span className="text-sm text-slate-400">{release.date}</span>
                  </div>
                  <ul className="space-y-1">
                    {release.changes.map((change, i) => (
                      <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                        <span className="text-green-400 mt-1">•</span>
                        {change}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-700 bg-slate-800/50">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400">
              © 2025 XFactor Trading • AI-Powered Automated Trading System
            </p>
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded">
                {VERSION}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
