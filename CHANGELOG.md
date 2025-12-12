# Changelog

All notable changes to the XFactor Bot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

