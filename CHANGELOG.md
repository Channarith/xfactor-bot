# Changelog

All notable changes to the XFactor Bot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.9] - 2025-12-21

### 🔒 XFactor-botMin Deployment Mode

#### MIN Mode for foresight.nvidia.com
- **Restricted Features**: Broker connections and Live trading disabled by default
- **Easter Egg Unlock**: Click the MIN badge 7 times quickly to trigger unlock prompt
- **Unlock Password**: `106431` unlocks full features
- **Visual Indicator**: MIN badge shows lock icon when restricted, sparkles when unlocked (MIN+)
- **Session Persistence**: Unlock state persists for browser session

#### Deployment Scripts
- **`scripts/deploy-foresight.sh`**: Deploy MIN version to foresight.nvidia.com:9876
- **`scripts/preview-min.sh`**: Test MIN mode locally before deployment
- **`scripts/stop-min-preview.sh`**: Stop local MIN preview

#### Features in MIN Mode (Always Available)
- ✅ All Help & Glossary features (500+ terms, images, audio)
- ✅ AI Market Forecasting (demo data)
- ✅ News & Sentiment feed
- ✅ Video Platforms Intelligence
- ✅ Bot Manager (view/create, paper mode only)
- ❌ Broker connections (locked)
- ❌ Live trading mode (locked)

### 🎤 Voice & Audio Features

#### Audio Readout (Text-to-Speech)
- **News Headlines**: "🔊" button to read top 5 news headlines aloud
- **AI Assistant**: "🔊" button to read last AI response aloud
- **Glossary Terms**: Each term has speaker button to read definition aloud
- **Browser Native**: Uses Web Speech API for speech synthesis

#### Voice Input (Speech-to-Text)
- **AI Assistant**: Microphone button for voice dictation of questions
- **Glossary Search**: Voice search button for hands-free term lookup
- **Auto-Submit**: Voice input auto-submits after speech recognition completes
- **Visual Feedback**: Pulsing red indicator when listening

### 🔍 Enhanced Search & Navigation

#### AI Forecasting - Name Search
- **Company Name Search**: Search "Apple" or "Microsoft" instead of just symbols
- **Autocomplete Dropdown**: Shows matching companies with symbol, name, exchange
- **Debounced Search**: 300ms delay to prevent excessive API calls
- **Keyboard Navigation**: Enter to forecast, Escape to close suggestions

### 📰 Live News Features

#### Auto-Update Feature
- **Live Updates Toggle**: Enable automatic news refresh (15s/30s/1m/2m/5m)
- **"LIVE" Indicator**: Pulsing green badge when auto-update is active
- **Configurable Interval**: Dropdown to select update frequency

### 📊 Improved Data Visualization

#### AI Pattern Predictions - Visual Charts
- **Mini SVG Charts**: Each pattern prediction now shows fluctuation visualization
- **Bullish Patterns**: Green upward-trending pattern lines
- **Bearish Patterns**: Red downward-trending pattern lines
- **Entry/Target Markers**: Visual price markers on mini charts

#### Pagination Controls
- **Items Per Page Selector**: Choose 10, 25, 50, or All items
- **Trader Insights**: Dropdown selector for insider trades, top traders, etc.
- **Page Resets**: Auto-reset to page 1 when changing items per page

### ⚙️ Settings & Configuration

#### Integrations Panel Improvements
- **Manage Integrations Button Fixed**: Now toggles configure mode
- **AI Providers Section**: Shows OpenAI, Anthropic, Ollama status
- **Configure Links**: Each integration shows configure button when managing
- **Done Button**: Clear exit from manage mode

#### AI Provider API Endpoints
- **GET /api/integrations/ai/providers**: List all AI providers and status
- **POST /api/integrations/ai/providers/{provider}/test**: Test provider connection
- **Ollama Detection**: Automatically checks if Ollama is running locally
- **Model Availability**: Lists available models for local Ollama

### 📚 Glossary Enhancements

#### Encyclopedia-Style Images
- **Image Support**: Glossary terms now support external images
- **Fibonacci Retracement**: Added visual diagram from Investopedia
- **RSI Indicator**: Added overbought/oversold visualization
- **MACD Chart**: Added crossover and histogram diagram
- **Bollinger Bands**: Added squeeze and expansion visualization
- **Head & Shoulders**: Added pattern structure diagram
- **Double Top**: Added M-pattern visualization
- **Image Credits**: Source attribution for all images

#### Data Display Improvements
- **Video Platforms**: Added last update timestamp display
- **Refresh Button Enhancement**: Spinner animation while loading
- **Loading States**: All panels show loading indicators

---

## [1.0.8] - 2025-12-19

### 🐳 Docker Development Improvements

#### Rebuild Script
- **`scripts/docker-rebuild.sh`**: Always rebuilds with latest code
- **Options**: `--clean` (no cache), `--logs` (show logs), `--stop` (just stop)
- **Auto-version**: Displays current version from package.json

#### Development Docker Compose
- **`docker-compose.dev.yml`**: Volume-mounted source code for live changes
- **Auto-reload**: Python backend auto-reloads on file changes
- **No rebuild needed**: Just save files and refresh browser
- **Frontend updates**: Run `cd frontend && npm run build` for UI changes

### 🔧 Strategy Controls Sync Fix

#### Trading Strategies ↔ Strategy Controls Synchronization
- **Fixed Sync Issue**: Trading strategies in Create Bot now properly sync with Strategy Controls
- **BotManager API Fix**: Now uses `getApiBaseUrl()` for strategy status fetch
- **Re-fetch on Create**: Strategy status re-fetches when Create Bot form opens
- **StrategyPanel Backend Sync**: Toggles now update backend feature flags in real-time
- **Added Feature Flags**: strategy_ai, strategy_social, strategy_options, strategy_seasonal

#### Backend Error Fixes
- **Yahoo Finance API**: Fixed boolean parameter error in symbol search (`enableFuzzyQuery`)
- **All parameters now strings**: Prevents "Invalid variable type: value should be str" errors

### 📚 Expanded Trading Glossary - 528 Terms

#### Massive Glossary Expansion
- **528 Terms**: Increased from 290 to 528 comprehensive trading terms
- **Acronyms**: M&A, ATRWAC, FOMC, GDP, CPI, NFP, QE/QT, SPAC, and 50+ more
- **Seasonal Events**: Summer Doldrums, Sell in May, October Effect, Santa Rally, Window Dressing, Tax Loss Selling
- **Order Types**: Stop Limit, OCO, Bracket, GTC, IOC, FOK, MOC, TWAP, VWAP execution
- **Bot Configuration**: Max Positions, Max Position Size, Risk Per Trade, Cooldown Period, Daily Loss Limit, Weekly Loss Limit
- **Risk Metrics**: Beta-Adjusted Exposure, Gross/Net Exposure, Concentration Risk, Tail Risk, Black Swan
- **Forex**: Pip, Lot Size, Currency Pairs, Sessions, Carry Trade, Safe Haven currencies
- **Commodities**: Crude Oil, Gold, Silver, Copper, Natural Gas, Agriculture
- **Corporate Actions**: M&A, Spin-Offs, Tender Offers, Buybacks, Lock-Up Periods
- **Factor Investing**: Value, Momentum, Quality, Size, Low Volatility factors
- **Whale Tracking**: Whale, Whale Alert, Whale Accumulation/Distribution, Dark Pool Activity

