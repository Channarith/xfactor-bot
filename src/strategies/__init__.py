"""Trading strategies module."""

from src.strategies.base_strategy import BaseStrategy, Signal, SignalType
from src.strategies.technical import TechnicalStrategy
from src.strategies.momentum import MomentumStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.news_sentiment import NewsSentimentStrategy
from src.strategies.seasonal_events import (
    SeasonalEventsCalendar,
    SeasonalEvent,
    Season,
    MarketImpact,
    get_seasonal_calendar,
)

# v1.0.1 - New Quantvue-inspired modules
from src.strategies.volatility_adaptive import (
    VolatilityAdaptiveEngine,
    VolatilityAdaptiveConfig,
    AdaptiveStopLevels,
    get_volatility_engine,
    calculate_adaptive_stops,
)
from src.strategies.market_regime import (
    MarketRegimeDetector,
    MarketRegime,
    TrendDirection,
    RegimeAnalysis,
    get_regime_detector,
    detect_regime,
)
from src.strategies.martingale import (
    MartingalePositionSizer,
    MartingaleConfig,
    MartingaleType,
    create_martingale_sizer,
)
from src.strategies.templates import (
    StrategyTemplate,
    get_all_templates,
    get_template,
    search_templates,
)
from src.strategies.visual_builder import (
    VisualStrategyEngine,
    VisualStrategy,
    StrategyNode,
    get_visual_strategy_engine,
)

__all__ = [
    # Base
    "BaseStrategy",
    "Signal",
    "SignalType",
    # Strategies
    "TechnicalStrategy",
    "MomentumStrategy",
    "MeanReversionStrategy",
    "NewsSentimentStrategy",
    # Seasonal
    "SeasonalEventsCalendar",
    "SeasonalEvent",
    "Season",
    "MarketImpact",
    "get_seasonal_calendar",
    # Volatility Adaptive
    "VolatilityAdaptiveEngine",
    "VolatilityAdaptiveConfig",
    "AdaptiveStopLevels",
    "get_volatility_engine",
    "calculate_adaptive_stops",
    # Market Regime
    "MarketRegimeDetector",
    "MarketRegime",
    "TrendDirection",
    "RegimeAnalysis",
    "get_regime_detector",
    "detect_regime",
    # Martingale
    "MartingalePositionSizer",
    "MartingaleConfig",
    "MartingaleType",
    "create_martingale_sizer",
    # Templates
    "StrategyTemplate",
    "get_all_templates",
    "get_template",
    "search_templates",
    # Visual Builder
    "VisualStrategyEngine",
    "VisualStrategy",
    "StrategyNode",
    "get_visual_strategy_engine",
]

