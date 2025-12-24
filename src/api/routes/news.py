"""
News and sentiment API routes.

Fetches real news from RSS feeds and financial news APIs.
"""

import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

import aiohttp
import feedparser
from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

router = APIRouter()


class NewsItem(BaseModel):
    """News item model."""
    article_id: str
    source: str
    headline: str
    summary: Optional[str] = None
    url: Optional[str] = None
    timestamp: str
    sentiment: Optional[float] = None
    urgency: Optional[float] = None
    tickers: List[str] = []
    category: Optional[str] = None
    region: Optional[str] = None


# RSS Feed sources for financial news
RSS_FEEDS = {
    # Major Financial News
    "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
    "Reuters Markets": "https://feeds.reuters.com/reuters/companyNews",
    "CNBC Top News": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "CNBC World": "https://www.cnbc.com/id/100727362/device/rss/rss.html",
    "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories",
    "MarketWatch Breaking": "https://feeds.marketwatch.com/marketwatch/marketpulse",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "Seeking Alpha": "https://seekingalpha.com/market_currents.xml",
    "Investing.com": "https://www.investing.com/rss/news.rss",
    # Sector-Specific
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    # Crypto
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
}

# Keywords for ticker extraction
TICKER_PATTERNS = [
    r'\b([A-Z]{1,5})\b',  # Basic ticker pattern
]

# Common non-ticker words to exclude
NON_TICKERS = {
    'CEO', 'CFO', 'COO', 'CTO', 'IPO', 'SEC', 'FDA', 'FTC', 'DOJ', 'FBI', 'CIA',
    'USA', 'NYSE', 'GDP', 'CPI', 'PPI', 'ETF', 'EPS', 'PE', 'AI', 'ML', 'API',
    'THE', 'AND', 'FOR', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE',
    'OUR', 'OUT', 'DAY', 'HAD', 'HOW', 'MAN', 'NEW', 'NOW', 'OLD', 'SEE', 'WAY',
    'WHO', 'BOY', 'DID', 'GET', 'HAS', 'HIM', 'HIS', 'LET', 'PUT', 'SAY', 'SHE',
    'TOO', 'USE', 'MAY', 'FED', 'EU', 'UK', 'US', 'AM', 'PM', 'EST', 'PST',
}

# Known ticker mappings
KNOWN_TICKERS = {
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 
    'NFLX', 'INTC', 'CSCO', 'ORCL', 'IBM', 'CRM', 'ADBE', 'PYPL', 'SQ', 'SHOP',
    'UBER', 'LYFT', 'ABNB', 'COIN', 'PLTR', 'SNOW', 'NET', 'CRWD', 'ZS', 'DDOG',
    'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'BTC', 'ETH', 'XRP', 'SOL', 'DOGE',
    'JPM', 'BAC', 'GS', 'MS', 'WFC', 'C', 'V', 'MA', 'AXP', 'BRK',
    'XOM', 'CVX', 'COP', 'OXY', 'SLB', 'HAL', 'BP', 'SHEL',
    'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'UNH', 'CVS', 'MRNA', 'BNTX',
    'WMT', 'TGT', 'COST', 'HD', 'LOW', 'NKE', 'MCD', 'SBUX', 'KO', 'PEP',
    'DIS', 'CMCSA', 'T', 'VZ', 'TMUS', 'NFLX', 'PARA', 'WBD',
    'BA', 'LMT', 'RTX', 'NOC', 'GD', 'CAT', 'DE', 'MMM', 'HON', 'GE',
    'SMCI', 'ARM', 'AVGO', 'MU', 'QCOM', 'TXN', 'AMAT', 'LRCX', 'KLAC',
}


def extract_tickers(text: str) -> List[str]:
    """Extract potential stock tickers from text."""
    if not text:
        return []
    
    words = re.findall(r'\b[A-Z]{2,5}\b', text.upper())
    tickers = []
    
    for word in words:
        if word not in NON_TICKERS and word in KNOWN_TICKERS:
            if word not in tickers:
                tickers.append(word)
    
    return tickers[:5]  # Limit to 5 tickers