#### UI Updates
- **Search placeholder**: Updated to reflect 500+ terms
- **Feature descriptions**: Updated across all mentions

---

## [1.0.7] - 2025-12-19

### 🔮 AI Market Forecasting - Fully Operational

#### Route Ordering Fix
- **Fixed API Route Bug**: Static routes (`/hypothesis/active`, `/catalysts/imminent`) now properly prioritized before dynamic routes (`/hypothesis/{symbol}`, `/catalysts/{symbol}`)
- **All 4 Tabs Working**: Trending, Catalysts, AI Hypotheses, and Viral tabs now populate correctly

#### Auto-Fetch on Startup
- **Automatic Data Population**: Forecasting data now auto-fetches when server starts
- **No Manual Refresh Needed**: Data available immediately without clicking Force Fetch
- **30 Popular Symbols**: NVDA, AAPL, TSLA, MSFT, GOOGL, AMZN, META, AMD, and 22 more

#### Enhanced Data Generation
- **Lower Thresholds**: More inclusive data generation for comprehensive coverage
- **Synthetic Catalysts**: Generated when no earnings data available from yfinance
- **8+ AI Hypotheses**: Generated per fetch cycle based on top movers
- **15+ Viral Signals**: Buzz/trending signals for market movers

#### Technical Improvements
- **FastAPI Route Priority**: Static paths before parameterized paths
- **Background Task Fixes**: Proper async handling for force-fetch
- **Cache Synchronization**: Reliable data caching for all forecasting endpoints

---

## [1.0.6] - 2025-12-19

### 📊 AI Pattern Predictions

#### Pattern Detection
- **Trend Continuation/Reversal**: Confidence scores for trend analysis
- **Volatility Squeeze Breakout**: Detecting compression before expansion
- **Mean Reversion Signals**: Overbought/Oversold detection
- **Support/Resistance Testing**: Key level alerts
- **Analyst Divergence**: When price diverges from analyst consensus
- **Momentum Divergence**: Price vs momentum indicator divergence

### 📈 Visual Diagrams in Glossary

#### SVG Charts Added
- **Indicators**: RSI, MACD, Bollinger Bands, SMA/EMA diagrams
- **Patterns**: Head & Shoulders, Double Top/Bottom visualizations
- **Risk Management**: Stop Loss, Risk/Reward, Drawdown illustrations
- **Fibonacci**: Retracement level visualization
- **Trend Analysis**: Support/Resistance and Trend line diagrams

### 🔢 Score Breakdown with Formulas
- **Full Calculation Display**: Mathematical formulas for each score component
- **Weighted Breakdown**: Live calculation showing contribution percentages
- **Speculation Score**: Complete transparency on how scores are derived

### 📰 Fixed News Sources
- **yfinance API Update**: Adapted to new nested API structure
- **Proper Attribution**: Yahoo Finance, Reuters, etc. correctly displayed
- **No More "Unknown"**: All news articles show proper source

### ⛔ Strategy Disable Enforcement
- **Create Bot Protection**: Disabled strategies unselectable in form
- **Visual Indicators**: Grayed out with ⛔ icon and strikethrough
- **API Endpoint**: `GET /api/admin/strategies/status` for status check

### 🔢 Bot Numbering
- **Sequential Numbers**: All 40 bots numbered in Bot Manager list

### 🔗 Clickable External References
- **Influencer Links**: Names link to YouTube/TikTok/Instagram profiles
- **News Articles**: Click to open source website
- **Whale Alerts**: Links to blockchain explorers
- **Earnings/Signals**: Links to EarningsWhispers, Finviz, etc.

---

## [1.0.5] - 2025-12-19

### 💱 Forex Trading Bots

#### New Currency Trading Bots (3)
- **Major Forex Pairs**: EUR/USD, GBP/USD, USD/JPY, USD/CHF
- **Asia-Pacific FX**: AUD/USD, NZD/USD, USD/SGD, USD/HKD
- **Euro Crosses**: EUR/GBP, EUR/JPY, EUR/CHF, EUR/AUD

#### InstrumentType Extension
- **FOREX Added**: New instrument type for forex pairs
- **40 Total Bots**: Stocks, Options, Futures, Crypto, Commodities, Forex

### 📚 Comprehensive Trading Glossary
- **290+ Terms**: Searchable trading terminology
- **Categories**: Indicators, Patterns, Strategies, Risk Management, etc.
- **Visual Diagrams**: SVG illustrations for key concepts
- **XFactor Tips**: How each term applies to the platform

### 🔄 Dynamic Version Display
- **package.json Source**: Version injected at build time via Vite
- **No Hardcoding**: Single source of truth for version

### 🧠 Agentic Tuning (ATRWAC)
- **AI Auto-Tuning**: Anthropic, OpenAI, or Ollama integration
- **Strategy Optimization**: Automatic parameter adjustment
- **Real-time Feedback**: Performance-based tuning

### 📹 Video Platforms Intelligence
- **50+ Influencers**: YouTube, TikTok, Instagram tracking
- **Clickable Profiles**: Direct links to influencer pages
- **Viral Alerts**: Real-time trending content detection

---

## [1.0.4] - 2025-12-18

### 🔮 Market Forecasting - Price Projection Charts

#### Extrapolation Forecasting
- **Time Series Projections**: Extend historical price data into future dates (2026, 2027)
- **Multiple Horizons**: 1 month, 3 months, 6 months, and 1 year forecasts
- **Confidence Bands**: Upper/lower price bands based on historical volatility
- **Trend Extrapolation**: Linear regression with analyst target blending
- **Interactive Chart**: Visualize historical prices and projected future prices on one chart

#### Target Price Analysis
- **Bear/Base/Bull Cases**: Three-tier price targets with percentage changes
- **Analyst Consensus**: Integrated Wall Street analyst price targets
- **Recommendation Display**: Buy/Hold/Sell ratings with analyst count
- **Volatility Assessment**: Annualized volatility indicator with color coding

#### Quick Symbol Access
- **Quick Pick Buttons**: One-click access to popular stocks (NVDA, AAPL, TSLA, etc.)
- **Enter Key Search**: Press Enter to fetch projections instantly
- **Error Handling**: Clear error messages for invalid symbols

### 📊 Stock Analyzer - Comprehensive Time Series Analysis

#### Stock Search & Analysis
- **Global Symbol Search**: Search any stock by ticker or company name across all major exchanges
- **Comprehensive Historical Data**: 1mo, 3mo, 6mo, 1y, 2y, 5y historical price data
- **Interactive Candlestick Chart**: Full OHLCV candlestick charting with lightweight-charts
- **Real-time Metrics**: Current price, market cap, P/E, PEG, profit margin, beta, dividend yield

#### Overlay System - Multiple Data Series
- **Technical Indicators**:
  - SMA 20, 50, 200 (Simple Moving Averages)
  - EMA 12, 26 (Exponential Moving Averages)
  - RSI 14 (Relative Strength Index)
- **Volume Analysis**: Volume bars with 20-day SMA overlay
- **Toggle Controls**: Enable/disable any overlay independently
- **Color-coded Series**: Each overlay has distinct color for clarity

#### Inflection Point Detection
- **Peak Detection**: Identifies local price peaks with magnitude calculation
- **Trough Detection**: Identifies local price troughs with magnitude calculation
- **Golden Cross**: 20-day SMA crossing above 50-day SMA (bullish signal)
- **Death Cross**: 20-day SMA crossing below 50-day SMA (bearish signal)
- **Visual Markers**: Arrow markers on chart at each inflection point
- **Inflection List**: Expandable list with details for each detected point

