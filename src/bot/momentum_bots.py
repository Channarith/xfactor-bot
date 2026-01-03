"""
Momentum Bot Templates - Specialized bots for momentum-based trading.

Four bot templates that auto-select from cached momentum rankings:

1. Sector Rotation Bot
   - Rotates into top stocks from hottest sectors
   - Rebalances daily at market open
   
2. Social Momentum Bot
   - Trades viral/trending stocks from social data
   - Quick entries on buzz spikes
   
3. News Momentum Bot
   - Trades on news volume and sentiment spikes
   - Catalyst-driven entries
   
4. Composite Momentum Bot
   - Combines all momentum signals
   - Only trades when multiple signals align
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set
from enum import Enum
import asyncio

from loguru import logger

from src.bot.bot_instance import BotConfig, BotInstance, BotStatus, InstrumentType


class MomentumBotType(str, Enum):
    """Types of momentum bots."""
    SECTOR_ROTATION = "sector_rotation"
    SOCIAL_MOMENTUM = "social_momentum"
    NEWS_MOMENTUM = "news_momentum"
    COMPOSITE_MOMENTUM = "composite_momentum"


@dataclass
class MomentumBotConfig:
    """Configuration specific to momentum bots."""
    bot_type: MomentumBotType
    
    # Common settings
    max_positions: int = 10
    position_size_pct: float = 10.0  # % of portfolio per position
    rebalance_frequency: str = "daily"  # hourly, daily, weekly
    
    # Entry/exit thresholds
    min_momentum_score: float = 70.0  # Minimum score to enter
    exit_score_threshold: float = 40.0  # Exit when score drops below
    
    # Sector Rotation specific
    sectors_to_trade: int = 3  # Trade top N sectors
    stocks_per_sector: int = 3  # Top N stocks from each sector
    
    # Social Momentum specific
    min_buzz_score: float = 70.0
    viral_only: bool = False  # Only trade viral stocks
    max_hold_hours: int = 48  # Quick trades
    
    # News Momentum specific
    min_news_score: float = 60.0
    positive_sentiment_only: bool = True
    catalyst_types: List[str] = field(default_factory=list)  # earnings, fda, etc.
    
    # Composite specific
    require_all_signals: bool = True  # Require price + social + news
    min_composite_score: float = 80.0
    
    def to_dict(self) -> dict:
        return {
            "bot_type": self.bot_type.value,
            "max_positions": self.max_positions,
            "position_size_pct": self.position_size_pct,
            "rebalance_frequency": self.rebalance_frequency,
            "min_momentum_score": self.min_momentum_score,
            "exit_score_threshold": self.exit_score_threshold,
            "sectors_to_trade": self.sectors_to_trade,
            "stocks_per_sector": self.stocks_per_sector,
            "min_buzz_score": self.min_buzz_score,
            "viral_only": self.viral_only,
            "max_hold_hours": self.max_hold_hours,
            "min_news_score": self.min_news_score,
            "positive_sentiment_only": self.positive_sentiment_only,
            "catalyst_types": self.catalyst_types,
            "require_all_signals": self.require_all_signals,
            "min_composite_score": self.min_composite_score,
        }


class MomentumBotBase:
    """Base class for momentum bots with common functionality."""
    
    def __init__(self, config: MomentumBotConfig, bot_config: BotConfig):
        self.momentum_config = config
        self.bot_config = bot_config
        self._current_positions: Set[str] = set()
        self._entry_times: Dict[str, datetime] = {}
        self._last_rebalance: Optional[datetime] = None
        
    async def get_target_symbols(self) -> List[str]:
        """Get symbols to trade based on momentum rankings. Override in subclass."""
        raise NotImplementedError
    
    async def should_rebalance(self) -> bool:
        """Check if it's time to rebalance."""
        if self._last_rebalance is None:
            return True
        
        now = datetime.now()
        freq = self.momentum_config.rebalance_frequency
        
        if freq == "hourly":
            return (now - self._last_rebalance) >= timedelta(hours=1)
        elif freq == "daily":
            # Rebalance at market open (9:30 AM)
            if now.hour == 9 and now.minute >= 30:
                return self._last_rebalance.date() < now.date()
        elif freq == "weekly":
            return (now - self._last_rebalance) >= timedelta(days=7)
        
        return False
    
    async def get_exit_candidates(self) -> List[str]:
        """Get positions that should be exited."""
        from src.data.momentum_screener import get_momentum_screener
        
        screener = get_momentum_screener()
        exits = []
        
        for symbol in self._current_positions:
            score = screener.get_symbol_score(symbol)
            
            if score is None:
                # No data, consider exiting
                exits.append(symbol)
            elif score.composite_score < self.momentum_config.exit_score_threshold:
                exits.append(symbol)
        
        return exits


