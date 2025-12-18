"""
XFactor Bot Forex Trading Module

Comprehensive Forex trading capabilities including:
- 60+ currency pairs (majors, minors, exotics)
- Pip calculations and lot sizing
- Session-based trading (Tokyo, London, New York, Sydney)
- Currency strength and correlation analysis
- Economic calendar integration
- Swap/rollover calculations
- Multi-broker support (MT4/5, OANDA, FXCM, IG)
"""

from src.forex.core import (
    ForexPair,
    ForexSession,
    PipCalculator,
    LotSizer,
    get_forex_pairs,
    get_current_session,
)
from src.forex.currency_strength import (
    CurrencyStrengthMeter,
    get_currency_strength,
)
from src.forex.economic_calendar import (
    EconomicCalendar,
    EconomicEvent,
    get_economic_calendar,
)
from src.forex.strategies import (
    CarryTradeStrategy,
    SessionBreakoutStrategy,
    NewsTradeStrategy,
)

__all__ = [
    # Core
    "ForexPair",
    "ForexSession",
    "PipCalculator",
    "LotSizer",
    "get_forex_pairs",
    "get_current_session",
    # Currency Strength
    "CurrencyStrengthMeter",
    "get_currency_strength",
    # Economic Calendar
    "EconomicCalendar",
    "EconomicEvent",
    "get_economic_calendar",
    # Strategies
    "CarryTradeStrategy",
    "SessionBreakoutStrategy",
    "NewsTradeStrategy",
]