#### Future Projections & Target Meeting Analysis
- **Analyst Price Targets**: Low, mean, and high price targets displayed
- **Target Lines**: Dashed lines on chart showing analyst targets projected forward
- **Trend Analysis**: Current bullish/bearish trend based on SMA relationship
- **Momentum Assessment**: Accelerating/stable momentum calculation
- **Target Probability**: Confidence level (high/medium/low) for meeting targets
- **Days to Target**: Estimated trading days to reach mean target at current momentum
- **Assessment Text**: Human-readable analysis of target meeting likelihood

#### Fundamental Data Time Series
- **EPS History**: Quarterly earnings per share over time
- **Revenue History**: Quarterly revenue in billions
- **P/E Ratio Tracking**: Price-to-earnings evolution
- **Market Cap History**: Market capitalization changes
- **Employee Count**: Workforce size data

#### Earnings & Dividends
- **Earnings History**: Past 20 quarters with reported vs estimated EPS
- **Surprise Tracking**: Earnings surprise percentage
- **Dividend History**: Up to 40 dividend payments
- **Future Estimates**: Next 4+ quarters of analyst EPS estimates

#### New API Endpoints
- `GET /api/stock-analysis/analyze/{symbol}` - Complete stock analysis
- `GET /api/stock-analysis/inflection-points/{symbol}` - Inflection points only
- `GET /api/stock-analysis/projections/{symbol}` - Analyst projections
- `GET /api/stock-analysis/compare` - Compare multiple stocks

#### New Files
- `src/api/routes/stock_analysis.py` - Stock analysis API endpoints
- `frontend/src/components/StockAnalyzer.tsx` - Stock analyzer UI component

---

## [1.0.3] - 2025-12-17

### 🔮 AI-Powered Market Forecasting & Speculation Engine

### 🛡️ Bot Risk Management System

#### Risk Scoring
- **Overall Risk Score (0-100)**: Weighted composite of all risk factors
- **Risk Levels**: Critical (80+), High (60-80), Elevated (40-60), Moderate (20-40), Low (0-20)
- **Color-coded indicators**: Visual risk level representation

#### Risk Components (8 factors)
- **Position Size Risk**: Maximum position as % of portfolio
- **Concentration Risk**: Single asset exposure
- **Drawdown Risk**: Current and max drawdown
- **Volatility Risk**: Daily/annualized volatility
- **Leverage Risk**: Margin usage
- **Correlation Risk**: Position correlation
- **Win Rate Risk**: Trading accuracy
- **Exposure Risk**: Total capital at risk

#### Risk-Adjusted Metrics
- **Sharpe Ratio**: Risk-adjusted return
- **Sortino Ratio**: Downside risk-adjusted return
- **Calmar Ratio**: Return vs max drawdown
- **Profit Factor**: Gross profit / gross loss
- **Value at Risk (VaR)**: 95% and 99% confidence
- **Expected Shortfall**: CVaR / tail risk

#### Risk Alerts
- **Real-time alerts**: Triggered when thresholds exceeded
- **Alert levels**: Critical, High, Elevated
- **Categories**: Drawdown, Exposure, Concentration, Win Rate, Leverage
- **Recommendations**: Actionable suggestions per alert

#### New API Endpoints
- `GET /api/bots/risk/{bot_id}/score` - Get bot risk score
- `POST /api/bots/risk/{bot_id}/calculate` - Calculate with custom data
- `GET /api/bots/risk/all` - All bot risk scores
- `GET /api/bots/risk/high-risk` - High-risk bots only
- `GET /api/bots/risk/{bot_id}/metrics` - Detailed metrics
- `GET /api/bots/risk/{bot_id}/components` - Component breakdown
- `GET /api/bots/risk/alerts` - All active alerts
- `GET /api/bots/risk/{bot_id}/alerts` - Bot-specific alerts
- `GET /api/bots/risk/portfolio` - Portfolio-wide risk
- `GET /api/bots/risk/{bot_id}/widget` - Compact widget data
- `GET /api/bots/risk/dashboard` - Risk dashboard
- `GET /api/bots/risk/thresholds` - View thresholds
- `PUT /api/bots/risk/thresholds` - Update thresholds

#### New Files
- `src/bot/risk_manager.py` - Risk scoring engine
- `src/api/routes/bot_risk.py` - Risk API endpoints

### 📹 Video Platform Sentiment Analysis

#### Platforms Supported
- **YouTube**: Financial channels, stock analysis videos
- **TikTok**: FinTok, stock tips, trading influencers
- **Instagram**: Financial influencers, trading reels/posts

#### Features
- **Trending Content**: Track trending financial videos across platforms
- **Symbol Mentions**: Find all video content mentioning specific stocks
- **Influencer Tracking**: Monitor 50+ known financial influencers
- **Viral Alerts**: Real-time alerts for viral trading content (70+ score)
- **Engagement Analysis**: Views, likes, comments, shares, saves
- **Content Categorization**: Stock analysis, trading tips, earnings, crypto, etc.
- **Hashtag Tracking**: Monitor #stocktok, #fintok, #investing, etc.

#### Known Influencer Database
- **YouTube**: MeetKevin, Graham Stephan, Andrei Jikh, Tom Nash, Stock Moe
- **TikTok**: Stock Trader Pro, Trading with Brian, FinTok King
- **Instagram**: WallStreetBets, TradingView, Investors Club

#### New API Endpoints
- `GET /api/video/trending` - Trending financial content
- `GET /api/video/trending/youtube` - YouTube trending
- `GET /api/video/trending/tiktok` - TikTok trending
- `GET /api/video/trending/instagram` - Instagram trending
- `GET /api/video/symbol/{symbol}` - Content mentioning a symbol
- `GET /api/video/influencers` - Top financial influencers
- `GET /api/video/influencers/{symbol}` - Influencers mentioning symbol
- `GET /api/video/viral` - Viral content alerts
- `GET /api/video/search` - Search video content
- `GET /api/video/dashboard` - Video platform dashboard
- `POST /api/video/content` - Add content for analysis

#### New Files
- `src/forecasting/video_platforms.py` - YouTube/TikTok/Instagram analyzer
- `src/api/routes/video_sentiment.py` - Video platform API endpoints

---

This release adds a comprehensive speculation and forecasting engine to identify
stocks with high growth potential using social sentiment, trend detection, and AI.

### Added

#### Social Sentiment Engine
- **Multi-Platform Analysis**: Twitter/X, Reddit, StockTwits, Discord, Telegram
- **Symbol Extraction**: Automatic $SYMBOL cashtag detection
- **Sentiment Classification**: Bullish/Bearish/Neutral with 0-100 scoring
- **Influencer Detection**: Track mentions from known financial influencers
- **Trending Symbols**: Real-time trending rankings by social activity
- **Sentiment Movers**: Track biggest sentiment changes

#### Buzz & Viral Trend Detection
- **Trend Strength**: Viral (10x), Surging (5x), Rising (2x) normal activity
- **Trend Stage**: Early, Growing, Peak, Mature, Declining lifecycle
- **Early Mover Detection**: Find trends before they go viral
- **Cross-Platform Correlation**: Stocks trending on multiple platforms
- **Influencer Alerts**: Real-time alerts when influencers mention stocks
- **Velocity & Acceleration**: Track mention momentum