class SectorRotationBot(MomentumBotBase):
    """
    Sector Rotation Bot - Rotates into top stocks from hottest sectors.
    
    Strategy:
    - Identifies sectors with highest average momentum
    - Buys top N stocks from top M sectors
    - Rebalances daily at market open
    - Exits when sector momentum fades
    """
    
    async def get_target_symbols(self) -> List[str]:
        """Get target symbols from top sectors."""
        from src.data.momentum_screener import get_momentum_screener
        
        screener = get_momentum_screener()
        
        # Get sector heatmap
        heatmap = screener.get_sector_heatmap()
        
        if not heatmap:
            logger.warning("No sector data available")
            return []
        
        # Get top sectors
        top_sectors = list(heatmap.keys())[:self.momentum_config.sectors_to_trade]
        
        logger.info(f"SectorRotation: Top sectors = {top_sectors}")
        
        # Get top stocks from each sector
        symbols = []
        for sector in top_sectors:
            sector_stocks = screener.get_top_by_sector(
                sector, 
                count=self.momentum_config.stocks_per_sector
            )
            
            for stock in sector_stocks:
                if stock.composite_score >= self.momentum_config.min_momentum_score:
                    symbols.append(stock.symbol)
        
        # Limit to max positions
        return symbols[:self.momentum_config.max_positions]


class SocialMomentumBot(MomentumBotBase):
    """
    Social Momentum Bot - Trades viral/trending stocks.
    
    Strategy:
    - Monitors social media buzz scores
    - Buys stocks going viral (rapid mention increase)
    - Quick trades with short hold times
    - Exits when buzz fades
    """
    
    async def get_target_symbols(self) -> List[str]:
        """Get target symbols from social momentum."""
        from src.forecasting.social_sentiment import get_social_sentiment_engine
        
        engine = get_social_sentiment_engine()
        
        symbols = []
        
        if self.momentum_config.viral_only:
            # Get viral stocks only
            viral = await engine.get_viral_stocks(
                min_buzz_score=self.momentum_config.min_buzz_score
            )
            symbols = [v["symbol"] for v in viral]
        else:
            # Get trending stocks
            trending = await engine.get_top_trending(
                count=self.momentum_config.max_positions * 2
            )
            symbols = [
                t["symbol"] for t in trending 
                if t["buzz_score"] >= self.momentum_config.min_buzz_score
            ]
        
        logger.info(f"SocialMomentum: Found {len(symbols)} trending symbols")
        
        return symbols[:self.momentum_config.max_positions]
    
    async def get_exit_candidates(self) -> List[str]:
        """Exit positions held too long or with fading buzz."""
        exits = await super().get_exit_candidates()
        
        # Also exit positions held longer than max_hold_hours
        now = datetime.now()
        for symbol in self._current_positions:
            if symbol not in exits:
                entry_time = self._entry_times.get(symbol)
                if entry_time:
                    hold_hours = (now - entry_time).total_seconds() / 3600
                    if hold_hours >= self.momentum_config.max_hold_hours:
                        exits.append(symbol)
        
        return exits


class NewsMomentumBot(MomentumBotBase):
    """
    News Momentum Bot - Trades on news volume and sentiment.
    
    Strategy:
    - Monitors news article counts and sentiment
    - Buys on positive news surges
    - Filters by catalyst type (earnings, FDA, etc.)
    - Quick entries with same-day or next-day exits
    """
    
    async def get_target_symbols(self) -> List[str]:
        """Get target symbols from news momentum."""
        from src.data.news_momentum import get_news_momentum
        
        news = get_news_momentum()
        
        symbols = []
        
        # Get top news momentum stocks
        if self.momentum_config.catalyst_types:
            # Filter by catalyst type
            for catalyst in self.momentum_config.catalyst_types:
                catalyst_stocks = news.get_by_catalyst(catalyst)
                for stock in catalyst_stocks:
                    if stock.volume_score >= self.momentum_config.min_news_score:
                        if not self.momentum_config.positive_sentiment_only or stock.avg_sentiment > 0:
                            symbols.append(stock.symbol)
        else:
            # Get top by news volume
            if self.momentum_config.positive_sentiment_only:
                top_news = news.get_positive_momentum(
                    min_sentiment=0.2,
                    count=self.momentum_config.max_positions * 2
                )
            else:
                top_news = news.get_top_news_momentum(
                    count=self.momentum_config.max_positions * 2
                )
            
            symbols = [
                n.symbol for n in top_news 
                if n.volume_score >= self.momentum_config.min_news_score
            ]
        
        logger.info(f"NewsMomentum: Found {len(symbols)} news-driven symbols")
        
        return list(set(symbols))[:self.momentum_config.max_positions]


class CompositeMomentumBot(MomentumBotBase):
    """
    Composite Momentum Bot - Combines all momentum signals.
    
    Strategy:
    - Only trades when multiple signals align
    - Requires high composite score (price + volume + social + news)
    - Highest selectivity, best risk-adjusted returns
    - Longer hold periods
    """
    
    async def get_target_symbols(self) -> List[str]:
        """Get target symbols with aligned momentum signals."""
        from src.data.momentum_screener import get_momentum_screener
        
        screener = get_momentum_screener()
        
        # Get top composite scores
        top_scores = screener.get_top(count=50)
        
        symbols = []
        for score in top_scores:
            # Check minimum composite score
            if score.composite_score < self.momentum_config.min_composite_score:
                continue
            
            # Check signal alignment if required
            if self.momentum_config.require_all_signals:
                # All signals must be positive
                if score.price_momentum < 50:  # Below average
                    continue
                if score.social_buzz < 30:  # Low social activity
                    continue
                if score.news_volume < 20:  # Low news coverage
                    continue
            
            symbols.append(score.symbol)
        
        logger.info(f"CompositeMomentum: Found {len(symbols)} aligned symbols")
        
        return symbols[:self.momentum_config.max_positions]


