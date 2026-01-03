"""
Momentum Screener - Unified momentum scoring and ranking system.

Combines multiple momentum factors:
- Price momentum (ROC, trend strength)
- Volume momentum (volume ratio, surge detection)
- Social momentum (buzz score, viral potential)
- News momentum (article count, sentiment)

Provides:
- Composite momentum scores (0-100)
- Sector rankings
- Overall rankings
- Filtering and search
"""

import asyncio
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from loguru import logger


class MomentumType(str, Enum):
    """Types of momentum signals."""
    PRICE = "price"
    VOLUME = "volume"
    SOCIAL = "social"
    NEWS = "news"
    COMPOSITE = "composite"


@dataclass
class MomentumScore:
    """Unified momentum score for a symbol."""
    symbol: str
    sector: str
    
    # Price momentum (0-100)
    price_momentum: float = 0.0
    price_change_pct: float = 0.0
    
    # Volume momentum (0-100)
    volume_momentum: float = 0.0
    volume_ratio: float = 0.0
    
    # Social momentum (0-100)
    social_buzz: float = 0.0
    viral_score: float = 0.0
    influencer_score: float = 0.0
    
    # News momentum (0-100)
    news_volume: float = 0.0
    news_sentiment: float = 0.0
    
    # Composite score (weighted average)
    composite_score: float = 0.0
    
    # Rankings
    sector_rank: int = 0
    overall_rank: int = 0
    
    # Metadata
    tier: str = ""  # hot_100, active_1000, full_universe
    timestamp: Optional[str] = None
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result["timestamp"] = self.timestamp or datetime.now().isoformat()
        return result
    
    @classmethod
    def from_scan_result(cls, scan_result, sector: str = "") -> "MomentumScore":
        """Create MomentumScore from a ScanResult."""
        return cls(
            symbol=scan_result.symbol,
            sector=sector or scan_result.sector,
            price_momentum=scan_result.momentum_score,
            price_change_pct=scan_result.price_change_pct,
            volume_momentum=min(scan_result.volume_ratio * 25, 100),  # Scale volume ratio
            volume_ratio=scan_result.volume_ratio,
            tier=scan_result.tier,
            timestamp=scan_result.timestamp,
        )


# Default weights for composite score
DEFAULT_WEIGHTS = {
    "price": 0.40,    # 40% price momentum
    "volume": 0.20,   # 20% volume
    "social": 0.20,   # 20% social
    "news": 0.20,     # 20% news
}