#### Speculation Scoring Algorithm
- **Growth Forecast Scores**: 0-100 speculation score per symbol
- **Component Scores**: Social, Sentiment, Catalyst, Technical, Momentum, Squeeze
- **Price Targets**: Bullish, Base, Bearish target estimates
- **Risk Classification**: Very High, High, Moderate, Low
- **Short Squeeze Detection**: Based on short interest and options flow
- **Top Speculative Picks**: Ranked list of high-potential opportunities

#### Catalyst Tracker
- **20+ Catalyst Types**: Earnings, FDA, Product Launch, IPO Lockup, Insider, etc.
- **Impact Assessment**: Major, Significant, Moderate, Minor
- **Catalyst Calendar**: Earnings, FDA, Lockup, Insider calendars
- **Catalyst Density**: Analysis of event concentration
- **Search Catalysts**: Keyword-based catalyst search

#### AI Hypothesis Generator
- **Automated Thesis Generation**: AI creates trading hypotheses
- **Category Classification**: Momentum, Contrarian, Event-Driven, etc.
- **Thematic Scanning**: Generate hypotheses around market themes
- **Discovery Scans**: Automated opportunity discovery
- **Validation Tracking**: Track hypothesis outcomes for learning

### New API Endpoints (40+)
- `GET /api/forecast/sentiment/{symbol}` - Symbol sentiment analysis
- `GET /api/forecast/sentiment/trending/symbols` - Trending by social activity
- `GET /api/forecast/buzz/trending` - Active trend signals
- `GET /api/forecast/buzz/early-movers` - Early-stage opportunities
- `GET /api/forecast/buzz/viral` - Viral alerts
- `GET /api/forecast/buzz/influencer-alerts` - Influencer mentions
- `GET /api/forecast/speculation/{symbol}` - Growth forecast
- `GET /api/forecast/speculation/top-picks` - Top speculative picks
- `GET /api/forecast/speculation/squeeze-candidates` - Squeeze candidates
- `GET /api/forecast/catalysts/{symbol}` - Symbol catalysts
- `GET /api/forecast/catalysts/imminent` - Upcoming catalysts
- `GET /api/forecast/catalysts/earnings` - Earnings calendar
- `GET /api/forecast/catalysts/fda` - FDA calendar
- `GET /api/forecast/hypothesis/{symbol}` - Generate hypothesis
- `GET /api/forecast/hypothesis/theme/{theme}` - Thematic hypotheses
- `GET /api/forecast/analysis/{symbol}` - Full analysis
- `GET /api/forecast/dashboard` - Forecasting dashboard

### New Files
- `src/forecasting/social_sentiment.py` - Social media sentiment engine
- `src/forecasting/buzz_detector.py` - Viral trend detection
- `src/forecasting/speculation_scorer.py` - Growth forecasting algorithm
- `src/forecasting/catalyst_tracker.py` - Event catalyst tracking
- `src/forecasting/hypothesis_generator.py` - AI hypothesis generation
- `src/api/routes/forecasting.py` - 40+ forecasting API endpoints

---

## [1.0.2] - 2025-12-17

### 🌍 Comprehensive Forex Trading Module

This release adds complete Forex trading capabilities with all the bells and whistles.

### Added

#### Forex Core Module
- **60+ Currency Pairs**: Majors, minors, exotics, and commodity-linked pairs
- **Pip Calculator**: Accurate pip calculations for all pair types (4 and 2 decimal)
- **Lot Sizer**: Risk-based position sizing (standard, mini, micro, nano lots)
- **Session Detection**: Tokyo, London, New York, Sydney with overlap detection
- **Swap Rates**: Overnight rollover rate information

#### Currency Strength Analysis
- **Real-time Strength Meter**: 0-100 scoring for all major currencies (USD, EUR, GBP, JPY, CHF, AUD, CAD, NZD)
- **Correlation Matrix**: Pair-to-pair correlation analysis
- **Best Pair Selector**: Automatically find strongest vs weakest currency pair
- **Divergence Detection**: Identify momentum changes before they happen

#### Economic Calendar
- **12+ High-Impact Events**: FOMC, NFP, ECB, BOE, CPI, GDP, PMI
- **Impact Classification**: High, medium, low impact levels
- **News Avoidance Check**: `/api/forex/calendar/should-trade/{pair}`
- **Trade Setup Generator**: Get entry/exit levels for news trading

#### Forex Strategies
- **Carry Trade**: Profit from interest rate differentials
- **Session Breakout**: Trade London/NY session opens
- **News Trading**: Straddle and fade strategies around events
- **Asian Range Breakout**: Trade Asian session range at London open
- **Currency Correlation**: Trade based on strength analysis

#### Forex Broker Integrations
- **MetaTrader 5**: Full integration (Windows, pip install MetaTrader5)
  - Real-time quotes and charts
  - Order execution with SL/TP
  - Position management
  - Expert Advisor compatibility
- **OANDA**: REST API v20 integration
  - Practice and Live accounts
  - Market and limit orders
  - Streaming prices
  - Historical data

### New API Endpoints
- `GET /api/forex/pairs` - List all currency pairs
- `POST /api/forex/calculate-pips` - Calculate pips and P&L
- `POST /api/forex/calculate-lot-size` - Risk-based lot sizing
- `GET /api/forex/sessions` - Current trading sessions
- `GET /api/forex/currency-strength` - Currency strength analysis
- `GET /api/forex/calendar` - Economic calendar
- `GET /api/forex/calendar/should-trade/{pair}` - News avoidance check
- `GET /api/forex/strategies` - Available Forex strategies
- `GET /api/forex/strategies/carry-trade/best-pairs` - Best carry trades
- `GET /api/forex/brokers` - Supported Forex brokers

### New Files
- `src/forex/core.py` - Pairs, pips, lots, sessions
- `src/forex/currency_strength.py` - Currency strength meter
- `src/forex/economic_calendar.py` - Economic events
- `src/forex/strategies.py` - 5 Forex-specific strategies
- `src/forex/brokers/metatrader.py` - MT5 integration
- `src/forex/brokers/oanda.py` - OANDA integration
- `src/api/routes/forex.py` - Forex API routes

---

## [1.0.1] - 2025-12-17

### 🎉 Major Release: Quantvue-Inspired Features

This release adds 8 new major features inspired by Quantvue's automated trading platform,
bringing XFactor Bot to feature parity and beyond.

### Added

#### Priority 1 - High Value Features
- **Volatility-Adaptive SL/TP**: ATR-based dynamic stop losses and take profits
  - Automatically adjusts stops based on current market volatility
  - Supports low/normal/high/extreme volatility classifications
  - Configurable ATR multipliers and risk limits
  - Trailing stops that adapt to volatility
  
- **TradingView Webhook Integration**: Receive alerts from TradingView
  - POST endpoint: `/api/webhook/tradingview`
  - Supports JSON and simple text formats (TICKER,ACTION,PRICE,QTY)
  - Alert history and status tracking
  - Configurable webhook secret for security
  
- **Market Regime Detection**: Automatic trend vs range classification
  - ADX-based trend strength detection
  - Bollinger Band squeeze detection for ranges
  - Momentum regime classification
  - Trading recommendations based on regime

#### Priority 2 - Nice to Have Features
- **Martingale Position Sizing**: Multiple Martingale strategies
  - Classic (2x after loss)
  - Anti-Martingale (2x after win)
  - Fibonacci sequence sizing
  - D'Alembert (fixed increment)
  - Built-in risk controls and drawdown kill switch
  
