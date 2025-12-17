# Changelog

All notable changes to the XFactor Bot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