def simple_sentiment(text: str) -> float:
    """Calculate simple sentiment score from text."""
    if not text:
        return 0.0
    
    text_lower = text.lower()
    
    positive_words = [
        'surge', 'soar', 'jump', 'rally', 'gain', 'rise', 'climb', 'boost',
        'beat', 'exceed', 'strong', 'bullish', 'upgrade', 'outperform', 'buy',
        'growth', 'profit', 'record', 'high', 'breakthrough', 'success', 'wins',
        'positive', 'optimistic', 'confident', 'expand', 'increase', 'up',
    ]
    
    negative_words = [
        'fall', 'drop', 'plunge', 'crash', 'decline', 'sink', 'tumble', 'slide',
        'miss', 'disappoint', 'weak', 'bearish', 'downgrade', 'underperform', 'sell',
        'loss', 'warning', 'low', 'concern', 'fail', 'cut', 'layoff', 'lawsuit',
        'negative', 'pessimistic', 'worried', 'shrink', 'decrease', 'down',
    ]
    
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)
    
    total = pos_count + neg_count
    if total == 0:
        return 0.0
    
    # Score between -1 and 1
    score = (pos_count - neg_count) / max(total, 1)
    return round(max(-1.0, min(1.0, score)), 2)


def get_category(text: str, source: str) -> str:
    """Determine news category from text and source."""
    text_lower = text.lower()
    
    if any(w in text_lower for w in ['crypto', 'bitcoin', 'ethereum', 'blockchain']):
        return 'Crypto'
    if any(w in text_lower for w in ['fed', 'interest rate', 'inflation', 'gdp', 'cpi']):
        return 'Fed'
    if any(w in text_lower for w in ['earnings', 'revenue', 'profit', 'eps', 'quarterly']):
        return 'Earnings'
    if any(w in text_lower for w in ['merger', 'acquisition', 'acquire', 'buyout', 'deal']):
        return 'M&A'
    if any(w in text_lower for w in ['fda', 'drug', 'approval', 'clinical', 'trial']):
        return 'FDA'
    if any(w in text_lower for w in ['tech', 'ai', 'software', 'cloud', 'semiconductor']):
        return 'Tech'
    if any(w in text_lower for w in ['oil', 'energy', 'gas', 'opec']):
        return 'Energy'
    
    return 'General'


def get_region(source: str) -> str:
    """Determine region from source."""
    source_lower = source.lower()
    
    if any(w in source_lower for w in ['reuters', 'cnbc', 'marketwatch', 'yahoo', 'seeking']):
        return 'US'
    if any(w in source_lower for w in ['ft', 'bbc', 'guardian']):
        return 'EU'
    if any(w in source_lower for w in ['nikkei', 'scmp', 'caixin']):
        return 'Asia'
    
    return 'Global'


async def fetch_rss_feed(session: aiohttp.ClientSession, source: str, url: str) -> List[Dict[str, Any]]:
    """Fetch and parse a single RSS feed."""
    articles = []
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                content = await response.text()
                feed = feedparser.parse(content)
                
                for entry in feed.entries[:20]:  # Limit to 20 per feed
                    # Generate unique ID
                    article_id = hashlib.md5(
                        (entry.get('link', '') + entry.get('title', '')).encode()
                    ).hexdigest()[:12]
                    
                    # Parse timestamp
                    timestamp = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            timestamp = datetime(*entry.published_parsed[:6])
                        except:
                            pass
                    
                    headline = entry.get('title', '').strip()
                    summary = entry.get('summary', entry.get('description', '')).strip()
                    
                    # Clean HTML from summary
                    summary = re.sub(r'<[^>]+>', '', summary)[:500]
                    
                    articles.append({
                        'article_id': article_id,
                        'source': source,
                        'headline': headline,
                        'summary': summary,
                        'url': entry.get('link', ''),
                        'timestamp': timestamp.isoformat(),
                        'tickers': extract_tickers(headline + ' ' + summary),
                        'sentiment': simple_sentiment(headline + ' ' + summary),
                        'category': get_category(headline + ' ' + summary, source),
                        'region': get_region(source),
                    })
                    
    except asyncio.TimeoutError:
        logger.debug(f"Timeout fetching {source}")
    except Exception as e:
        logger.debug(f"Error fetching {source}: {e}")
    
    return articles