- **Strategy Templates Library**: Pre-configured trading strategies
  - 10+ templates across categories (trend, mean-reversion, breakout, scalping)
  - Detailed entry/exit rules and indicator settings
  - Risk level and timeframe classifications
  - Search and filter capabilities
  
- **NinjaTrader Integration**: Connect to NinjaTrader 8
  - ATI (Automated Trading Interface) connection
  - Order placement with bracket orders
  - Position and account sync
  - Support for futures and forex

#### Priority 3 - Future Features (Backend Ready)
- **Visual Strategy Builder**: Drag-and-drop strategy creation
  - Node-based strategy definition
  - Trigger, condition, and action nodes
  - Flow control (if/else, wait)
  - Strategy save/load functionality
  
- **Social Trading Platform**: Share and copy strategies
  - Strategy marketplace with leaderboard
  - Performance tracking and ratings
  - Copy trading modes (mirror, scaled, signals)
  - Strategy reviews and search

### New API Endpoints
- `GET /api/strategies/templates` - List strategy templates
- `POST /api/strategies/adaptive-stops/calculate` - Calculate adaptive SL/TP
- `POST /api/strategies/regime/detect` - Detect market regime
- `GET /api/strategies/martingale/types` - List Martingale strategies
- `GET /api/strategies/visual-builder/node-templates` - Visual builder nodes
- `GET /api/strategies/social/leaderboard` - Top performing strategies
- `POST /api/webhook/tradingview` - TradingView alerts

### New Files
- `src/strategies/volatility_adaptive.py` - Volatility-adaptive stops
- `src/strategies/market_regime.py` - Market regime detection
- `src/strategies/martingale.py` - Martingale position sizing
- `src/strategies/templates.py` - Strategy templates library
- `src/strategies/visual_builder.py` - Visual strategy builder
- `src/social/trading.py` - Social trading platform
- `src/brokers/ninjatrader.py` - NinjaTrader integration
- `src/api/routes/tradingview.py` - TradingView webhook routes
- `src/api/routes/strategies.py` - Strategy API routes

## [0.9.8] - 2025-12-17

### Added
- **Comprehensive Debug Logging**: System info, port checks, and dependency verification at startup
  - Platform, architecture, hostname, and IP address logging
  - Port availability check before binding
  - Detailed error messages with troubleshooting commands
- **WebSocket Debug Info**: Close code meanings (1000-1015) in browser console
  - Debug tips for connection errors (netstat/lsof commands)
  - Health check result logging for faster troubleshooting

### Changed
- **Platform-Specific Build**: PyInstaller now handles platform differences
  - Excludes `uvloop` on Windows (Unix-only library)
  - Excludes `psycopg2` on Windows (requires PostgreSQL libs)
  - Excludes GUI packages on Linux (not needed for server)

### Fixed
- **Linux Zombie Cleanup**: Added fallback command chain
  - `pgrep` → `ps + grep` fallback for minimal distros
  - `lsof` → `ss` → `fuser` fallback chain for port cleanup
- **Windows Zombie Cleanup**: Enhanced process termination
  - Tries multiple backend binary names
  - PowerShell fallback for more reliable port cleanup
  - Handles ESTABLISHED connections in addition to LISTENING
- **WebSocket Connection Loops**: Fixed React dependency loop
  - Added `isConnectedRef` and `connectRef` for stable references
  - Empty deps array on main effect (runs once, uses refs)
  - Duplicate connection guard to prevent simultaneous connects
- **Import Errors**: Fixed `get_bot_manager()` import across codebase
  - `src/api/routes/agentic_tuning.py`
  - `src/api/main.py`
  - `desktop/scripts/run_backend.py`

## [0.9.7] - 2025-12-16

### Added
- **Offline Admin Login**: Admin panel now works even when backend is down
  - Fallback authentication with local password
  - "Offline Mode" indicator in admin panel header
  - Login hint showing offline capability
- **Enhanced Debug Logging**: Detailed console logging for bot fetch errors
  - Full URL, headers, and response info logged
  - Health check on error to diagnose connectivity
  - Stack traces for debugging
- **Agentic Tuning (ATRWAC)**: Algorithm for optimizing trading bot fleet
- **Zombie Process Cleanup**: Scripts for macOS/Linux/Windows

### Changed
- **API URL Handling**: Improved `apiUrl` helper and fetch patching for Tauri desktop
- **BotManager**: Uses `apiUrl` helper consistently for all API calls

### Fixed
- **CSP Policy**: Added `127.0.0.1` to Content Security Policy for desktop app
- **Backend Detection**: Improved search for backend binary in multiple locations
  - Now searches MacOS dir, Resources, binaries subfolder, app data dir, and exe dir
  - Tries multiple binary names (with/without architecture suffix)
- **"Failed to fetch bots" on legacy Mac**: Better error diagnostics
- **Admin panel accessibility**: Always accessible regardless of backend status
- **Backend Not Killed on UI Reload**: Refactored cleanup into soft/hard modes
  - Soft cleanup (component unmount): Only clears WebSocket and intervals, keeps backend alive
  - Hard cleanup (app close): Full cleanup including stopping bots and killing backend
  - Prevents unintended backend termination during React re-renders
- **Detached Backend Process**: Backend now starts as detached process on all platforms
  - Uses `setsid` on Unix, `DETACHED_PROCESS` on Windows
  - Backend survives unexpected frontend crashes
- **Rate-Limited Reconnection**: WebSocket uses exponential backoff with jitter
  - Fast retries (1s, 2s, 4s, 8s, 16s) for first 5 attempts
  - Then settles at 30s intervals for continuous background checking
  - Background health check every 15s when disconnected

## [0.9.6] - 2025-12-16

### Added
- **Help Modal**: In-app help with Features, Quick Start guide, and Changelog
  - Version info display in header
  - Searchable feature documentation
- **ChromeOS Support**: Linux .deb build works on ChromeOS via Crostini

### Changed
- **Improved x64 Backend**: Rebuilt x64 backend with all dependencies properly bundled
- **GitHub Actions**: Fixed Rust toolchain action (`dtolnay/rust-toolchain`)
- **Manual DMG Creation**: Added fallback DMG creation using `hdiutil` when bundle script fails

### Fixed
- **Gatekeeper Blocking**: Documentation for fixing macOS security blocks on unsigned apps
- **Backend Launch on Intel Mac**: Fixed backend binary bundling for x86_64 architecture
- **Version Sync**: Cargo.toml now matches tauri.conf.json version

### Notes
- For Intel Macs: Run `sudo xattr -cr "/Applications/XFactor Bot.app"` after install
- x64 DMG: 391MB (includes full Python runtime)
- ARM64 DMG: 180MB (includes full Python runtime)

## [0.9.5] - 2025-12-14

### Added
- **Hypothesis Testing Framework**: Added `hypothesis>=6.0.0` for property-based testing
- **API-Based LLM Strategy**: Shifted from bundled PyTorch/Transformers to API-based LLMs
  - OpenAI (GPT-4, GPT-3.5) - API key required
  - Anthropic Claude - API key required
  - Ollama (local) - Free, runs locally
  - Configurable via Admin Panel

### Changed
- **Smaller Desktop Bundle**: Removed torch/transformers from PyInstaller bundle
  - Reduces app size from ~2GB to ~200MB
  - More reliable cross-platform builds
  - AI features work via API calls instead of local inference