# ============================================================================
# BOT TEMPLATES FOR BOT MANAGER
# ============================================================================

def get_momentum_bot_templates() -> List[Dict]:
    """Get momentum bot templates for the bot manager."""
    return [
        {
            "id": "sector_rotation",
            "name": "Sector Rotation Bot",
            "description": "Rotates into top stocks from hottest sectors. Rebalances daily.",
            "type": MomentumBotType.SECTOR_ROTATION.value,
            "icon": "🔄",
            "category": "momentum",
            "default_config": MomentumBotConfig(
                bot_type=MomentumBotType.SECTOR_ROTATION,
                max_positions=9,  # 3 sectors x 3 stocks
                sectors_to_trade=3,
                stocks_per_sector=3,
                rebalance_frequency="daily",
            ).to_dict(),
            "risk_level": "medium",
            "expected_trades": "3-9 trades per rebalance",
            "hold_period": "1-5 days",
        },
        {
            "id": "social_momentum",
            "name": "Social Momentum Bot",
            "description": "Trades viral and trending stocks from social media buzz.",
            "type": MomentumBotType.SOCIAL_MOMENTUM.value,
            "icon": "📱",
            "category": "momentum",
            "default_config": MomentumBotConfig(
                bot_type=MomentumBotType.SOCIAL_MOMENTUM,
                max_positions=5,
                min_buzz_score=70,
                viral_only=False,
                max_hold_hours=48,
                rebalance_frequency="hourly",
            ).to_dict(),
            "risk_level": "high",
            "expected_trades": "5-15 trades per day",
            "hold_period": "hours to 2 days",
        },
        {
            "id": "news_momentum",
            "name": "News Momentum Bot",
            "description": "Trades on news volume spikes and positive sentiment.",
            "type": MomentumBotType.NEWS_MOMENTUM.value,
            "icon": "📰",
            "category": "momentum",
            "default_config": MomentumBotConfig(
                bot_type=MomentumBotType.NEWS_MOMENTUM,
                max_positions=5,
                min_news_score=60,
                positive_sentiment_only=True,
                catalyst_types=[],  # All catalysts
                rebalance_frequency="hourly",
            ).to_dict(),
            "risk_level": "medium-high",
            "expected_trades": "3-10 trades per day",
            "hold_period": "hours to 1 day",
        },
        {
            "id": "composite_momentum",
            "name": "Composite Momentum Bot",
            "description": "Only trades when price, social, and news signals align.",
            "type": MomentumBotType.COMPOSITE_MOMENTUM.value,
            "icon": "🎯",
            "category": "momentum",
            "default_config": MomentumBotConfig(
                bot_type=MomentumBotType.COMPOSITE_MOMENTUM,
                max_positions=5,
                min_composite_score=80,
                require_all_signals=True,
                rebalance_frequency="daily",
            ).to_dict(),
            "risk_level": "medium",
            "expected_trades": "1-5 trades per day",
            "hold_period": "2-7 days",
        },
    ]


def create_momentum_bot(
    template_id: str,
    name: Optional[str] = None,
    custom_config: Optional[Dict] = None,
) -> BotInstance:
    """
    Create a momentum bot from a template.
    
    Args:
        template_id: One of sector_rotation, social_momentum, news_momentum, composite_momentum
        name: Custom name for the bot
        custom_config: Override default config values
    
    Returns:
        BotInstance ready to start
    """
    templates = {t["id"]: t for t in get_momentum_bot_templates()}
    
    if template_id not in templates:
        raise ValueError(f"Unknown momentum bot template: {template_id}")
    
    template = templates[template_id]
    
    # Merge custom config
    config_dict = template["default_config"].copy()
    if custom_config:
        config_dict.update(custom_config)
    
    # Create BotConfig
    bot_name = name or f"{template['name']} #{datetime.now().strftime('%H%M')}"
    
    bot_config = BotConfig(
        name=bot_name,
        description=template["description"],
        instrument_type=InstrumentType.STOCK,
        symbols=[],  # Will be auto-selected from momentum rankings
        strategies=["momentum"],
        max_positions=config_dict.get("max_positions", 10),
        trade_frequency_seconds=300,  # 5 minutes
        use_paper_trading=True,  # Default to paper
    )
    
    # Store momentum config in bot config's ai_interpreted_config
    bot_config.ai_interpreted_config = {
        "momentum_bot_type": template_id,
        "momentum_config": config_dict,
    }
    
    return BotInstance(bot_config)

