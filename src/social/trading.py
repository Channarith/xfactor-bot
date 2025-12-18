"""
Social Trading Module

Enables users to share, copy, and follow successful trading strategies.
Similar to platforms like eToro's CopyTrader or ZuluTrade.

Features:
- Strategy sharing and marketplace
- Copy trading (mirror trades)
- Leaderboard of top performers
- Strategy ratings and reviews
- Performance tracking
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import hashlib

from loguru import logger


class PrivacyLevel(Enum):
    """Strategy sharing privacy levels."""
    PRIVATE = "private"      # Only owner can see
    FOLLOWERS = "followers"  # Only followers can see
    PUBLIC = "public"        # Everyone can see
    PREMIUM = "premium"      # Paid access


class CopyMode(Enum):
    """How to copy trades from a strategy."""
    MIRROR = "mirror"        # Copy exact trades
    SCALED = "scaled"        # Scale by factor
    SIGNALS = "signals"      # Get signals, execute manually


@dataclass
class StrategyPerformance:
    """Performance metrics for a shared strategy."""
    total_return_pct: float = 0.0
    monthly_return_pct: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    total_trades: int = 0
    avg_trade_duration_hours: float = 0.0
    profit_factor: float = 0.0
    
    # Time-based returns
    return_1d: float = 0.0
    return_7d: float = 0.0
    return_30d: float = 0.0
    return_90d: float = 0.0
    return_1y: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0


@dataclass
class SharedStrategy:
    """A strategy shared on the social trading platform."""
    id: str
    owner_id: str
    owner_name: str
    name: str
    description: str
    strategy_type: str
    privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    
    # Performance
    performance: StrategyPerformance = field(default_factory=StrategyPerformance)
    
    # Social metrics
    followers_count: int = 0
    copiers_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    asset_classes: List[str] = field(default_factory=list)
    risk_level: str = "moderate"
    min_capital: float = 1000.0
    
    # Trading info
    avg_trades_per_day: float = 0.0
    typical_holding_period: str = "days"
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type,
            "privacy": self.privacy.value,
            "performance": {
                "total_return_pct": self.performance.total_return_pct,
                "monthly_return_pct": self.performance.monthly_return_pct,
                "win_rate": self.performance.win_rate,
                "sharpe_ratio": self.performance.sharpe_ratio,
                "max_drawdown_pct": self.performance.max_drawdown_pct,
                "total_trades": self.performance.total_trades,
                "return_30d": self.performance.return_30d,
            },
            "followers_count": self.followers_count,
            "copiers_count": self.copiers_count,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "tags": self.tags,
            "asset_classes": self.asset_classes,
            "risk_level": self.risk_level,
            "min_capital": self.min_capital,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CopyRelationship:
    """Relationship between a copier and a strategy."""
    id: str
    copier_id: str
    strategy_id: str
    copy_mode: CopyMode
    scale_factor: float = 1.0
    max_position_size: float = 1000.0
    is_active: bool = True
    started_at: datetime = field(default_factory=datetime.now)
    
    # Performance since copying
    pnl_since_copy: float = 0.0
    trades_copied: int = 0


@dataclass
class StrategyReview:
    """User review of a strategy."""
    id: str
    user_id: str
    user_name: str
    strategy_id: str
    rating: int  # 1-5 stars
    comment: str
    created_at: datetime = field(default_factory=datetime.now)
    helpful_count: int = 0


class SocialTradingPlatform:
    """
    Social trading platform for strategy sharing and copying.
    
    Usage:
        platform = SocialTradingPlatform()
        strategy = platform.share_strategy(user_id, strategy_config)
        platform.follow_strategy(follower_id, strategy.id)
        top_strategies = platform.get_leaderboard()
    """
    
    def __init__(self):
        self._strategies: Dict[str, SharedStrategy] = {}
        self._copy_relationships: Dict[str, CopyRelationship] = {}
        self._reviews: Dict[str, List[StrategyReview]] = {}
        self._followers: Dict[str, List[str]] = {}  # strategy_id -> [user_ids]
        
        # Initialize with some sample strategies for demo
        self._init_sample_strategies()
    
    def _init_sample_strategies(self):
        """Initialize with sample strategies for demo."""
        samples = [
            SharedStrategy(
                id="sample_1",
                owner_id="demo_user",
                owner_name="TrendMaster",
                name="Golden Cross Rider",
                description="Classic trend following using 50/200 EMA crossovers. Trades major stocks and ETFs.",
                strategy_type="trend_following",
                performance=StrategyPerformance(
                    total_return_pct=47.5,
                    monthly_return_pct=3.2,
                    win_rate=45.0,
                    sharpe_ratio=1.8,
                    max_drawdown_pct=12.5,
                    total_trades=156,
                    return_30d=5.2,
                ),
                followers_count=234,
                copiers_count=89,
                rating=4.5,
                rating_count=45,
                tags=["trend", "ema", "swing"],
                asset_classes=["stocks", "etf"],
                risk_level="moderate",
            ),
            SharedStrategy(
                id="sample_2",
                owner_id="demo_user_2",
                owner_name="ScalpKing",
                name="Intraday RSI Scalper",
                description="High-frequency scalping using RSI divergences. Targets 0.3-0.5% moves.",
                strategy_type="scalping",
                performance=StrategyPerformance(
                    total_return_pct=78.3,
                    monthly_return_pct=5.8,
                    win_rate=62.0,
                    sharpe_ratio=2.1,
                    max_drawdown_pct=8.2,
                    total_trades=1250,
                    return_30d=8.1,
                ),
                followers_count=567,
                copiers_count=201,
                rating=4.8,
                rating_count=112,
                tags=["scalping", "rsi", "intraday"],
                asset_classes=["stocks", "futures"],
                risk_level="aggressive",
            ),
            SharedStrategy(
                id="sample_3",
                owner_id="demo_user_3",
                owner_name="CryptoWhale",
                name="BTC Mean Reversion",
                description="Mean reversion strategy for Bitcoin using Bollinger Bands and volume profile.",
                strategy_type="mean_reversion",
                performance=StrategyPerformance(
                    total_return_pct=125.0,
                    monthly_return_pct=8.5,
                    win_rate=58.0,
                    sharpe_ratio=1.5,
                    max_drawdown_pct=22.0,
                    total_trades=89,
                    return_30d=12.3,
                ),
                followers_count=1234,
                copiers_count=456,
                rating=4.2,
                rating_count=89,
                tags=["crypto", "bitcoin", "mean-reversion"],
                asset_classes=["crypto"],
                risk_level="aggressive",
            ),
        ]
        
        for strategy in samples:
            self._strategies[strategy.id] = strategy
    
    def share_strategy(
        self,
        owner_id: str,
        owner_name: str,
        name: str,
        description: str,
        strategy_type: str,
        privacy: PrivacyLevel = PrivacyLevel.PUBLIC,
        tags: List[str] = None,
        asset_classes: List[str] = None,
    ) -> SharedStrategy:
        """
        Share a strategy on the platform.
        
        Args:
            owner_id: User ID of the strategy owner
            owner_name: Display name of the owner
            name: Strategy name
            description: Strategy description
            strategy_type: Type of strategy
            privacy: Privacy level
            tags: Strategy tags
            asset_classes: Supported asset classes
        
        Returns:
            Created SharedStrategy
        """
        strategy_id = str(uuid.uuid4())
        
        strategy = SharedStrategy(
            id=strategy_id,
            owner_id=owner_id,
            owner_name=owner_name,
            name=name,
            description=description,
            strategy_type=strategy_type,
            privacy=privacy,
            tags=tags or [],
            asset_classes=asset_classes or [],
        )
        
        self._strategies[strategy_id] = strategy
        self._followers[strategy_id] = []
        self._reviews[strategy_id] = []
        
        logger.info(f"Strategy shared: {name} by {owner_name}")
        return strategy
    
    def get_strategy(self, strategy_id: str) -> Optional[SharedStrategy]:
        """Get a strategy by ID."""
        return self._strategies.get(strategy_id)
    
    def list_strategies(
        self,
        strategy_type: Optional[str] = None,
        asset_class: Optional[str] = None,
        risk_level: Optional[str] = None,
        min_return: Optional[float] = None,
        sort_by: str = "rating",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List and filter strategies.
        
        Args:
            strategy_type: Filter by strategy type
            asset_class: Filter by asset class
            risk_level: Filter by risk level
            min_return: Minimum total return percentage
            sort_by: Sort field (rating, return, followers, copiers)
            limit: Maximum results
        
        Returns:
            List of strategy dictionaries
        """
        strategies = list(self._strategies.values())
        
        # Apply filters
        if strategy_type:
            strategies = [s for s in strategies if s.strategy_type == strategy_type]
        if asset_class:
            strategies = [s for s in strategies if asset_class in s.asset_classes]
        if risk_level:
            strategies = [s for s in strategies if s.risk_level == risk_level]
        if min_return is not None:
            strategies = [s for s in strategies if s.performance.total_return_pct >= min_return]
        
        # Filter out private strategies
        strategies = [s for s in strategies if s.privacy != PrivacyLevel.PRIVATE]
        
        # Sort
        sort_fields = {
            "rating": lambda s: s.rating,
            "return": lambda s: s.performance.total_return_pct,
            "followers": lambda s: s.followers_count,
            "copiers": lambda s: s.copiers_count,
            "win_rate": lambda s: s.performance.win_rate,
            "sharpe": lambda s: s.performance.sharpe_ratio,
        }
        
        sort_func = sort_fields.get(sort_by, sort_fields["rating"])
        strategies.sort(key=sort_func, reverse=True)
        
        return [s.to_dict() for s in strategies[:limit]]
    
    def get_leaderboard(
        self,
        period: str = "30d",
        asset_class: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get top performing strategies.
        
        Args:
            period: Time period (1d, 7d, 30d, 90d, 1y, all)
            asset_class: Filter by asset class
            limit: Number of results
        
        Returns:
            Leaderboard with rankings
        """
        strategies = list(self._strategies.values())
        
        if asset_class:
            strategies = [s for s in strategies if asset_class in s.asset_classes]
        
        strategies = [s for s in strategies if s.privacy != PrivacyLevel.PRIVATE]
        
        # Sort by return for the period
        period_map = {
            "1d": lambda s: s.performance.return_1d,
            "7d": lambda s: s.performance.return_7d,
            "30d": lambda s: s.performance.return_30d,
            "90d": lambda s: s.performance.return_90d,
            "1y": lambda s: s.performance.return_1y,
            "all": lambda s: s.performance.total_return_pct,
        }
        
        sort_func = period_map.get(period, period_map["30d"])
        strategies.sort(key=sort_func, reverse=True)
        
        leaderboard = []
        for rank, strategy in enumerate(strategies[:limit], 1):
            entry = strategy.to_dict()
            entry["rank"] = rank
            entry["period_return"] = sort_func(strategy)
            leaderboard.append(entry)
        
        return leaderboard
    
    def follow_strategy(self, user_id: str, strategy_id: str) -> bool:
        """Follow a strategy to receive updates."""
        if strategy_id not in self._strategies:
            return False
        
        if strategy_id not in self._followers:
            self._followers[strategy_id] = []
        
        if user_id not in self._followers[strategy_id]:
            self._followers[strategy_id].append(user_id)
            self._strategies[strategy_id].followers_count += 1
            logger.info(f"User {user_id} followed strategy {strategy_id}")
            return True
        
        return False
    
    def unfollow_strategy(self, user_id: str, strategy_id: str) -> bool:
        """Unfollow a strategy."""
        if strategy_id in self._followers and user_id in self._followers[strategy_id]:
            self._followers[strategy_id].remove(user_id)
            self._strategies[strategy_id].followers_count -= 1
            return True
        return False
    
    def start_copying(
        self,
        copier_id: str,
        strategy_id: str,
        copy_mode: CopyMode = CopyMode.SCALED,
        scale_factor: float = 1.0,
        max_position_size: float = 1000.0,
    ) -> Optional[CopyRelationship]:
        """
        Start copying a strategy.
        
        Args:
            copier_id: User ID of the copier
            strategy_id: Strategy to copy
            copy_mode: How to copy (mirror, scaled, signals)
            scale_factor: Position scaling factor
            max_position_size: Maximum position size
        
        Returns:
            CopyRelationship if successful
        """
        if strategy_id not in self._strategies:
            return None
        
        relationship_id = f"{copier_id}_{strategy_id}"
        
        relationship = CopyRelationship(
            id=relationship_id,
            copier_id=copier_id,
            strategy_id=strategy_id,
            copy_mode=copy_mode,
            scale_factor=scale_factor,
            max_position_size=max_position_size,
        )
        
        self._copy_relationships[relationship_id] = relationship
        self._strategies[strategy_id].copiers_count += 1
        
        logger.info(f"User {copier_id} started copying strategy {strategy_id}")
        return relationship
    
    def stop_copying(self, copier_id: str, strategy_id: str) -> bool:
        """Stop copying a strategy."""
        relationship_id = f"{copier_id}_{strategy_id}"
        
        if relationship_id in self._copy_relationships:
            self._copy_relationships[relationship_id].is_active = False
            self._strategies[strategy_id].copiers_count -= 1
            return True
        return False
    
    def add_review(
        self,
        user_id: str,
        user_name: str,
        strategy_id: str,
        rating: int,
        comment: str,
    ) -> Optional[StrategyReview]:
        """Add a review to a strategy."""
        if strategy_id not in self._strategies:
            return None
        
        if rating < 1 or rating > 5:
            return None
        
        review = StrategyReview(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_name=user_name,
            strategy_id=strategy_id,
            rating=rating,
            comment=comment,
        )
        
        if strategy_id not in self._reviews:
            self._reviews[strategy_id] = []
        
        self._reviews[strategy_id].append(review)
        
        # Update strategy rating
        strategy = self._strategies[strategy_id]
        all_ratings = [r.rating for r in self._reviews[strategy_id]]
        strategy.rating = sum(all_ratings) / len(all_ratings)
        strategy.rating_count = len(all_ratings)
        
        return review
    
    def get_reviews(self, strategy_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get reviews for a strategy."""
        reviews = self._reviews.get(strategy_id, [])
        
        return [
            {
                "id": r.id,
                "user_name": r.user_name,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
                "helpful_count": r.helpful_count,
            }
            for r in sorted(reviews, key=lambda r: r.created_at, reverse=True)[:limit]
        ]
    
    def search_strategies(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search strategies by name, description, or tags."""
        query = query.lower()
        results = []
        
        for strategy in self._strategies.values():
            if strategy.privacy == PrivacyLevel.PRIVATE:
                continue
            
            if (query in strategy.name.lower() or
                query in strategy.description.lower() or
                any(query in tag for tag in strategy.tags)):
                results.append(strategy.to_dict())
        
        return results[:limit]


# Singleton instance
_platform: Optional[SocialTradingPlatform] = None


def get_social_trading_platform() -> SocialTradingPlatform:
    """Get or create the social trading platform singleton."""
    global _platform
    if _platform is None:
        _platform = SocialTradingPlatform()
    return _platform

