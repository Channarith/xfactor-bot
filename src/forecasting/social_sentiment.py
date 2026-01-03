"""
Social Sentiment Engine

Aggregates and analyzes sentiment from multiple social media sources
to gauge market sentiment and identify emerging opportunities.

Data Sources:
- Twitter/X (via API or scraping)
- Reddit (r/wallstreetbets, r/stocks, r/investing, r/options)
- StockTwits
- Discord trading servers
- Telegram channels
- News comments
- YouTube financial channels
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta, timezone
from enum import Enum
import asyncio
import re
from collections import defaultdict

from loguru import logger


class SentimentSource(Enum):
    """Social media sentiment sources."""
    TWITTER = "twitter"
    REDDIT = "reddit"
    STOCKTWITS = "stocktwits"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    NEWS_COMMENTS = "news_comments"
    YOUTUBE = "youtube"


class SentimentLevel(Enum):
    """Sentiment classification."""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


@dataclass
class SocialPost:
    """A single social media post."""
    id: str
    source: SentimentSource
    author: str
    content: str
    timestamp: datetime
    likes: int = 0
    shares: int = 0
    comments: int = 0
    followers: int = 0              # Author's followers
    is_influencer: bool = False     # Has large following
    sentiment_score: float = 0.0    # -1 to +1
    symbols_mentioned: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    
    @property
    def engagement_score(self) -> float:
        """Calculate engagement score."""
        return (self.likes * 1 + self.shares * 3 + self.comments * 2) / max(self.followers, 1) * 1000
    
    @property
    def virality_potential(self) -> float:
        """Estimate virality potential."""
        base = self.engagement_score
        if self.is_influencer:
            base *= 2
        return min(100, base)


@dataclass
class SymbolSentiment:
    """Aggregated sentiment for a symbol."""
    symbol: str
    overall_sentiment: SentimentLevel
    sentiment_score: float           # -100 to +100
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    total_mentions: int = 0
    total_engagement: int = 0
    influencer_mentions: int = 0
    trending_score: float = 0.0      # 0-100
    momentum: str = "neutral"        # rising, falling, neutral
    sources: Dict[str, int] = field(default_factory=dict)
    top_posts: List[SocialPost] = field(default_factory=list)
    key_themes: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "overall_sentiment": self.overall_sentiment.value,
            "sentiment_score": round(self.sentiment_score, 1),
            "bullish_count": self.bullish_count,
            "bearish_count": self.bearish_count,
            "neutral_count": self.neutral_count,
            "total_mentions": self.total_mentions,
            "total_engagement": self.total_engagement,
            "influencer_mentions": self.influencer_mentions,
            "trending_score": round(self.trending_score, 1),
            "momentum": self.momentum,
            "sources": self.sources,
            "key_themes": self.key_themes,
            "last_updated": self.last_updated.isoformat(),
        }


class SocialSentimentEngine:
    """
    Aggregates social sentiment from multiple sources.
    
    Usage:
        engine = SocialSentimentEngine()
        
        # Add posts from various sources
        engine.add_post(post)
        
        # Get sentiment for a symbol
        sentiment = engine.get_sentiment("NVDA")
        
        # Get trending symbols
        trending = engine.get_trending_symbols()
    """
    
    # Sentiment keywords for basic analysis
    BULLISH_KEYWORDS = [
        "buy", "long", "calls", "moon", "rocket", "bullish", "breakout",
        "undervalued", "accumulate", "diamond hands", "hodl", "pump",
        "squeeze", "gamma", "tendies", "yolo", "all in", "to the moon",
        "parabolic", "explosive", "massive upside", "buying opportunity",
        "strong buy", "price target", "beat earnings", "upgrade",
    ]
    
    BEARISH_KEYWORDS = [
        "sell", "short", "puts", "dump", "crash", "bearish", "overvalued",
        "bubble", "scam", "fraud", "bankrupt", "dead", "avoid", "warning",
        "downgrade", "miss", "disappointed", "falling knife", "bag holder",
        "rug pull", "ponzi", "exit", "take profits", "top", "overbought",
    ]
    
    # Regex pattern for stock symbols
    SYMBOL_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')
    CASHTAG_PATTERN = re.compile(r'(?:^|\s)\$([A-Z]{1,5})(?:\s|$|[.,!?])')
    
    def __init__(self):
        self._posts: List[SocialPost] = []
        self._sentiment_cache: Dict[str, SymbolSentiment] = {}
        self._symbol_posts: Dict[str, List[SocialPost]] = defaultdict(list)
        self._last_update: Optional[datetime] = None
        
        # API clients (initialized on demand)
        self._twitter_client = None
        self._reddit_client = None
        
        # Callbacks for real-time updates
        self._callbacks: List[Callable] = []
    
    def add_post(self, post: SocialPost) -> None:
        """Add a social media post for analysis."""
        # Extract symbols if not already done
        if not post.symbols_mentioned:
            post.symbols_mentioned = self._extract_symbols(post.content)
        
        # Calculate sentiment if not set
        if post.sentiment_score == 0:
            post.sentiment_score = self._calculate_sentiment(post.content)
        
        self._posts.append(post)
        
        # Index by symbol
        for symbol in post.symbols_mentioned:
            self._symbol_posts[symbol].append(post)
            # Invalidate cache
            if symbol in self._sentiment_cache:
                del self._sentiment_cache[symbol]
        
        # Notify callbacks
        for callback in self._callbacks:
            callback(post)
    
    def _extract_symbols(self, content: str) -> List[str]:
        """Extract stock symbols from content."""
        symbols = set()
        
        # Find $SYMBOL cashtags
        for match in self.CASHTAG_PATTERN.findall(content.upper()):
            if len(match) <= 5 and match.isalpha():
                symbols.add(match)
        
        # Find $SYMBOL patterns
        for match in self.SYMBOL_PATTERN.findall(content.upper()):
            if len(match) <= 5 and match.isalpha():
                symbols.add(match)
        
        return list(symbols)
    
    def _calculate_sentiment(self, content: str) -> float:
        """
        Calculate sentiment score from content.
        Returns -1 (bearish) to +1 (bullish).
        """
        content_lower = content.lower()
        
        bullish_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in content_lower)
        bearish_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in content_lower)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0
        
        return (bullish_count - bearish_count) / total
    
    def get_sentiment(self, symbol: str) -> Optional[SymbolSentiment]:
        """
        Get aggregated sentiment for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "NVDA")
        
        Returns:
            SymbolSentiment with analysis
        """
        symbol = symbol.upper()
        
        # Check cache
        if symbol in self._sentiment_cache:
            cache = self._sentiment_cache[symbol]
            if (datetime.now(timezone.utc) - cache.last_updated).seconds < 300:  # 5 min cache
                return cache
        
        posts = self._symbol_posts.get(symbol, [])
        
        if not posts:
            return None
        
        # Aggregate metrics
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        total_engagement = 0
        influencer_mentions = 0
        sentiment_sum = 0.0
        sources: Dict[str, int] = defaultdict(int)
        
        for post in posts:
            if post.sentiment_score > 0.2:
                bullish_count += 1
            elif post.sentiment_score < -0.2:
                bearish_count += 1
            else:
                neutral_count += 1
            
            sentiment_sum += post.sentiment_score
            total_engagement += post.likes + post.shares + post.comments
            sources[post.source.value] += 1
            
            if post.is_influencer:
                influencer_mentions += 1
        
        total_mentions = len(posts)
        avg_sentiment = sentiment_sum / total_mentions if total_mentions > 0 else 0
        
        # Convert to -100 to +100 scale
        sentiment_score = avg_sentiment * 100
        
        # Determine overall sentiment
        if sentiment_score >= 40:
            overall = SentimentLevel.VERY_BULLISH
        elif sentiment_score >= 15:
            overall = SentimentLevel.BULLISH
        elif sentiment_score <= -40:
            overall = SentimentLevel.VERY_BEARISH
        elif sentiment_score <= -15:
            overall = SentimentLevel.BEARISH
        else:
            overall = SentimentLevel.NEUTRAL
        
        # Calculate trending score based on recent activity
        recent_posts = [p for p in posts 
                       if (datetime.now(timezone.utc) - p.timestamp).total_seconds() < 3600]
        trending_score = min(100, len(recent_posts) * 5 + (influencer_mentions * 10))
        
        # Calculate momentum (comparing recent to older sentiment)
        recent_sentiment = sum(p.sentiment_score for p in recent_posts) / len(recent_posts) if recent_posts else 0
        older_posts = [p for p in posts if p not in recent_posts]
        older_sentiment = sum(p.sentiment_score for p in older_posts) / len(older_posts) if older_posts else 0
        
        if recent_sentiment > older_sentiment + 0.1:
            momentum = "rising"
        elif recent_sentiment < older_sentiment - 0.1:
            momentum = "falling"
        else:
            momentum = "stable"
        
        # Extract key themes (simplified)
        all_hashtags = []
        for post in posts:
            all_hashtags.extend(post.hashtags)
        
        theme_counts = defaultdict(int)
        for tag in all_hashtags:
            theme_counts[tag] += 1
        
        key_themes = sorted(theme_counts.keys(), key=lambda x: theme_counts[x], reverse=True)[:5]
        
        # Get top posts by engagement
        top_posts = sorted(posts, key=lambda p: p.engagement_score, reverse=True)[:5]
        
        sentiment = SymbolSentiment(
            symbol=symbol,
            overall_sentiment=overall,
            sentiment_score=sentiment_score,
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            neutral_count=neutral_count,
            total_mentions=total_mentions,
            total_engagement=total_engagement,
            influencer_mentions=influencer_mentions,
            trending_score=trending_score,
            momentum=momentum,
            sources=dict(sources),
            top_posts=top_posts,
            key_themes=key_themes,
        )
        
        self._sentiment_cache[symbol] = sentiment
        return sentiment
    
    def get_trending_symbols(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get symbols with highest recent social activity.
        
        Returns:
            List of trending symbols with metrics
        """
        symbol_activity: Dict[str, Dict] = {}
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for symbol, posts in self._symbol_posts.items():
            recent_posts = [p for p in posts if p.timestamp > cutoff]
            if not recent_posts:
                continue
            
            engagement = sum(p.likes + p.shares + p.comments for p in recent_posts)
            sentiment = sum(p.sentiment_score for p in recent_posts) / len(recent_posts)
            
            symbol_activity[symbol] = {
                "symbol": symbol,
                "mentions_24h": len(recent_posts),
                "engagement_24h": engagement,
                "sentiment_score": round(sentiment * 100, 1),
                "trending_rank": 0,
            }
        
        # Sort by mentions and engagement
        sorted_symbols = sorted(
            symbol_activity.values(),
            key=lambda x: (x["mentions_24h"] * 2 + x["engagement_24h"] / 1000),
            reverse=True,
        )
        
        # Add ranks
        for i, sym in enumerate(sorted_symbols[:limit], 1):
            sym["trending_rank"] = i
        
        return sorted_symbols[:limit]
    
    def get_sentiment_movers(self, hours: int = 24) -> Dict[str, List[Dict]]:
        """
        Get symbols with biggest sentiment changes.
        
        Returns:
            Dict with "improving" and "deteriorating" lists
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        half_cutoff = datetime.now(timezone.utc) - timedelta(hours=hours // 2)
        
        movers = {"improving": [], "deteriorating": []}
        
        for symbol, posts in self._symbol_posts.items():
            recent = [p for p in posts if p.timestamp > half_cutoff]
            older = [p for p in posts if cutoff < p.timestamp <= half_cutoff]
            
            if len(recent) < 3 or len(older) < 3:
                continue
            
            recent_sent = sum(p.sentiment_score for p in recent) / len(recent)
            older_sent = sum(p.sentiment_score for p in older) / len(older)
            change = (recent_sent - older_sent) * 100
            
            if abs(change) >= 10:
                entry = {
                    "symbol": symbol,
                    "sentiment_change": round(change, 1),
                    "current_sentiment": round(recent_sent * 100, 1),
                    "previous_sentiment": round(older_sent * 100, 1),
                    "mentions": len(recent),
                }
                
                if change > 0:
                    movers["improving"].append(entry)
                else:
                    movers["deteriorating"].append(entry)
        
        # Sort by magnitude of change
        movers["improving"].sort(key=lambda x: x["sentiment_change"], reverse=True)
        movers["deteriorating"].sort(key=lambda x: x["sentiment_change"])
        
        return movers
    
    async def fetch_twitter_sentiment(self, symbols: List[str]) -> List[SocialPost]:
        """
        Fetch sentiment from Twitter/X.
        
        Note: Requires Twitter API credentials.
        """
        posts = []
        
        # This would use Twitter API v2
        # For demo, we'll generate sample data
        logger.info(f"Fetching Twitter sentiment for {len(symbols)} symbols")
        
        # Placeholder for actual API integration
        # In production, use tweepy or twitter-api-client
        
        return posts
    
    async def fetch_reddit_sentiment(
        self,
        subreddits: List[str] = None,
        limit: int = 100,
    ) -> List[SocialPost]:
        """
        Fetch sentiment from Reddit.
        
        Default subreddits: wallstreetbets, stocks, investing, options
        """
        subreddits = subreddits or ["wallstreetbets", "stocks", "investing", "options"]
        posts = []
        
        try:
            import praw
            
            # Initialize Reddit client if not exists
            if not self._reddit_client:
                # Would need credentials from config
                logger.warning("Reddit client not configured")
                return posts
            
            for subreddit_name in subreddits:
                try:
                    subreddit = self._reddit_client.subreddit(subreddit_name)
                    
                    for submission in subreddit.hot(limit=limit):
                        symbols = self._extract_symbols(submission.title + " " + submission.selftext)
                        
                        if symbols:
                            post = SocialPost(
                                id=submission.id,
                                source=SentimentSource.REDDIT,
                                author=str(submission.author),
                                content=submission.title + "\n" + submission.selftext[:500],
                                timestamp=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                                likes=submission.score,
                                comments=submission.num_comments,
                                symbols_mentioned=symbols,
                            )
                            post.sentiment_score = self._calculate_sentiment(post.content)
                            posts.append(post)
                            
                except Exception as e:
                    logger.warning(f"Error fetching r/{subreddit_name}: {e}")
            
        except ImportError:
            logger.warning("praw not installed. Run: pip install praw")
        
        return posts
    
    def on_new_post(self, callback: Callable[[SocialPost], None]) -> None:
        """Register callback for new posts."""
        self._callbacks.append(callback)
    
    # =========================================================================
    # MOMENTUM INTEGRATION METHODS
    # =========================================================================
    
    async def get_top_trending(self, count: int = 12) -> List[dict]:
        """
        Get top trending symbols by mention count.
        
        Returns symbols with highest social media mentions in last 24h.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        
        # Count mentions per symbol
        mention_counts: Dict[str, int] = defaultdict(int)
        sentiment_totals: Dict[str, float] = defaultdict(float)
        
        for post in self._posts:
            if post.timestamp >= cutoff:
                for symbol in post.symbols_mentioned:
                    mention_counts[symbol] += 1
                    sentiment_totals[symbol] += post.sentiment_score
        
        # Build trending list
        trending = []
        for symbol, count_val in mention_counts.items():
            avg_sentiment = sentiment_totals[symbol] / count_val if count_val > 0 else 0
            trending.append({
                "symbol": symbol,
                "mentions": count_val,
                "avg_sentiment": round(avg_sentiment, 2),
                "buzz_score": min(count_val * 5, 100),  # Scale to 0-100
            })
        
        # Sort by mentions
        trending.sort(key=lambda x: x["mentions"], reverse=True)
        
        return trending[:count]
    
    async def get_viral_stocks(self, min_buzz_score: float = 80) -> List[dict]:
        """
        Get stocks with viral buzz (high mention velocity).
        
        Viral = rapid increase in mentions compared to baseline.
        """
        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(hours=6)
        baseline_cutoff = now - timedelta(hours=24)
        
        # Count recent vs baseline mentions
        recent_counts: Dict[str, int] = defaultdict(int)
        baseline_counts: Dict[str, int] = defaultdict(int)
        
        for post in self._posts:
            for symbol in post.symbols_mentioned:
                if post.timestamp >= recent_cutoff:
                    recent_counts[symbol] += 1
                elif post.timestamp >= baseline_cutoff:
                    baseline_counts[symbol] += 1
        
        viral = []
        for symbol in set(recent_counts.keys()) | set(baseline_counts.keys()):
            recent = recent_counts[symbol]
            baseline = max(baseline_counts[symbol], 1)  # Avoid division by zero
            
            # Viral ratio: how many times more mentions vs baseline
            viral_ratio = recent / baseline
            
            # Calculate viral score
            viral_score = min(viral_ratio * 20, 100)
            
            if viral_score >= min_buzz_score:
                viral.append({
                    "symbol": symbol,
                    "recent_mentions": recent,
                    "baseline_mentions": baseline_counts[symbol],
                    "viral_ratio": round(viral_ratio, 2),
                    "viral_score": round(viral_score, 1),
                })
        
        viral.sort(key=lambda x: x["viral_score"], reverse=True)
        return viral
    
    async def get_influencer_picks(self, min_followers: int = 10000) -> List[dict]:
        """
        Get stocks mentioned by high-follower accounts.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=48)
        
        influencer_picks: Dict[str, List[dict]] = defaultdict(list)
        
        for post in self._posts:
            if post.timestamp >= cutoff and post.is_influencer and post.followers >= min_followers:
                for symbol in post.symbols_mentioned:
                    influencer_picks[symbol].append({
                        "author": post.author,
                        "followers": post.followers,
                        "sentiment": post.sentiment_score,
                        "source": post.source.value,
                    })
        
        results = []
        for symbol, picks in influencer_picks.items():
            total_reach = sum(p["followers"] for p in picks)
            avg_sentiment = sum(p["sentiment"] for p in picks) / len(picks) if picks else 0
            
            results.append({
                "symbol": symbol,
                "influencer_count": len(picks),
                "total_reach": total_reach,
                "avg_sentiment": round(avg_sentiment, 2),
                "influencer_score": min(len(picks) * 20, 100),
                "top_influencers": picks[:5],
            })
        
        results.sort(key=lambda x: x["total_reach"], reverse=True)
        return results
    
    async def get_symbol_sentiment(self, symbol: str) -> Optional[dict]:
        """Get aggregated sentiment data for a specific symbol."""
        symbol = symbol.upper()
        symbol_posts = [p for p in self._posts if symbol in p.symbols_mentioned]
        
        if not symbol_posts:
            return None
        
        now = datetime.now(timezone.utc)
        cutoff_24h = now - timedelta(hours=24)
        recent_posts = [p for p in symbol_posts if p.timestamp >= cutoff_24h]
        
        if not recent_posts:
            return None
        
        mentions = len(recent_posts)
        avg_sentiment = sum(p.sentiment_score for p in recent_posts) / mentions
        influencer_mentions = sum(1 for p in recent_posts if p.is_influencer)
        total_engagement = sum(p.likes + p.shares + p.comments for p in recent_posts)
        
        return {
            "symbol": symbol,
            "mentions_24h": mentions,
            "avg_sentiment": avg_sentiment,
            "buzz_score": min(mentions * 5, 100),
            "viral_score": min((mentions / max(len(symbol_posts) / 24, 1)) * 20, 100),
            "influencer_score": min(influencer_mentions * 20, 100),
            "total_engagement": total_engagement,
        }
    
    async def get_momentum_scores(self) -> Dict[str, dict]:
        """Get momentum scores for all tracked symbols."""
        scores = {}
        
        all_symbols = set()
        for post in self._posts:
            all_symbols.update(post.symbols_mentioned)
        
        for symbol in all_symbols:
            data = await self.get_symbol_sentiment(symbol)
            if data:
                scores[symbol] = data
        
        return scores


# Singleton instance
_sentiment_engine: Optional[SocialSentimentEngine] = None


def get_social_sentiment() -> SocialSentimentEngine:
    """Get or create the social sentiment engine singleton."""
    global _sentiment_engine
    if _sentiment_engine is None:
        _sentiment_engine = SocialSentimentEngine()
    return _sentiment_engine


# Alias for momentum screener compatibility
def get_social_sentiment_engine() -> SocialSentimentEngine:
    """Alias for get_social_sentiment()."""
    return get_social_sentiment()