- **GitHub Actions**: Linux build now included in release if successful

### Fixed
- **NumPy 2.x Compatibility**: Pinned numpy<2.0.0 in requirements.txt
- **PyInstaller Bundling**: Comprehensive `--collect-all` for all dependencies

## [0.9.4] - 2024-12-13

### Fixed
- **Sidecar Binary Bundling**: Fixed issue where backend binary was bundled without target-triple suffix
  - Removed conflicting `resources` entry from Tauri config that was overwriting the correctly-named sidecar
  - Cleaned up unnecessary `.app` bundle from binaries folder
  - Backend binary now correctly bundled as `xfactor-backend-aarch64-apple-darwin` (or x64 equivalent)
  - Desktop app should now properly auto-launch backend and show "Connected" status

### Notes
- x64 DMG requires Intel Mac for full functionality (backend cross-compilation not supported from ARM)
- ARM64 DMG fully functional on Apple Silicon Macs

## [0.9.3] - 2024-12-13

### Added
- **Auto-Tune UI**: Full user interface for automatic strategy optimization
  - New "Auto-Tune" tab in bot details modal
  - Mode selection: Conservative, Moderate, Aggressive with visual descriptions
  - Live metrics display: Win Rate, Profit Factor, Max Drawdown
  - Adjustments history with expandable list showing parameter changes
  - Enable/Disable/Reset controls for each bot
  - Real-time status updates every 30 seconds

- **Seasonal Events UI**: Added to Strategy Controls panel
  - New "Seasonal Events" category with dedicated toggles
  - Holiday Adjustments toggle (Black Friday, Christmas, etc.)
  - Earnings Season Mode toggle
  - Santa Claus Rally toggle
  - January Effect toggle
  - Summer Doldrums toggle
  - Tax-Loss Harvesting toggle

- **Enhanced Bot Details**: Additional tracking metrics
  - Win Rate display with color-coded thresholds
  - Total P&L (lifetime) 
  - Uptime display in the Performance Metrics section
  - Error status section (shows green "No Errors" or red with count)
  - Improved 3-column Performance Metrics grid

### Changed
- **Bot Performance Chart**: Now has 3 tabs (Performance, Details, Auto-Tune)
- **Strategy Panel**: Added 7 new seasonal event toggles
- **Release Structure**: All DMGs now organized under `releases/` folder

### Fixed
- **Event Loop Error**: Fixed "Cannot close a running event loop" in bot threading
- **Async Coroutine Warning**: Fixed unawaited coroutine in BotAutoOptimizer.stop()
- **Test Warnings**: Resolved all async-related test warnings

## [0.9.2] - 2024-12-13

### Changed
- Version bump for internal testing

## [0.9.1] - 2024-12-13

### Added
- **Auto-Optimizer for Trading Bots**: Automatic performance analysis and strategy adjustment
  - Real-time performance monitoring (win rate, profit factor, drawdown, Sharpe ratio)
  - Automatic parameter adjustment based on performance metrics
  - Three optimization modes: Conservative (10% max), Moderate (20% max), Aggressive (35% max)
  - Adjustable parameters: stop loss, take profit, position size, RSI levels, momentum thresholds
  - Safety features: daily adjustment limits, cooldown periods, revert on worse performance
  - Per-bot enable/disable with individual configuration
  - API endpoints: `/api/optimizer/status`, `/api/optimizer/bot/{id}/enable`, `/api/optimizer/recommendations`
  - Automatic baseline and best-performance tracking
  - Trade-by-trade analysis with trend detection (improving/declining/neutral)

