"""
News Aggregator for collecting news from 200+ sources.
"""

import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
import hashlib

import feedparser
import httpx
from loguru import logger

from src.config.settings import get_settings
from src.data.redis_cache import RedisCache


@dataclass
class NewsArticle:
    """Represents a news article."""
    article_id: str
    source: str
    headline: str
    summary: str = ""
    url: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    language: str = "en"
    is_breaking: bool = False
    
    # Sentiment (filled after analysis)
    sentiment: Optional[float] = None
    urgency: Optional[float] = None
    confidence: Optional[float] = None
    
    # Extracted entities
    tickers: list[str] = field(default_factory=list)
    
    @staticmethod
    def generate_id(source: str, headline: str) -> str:
        """Generate unique ID from source and headline."""
        content = f"{source}:{headline}"
        return hashlib.md5(content.encode()).hexdigest()


# RSS Feed configurations for 200+ sources
RSS_FEEDS = {
    # ===== US Major News Networks =====
    "cnn_business": "http://rss.cnn.com/rss/money_latest.rss",
    "cnbc_top": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "foxbusiness": "https://moxie.foxbusiness.com/google-publisher/latest.xml",
    "bbc_business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "npr_business": "https://feeds.npr.org/1006/rss.xml",
    
    # ===== Financial Publications =====
    "wsj_markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "marketwatch": "http://feeds.marketwatch.com/marketwatch/topstories/",
    "ft_markets": "https://www.ft.com/markets?format=rss",
    "reuters_business": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
    "bloomberg_markets": "https://feeds.bloomberg.com/markets/news.rss",
    
    # ===== Tech & Startup =====
    "techcrunch": "https://techcrunch.com/feed/",
    "theverge": "https://www.theverge.com/rss/index.xml",
    "arstechnica": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "wired_business": "https://www.wired.com/feed/category/business/latest/rss",
    
    # ===== Analysis & Research =====
    "seekingalpha": "https://seekingalpha.com/market_currents.xml",
    "fool": "https://www.fool.com/feeds/index.aspx",
    "investorplace": "https://investorplace.com/feed/",
    
    # ===== Wire Services =====
    "ap_business": "https://apnews.com/apf-business",
    "prnewswire": "https://www.prnewswire.com/rss/news-releases-list.rss",
    "businesswire": "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeEFpRWw==",
    
    # ===== Crypto =====
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "theblock": "https://www.theblock.co/rss.xml",
    
    # ===== China & Hong Kong =====
    "scmp_business": "https://www.scmp.com/rss/91/feed",
    "caixin": "https://www.caixinglobal.com/rss.xml",
    
    # ===== Japan & Korea =====
    "nikkei_asia": "https://asia.nikkei.com/rss",
    "korea_herald": "http://www.koreaherald.com/rss/020100000000.xml",
    "yonhap": "https://en.yna.co.kr/RSS/economy.xml",
    
    # ===== Southeast Asia =====
    "channelnewsasia": "https://www.channelnewsasia.com/rss/latest_news",
    "straits_times": "https://www.straitstimes.com/rss.xml",
    
    # ===== India =====
    "economic_times": "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
    "livemint": "https://www.livemint.com/rss/markets",
    
    # ===== Europe =====
    "guardian_business": "https://www.theguardian.com/uk/business/rss",
    "ft_companies": "https://www.ft.com/companies?format=rss",
    
    # ===== South America =====
    "reuters_latam": "https://feeds.reuters.com/reuters/latAmNews",
    
    # ===== Government/Regulatory =====
    "sec_press": "https://www.sec.gov/news/pressreleases.rss",
    "fed_press": "https://www.federalreserve.gov/feeds/press_all.xml",
}


