# ⚡ XFactor Bot - AI-Powered Market Research Platform

An advanced market research and analysis platform with AI-powered forecasting, real-time news sentiment analysis, and comprehensive trading education tools.

![XFactor Bot Dashboard](data/xfactorbot_screenshot.png)

## 🚀 Features

### AI Market Forecasting
- **Price Projections** - AI-generated price targets with confidence intervals
- **Pattern Detection** - Trend continuation, breakout, mean reversion signals
- **Catalyst Tracking** - Earnings, FDA approvals, product launches
- **Speculation Scoring** - 0-100 growth potential scoring

### News & Sentiment Intelligence
- 100+ global news sources (Reuters, Bloomberg, WSJ, Caixin, Nikkei, etc.)
- Real-time sentiment analysis using FinBERT
- Social media trend detection
- Viral content alerts from financial influencers

### Stock Analyzer
- Comprehensive historical data analysis (1mo to 5y)
- Interactive candlestick charts with technical overlays
- SMA/EMA, RSI, MACD, Bollinger Bands
- Inflection point detection (peaks, troughs, crossovers)
- Analyst price target integration

### Video Platforms Intelligence
- YouTube, TikTok, Instagram financial content tracking
- 50+ known financial influencers monitored
- Viral alert detection for trending stocks
- Engagement metrics analysis

### Trading Glossary
- **500+ terms** covering all aspects of trading
- Visual diagrams for technical patterns
- Audio readout for hands-free learning
- Voice search capability

### Forex & Crypto Research
- Currency strength analysis
- Economic calendar integration
- Crypto Fear & Greed Index
- Whale tracking alerts

## 📋 Requirements

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional)

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone https://gitlab-master.nvidia.com/cvanthin/000_trading.git
cd 000_trading
```

### 2. Set up Python environment
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Start the backend
```bash
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 9876
```

### 4. Start the frontend
```bash
cd frontend
npm install
npm run dev
```

## 🌐 Access

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | http://localhost:9876 | React research platform |
| **API Docs** | http://localhost:9876/docs | Swagger API documentation |

## ⚙️ Configuration (Optional)

### AI Providers
```env
# Anthropic Claude (recommended)
ANTHROPIC_API_KEY=your_key

# Ollama (local, no key needed)
OLLAMA_HOST=http://localhost:11434
```

### Data Sources
```env
# News APIs (optional - uses free sources by default)
NEWSAPI_API_KEY=your_key
FINNHUB_API_KEY=your_key
```

## 🏗️ Architecture

```
├── src/
│   ├── api/              # FastAPI backend
│   ├── ai/               # AI assistant integration
│   ├── data_sources/     # Market data providers
│   ├── news_intel/       # News aggregation & sentiment
│   ├── forecasting/      # AI market forecasting
│   └── monitoring/       # Prometheus metrics
├── frontend/             # React dashboard
└── xfactor-bot/          # Docker configuration
```

## 📊 Dashboard Features

- **Live News Feed** - 100 items with pagination, sentiment filtering
- **AI Forecasting** - Price projections and pattern detection
- **Stock Analyzer** - Technical analysis with overlays
- **Video Intelligence** - Social media trend tracking
- **Trading Glossary** - 500+ educational terms with visuals
- **Forex Panel** - Currency research and analysis
- **Crypto Panel** - Cryptocurrency research tools

## 📈 Research Capabilities

| Feature | Description |
|---------|-------------|
| **AI Projections** | ML-based price forecasting |
| **Sentiment Analysis** | NLP-powered news sentiment |
| **Technical Overlays** | RSI, MACD, Bollinger Bands |
| **Inflection Detection** | Automated peak/trough finding |
| **Social Tracking** | Influencer and viral content |

## 🎤 Voice Features

- **Audio Readout** - News, glossary terms, AI responses
- **Voice Search** - Hands-free glossary lookup
- **Voice Input** - Dictate questions to AI assistant

## 🚧 Roadmap

- [x] AI Market Forecasting with pattern detection
- [x] 500+ term trading glossary with visuals
- [x] Voice/audio features for accessibility
- [x] Video platform intelligence
- [ ] Additional language support
- [ ] Mobile-optimized interface

## 📄 License

Proprietary - Internal use only

## 👤 Author
Chan