- **Seasonal Events Calendar**: Holiday and calendar-based trading adjustments
  - Automatic detection of seasonal events (Black Friday, Christmas, Santa Rally, etc.)
  - Real-time date awareness for Momentum and Technical (Trend) strategies
  - Holiday period detection (Black Friday, Cyber Monday, Valentine's Day, etc.)
  - Earnings season awareness (Q1-Q4 reporting periods)
  - Sector-specific adjustments (retail, e-commerce, travel, energy)
  - Market patterns: Summer Doldrums, September Effect, Q4 Rally, January Effect
  - Tax-related events: Tax Loss Harvesting, Post-Tax Deadline Rally
  - API endpoints: `/api/seasonal/context`, `/api/seasonal/adjustment`, `/api/seasonal/events/active`
  
- **Desktop Installation Guide**: Comprehensive documentation for desktop app users
  - Step-by-step installation for macOS, Windows, and Linux
  - "Disconnected" status troubleshooting guide
  - Manual backend setup instructions for developers
  - Quick one-liner command for starting backend

### Changed
- **Bot Manager**: Now integrates with auto-optimizer for all 37 bots
- **Momentum Strategy**: Now includes seasonal event awareness with automatic adjustments
- **Technical Strategy**: Now includes seasonal event awareness for trend analysis

### Fixed
- **Server-side caching**: Added cache-busting headers to ensure latest frontend is always served
- **Docker/Desktop conflict**: Resolved issue where stale Docker containers blocked fresh server startup
- **Frontend serving**: Improved FastAPI static file serving with no-cache headers

### Tests Added
- **test_seasonal_events.py**: 24 tests for seasonal calendar, holiday detection, market patterns
- **test_auto_optimizer.py**: 29 tests for performance analysis, parameter adjustment, optimization modes
- **test_api_performance.py**: Tests for bot/position performance charts and sorting
- **test_api_optimizer.py**: Tests for optimizer API endpoints (enable, disable, recommendations)
- **test_api_seasonal.py**: Tests for seasonal API endpoints (context, adjustment, events)

## [0.9.0] - 2024-12-12

### Added
- **Desktop Application (Tauri)**: Native desktop app for macOS, Windows, and Linux
  - Built with Tauri 2.0 for lightweight, secure native experience
  - macOS: Apple Silicon (ARM64) and Intel (x64) support
  - Windows: x64 builds (.exe, .msi installers)
  - Linux: x64 builds (.deb, .AppImage)
  - System tray integration with quick actions
  - Native menus with keyboard shortcuts
  - Auto-update capability
  - Single instance enforcement

- **Multiple Broker Authentication Methods**: Easier connection for all user levels
  - **OAuth Login**: Schwab, Tradier - "Login with" button for secure browser auth
  - **Username/Password**: Robinhood, Webull (Beta), IBKR - Familiar login with 2FA support
  - **API Keys**: Alpaca - Standard API key authentication
  - **TWS Gateway**: IBKR - Professional trading platform integration (alternative to username/password)
  - Visual auth type indicators in broker selection
  - Beta badges for unofficial API integrations
  - IBKR connection method toggle: Username/Password (Client Portal API) or TWS/Gateway

- **37 Trading Bots Documentation**: Comprehensive draw.io diagram
  - All 37 pre-configured bots documented with strategies
  - Strategy permutation matrix showing usage patterns
  - Bot categories: Stocks (10), Options (5), Futures (4), Leveraged ETF (2), Commodity (8), Crypto (8)
  - Diagram at: `docs/xfactor-bot-37-bots-diagram.drawio`

- **Global Stock Exchange Support**: Access to ALL stocks worldwide (~40,000+ symbols)
  - 40+ global exchanges: NYSE, NASDAQ, LSE, TSE (Tokyo), HKEX, Shanghai, Shenzhen, TSX, ASX, and more
  - Symbol search API: `/api/symbols/search?q=toyota` finds stocks across all exchanges
  - Exchange suffixes supported: .L (London), .T (Tokyo), .HK (Hong Kong), .DE (Germany), .SS (Shanghai), .AX (Australia), .TO (Toronto), .PA (Paris), .MI (Milan), .NS (India), .KS (Korea), .TW (Taiwan), .SA (Brazil), .BA (Argentina), .MX (Mexico)
  - Popular symbols endpoint: `/api/symbols/popular?category=international`
  - Symbol validation: `/api/symbols/validate?symbols=AAPL,7203.T,HSBA.L`
  - Exchange listing: `/api/symbols/exchanges` with trading hours, currencies, and stock counts
  - Dynamic lookup via Yahoo Finance API for real-time symbol discovery

- **Cross-Platform CI/CD**: Automated desktop builds
  - GitLab CI pipeline for all platforms
  - GitHub Actions workflow for GitHub users
  - Artifact publishing for releases
  - Manual trigger support for on-demand builds

### Changed
- Desktop app automatically connects to localhost:9876 backend
- Fetch API patched for Tauri environment
- WebSocket URL detection for desktop vs browser

## [0.8.0] - 2024-12-12

### Added
- **Backtesting Engine**: Complete historical simulation system
  - Event-driven architecture with realistic execution modeling
  - Slippage and commission calculations
  - Multiple data sources (yfinance, Alpaca, IBKR, CSV)
  - Walk-forward analysis support for strategy validation
  - Performance metrics: Sharpe, Sortino, max drawdown, win rate

- **ML-Based Strategy Optimizer**: Machine learning optimization for trading strategies
  - Multiple algorithms: Grid Search, Random Search, Bayesian, Genetic
  - Cross-validation to prevent overfitting
  - Parameter sensitivity analysis
  - Early stopping with convergence detection
  - Multiple objective metrics (Sharpe, Sortino, Calmar, profit factor)

- **Portfolio Rebalancer**: Automated portfolio rebalancing system
  - Multiple methods: Threshold, Calendar, Tactical, Hybrid
  - Drift monitoring and alerts
  - Tax-efficient trading optimization
  - Transaction cost estimation
  - Multi-asset class support

- **Tax-Loss Harvesting**: Automated tax optimization
  - Automatic loss identification
  - Wash sale rule compliance (30-day window tracking)
  - Replacement security selection
  - Year-end tax impact estimation
  - Gain/loss offsetting strategies

- **Multi-Account Support**: Manage multiple trading accounts
  - Connect to multiple brokers simultaneously
  - Unified portfolio view across all accounts
  - Cross-account position tracking
  - Account-specific trading rules
  - Aggregated performance metrics

- **IBKR Options/Futures Configuration**: Advanced trading setup in Admin Panel
  - Options trading levels (1-4) with permissions
  - Futures contract selection (ES, NQ, RTY, YM, CL, GC, SI, ZB, ZN)
  - Margin type configuration (intraday/overnight)
  - Forex and crypto trading toggles

### Changed
- **WebSocket Reconnection**: Improved stability with exponential backoff
  - Connection timeout handling (10s)
  - Heartbeat ping/pong every 30 seconds
  - Max 10 reconnect attempts with jitter
  - Visibility change and online event handlers
  - Clean connection state management

- Header now shows WebSocket connection state (connecting, connected, error)

### New Modules
- `src/backtesting/` - Backtesting engine and walk-forward analysis
- `src/ml/` - ML-based strategy optimization
- `src/portfolio/` - Rebalancing and tax-loss harvesting
- `src/accounts/` - Multi-account management

## [0.7.0] - 2024-12-12

### Added
- **Paper Trading Support**: Full integration with broker paper trading accounts
  - IBKR paper trading with $1,000,000 simulated cash (port 7497)
  - Alpaca paper trading with $100,000 simulated cash
  - Auto port switching between paper (7497) and live (7496) modes
  - Visual indicators showing paper trading status and simulated balance

- **Trading Mode System**: Switch between Demo, Paper, and Live modes
  - `TradingModeContext` for global mode state management
  - `TradingModeSelector` component in header with mode switching
  - Safety confirmation dialog before enabling Live mode
  - Mode persistence across sessions (except Live for safety)

- **Broker Configuration Panel**: New Admin Panel tab for broker management
  - IBKR and Alpaca broker connection support
  - Connection status display with account details
  - Buying power and portfolio value display
  - Paper trading info with simulated cash amounts

- **Authentication Modals**: User notifications for protected actions
  - Auth required modal for Pause/Kill Switch buttons in header
  - Auth required modal for bot start/stop/pause controls
  - Clear instructions on how to unlock admin access

- **Crypto Trading Dashboard**: New `CryptoPanel` component
  - Live crypto prices from CoinGecko API
  - Fear & Greed Index display
  - Whale alert tracking
  - Crypto bot management

- **Commodity Trading Dashboard**: New `CommodityPanel` component
  - Gold, silver, oil, gas, and other commodity tracking
  - ETF and futures support
  - Seasonal trading indicators

- **Fee Tracking System**: New `FeeTracker` component
  - Broker-specific fee structures (IBKR, Alpaca, Schwab, Tradier)
  - Fee breakdown by type (commission, spread, exchange, regulatory)
  - Fee estimator for trade planning
  - `/api/fees/*` endpoints for fee data

- **Increased Bot Capacity**: MAX_BOTS increased from 40 to 100
  - Updated in `bot_instance.py`, `bot_manager.py`, and frontend

### Changed
- Header trading controls now check authentication before executing
- Pause button toggles between Pause/Resume states
- Kill Switch requires confirmation dialog
- Portfolio summary fetches real data instead of mock data
- Positions table shows empty state when no broker connected
- Equity chart shows empty state when no data available
- Docker compose folder renamed from `docker/` to `xfactor-bot/`
- Docker compose port changed to 9876

### Fixed
- React hooks error (#300) in EquityChart component
- CORS configuration for foresight.nvidia.com:9876
- Null reference errors in CryptoPanel numeric displays
- WebSocket connection stability improvements

### Removed
- Mock data from PositionsTable (shows real or empty data)
- Mock data from Dashboard portfolio summary
- Simulated equity data from EquityChart

## [0.6.0] - 2024-12-11

### Added
- **Ollama Integration**: Connect to local LLM models
  - Support for Ollama running at localhost:11434
  - Compatible with Llama 3.1, Mistral, CodeLlama, Phi, Gemma, etc.
  - OllamaClient with chat, generate, and embeddings support
  - Streaming response support
  - Model listing and pulling via API

- **Multi-LLM Provider Support**: Switch between AI providers
  - OpenAI (GPT-4, GPT-3.5)
  - Ollama (Local LLMs)
  - Anthropic (Claude)
  - Runtime provider switching via API
  - Per-request provider override

- **New API Endpoints**:
  - `GET /api/ai/providers` - List available LLM providers
  - `POST /api/ai/providers/set` - Switch default provider
  - `GET /api/ai/ollama/status` - Check Ollama server status
  - `GET /api/ai/ollama/models` - List installed Ollama models
  - `POST /api/ai/ollama/pull/{model}` - Pull new Ollama model

- **UI Provider Selector**: Choose LLM provider in AI Assistant
  - Settings panel with provider buttons
  - Visual indicator of current provider
  - Available model display for Ollama

### Changed
- AI Assistant now supports multiple providers
- Chat requests can override provider per-message
- Settings expanded with Ollama configuration options

## [0.5.0] - 2024-12-11

### Added
- **Comprehensive Test Suite**: 150+ test cases covering all implemented features
  - API tests for bots, admin, risk, AI, integrations, positions, config
  - Unit tests for BotManager, BotInstance, brokers
  - Integration tests for data sources and news intelligence
  - WebSocket and CORS tests
  - Shared fixtures in conftest.py
  - pytest.ini configuration with markers and coverage settings

### Changed
- Updated conftest.py with comprehensive fixtures for testing

## [0.4.0] - 2024-12-11

### Added
- **Frontend-Backend Integration**: All UI components now properly connect to API
  - AuthContext for global authentication state
  - Token persistence in localStorage
  - Auto-verification on app load

### Fixed
- RiskControls now fetches from `/api/risk/limits` and `/api/risk/status`
- Pause/Resume/Kill Switch buttons fully functional
- PositionsTable fetches from `/api/positions/` with search and sort
- StrategyPanel saves to `/api/config/parameters`
- AdminPanel integrated with global AuthContext
- Dashboard passes auth token to child components

## [0.3.0] - 2024-12-11

### Added
- **Strategy Panel Expansion**: 40+ configurable parameters across 6 categories
  - Technical Analysis: RSI, MACD, Bollinger Bands, SMA/EMA crossovers
  - Momentum & Trend: ADX, breakout detection, volume confirmation
  - News & Sentiment: FinBERT, headline analysis, social monitoring
  - AI & Machine Learning: GPT-4 analysis, pattern recognition, anomaly detection
  - Social Trading: Top traders following, insider activity, community signals
  - Risk Management: Dynamic sizing, correlation limits, volatility adjustment

### Changed
- Strategy toggles expanded from 4 to 16
- Added 24 parameter sliders with descriptions
- Added 5 dropdown selects for strategy modes

## [0.2.0] - 2024-12-11

### Added
- **DataFilters Component**: Reusable search, sort, and filter for all panels
  - Search input with clear button
  - Sort dropdown with ascending/descending toggle
  - Dynamic filter builder (field, operator, value)
  - Quick filter chips
  - Results counter

- **Enhanced Trader Insights Panel**: 7 tabs with pagination
  - OpenInsider: Insider trading activity
  - Top Traders: Following successful traders
  - Finviz Signals: Technical signals
  - Moving Averages: MA crossover alerts
  - Earnings: Upcoming earnings calendar
  - Press Releases: Company announcements
  - AInvest AI: AI-powered recommendations

- **AInvest Integration**: Full API integration
  - `/api/integrations/ainvest/recommendations`
  - `/api/integrations/ainvest/sentiment/{symbol}`
  - `/api/integrations/ainvest/signals`
  - `/api/integrations/ainvest/insider-trades`
  - `/api/integrations/ainvest/earnings`
  - `/api/integrations/ainvest/news`

### Fixed
- MAX_BOTS increased to 25 in both `bot_manager.py` and `bot_instance.py`
- Frontend BotManager display updated to show /25 limit

## [0.1.0] - 2024-12-10

### Added
- **Multi-Broker Support**: Abstracted broker interface
  - AlpacaBroker implementation
  - SchwabBroker implementation (simulated)
  - TradierBroker implementation
  - BrokerRegistry for dynamic broker management

- **Banking Integration**: Plaid API for ACH transfers
  - Link token creation
  - Account connection
  - Transfer initiation and management

- **Options & Futures Trading**: Extended bot configurations
  - Options: calls, puts, DTE range, delta selection
  - Futures: ES, NQ, micro contracts, session control
  - Leveraged ETFs: TQQQ/SQQQ, SOXL swing trading

- **25 Default Bots**: Pre-configured trading bots
  - 10 Stock bots (Tech Momentum, ETF Swing, News Sentiment, etc.)
  - 5 Options bots (SPY Calls, QQQ Tech, 0DTE Scalper, etc.)
  - 4 Futures bots (ES Scalper, NQ Micro, Crude Oil, etc.)
  - 2 Leveraged ETF bots (TQQQ/SQQQ, SOXL)

- **Collapsible Dashboard Panels**: Expand/collapse and maximize
- **News Feed Enhancements**: Pagination, full-screen mode, 100 items
- **TradingView Webhook Integration**: Process incoming alerts

### Changed
- Rebranded to XFactor Bot with new logo and color scheme
- Frontend port changed to 9876
- API proxy updated for new port

## [0.0.5] - 2024-12-09

### Added
- **AI Assistant**: GPT-4 powered trading assistant
  - Context-aware responses with portfolio data
  - Performance queries and optimization recommendations
  - Conversation history management
  - Example questions
  - `/api/ai/chat`, `/api/ai/insights`, `/api/ai/optimize`

### Fixed
- Equity chart time range buttons (1D, 1W, 1M) now functional
- Chart properly re-renders on time range change

## [0.0.4] - 2024-12-09

### Added
- **Multi-Bot System**: Run up to 25 simultaneous bots
  - BotManager for centralized bot management
  - BotInstance with full lifecycle (start, stop, pause, resume)
  - BotConfig with comprehensive trading parameters
  - Bulk operations (start-all, stop-all, pause-all)

- **Real Equity Chart**: Using lightweight-charts library
  - Area chart with gradient fill
  - Time range filtering
  - Performance statistics

### Changed
- Default bot count increased from 5 to 10 to 25

## [0.0.3] - 2024-12-08

### Added
- **Admin Panel**: Password-protected feature management
  - Login with password (106431)
  - Feature flags by category
  - Bulk toggle operations
  - Emergency controls (disable trading, disable news)

### Fixed
- NaN handling in CSV parser for news files
- API route ordering (static routes before parameterized)

## [0.0.2] - 2024-12-08

### Added
- **News & Sentiment Intelligence Layer**: 200+ global data sources
  - US sources: Bloomberg, Reuters, WSJ, CNBC, etc.
  - Asia sources: Caixin, Nikkei, South China Morning Post
  - Europe sources: Financial Times, Der Spiegel, Les Echos
  - Latin America sources: Valor Econômico, El Economista
  - Social media: Twitter/X, Reddit (r/wallstreetbets)
  - Local file watcher for CSV, PDF, DOCX, TXT

- **Sentiment Analysis**: FinBERT and LLM-based analysis
- **Entity Extraction**: Ticker and company name recognition
- **Translation**: Multi-language support with deep-translator

## [0.0.1] - 2024-12-07

### Added
- Initial project setup
- FastAPI backend with modular architecture
- React frontend with TypeScript and Tailwind CSS
- Docker and Docker Compose configuration
- IBKR API integration structure
- Basic trading strategies (Technical, Momentum, MeanReversion, NewsSentiment)
- Risk management system
- TimescaleDB for time-series data
- Redis for caching
- Prometheus metrics and Grafana dashboards

---

## Roadmap

### Upcoming Features
- [ ] Live paper trading with IBKR
- [ ] Backtesting engine
- [ ] Mobile app (React Native)
- [ ] Desktop app (Electron)
- [ ] ML-based strategy optimization
- [ ] Portfolio rebalancing automation
- [ ] Tax-loss harvesting
- [ ] Multi-account support

### Known Issues
- WebSocket reconnection may require page refresh
- Some data sources require API keys to function
- Options/Futures trading requires broker-specific setup