class MomentumScreener:
    """
    Unified momentum screening and ranking system.
    
    Queries cached scan results and combines with social/news data
    to produce composite momentum scores.
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self._weights = weights or DEFAULT_WEIGHTS.copy()
        self._lock = threading.Lock()
        
        # Cached rankings
        self._rankings: List[MomentumScore] = []
        self._by_sector: Dict[str, List[MomentumScore]] = {}
        self._last_update: Optional[datetime] = None
        
        logger.info("MomentumScreener initialized")
    
    def set_weights(self, weights: Dict[str, float]) -> None:
        """Set custom weights for composite scoring."""
        self._weights = weights
    
    async def refresh_rankings(self) -> None:
        """Refresh rankings from scan results and external data."""
        from src.data.universe_scanner import get_universe_scanner
        from src.data.sectors import find_sector_for_symbol
        
        scanner = get_universe_scanner()
        
        # Get best available scan results
        scan_results = scanner.get_hot_100() or scanner.get_active_1000() or scanner.get_full_universe()
        
        if not scan_results:
            logger.warning("No scan results available for momentum ranking")
            return
        
        # Convert to MomentumScores
        scores = []
        for result in scan_results:
            sector = find_sector_for_symbol(result.symbol) or ""
            score = MomentumScore.from_scan_result(result, sector)
            
            # Add social momentum (from social sentiment if available)
            social_data = await self._get_social_momentum(result.symbol)
            if social_data:
                score.social_buzz = social_data.get("buzz_score", 0)
                score.viral_score = social_data.get("viral_score", 0)
                score.influencer_score = social_data.get("influencer_score", 0)
            
            # Add news momentum
            news_data = await self._get_news_momentum(result.symbol)
            if news_data:
                score.news_volume = news_data.get("volume_score", 0)
                score.news_sentiment = news_data.get("sentiment_score", 0)
            
            # Calculate composite score
            score.composite_score = self._calculate_composite(score)
            
            scores.append(score)
        
        # Sort by composite score
        scores.sort(key=lambda x: x.composite_score, reverse=True)
        
        # Assign overall rankings
        for i, score in enumerate(scores):
            score.overall_rank = i + 1
        
        # Group by sector and assign sector rankings
        by_sector: Dict[str, List[MomentumScore]] = {}
        for score in scores:
            if score.sector:
                if score.sector not in by_sector:
                    by_sector[score.sector] = []
                by_sector[score.sector].append(score)
        
        for sector_scores in by_sector.values():
            sector_scores.sort(key=lambda x: x.composite_score, reverse=True)
            for i, score in enumerate(sector_scores):
                score.sector_rank = i + 1
        
        # Update cache
        with self._lock:
            self._rankings = scores
            self._by_sector = by_sector
            self._last_update = datetime.now()
        
        logger.info(f"Momentum rankings refreshed: {len(scores)} symbols, {len(by_sector)} sectors")
    
    async def _get_social_momentum(self, symbol: str) -> Optional[Dict]:
        """Get social momentum data for a symbol."""
        try:
            from src.forecasting.social_sentiment import get_social_sentiment_engine
            
            engine = get_social_sentiment_engine()
            sentiment = await engine.get_symbol_sentiment(symbol)
            
            if sentiment:
                return {
                    "buzz_score": getattr(sentiment, 'buzz_score', 0),
                    "viral_score": getattr(sentiment, 'viral_score', 0),
                    "influencer_score": getattr(sentiment, 'influencer_score', 0),
                }
        except Exception as e:
            logger.debug(f"Could not get social momentum for {symbol}: {e}")
        
        return None
    
    async def _get_news_momentum(self, symbol: str) -> Optional[Dict]:
        """Get news momentum data for a symbol."""
        try:
            from src.data.news_momentum import get_news_momentum
            
            news = get_news_momentum()
            data = await news.get_symbol_momentum(symbol)
            
            if data:
                return {
                    "volume_score": data.get("volume_score", 0),
                    "sentiment_score": data.get("sentiment_score", 0),
                }
        except Exception as e:
            logger.debug(f"Could not get news momentum for {symbol}: {e}")
        
        return None
    
    def _calculate_composite(self, score: MomentumScore) -> float:
        """Calculate weighted composite momentum score."""
        # Price component
        price_component = score.price_momentum * self._weights.get("price", 0.4)
        
        # Volume component
        volume_component = score.volume_momentum * self._weights.get("volume", 0.2)
        
        # Social component (average of buzz, viral, influencer)
        social_avg = (score.social_buzz + score.viral_score + score.influencer_score) / 3
        social_component = social_avg * self._weights.get("social", 0.2)
        
        # News component (average of volume and sentiment)
        news_avg = (score.news_volume + (score.news_sentiment * 50 + 50)) / 2  # Normalize sentiment
        news_component = news_avg * self._weights.get("news", 0.2)
        
        composite = price_component + volume_component + social_component + news_component
        
        return max(0, min(100, composite))
    
    def get_top(self, count: int = 12) -> List[MomentumScore]:
        """Get top N stocks by composite momentum score."""
        with self._lock:
            return self._rankings[:count]
    
    def get_top_by_sector(self, sector: str, count: int = 12) -> List[MomentumScore]:
        """Get top N stocks in a specific sector."""
        with self._lock:
            sector_scores = self._by_sector.get(sector, [])
            return sector_scores[:count]
    
    def get_top_by_type(self, momentum_type: MomentumType, count: int = 12) -> List[MomentumScore]:
        """Get top N stocks by a specific momentum type."""
        with self._lock:
            if momentum_type == MomentumType.PRICE:
                sorted_scores = sorted(self._rankings, key=lambda x: x.price_momentum, reverse=True)
            elif momentum_type == MomentumType.VOLUME:
                sorted_scores = sorted(self._rankings, key=lambda x: x.volume_momentum, reverse=True)
            elif momentum_type == MomentumType.SOCIAL:
                sorted_scores = sorted(self._rankings, key=lambda x: x.social_buzz, reverse=True)
            elif momentum_type == MomentumType.NEWS:
                sorted_scores = sorted(self._rankings, key=lambda x: x.news_volume, reverse=True)
            else:
                sorted_scores = self._rankings
            
            return sorted_scores[:count]
    
    def get_sector_heatmap(self) -> Dict[str, float]:
        """Get average momentum score per sector (for heatmap)."""
        with self._lock:
            heatmap = {}
            for sector, scores in self._by_sector.items():
                if scores:
                    avg_score = sum(s.composite_score for s in scores) / len(scores)
                    heatmap[sector] = round(avg_score, 1)
            return dict(sorted(heatmap.items(), key=lambda x: x[1], reverse=True))
    
    def get_sector_leaders(self, count_per_sector: int = 3) -> Dict[str, List[MomentumScore]]:
        """Get top N leaders from each sector."""
        with self._lock:
            leaders = {}
            for sector, scores in self._by_sector.items():
                leaders[sector] = scores[:count_per_sector]
            return leaders
    
    def search(
        self,
        sector: Optional[str] = None,
        min_score: float = 0,
        min_price_momentum: float = 0,
        min_volume_ratio: float = 0,
        limit: int = 50,
    ) -> List[MomentumScore]:
        """Search/filter momentum scores."""
        with self._lock:
            results = self._rankings.copy()
        
        # Apply filters
        if sector:
            results = [r for r in results if r.sector == sector]
        
        if min_score > 0:
            results = [r for r in results if r.composite_score >= min_score]
        
        if min_price_momentum > 0:
            results = [r for r in results if r.price_momentum >= min_price_momentum]
        
        if min_volume_ratio > 0:
            results = [r for r in results if r.volume_ratio >= min_volume_ratio]
        
        return results[:limit]
    
    def get_symbol_score(self, symbol: str) -> Optional[MomentumScore]:
        """Get momentum score for a specific symbol."""
        with self._lock:
            for score in self._rankings:
                if score.symbol.upper() == symbol.upper():
                    return score
        return None
    
    def get_status(self) -> dict:
        """Get screener status."""
        with self._lock:
            return {
                "total_symbols": len(self._rankings),
                "sectors_count": len(self._by_sector),
                "last_update": self._last_update.isoformat() if self._last_update else None,
                "weights": self._weights,
            }
    
    def get_leaderboard(self, count: int = 20) -> List[dict]:
        """Get leaderboard data for display."""
        top_scores = self.get_top(count)
        return [
            {
                "rank": score.overall_rank,
                "symbol": score.symbol,
                "sector": score.sector,
                "composite_score": round(score.composite_score, 1),
                "price_momentum": round(score.price_momentum, 1),
                "volume_ratio": round(score.volume_ratio, 2),
                "social_buzz": round(score.social_buzz, 1),
                "price_change_pct": round(score.price_change_pct, 2),
            }
            for score in top_scores
        ]


# Global instance
_screener: Optional[MomentumScreener] = None
_screener_lock = threading.Lock()


def get_momentum_screener() -> MomentumScreener:
    """Get the global momentum screener instance."""
    global _screener
    
    with _screener_lock:
        if _screener is None:
            _screener = MomentumScreener()
        return _screener

