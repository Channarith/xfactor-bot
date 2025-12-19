"""
Video Platform Sentiment Analysis

Analyzes trading content from video platforms:
- YouTube (financial channels, stock analysis)
- TikTok (FinTok, stock tips, trading influencers)
- Instagram (financial influencers, trading posts)

Features:
- Video/post metadata extraction
- Engagement analysis
- Influencer tracking
- Trending content detection
- Sentiment from titles, descriptions, comments
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta, timezone
from enum import Enum
import re
from collections import defaultdict

from loguru import logger


class VideoPlatform(Enum):
    """Video/social platforms."""
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    FACEBOOK = "facebook"


class ContentType(Enum):
    """Content type classification."""
    VIDEO = "video"
    SHORT = "short"         # YouTube Shorts, TikTok, Reels
    POST = "post"           # Image post
    STORY = "story"
    LIVE = "live"
    REEL = "reel"


class ContentCategory(Enum):
    """Financial content category."""
    STOCK_ANALYSIS = "stock_analysis"
    MARKET_NEWS = "market_news"
    TRADING_TIPS = "trading_tips"
    EARNINGS = "earnings"
    IPO = "ipo"
    CRYPTO = "crypto"
    OPTIONS = "options"
    DAY_TRADING = "day_trading"
    SWING_TRADING = "swing_trading"
    INVESTING = "investing"
    MEME_STOCKS = "meme_stocks"
    PROMO = "promo"
    TUTORIAL = "tutorial"


@dataclass
class VideoContent:
    """A video/post from a platform."""
    id: str
    platform: VideoPlatform
    content_type: ContentType
    
    # Creator info
    creator_id: str
    creator_name: str
    creator_handle: str
    creator_followers: int
    
    # Content info
    title: str
    description: str
    url: str
    
    # Optional fields with defaults
    creator_verified: bool = False
    thumbnail_url: Optional[str] = None
    duration_seconds: int = 0
    published_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Engagement
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    
    # Analysis
    symbols_mentioned: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    categories: List[ContentCategory] = field(default_factory=list)
    sentiment_score: float = 0.0  # -1 to +1
    
    # Trending metrics
    views_velocity: float = 0.0  # Views per hour
    engagement_rate: float = 0.0  # Engagement / Views
    viral_score: float = 0.0  # 0-100
    
    @property
    def total_engagement(self) -> int:
        return self.likes + self.comments + self.shares + self.saves
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform.value,
            "content_type": self.content_type.value,
            "creator": {
                "id": self.creator_id,
                "name": self.creator_name,
                "handle": self.creator_handle,
                "followers": self.creator_followers,
                "verified": self.creator_verified,
            },
            "title": self.title,
            "description": self.description[:500] if self.description else "",
            "url": self.url,
            "thumbnail_url": self.thumbnail_url,
            "duration_seconds": self.duration_seconds,
            "published_at": self.published_at.isoformat(),
            "engagement": {
                "views": self.views,
                "likes": self.likes,
                "comments": self.comments,
                "shares": self.shares,
                "saves": self.saves,
                "total": self.total_engagement,
                "rate": round(self.engagement_rate, 4),
            },
            "analysis": {
                "symbols": self.symbols_mentioned,
                "hashtags": self.hashtags,
                "categories": [c.value for c in self.categories],
                "sentiment_score": round(self.sentiment_score, 2),
                "viral_score": round(self.viral_score, 1),
            },
        }


@dataclass
class FinancialInfluencer:
    """A financial content creator/influencer."""
    id: str
    platform: VideoPlatform
    name: str
    handle: str
    followers: int
    verified: bool = False
    url: str = ""  # Profile URL
    
    # Influence metrics
    avg_views: int = 0
    avg_engagement_rate: float = 0.0
    post_frequency: str = ""  # daily, weekly, etc.
    
    # Trading focus
    primary_focus: List[str] = field(default_factory=list)  # stocks, crypto, options
    typical_sentiment: str = "neutral"  # bullish, bearish, neutral
    accuracy_score: float = 0.0  # Historical accuracy 0-100
    
    # Engagement history
    total_posts: int = 0
    total_views: int = 0
    symbols_mentioned: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        # Generate URL if not set
        url = self.url
        if not url:
            if self.platform == VideoPlatform.YOUTUBE:
                url = f"https://www.youtube.com/@{self.handle}"
            elif self.platform == VideoPlatform.TIKTOK:
                url = f"https://www.tiktok.com/@{self.handle}"
            elif self.platform == VideoPlatform.INSTAGRAM:
                url = f"https://www.instagram.com/{self.handle}"
        
        return {
            "id": self.id,
            "platform": self.platform.value,
            "name": self.name,
            "handle": self.handle,
            "followers": self.followers,
            "verified": self.verified,
            "url": url,
            "metrics": {
                "avg_views": self.avg_views,
                "avg_engagement_rate": round(self.avg_engagement_rate, 4),
                "post_frequency": self.post_frequency,
                "total_posts": self.total_posts,
            },
            "focus": {
                "primary": self.primary_focus,
                "typical_sentiment": self.typical_sentiment,
                "accuracy_score": round(self.accuracy_score, 1),
            },
            "top_symbols": dict(sorted(
                self.symbols_mentioned.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
        }


class VideoPlatformAnalyzer:
    """
    Analyzes video content from YouTube, TikTok, and Instagram.
    
    Usage:
        analyzer = VideoPlatformAnalyzer()
        
        # Add content for analysis
        analyzer.add_content(video_content)
        
        # Get trending videos about stocks
        trending = analyzer.get_trending_content("stocks")
        
        # Get influencer mentions
        mentions = analyzer.get_influencer_mentions("NVDA")
    """
    
    # Financial hashtags to track
    FINANCIAL_HASHTAGS = {
        "youtube": [
            "stocks", "investing", "stockmarket", "trading", "daytrading",
            "wallstreet", "finance", "stockanalysis", "options", "crypto",
            "bitcoin", "ethereum", "financialfreedom", "passiveincome",
        ],
        "tiktok": [
            "stocktok", "fintok", "moneytok", "investingtiktok", "stockmarket",
            "daytrader", "tradinglife", "cryptotok", "wallstreetbets",
            "stocks", "investing101", "financetok", "richlife", "stocktips",
            "optionstrading", "forex", "swingtrade", "robinhood",
        ],
        "instagram": [
            "stocks", "stockmarket", "investing", "trader", "daytrader",
            "forex", "crypto", "bitcoin", "wealth", "financialfreedom",
            "tradingview", "stocktrading", "wallstreet", "optionstrading",
        ],
    }
    
    # Known financial influencers
    KNOWN_INFLUENCERS = {
        "youtube": [
            {"handle": "MeetKevin", "name": "Meet Kevin", "followers": 2000000, "focus": ["stocks", "real estate"], "url": "https://www.youtube.com/@MeetKevin"},
            {"handle": "GrahamStephan", "name": "Graham Stephan", "followers": 4500000, "focus": ["investing", "real estate"], "url": "https://www.youtube.com/@GrahamStephan"},
            {"handle": "AndreJikh", "name": "Andrei Jikh", "followers": 2200000, "focus": ["investing", "crypto"], "url": "https://www.youtube.com/@AndreiJikh"},
            {"handle": "TomNash", "name": "Tom Nash", "followers": 500000, "focus": ["stocks", "tech"], "url": "https://www.youtube.com/@TomNash"},
            {"handle": "StockMoe", "name": "Stock Moe", "followers": 400000, "focus": ["growth stocks"], "url": "https://www.youtube.com/@StockMoe"},
            {"handle": "JosephCarlson", "name": "Joseph Carlson", "followers": 300000, "focus": ["dividend investing"], "url": "https://www.youtube.com/@TheJosephCarlsonShow"},
            {"handle": "MarkMoss", "name": "Mark Moss", "followers": 500000, "focus": ["crypto", "macro"], "url": "https://www.youtube.com/@MarkMoss"},
            {"handle": "Tickertape", "name": "Ticker Tape", "followers": 200000, "focus": ["stocks", "analysis"], "url": "https://www.youtube.com/@TickerSymbolYou"},
        ],
        "tiktok": [
            {"handle": "stocktraderpro", "name": "Stock Trader Pro", "followers": 1500000, "focus": ["day trading"], "url": "https://www.tiktok.com/@stocktraderpro"},
            {"handle": "tradingwithbrian", "name": "Trading with Brian", "followers": 800000, "focus": ["options"], "url": "https://www.tiktok.com/@tradingwithbrian"},
            {"handle": "investwithqai", "name": "Invest with Qai", "followers": 600000, "focus": ["stocks"], "url": "https://www.tiktok.com/@investwithqai"},
            {"handle": "stockswithtom", "name": "Stocks with Tom", "followers": 500000, "focus": ["swing trading"], "url": "https://www.tiktok.com/@stockswithtom"},
            {"handle": "fintokking", "name": "FinTok King", "followers": 400000, "focus": ["meme stocks"], "url": "https://www.tiktok.com/@fintokking"},
        ],
        "instagram": [
            {"handle": "wallstreetbets", "name": "WSB", "followers": 2000000, "focus": ["meme stocks", "options"], "url": "https://www.instagram.com/wallstreetbets"},
            {"handle": "stockmarket", "name": "Stock Market", "followers": 1500000, "focus": ["stocks"], "url": "https://www.instagram.com/stockmarket"},
            {"handle": "tradingview", "name": "TradingView", "followers": 1200000, "focus": ["charts", "analysis"], "url": "https://www.instagram.com/tradingview"},
            {"handle": "investorsclub", "name": "Investors Club", "followers": 800000, "focus": ["investing"], "url": "https://www.instagram.com/investorsclub"},
        ],
    }
    
    # Symbol extraction patterns
    SYMBOL_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')
    TICKER_PATTERN = re.compile(r'\b([A-Z]{2,5})\s+(?:stock|shares|calls|puts)\b', re.IGNORECASE)
    
    def __init__(self):
        self._content: Dict[str, List[VideoContent]] = defaultdict(list)
        self._influencers: Dict[str, FinancialInfluencer] = {}
        self._symbol_content: Dict[str, List[VideoContent]] = defaultdict(list)
        self._trending_cache: Dict[str, List[Dict]] = {}
        self._last_update: Optional[datetime] = None
    
    def add_content(self, content: VideoContent) -> None:
        """Add video content for analysis."""
        # Extract symbols if not done
        if not content.symbols_mentioned:
            content.symbols_mentioned = self._extract_symbols(
                f"{content.title} {content.description}"
            )
        
        # Calculate sentiment
        if content.sentiment_score == 0:
            content.sentiment_score = self._analyze_sentiment(
                f"{content.title} {content.description}"
            )
        
        # Calculate engagement rate
        if content.views > 0:
            content.engagement_rate = content.total_engagement / content.views
        
        # Calculate viral score
        content.viral_score = self._calculate_viral_score(content)
        
        # Categorize content
        if not content.categories:
            content.categories = self._categorize_content(content)
        
        # Store by platform
        self._content[content.platform.value].append(content)
        
        # Index by symbol
        for symbol in content.symbols_mentioned:
            self._symbol_content[symbol].append(content)
        
        # Track influencer
        self._track_influencer(content)
        
        self._last_update = datetime.now(timezone.utc)
    
    def _extract_symbols(self, text: str) -> List[str]:
        """Extract stock symbols from text."""
        symbols = set()
        
        # $SYMBOL format
        for match in self.SYMBOL_PATTERN.findall(text):
            if len(match) <= 5:
                symbols.add(match.upper())
        
        # "AAPL stock" format
        for match in self.TICKER_PATTERN.findall(text):
            if len(match) <= 5:
                symbols.add(match.upper())
        
        # Common stock names
        stock_names = {
            "apple": "AAPL", "tesla": "TSLA", "nvidia": "NVDA",
            "amazon": "AMZN", "google": "GOOGL", "microsoft": "MSFT",
            "meta": "META", "netflix": "NFLX", "amd": "AMD",
            "gamestop": "GME", "palantir": "PLTR", "nio": "NIO",
        }
        text_lower = text.lower()
        for name, symbol in stock_names.items():
            if name in text_lower:
                symbols.add(symbol)
        
        return list(symbols)
    
    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text (-1 to +1)."""
        text_lower = text.lower()
        
        bullish_words = [
            "buy", "bullish", "moon", "rocket", "calls", "long", "breakout",
            "undervalued", "accumulate", "strong", "growth", "upside",
            "all time high", "ath", "squeeze", "ripping", "exploding",
            "massive gains", "millionaire", "rich", "wealth",
        ]
        
        bearish_words = [
            "sell", "bearish", "crash", "puts", "short", "overvalued",
            "dump", "avoid", "warning", "scam", "bubble", "falling",
            "downside", "losses", "bankrupt", "fraud", "ponzi",
        ]
        
        bullish_count = sum(1 for word in bullish_words if word in text_lower)
        bearish_count = sum(1 for word in bearish_words if word in text_lower)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0
        
        return (bullish_count - bearish_count) / total
    
    def _calculate_viral_score(self, content: VideoContent) -> float:
        """Calculate viral potential score (0-100)."""
        score = 0.0
        
        # Views contribution (log scale)
        if content.views > 0:
            import math
            score += min(30, math.log10(content.views) * 5)
        
        # Engagement rate contribution
        if content.engagement_rate > 0.1:
            score += 20
        elif content.engagement_rate > 0.05:
            score += 15
        elif content.engagement_rate > 0.02:
            score += 10
        
        # Shares are strong viral indicator
        if content.shares > 1000:
            score += 20
        elif content.shares > 100:
            score += 10
        
        # Verified creator boost
        if content.creator_verified:
            score += 10
        
        # Large following boost
        if content.creator_followers > 1000000:
            score += 15
        elif content.creator_followers > 100000:
            score += 10
        
        # Recent content boost
        hours_old = (datetime.now(timezone.utc) - content.published_at).total_seconds() / 3600
        if hours_old < 24:
            score += 10
        elif hours_old < 72:
            score += 5
        
        return min(100, score)
    
    def _categorize_content(self, content: VideoContent) -> List[ContentCategory]:
        """Categorize financial content."""
        categories = []
        text = f"{content.title} {content.description}".lower()
        hashtags_lower = [h.lower() for h in content.hashtags]
        
        category_keywords = {
            ContentCategory.STOCK_ANALYSIS: ["analysis", "review", "breakdown", "deep dive"],
            ContentCategory.MARKET_NEWS: ["news", "update", "breaking", "report"],
            ContentCategory.TRADING_TIPS: ["tips", "strategy", "how to", "secrets"],
            ContentCategory.EARNINGS: ["earnings", "quarterly", "q1", "q2", "q3", "q4"],
            ContentCategory.IPO: ["ipo", "going public", "direct listing"],
            ContentCategory.CRYPTO: ["crypto", "bitcoin", "ethereum", "btc", "eth"],
            ContentCategory.OPTIONS: ["options", "calls", "puts", "spreads"],
            ContentCategory.DAY_TRADING: ["day trade", "daytrade", "scalp"],
            ContentCategory.SWING_TRADING: ["swing trade", "swing trading"],
            ContentCategory.MEME_STOCKS: ["meme", "ape", "diamond hands", "wsb"],
            ContentCategory.PROMO: ["promo", "sponsored", "discount", "free"],
            ContentCategory.TUTORIAL: ["tutorial", "beginner", "learn", "course"],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in text or kw in " ".join(hashtags_lower) for kw in keywords):
                categories.append(category)
        
        if not categories:
            categories.append(ContentCategory.INVESTING)
        
        return categories
    
    def _track_influencer(self, content: VideoContent) -> None:
        """Track influencer from content."""
        influencer_key = f"{content.platform.value}_{content.creator_handle}"
        
        if influencer_key not in self._influencers:
            self._influencers[influencer_key] = FinancialInfluencer(
                id=content.creator_id,
                platform=content.platform,
                name=content.creator_name,
                handle=content.creator_handle,
                followers=content.creator_followers,
                verified=content.creator_verified,
            )
        
        influencer = self._influencers[influencer_key]
        influencer.total_posts += 1
        influencer.total_views += content.views
        influencer.followers = max(influencer.followers, content.creator_followers)
        
        # Track symbols
        for symbol in content.symbols_mentioned:
            influencer.symbols_mentioned[symbol] = influencer.symbols_mentioned.get(symbol, 0) + 1
        
        # Update average views
        influencer.avg_views = influencer.total_views // max(influencer.total_posts, 1)
    
    def get_trending_content(
        self,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        hours: int = 24,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get trending financial content.
        
        Args:
            platform: Filter by platform (youtube, tiktok, instagram)
            category: Filter by category
            hours: Look-back window
            limit: Max results
        
        Returns:
            List of trending content
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        all_content = []
        platforms = [platform] if platform else ["youtube", "tiktok", "instagram"]
        
        for plat in platforms:
            all_content.extend(self._content.get(plat, []))
        
        # Filter by time
        recent = [c for c in all_content if c.published_at > cutoff]
        
        # Filter by category
        if category:
            try:
                cat = ContentCategory(category)
                recent = [c for c in recent if cat in c.categories]
            except ValueError:
                pass
        
        # Sort by viral score
        recent.sort(key=lambda x: x.viral_score, reverse=True)
        
        return [c.to_dict() for c in recent[:limit]]
    
    def get_content_for_symbol(
        self,
        symbol: str,
        hours: int = 72,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get all video content mentioning a symbol."""
        symbol = symbol.upper()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        content = self._symbol_content.get(symbol, [])
        recent = [c for c in content if c.published_at > cutoff]
        recent.sort(key=lambda x: x.viral_score, reverse=True)
        
        # Aggregate sentiment
        if recent:
            avg_sentiment = sum(c.sentiment_score for c in recent) / len(recent)
            total_views = sum(c.views for c in recent)
            total_engagement = sum(c.total_engagement for c in recent)
        else:
            avg_sentiment = 0
            total_views = 0
            total_engagement = 0
        
        # Platform breakdown
        by_platform = defaultdict(int)
        for c in recent:
            by_platform[c.platform.value] += 1
        
        return {
            "symbol": symbol,
            "content_count": len(recent),
            "total_views": total_views,
            "total_engagement": total_engagement,
            "avg_sentiment": round(avg_sentiment, 2),
            "sentiment_label": "bullish" if avg_sentiment > 0.2 else "bearish" if avg_sentiment < -0.2 else "neutral",
            "by_platform": dict(by_platform),
            "top_content": [c.to_dict() for c in recent[:limit]],
        }
    
    def get_influencer_mentions(
        self,
        symbol: Optional[str] = None,
        platform: Optional[str] = None,
        min_followers: int = 100000,
    ) -> List[Dict[str, Any]]:
        """Get influencer mentions of stocks."""
        influencers = list(self._influencers.values())
        
        # Filter by platform
        if platform:
            try:
                plat = VideoPlatform(platform)
                influencers = [i for i in influencers if i.platform == plat]
            except ValueError:
                pass
        
        # Filter by followers
        influencers = [i for i in influencers if i.followers >= min_followers]
        
        # Filter by symbol if specified
        if symbol:
            symbol = symbol.upper()
            influencers = [i for i in influencers if symbol in i.symbols_mentioned]
        
        # Sort by followers
        influencers.sort(key=lambda x: x.followers, reverse=True)
        
        return [i.to_dict() for i in influencers[:20]]
    
    def get_top_influencers(
        self,
        platform: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get top financial influencers."""
        influencers = list(self._influencers.values())
        
        if platform:
            try:
                plat = VideoPlatform(platform)
                influencers = [i for i in influencers if i.platform == plat]
            except ValueError:
                pass
        
        influencers.sort(key=lambda x: x.followers, reverse=True)
        
        return [i.to_dict() for i in influencers[:limit]]
    
    def get_viral_alerts(
        self,
        min_viral_score: float = 70,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get viral content alerts."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        viral = []
        for platform_content in self._content.values():
            for content in platform_content:
                if content.published_at > cutoff and content.viral_score >= min_viral_score:
                    viral.append(content)
        
        viral.sort(key=lambda x: x.viral_score, reverse=True)
        
        return [c.to_dict() for c in viral[:20]]
    
    def get_platform_summary(self) -> Dict[str, Any]:
        """Get summary across all platforms."""
        summary = {}
        
        for platform in ["youtube", "tiktok", "instagram"]:
            content = self._content.get(platform, [])
            
            if content:
                recent_24h = [c for c in content 
                            if (datetime.now(timezone.utc) - c.published_at).total_seconds() < 86400]
                
                summary[platform] = {
                    "total_content": len(content),
                    "content_24h": len(recent_24h),
                    "total_views": sum(c.views for c in content),
                    "avg_engagement_rate": sum(c.engagement_rate for c in content) / len(content) if content else 0,
                    "avg_sentiment": sum(c.sentiment_score for c in content) / len(content) if content else 0,
                    "top_symbols": self._get_top_symbols(content),
                }
            else:
                summary[platform] = {
                    "total_content": 0,
                    "content_24h": 0,
                    "total_views": 0,
                    "avg_engagement_rate": 0,
                    "avg_sentiment": 0,
                    "top_symbols": [],
                }
        
        return summary
    
    def _get_top_symbols(self, content: List[VideoContent], limit: int = 10) -> List[Dict]:
        """Get top mentioned symbols from content list."""
        symbol_counts: Dict[str, int] = defaultdict(int)
        symbol_views: Dict[str, int] = defaultdict(int)
        
        for c in content:
            for symbol in c.symbols_mentioned:
                symbol_counts[symbol] += 1
                symbol_views[symbol] += c.views
        
        sorted_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"symbol": s, "mentions": c, "total_views": symbol_views[s]}
            for s, c in sorted_symbols[:limit]
        ]
    
    def search_content(
        self,
        query: str,
        platform: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search content by keyword."""
        query_lower = query.lower()
        results = []
        
        platforms = [platform] if platform else ["youtube", "tiktok", "instagram"]
        
        for plat in platforms:
            for content in self._content.get(plat, []):
                searchable = f"{content.title} {content.description} {' '.join(content.hashtags)}".lower()
                
                if query_lower in searchable:
                    results.append(content)
        
        results.sort(key=lambda x: x.viral_score, reverse=True)
        
        return [c.to_dict() for c in results[:limit]]


# Singleton instance
_video_analyzer: Optional[VideoPlatformAnalyzer] = None


def get_video_analyzer() -> VideoPlatformAnalyzer:
    """Get or create the video platform analyzer singleton."""
    global _video_analyzer
    if _video_analyzer is None:
        _video_analyzer = VideoPlatformAnalyzer()
    return _video_analyzer


def populate_sample_video_data() -> Dict[str, int]:
    """
    Populate the video analyzer with realistic sample data.
    Returns count of content added per platform.
    """
    import random
    
    analyzer = get_video_analyzer()
    
    # Sample data for popular stock symbols
    symbols_data = {
        "NVDA": {"name": "NVIDIA", "sector": "Tech", "trend": "bullish"},
        "AAPL": {"name": "Apple", "sector": "Tech", "trend": "neutral"},
        "TSLA": {"name": "Tesla", "sector": "Auto", "trend": "volatile"},
        "MSFT": {"name": "Microsoft", "sector": "Tech", "trend": "bullish"},
        "AMD": {"name": "AMD", "sector": "Tech", "trend": "bullish"},
        "META": {"name": "Meta", "sector": "Tech", "trend": "bullish"},
        "GOOGL": {"name": "Google", "sector": "Tech", "trend": "neutral"},
        "AMZN": {"name": "Amazon", "sector": "Tech", "trend": "bullish"},
        "GME": {"name": "GameStop", "sector": "Retail", "trend": "volatile"},
        "AMC": {"name": "AMC", "sector": "Entertainment", "trend": "volatile"},
        "PLTR": {"name": "Palantir", "sector": "Tech", "trend": "bullish"},
        "COIN": {"name": "Coinbase", "sector": "Crypto", "trend": "volatile"},
        "SPY": {"name": "S&P 500 ETF", "sector": "ETF", "trend": "bullish"},
        "QQQ": {"name": "Nasdaq ETF", "sector": "ETF", "trend": "bullish"},
    }
    
    # YouTube video templates
    youtube_templates = [
        ("{symbol} Stock Analysis: Why It's Going to {direction}!",
         "In-depth technical and fundamental analysis of ${symbol}. Looking at key support and resistance levels, earnings trends, and institutional buying."),
        ("Is {symbol} a Buy Right Now? {name} Stock Deep Dive",
         "Full analysis of {name} ({symbol}) stock. We examine the financials, growth potential, and risks."),
        ("{symbol} Price Prediction 2025 - MUST WATCH Before Buying!",
         "My {symbol} price target for 2025 and beyond. Technical analysis, catalysts, and key levels to watch."),
        ("Why I'm {action} {symbol} Stock Today",
         "Here's my updated thesis on {name} stock and why I made this move in my portfolio."),
        ("{name} Earnings Review - What You Need to Know",
         "Breaking down {symbol} latest earnings report. Revenue, EPS, guidance, and what it means for investors."),
        ("{symbol} vs {alt_symbol}: Which Stock Should You Buy?",
         "Comparing these two {sector} stocks to help you make the best investment decision."),
        ("The TRUTH About {symbol} Stock Nobody's Talking About",
         "Important insights about {name} that mainstream media isn't covering. Due diligence you need to see."),
        ("{symbol} Technical Analysis: Key Levels for This Week",
         "Weekly chart analysis for ${symbol}. Support, resistance, and potential trade setups."),
    ]
    
    # TikTok video templates
    tiktok_templates = [
        ("POV: You bought ${symbol} at the dip 📈🚀",
         "This is what happens when you trust the process #stocks #{symbol} #investing"),
        ("${symbol} to the moon? 🌙 Here's why #trading",
         "Quick analysis on why {name} could explode #{symbol} #stocktok #fintok"),
        ("Day trading ${symbol} live! 💰",
         "Watch me trade {symbol} in real time #daytrading #stockmarket #trader"),
        ("${symbol} is about to {direction}... 👀",
         "You heard it here first #{symbol} #{sector}stocks #investing #alpha"),
        ("How to trade ${symbol} like a pro 📊",
         "Simple strategy that works #{symbol} #tradingstrategy #fintok"),
        ("I made $X trading ${symbol} today!",
         "Here's exactly how #{symbol} #daytrader #stocktok #gains"),
        ("Why everyone is talking about ${symbol} 🔥",
         "The hype is real #{name} #{symbol} #trending #stocks"),
    ]
    
    # Instagram templates
    instagram_templates = [
        ("📊 {symbol} Stock Watchlist Alert",
         "Adding ${symbol} to my watchlist. Key level: $XXX. What's your take? #stocks #investing #{symbol}"),
        ("🎯 {symbol} Trade Setup",
         "Looking at {name} for a potential swing trade. Risk/reward looks good. #{symbol} #trading #stockmarket"),
        ("💡 {name} Stock DD",
         "Here's why I'm watching ${symbol} closely this week. Swipe for details → #{symbol} #duediligence #stocks"),
        ("📈 Portfolio Update: {symbol}",
         "Just added more {symbol} to my position. Long term conviction play. #{symbol} #investing #portfolio"),
        ("⚠️ {symbol} Analysis",
         "Important levels to watch for {name} stock. Don't miss this move! #{symbol} #technicalanalysis"),
    ]
    
    # Influencer names
    youtube_channels = [
        ("Stock Moe", "StockMoe", 450000),
        ("Financial Education", "FinancialEducation", 1200000),
        ("Meet Kevin", "MeetKevin", 1800000),
        ("Graham Stephan", "GrahamStephan", 4500000),
        ("Andrei Jikh", "AndreiJikh", 2100000),
        ("Tom Nash", "TomNash", 380000),
        ("Everything Money", "EverythingMoney", 520000),
        ("Ticker Symbol You", "TickerSymbolYou", 290000),
    ]
    
    tiktok_creators = [
        ("StockGuru", "stockguru", 890000),
        ("TraderTom", "tradertom", 650000),
        ("FinanceWithSharan", "financewithsharan", 1200000),
        ("TashInvests", "tashinvests", 780000),
        ("StockDads", "stockdads", 450000),
    ]
    
    instagram_creators = [
        ("InvestWithJohn", "investwithjohn", 520000),
        ("StockPicksPro", "stockpickspro", 340000),
        ("WealthBuilders", "wealthbuilders", 890000),
        ("TradingMentor", "tradingmentor", 670000),
    ]
    
    counts = {"youtube": 0, "tiktok": 0, "instagram": 0}
    now = datetime.now(timezone.utc)
    
    # Generate YouTube content
    for symbol, data in symbols_data.items():
        for template in random.sample(youtube_templates, min(3, len(youtube_templates))):
            channel = random.choice(youtube_channels)
            alt_symbol = random.choice([s for s in symbols_data.keys() if s != symbol])
            direction = "UP" if random.random() > 0.3 else "DOWN"
            action = "BUYING" if direction == "UP" else "SELLING"
            
            title = template[0].format(
                symbol=symbol, name=data["name"], sector=data["sector"],
                direction=direction, action=action, alt_symbol=alt_symbol
            )
            description = template[1].format(
                symbol=symbol, name=data["name"], sector=data["sector"]
            )
            
            hours_ago = random.randint(1, 72)
            views = random.randint(5000, 500000)
            likes = int(views * random.uniform(0.02, 0.08))
            comments = int(views * random.uniform(0.001, 0.01))
            
            video_id = f"yt_{symbol.lower()}_{random.randint(1000, 9999)}"
            content = VideoContent(
                id=video_id,
                platform=VideoPlatform.YOUTUBE,
                content_type=ContentType.VIDEO,
                creator_id=channel[1],
                creator_name=channel[0],
                creator_handle=channel[1],
                creator_followers=channel[2],
                title=title,
                description=description,
                url=f"https://youtube.com/watch?v={video_id}",
                published_at=now - timedelta(hours=hours_ago),
                views=views,
                likes=likes,
                comments=comments,
                shares=int(views * random.uniform(0.001, 0.005)),
                symbols_mentioned=[symbol],
                hashtags=[f"#{symbol}", "#stocks", "#investing", f"#{data['sector'].lower()}"],
                duration_seconds=random.randint(300, 1800),
                thumbnail_url=f"https://img.youtube.com/vi/{random.randint(10000, 99999)}/maxresdefault.jpg",
            )
            analyzer.add_content(content)
            counts["youtube"] += 1
    
    # Generate TikTok content
    for symbol, data in symbols_data.items():
        for template in random.sample(tiktok_templates, min(2, len(tiktok_templates))):
            creator = random.choice(tiktok_creators)
            direction = "moon 🚀" if random.random() > 0.4 else "dip 📉"
            
            title = template[0].format(
                symbol=symbol, name=data["name"], direction=direction, sector=data["sector"]
            )
            description = template[1].format(
                symbol=symbol, name=data["name"], sector=data["sector"]
            )
            
            hours_ago = random.randint(1, 48)
            views = random.randint(10000, 2000000)
            likes = int(views * random.uniform(0.05, 0.15))
            comments = int(views * random.uniform(0.005, 0.02))
            
            video_id = f"tt_{symbol.lower()}_{random.randint(1000, 9999)}"
            content = VideoContent(
                id=video_id,
                platform=VideoPlatform.TIKTOK,
                content_type=ContentType.SHORT,
                creator_id=creator[1],
                creator_name=creator[0],
                creator_handle=creator[1],
                creator_followers=creator[2],
                title=title,
                description=description,
                url=f"https://tiktok.com/@{creator[1]}/video/{video_id}",
                published_at=now - timedelta(hours=hours_ago),
                views=views,
                likes=likes,
                comments=comments,
                shares=int(views * random.uniform(0.01, 0.05)),
                symbols_mentioned=[symbol],
                hashtags=[f"#{symbol}", "#stocktok", "#fintok", "#trading"],
                duration_seconds=random.randint(15, 180),
            )
            analyzer.add_content(content)
            counts["tiktok"] += 1
    
    # Generate Instagram content
    for symbol, data in symbols_data.items():
        for template in random.sample(instagram_templates, min(2, len(instagram_templates))):
            creator = random.choice(instagram_creators)
            
            title = template[0].format(symbol=symbol, name=data["name"])
            description = template[1].format(symbol=symbol, name=data["name"])
            
            hours_ago = random.randint(1, 72)
            views = random.randint(1000, 100000)
            likes = int(views * random.uniform(0.03, 0.12))
            comments = int(views * random.uniform(0.002, 0.01))
            
            post_id = f"ig_{symbol.lower()}_{random.randint(1000, 9999)}"
            content = VideoContent(
                id=post_id,
                platform=VideoPlatform.INSTAGRAM,
                content_type=ContentType.REEL,
                creator_id=creator[1],
                creator_name=creator[0],
                creator_handle=creator[1],
                creator_followers=creator[2],
                title=title,
                description=description,
                url=f"https://instagram.com/p/{post_id}",
                published_at=now - timedelta(hours=hours_ago),
                views=views,
                likes=likes,
                comments=comments,
                shares=int(views * random.uniform(0.005, 0.02)),
                symbols_mentioned=[symbol],
                hashtags=[f"#{symbol}", "#investing", "#stocks", "#finance"],
            )
            analyzer.add_content(content)
            counts["instagram"] += 1
    
    logger.info(f"Populated video data: {counts}")
    return counts

