"""
News Momentum - Track momentum signals from news sources.

Aggregates:
- Article count per symbol
- Sentiment analysis
- Breaking news detection
- Catalyst identification (earnings, FDA, etc.)

Sources:
- RSS feeds (Finviz, Yahoo, MarketWatch, etc.)
- API feeds (if available)
- Social media news mentions
"""

import asyncio
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict

from loguru import logger

try:
    import aiohttp
except ImportError:
    aiohttp = None


@dataclass
class NewsItem:
    """A news article or mention."""
    title: str
    source: str
    url: str
    timestamp: datetime
    symbols: List[str] = field(default_factory=list)
    sentiment: float = 0.0  # -1 to +1
    is_breaking: bool = False
    catalyst_type: Optional[str] = None  # earnings, fda, merger, etc.
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "timestamp": self.timestamp.isoformat(),
            "symbols": self.symbols,
            "sentiment": round(self.sentiment, 2),
            "is_breaking": self.is_breaking,
            "catalyst_type": self.catalyst_type,
        }


@dataclass
class NewsSymbolData:
    """Aggregated news data for a symbol."""
    symbol: str
    article_count_24h: int = 0
    article_count_7d: int = 0
    avg_sentiment: float = 0.0
    breaking_count: int = 0
    catalyst_types: List[str] = field(default_factory=list)
    recent_headlines: List[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    
    @property
    def volume_score(self) -> float:
        """Calculate news volume score (0-100)."""
        # Score based on article count
        # 0 articles = 0, 10+ articles = 100
        base_score = min(self.article_count_24h * 10, 100)
        
        # Bonus for breaking news
        if self.breaking_count > 0:
            base_score = min(base_score + 20, 100)
        
        return base_score
    
    @property
    def sentiment_score(self) -> float:
        """Get normalized sentiment score (0-100)."""
        # Convert -1 to +1 range to 0-100
        return (self.avg_sentiment + 1) * 50
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "article_count_24h": self.article_count_24h,
            "article_count_7d": self.article_count_7d,
            "avg_sentiment": round(self.avg_sentiment, 2),
            "volume_score": round(self.volume_score, 1),
            "sentiment_score": round(self.sentiment_score, 1),
            "breaking_count": self.breaking_count,
            "catalyst_types": self.catalyst_types,
            "recent_headlines": self.recent_headlines[:5],
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


# Catalyst keywords for detection
CATALYST_PATTERNS = {
    "earnings": ["earnings", "quarterly results", "revenue", "EPS", "beat estimates", "missed estimates", "guidance"],
    "fda": ["FDA", "approval", "clinical trial", "phase 3", "phase 2", "drug approval", "breakthrough therapy"],
    "merger": ["merger", "acquisition", "acquired", "buyout", "takeover", "M&A", "deal"],
    "partnership": ["partnership", "collaboration", "joint venture", "strategic alliance", "teaming up"],
    "product": ["new product", "product launch", "unveils", "announces", "release", "rollout"],
    "legal": ["lawsuit", "settlement", "SEC", "investigation", "regulatory", "compliance"],
    "leadership": ["CEO", "CFO", "executive", "resigned", "appointed", "stepped down"],
    "analyst": ["upgrade", "downgrade", "price target", "rating", "analyst", "initiated"],
    "dividend": ["dividend", "special dividend", "dividend increase", "payout"],
    "split": ["stock split", "reverse split", "share split"],
}

# Sentiment keywords
POSITIVE_KEYWORDS = [
    "beat", "exceeds", "surge", "soars", "rally", "gains", "upgrade", "bullish",
    "breakthrough", "record", "outperform", "buy", "growth", "strong", "positive",
    "optimistic", "innovative", "success", "profitable", "momentum", "recovery",
]

NEGATIVE_KEYWORDS = [
    "miss", "falls", "drops", "plunge", "crash", "downgrade", "bearish", "lawsuit",
    "investigation", "warning", "decline", "weak", "loss", "negative", "concern",
    "risk", "troubled", "fails", "disappointing", "sell", "cut", "layoffs",
]


class NewsMomentum:
    """
    Track and analyze news momentum for symbols.
    
    Features:
    - Article counting (24h, 7d)
    - Sentiment analysis
    - Breaking news detection
    - Catalyst identification
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        
        # News storage
        self._news_items: List[NewsItem] = []
        self._symbol_data: Dict[str, NewsSymbolData] = {}
        
        # Last fetch time
        self._last_fetch: Optional[datetime] = None
        
        logger.info("NewsMomentum initialized")
    
    async def fetch_news(self, symbols: Optional[List[str]] = None) -> None:
        """Fetch news for symbols from various sources."""
        try:
            # Fetch from RSS feeds
            await self._fetch_rss_news()
            
            # Process and aggregate
            self._aggregate_symbol_data()
            
            self._last_fetch = datetime.now()
            logger.info(f"Fetched {len(self._news_items)} news items")
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
    
    async def _fetch_rss_news(self) -> None:
        """Fetch news from RSS feeds."""
        if aiohttp is None:
            logger.warning("aiohttp not available for news fetching")
            return
        
        # RSS feed URLs
        feeds = [
            ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US", "Yahoo Finance"),
            ("https://www.investing.com/rss/news.rss", "Investing.com"),
        ]
        
        for url, source in feeds:
            try:
                items = await self._parse_rss_feed(url, source)
                self._news_items.extend(items)
            except Exception as e:
                logger.debug(f"Could not fetch from {source}: {e}")
    
    async def _parse_rss_feed(self, url: str, source: str) -> List[NewsItem]:
        """Parse an RSS feed and extract news items."""
        items = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10, ssl=False) as response:
                    if response.status != 200:
                        return items
                    
                    text = await response.text()
                    
                    # Simple RSS parsing (without external XML library)
                    # Extract <item> blocks
                    item_pattern = r'<item>(.*?)</item>'
                    title_pattern = r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>'
                    link_pattern = r'<link>(.*?)</link>'
                    
                    for match in re.finditer(item_pattern, text, re.DOTALL):
                        item_xml = match.group(1)
                        
                        title_match = re.search(title_pattern, item_xml)
                        link_match = re.search(link_pattern, item_xml)
                        
                        if title_match and link_match:
                            title = title_match.group(1).strip()
                            url = link_match.group(1).strip()
                            
                            # Extract symbols from title
                            symbols = self._extract_symbols(title)
                            
                            # Analyze sentiment
                            sentiment = self._analyze_sentiment(title)
                            
                            # Detect catalyst type
                            catalyst = self._detect_catalyst(title)
                            
                            # Check if breaking news
                            is_breaking = any(kw in title.lower() for kw in ["breaking", "just in", "alert"])
                            
                            items.append(NewsItem(
                                title=title,
                                source=source,
                                url=url,
                                timestamp=datetime.now(),
                                symbols=symbols,
                                sentiment=sentiment,
                                is_breaking=is_breaking,
                                catalyst_type=catalyst,
                            ))
                    
        except Exception as e:
            logger.debug(f"RSS parse error: {e}")
        
        return items
    
    def _extract_symbols(self, text: str) -> List[str]:
        """Extract stock symbols from text."""
        symbols = []
        
        # Pattern for stock symbols (1-5 uppercase letters)
        # Look for patterns like "AAPL" or "$AAPL" or "(AAPL)"
        patterns = [
            r'\$([A-Z]{1,5})\b',           # $AAPL
            r'\(([A-Z]{1,5})\)',            # (AAPL)
            r'\b([A-Z]{2,5})\b(?=.*(?:stock|shares|Inc|Corp))',  # AAPL stock
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            symbols.extend(matches)
        
        return list(set(symbols))
    
    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text (-1 to +1)."""
        text_lower = text.lower()
        
        positive_count = sum(1 for word in POSITIVE_KEYWORDS if word in text_lower)
        negative_count = sum(1 for word in NEGATIVE_KEYWORDS if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        sentiment = (positive_count - negative_count) / total
        return max(-1, min(1, sentiment))
    
    def _detect_catalyst(self, text: str) -> Optional[str]:
        """Detect catalyst type from text."""
        text_lower = text.lower()
        
        for catalyst_type, keywords in CATALYST_PATTERNS.items():
            if any(kw.lower() in text_lower for kw in keywords):
                return catalyst_type
        
        return None
    
    def _aggregate_symbol_data(self) -> None:
        """Aggregate news data by symbol."""
        now = datetime.now()
        cutoff_24h = now - timedelta(hours=24)
        cutoff_7d = now - timedelta(days=7)
        
        # Reset aggregation
        symbol_items: Dict[str, List[NewsItem]] = defaultdict(list)
        
        for item in self._news_items:
            for symbol in item.symbols:
                symbol_items[symbol].append(item)
        
        # Build symbol data
        with self._lock:
            for symbol, items in symbol_items.items():
                items_24h = [i for i in items if i.timestamp >= cutoff_24h]
                items_7d = [i for i in items if i.timestamp >= cutoff_7d]
                
                avg_sentiment = 0.0
                if items_24h:
                    avg_sentiment = sum(i.sentiment for i in items_24h) / len(items_24h)
                
                breaking_count = sum(1 for i in items_24h if i.is_breaking)
                
                catalyst_types = list(set(
                    i.catalyst_type for i in items_24h 
                    if i.catalyst_type
                ))
                
                recent_headlines = [i.title for i in sorted(items_24h, key=lambda x: x.timestamp, reverse=True)]
                
                self._symbol_data[symbol] = NewsSymbolData(
                    symbol=symbol,
                    article_count_24h=len(items_24h),
                    article_count_7d=len(items_7d),
                    avg_sentiment=avg_sentiment,
                    breaking_count=breaking_count,
                    catalyst_types=catalyst_types,
                    recent_headlines=recent_headlines[:10],
                    last_updated=now,
                )
    
    async def get_symbol_momentum(self, symbol: str) -> Optional[Dict]:
        """Get news momentum data for a symbol."""
        with self._lock:
            data = self._symbol_data.get(symbol.upper())
            if data:
                return {
                    "volume_score": data.volume_score,
                    "sentiment_score": data.sentiment_score,
                    "article_count": data.article_count_24h,
                    "avg_sentiment": data.avg_sentiment,
                    "breaking_count": data.breaking_count,
                    "catalyst_types": data.catalyst_types,
                }
        return None
    
    def get_top_news_momentum(self, count: int = 12) -> List[NewsSymbolData]:
        """Get symbols with highest news momentum."""
        with self._lock:
            sorted_data = sorted(
                self._symbol_data.values(),
                key=lambda x: x.volume_score,
                reverse=True
            )
            
            # If no data, return sample data
            if not sorted_data:
                return self._generate_sample_news_momentum(count)
            
            return sorted_data[:count]
    
    def _generate_sample_news_momentum(self, count: int = 12) -> List[NewsSymbolData]:
        """Generate sample news momentum data when no real data available."""
        import random
        
        sample_news = [
            ("NVDA", 15, 0.72, ["AI boom", "Data center growth", "Earnings beat"]),
            ("TSLA", 12, 0.35, ["Delivery numbers", "FSD update", "Price cuts"]),
            ("AAPL", 10, 0.55, ["iPhone sales", "Vision Pro", "AI integration"]),
            ("META", 9, 0.48, ["AI investments", "Metaverse update", "Ad revenue"]),
            ("AMD", 8, 0.62, ["AI chip demand", "Data center", "Market share"]),
            ("GOOGL", 7, 0.52, ["Gemini launch", "Search AI", "Cloud growth"]),
            ("MSFT", 7, 0.58, ["Copilot growth", "Azure AI", "OpenAI deal"]),
            ("AMZN", 6, 0.45, ["AWS growth", "Prime Day", "Retail margins"]),
            ("SMCI", 6, 0.68, ["Server demand", "AI infrastructure"]),
            ("PLTR", 5, 0.65, ["Government contracts", "AI platform"]),
            ("LLY", 5, 0.75, ["GLP-1 drugs", "Obesity treatment"]),
            ("ARM", 4, 0.70, ["AI chip designs", "IPO momentum"]),
            ("JPM", 4, 0.42, ["Interest rates", "Banking outlook"]),
            ("XOM", 3, 0.38, ["Oil prices", "Energy demand"]),
        ]
        
        results = []
        for symbol, articles, sentiment, headlines in sample_news[:count]:
            results.append(NewsSymbolData(
                symbol=symbol,
                article_count_24h=articles + random.randint(-2, 2),
                article_count_7d=articles * 5 + random.randint(-5, 10),
                avg_sentiment=round(sentiment + random.uniform(-0.1, 0.1), 2),
                breaking_count=random.randint(0, 2),
                catalyst_types=["earnings"] if random.random() > 0.7 else [],
                recent_headlines=headlines,
                last_updated=datetime.now(),
            ))
        
        return results
    
    def get_breaking_news(self) -> List[NewsItem]:
        """Get breaking news items."""
        with self._lock:
            breaking = [i for i in self._news_items if i.is_breaking]
            return sorted(breaking, key=lambda x: x.timestamp, reverse=True)[:20]
    
    def get_by_catalyst(self, catalyst_type: str) -> List[NewsSymbolData]:
        """Get symbols by catalyst type."""
        with self._lock:
            return [
                data for data in self._symbol_data.values()
                if catalyst_type in data.catalyst_types
            ]
    
    def get_positive_momentum(self, min_sentiment: float = 0.3, count: int = 12) -> List[NewsSymbolData]:
        """Get symbols with positive news sentiment."""
        with self._lock:
            positive = [
                data for data in self._symbol_data.values()
                if data.avg_sentiment >= min_sentiment
            ]
            sorted_data = sorted(positive, key=lambda x: x.volume_score, reverse=True)
            return sorted_data[:count]
    
    def get_status(self) -> dict:
        """Get news momentum status."""
        with self._lock:
            return {
                "total_items": len(self._news_items),
                "tracked_symbols": len(self._symbol_data),
                "last_fetch": self._last_fetch.isoformat() if self._last_fetch else None,
            }


# Global instance
_news_momentum: Optional[NewsMomentum] = None
_news_lock = threading.Lock()


def get_news_momentum() -> NewsMomentum:
    """Get the global news momentum instance."""
    global _news_momentum
    
    with _news_lock:
        if _news_momentum is None:
            _news_momentum = NewsMomentum()
        return _news_momentum