async def fetch_all_news() -> List[Dict[str, Any]]:
    """Fetch news from all RSS sources concurrently."""
    all_articles = []
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_rss_feed(session, source, url)
            for source, url in RSS_FEEDS.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
    
    # Sort by timestamp (newest first)
    all_articles.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Deduplicate by headline similarity
    seen_headlines = set()
    unique_articles = []
    
    for article in all_articles:
        headline_key = article['headline'][:50].lower()
        if headline_key not in seen_headlines:
            seen_headlines.add(headline_key)
            unique_articles.append(article)
    
    return unique_articles[:100]  # Limit to 100 articles


# Cache for news
_news_cache: Dict[str, Any] = {
    'articles': [],
    'last_fetch': None,
    'cache_duration': 300,  # 5 minutes
}


@router.get("/")
async def get_recent_news(
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    ticker: Optional[str] = None,
):
    """
    Get recent news articles from RSS feeds.
    
    - Fetches from 10+ financial news RSS feeds
    - Includes sentiment analysis
    - Extracts mentioned tickers
    - Caches results for 5 minutes
    """
    global _news_cache
    
    # Check cache
    now = datetime.now()
    if (
        _news_cache['last_fetch'] is None or 
        (now - _news_cache['last_fetch']).seconds > _news_cache['cache_duration'] or
        len(_news_cache['articles']) == 0
    ):
        logger.info("Fetching fresh news from RSS feeds...")
        _news_cache['articles'] = await fetch_all_news()
        _news_cache['last_fetch'] = now
        logger.info(f"Fetched {len(_news_cache['articles'])} news articles")
    
    articles = _news_cache['articles']
    
    # Filter by category
    if category:
        articles = [a for a in articles if a.get('category', '').lower() == category.lower()]
    
    # Filter by ticker
    if ticker:
        ticker_upper = ticker.upper()
        articles = [a for a in articles if ticker_upper in a.get('tickers', [])]
    
    return {
        "articles": articles[:limit],
        "count": len(articles[:limit]),
        "total_available": len(_news_cache['articles']),
        "last_updated": _news_cache['last_fetch'].isoformat() if _news_cache['last_fetch'] else None,
        "sources": list(RSS_FEEDS.keys()),
    }


@router.get("/by-ticker/{ticker}")
async def get_news_by_ticker(ticker: str, limit: int = Query(20, ge=1, le=50)):
    """Get news for a specific ticker."""
    result = await get_recent_news(limit=100, ticker=ticker)
    articles = result['articles'][:limit]
    
    # Calculate average sentiment
    sentiments = [a.get('sentiment', 0) for a in articles if a.get('sentiment') is not None]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
    
    return {
        "ticker": ticker.upper(),
        "articles": articles,
        "count": len(articles),
        "sentiment_avg": round(avg_sentiment, 2),
    }


@router.get("/sentiment")
async def get_market_sentiment():
    """Get overall market sentiment from news."""
    result = await get_recent_news(limit=100)
    articles = result['articles']
    
    if not articles:
        return {
            "overall": 0,
            "by_category": {},
            "trending_tickers": [],
        }
    
    # Overall sentiment
    sentiments = [a.get('sentiment', 0) for a in articles]
    overall = sum(sentiments) / len(sentiments) if sentiments else 0
    
    # Sentiment by category
    by_category = {}
    for article in articles:
        cat = article.get('category', 'General')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(article.get('sentiment', 0))
    
    category_sentiment = {
        cat: round(sum(scores) / len(scores), 2)
        for cat, scores in by_category.items()
        if scores
    }
    
    # Trending tickers
    ticker_counts = {}
    for article in articles:
        for ticker in article.get('tickers', []):
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
    
    trending = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "overall": round(overall, 2),
        "by_category": category_sentiment,
        "trending_tickers": [{"ticker": t, "mentions": c} for t, c in trending],
    }


@router.get("/sources")
async def get_news_sources():
    """Get status of news sources."""
    return {
        "total": len(RSS_FEEDS),
        "active": len(RSS_FEEDS),
        "sources": [
            {"name": name, "url": url, "enabled": True}
            for name, url in RSS_FEEDS.items()
        ],
    }


@router.post("/refresh")
async def refresh_news():
    """Force refresh the news cache."""
    global _news_cache
    _news_cache['last_fetch'] = None
    result = await get_recent_news()
    return {
        "status": "refreshed",
        "count": result['count'],
    }