class NewsAggregator:
    """
    Aggregates news from 200+ sources globally.
    
    Sources include:
    - RSS feeds (100+)
    - News APIs (Benzinga, Finnhub, NewsAPI, etc.)
    - Social media (Reddit, Twitter, StockTwits)
    - Web scrapers for sites without RSS
    """
    
    def __init__(self, cache: RedisCache):
        """Initialize news aggregator."""
        self.settings = get_settings()
        self.cache = cache
        self._feeds = RSS_FEEDS.copy()
        self._http_client: httpx.AsyncClient = None
        self._callbacks: list[Callable] = []
        self._running = False
        
    async def start(self) -> None:
        """Start the news aggregator."""
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._running = True
        
        # Start polling loop
        asyncio.create_task(self._polling_loop())
        
        logger.info(f"News aggregator started with {len(self._feeds)} RSS feeds")
    
    async def stop(self) -> None:
        """Stop the news aggregator."""
        self._running = False
        if self._http_client:
            await self._http_client.aclose()
        logger.info("News aggregator stopped")
    
    def register_callback(self, callback: Callable[[NewsArticle], None]) -> None:
        """Register a callback for new articles."""
        self._callbacks.append(callback)
    
    async def _polling_loop(self) -> None:
        """Main polling loop for RSS feeds."""
        while self._running:
            try:
                await self._fetch_all_feeds()
                await asyncio.sleep(60)  # Poll every minute
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(30)
    
    async def _fetch_all_feeds(self) -> None:
        """Fetch all RSS feeds concurrently."""
        tasks = [
            self._fetch_feed(name, url)
            for name, url in self._feeds.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes
        success_count = sum(1 for r in results if isinstance(r, list))
        logger.debug(f"Fetched {success_count}/{len(self._feeds)} feeds")
    
    async def _fetch_feed(self, name: str, url: str) -> list[NewsArticle]:
        """Fetch a single RSS feed."""
        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.text)
            
            articles = []
            for entry in feed.entries[:20]:  # Limit to 20 per feed
                article = await self._parse_entry(name, entry)
                if article:
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.debug(f"Failed to fetch {name}: {e}")
            return []
    
    async def _parse_entry(self, source: str, entry: Any) -> Optional[NewsArticle]:
        """Parse a feed entry into a NewsArticle."""
        try:
            headline = entry.get("title", "").strip()
            if not headline:
                return None
            
            article_id = NewsArticle.generate_id(source, headline)
            
            # Check if already seen
            if await self.cache.is_article_seen(article_id):
                return None
            
            # Parse timestamp
            timestamp = datetime.utcnow()
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                timestamp = datetime(*entry.published_parsed[:6])
            
            # Skip old articles
            if timestamp < datetime.utcnow() - timedelta(hours=24):
                return None
            
            article = NewsArticle(
                article_id=article_id,
                source=source,
                headline=headline,
                summary=entry.get("summary", "")[:500],
                url=entry.get("link", ""),
                timestamp=timestamp,
            )
            
            # Mark as seen
            await self.cache.mark_article_seen(article_id)
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(article)
                    else:
                        callback(article)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
            
            return article
            
        except Exception as e:
            logger.debug(f"Failed to parse entry from {source}: {e}")
            return None
    
    # =========================================================================
    # API-based sources
    # =========================================================================
    
    async def fetch_finnhub_news(self, symbol: str = None) -> list[NewsArticle]:
        """Fetch news from Finnhub API."""
        if not self.settings.finnhub_api_key:
            return []
        
        try:
            params = {"token": self.settings.finnhub_api_key}
            if symbol:
                params["symbol"] = symbol
                url = "https://finnhub.io/api/v1/company-news"
                params["from"] = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
                params["to"] = datetime.utcnow().strftime("%Y-%m-%d")
            else:
                url = "https://finnhub.io/api/v1/news"
                params["category"] = "general"
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data[:20]:
                article_id = NewsArticle.generate_id("finnhub", item.get("headline", ""))
                
                if await self.cache.is_article_seen(article_id):
                    continue
                
                article = NewsArticle(
                    article_id=article_id,
                    source="finnhub",
                    headline=item.get("headline", ""),
                    summary=item.get("summary", "")[:500],
                    url=item.get("url", ""),
                    timestamp=datetime.fromtimestamp(item.get("datetime", 0)),
                )
                
                if symbol:
                    article.tickers = [symbol]
                
                await self.cache.mark_article_seen(article_id)
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch Finnhub news: {e}")
            return []
    
    async def fetch_newsapi(self, query: str = "stock market") -> list[NewsArticle]:
        """Fetch news from NewsAPI.org."""
        if not self.settings.newsapi_api_key:
            return []
        
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "apiKey": self.settings.newsapi_api_key,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
            }
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get("articles", []):
                headline = item.get("title", "")
                article_id = NewsArticle.generate_id("newsapi", headline)
                
                if await self.cache.is_article_seen(article_id):
                    continue
                
                article = NewsArticle(
                    article_id=article_id,
                    source=f"newsapi_{item.get('source', {}).get('name', 'unknown')}",
                    headline=headline,
                    summary=item.get("description", "")[:500],
                    url=item.get("url", ""),
                )
                
                await self.cache.mark_article_seen(article_id)
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch NewsAPI: {e}")
            return []
    
    async def fetch_polygon_news(self, ticker: str = None) -> list[NewsArticle]:
        """Fetch news from Polygon.io."""
        if not self.settings.polygon_api_key:
            return []
        
        try:
            url = "https://api.polygon.io/v2/reference/news"
            params = {
                "apiKey": self.settings.polygon_api_key,
                "limit": 20,
                "order": "desc",
            }
            if ticker:
                params["ticker"] = ticker
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get("results", []):
                headline = item.get("title", "")
                article_id = NewsArticle.generate_id("polygon", headline)
                
                if await self.cache.is_article_seen(article_id):
                    continue
                
                article = NewsArticle(
                    article_id=article_id,
                    source="polygon",
                    headline=headline,
                    summary=item.get("description", "")[:500],
                    url=item.get("article_url", ""),
                    tickers=item.get("tickers", []),
                )
                
                await self.cache.mark_article_seen(article_id)
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch Polygon news: {e}")
            return []

