"""
Forex Core Module

Provides fundamental Forex trading functionality:
- Currency pair definitions and metadata
- Pip calculations for all pair types
- Lot sizing (standard, mini, micro, nano)
- Trading session detection and overlap periods
- Spread monitoring and analysis
- Swap/rollover rate calculations
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from datetime import datetime, time, timezone, timedelta
import pytz

from loguru import logger


class PairType(Enum):
    """Currency pair classification."""
    MAJOR = "major"           # EUR/USD, GBP/USD, USD/JPY, etc.
    MINOR = "minor"           # EUR/GBP, EUR/CHF, GBP/JPY, etc.
    EXOTIC = "exotic"         # USD/TRY, EUR/ZAR, USD/MXN, etc.
    COMMODITY = "commodity"   # AUD/USD, USD/CAD, NZD/USD (commodity-linked)


class SessionName(Enum):
    """Major Forex trading sessions."""
    SYDNEY = "sydney"
    TOKYO = "tokyo"
    LONDON = "london"
    NEW_YORK = "new_york"


@dataclass
class ForexSession:
    """Trading session information."""
    name: SessionName
    open_time: time      # UTC
    close_time: time     # UTC
    timezone: str
    major_pairs: List[str]
    typical_volatility: str  # "low", "medium", "high"
    
    def is_active(self, current_time: Optional[datetime] = None) -> bool:
        """Check if session is currently active."""
        now = current_time or datetime.now(timezone.utc)
        current = now.time()
        
        if self.open_time < self.close_time:
            return self.open_time <= current <= self.close_time
        else:
            # Session spans midnight
            return current >= self.open_time or current <= self.close_time


@dataclass
class ForexPair:
    """Currency pair definition with metadata."""
    symbol: str                    # e.g., "EUR/USD"
    base_currency: str             # e.g., "EUR"
    quote_currency: str            # e.g., "USD"
    pair_type: PairType
    pip_decimal_places: int = 4    # 4 for most pairs, 2 for JPY pairs
    typical_spread_pips: float = 1.0
    avg_daily_range_pips: float = 80.0
    swap_long: float = 0.0         # Swap rate for long positions
    swap_short: float = 0.0        # Swap rate for short positions
    margin_requirement: float = 0.02  # 2% = 50:1 leverage
    trading_hours: str = "24/5"
    
    @property
    def pip_value(self) -> float:
        """Get the pip value (0.0001 or 0.01 for JPY pairs)."""
        return 10 ** (-self.pip_decimal_places)
    
    @property
    def is_jpy_pair(self) -> bool:
        """Check if this is a JPY pair (2 decimal places)."""
        return "JPY" in self.symbol
    
    def calculate_pips(self, price_change: float) -> float:
        """Convert price change to pips."""
        return price_change / self.pip_value
    
    def pips_to_price(self, pips: float) -> float:
        """Convert pips to price change."""
        return pips * self.pip_value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "base_currency": self.base_currency,
            "quote_currency": self.quote_currency,
            "pair_type": self.pair_type.value,
            "pip_decimal_places": self.pip_decimal_places,
            "pip_value": self.pip_value,
            "typical_spread_pips": self.typical_spread_pips,
            "avg_daily_range_pips": self.avg_daily_range_pips,
            "swap_long": self.swap_long,
            "swap_short": self.swap_short,
            "margin_requirement": self.margin_requirement,
        }


class LotType(Enum):
    """Forex lot sizes."""
    STANDARD = 100000   # 1 standard lot = 100,000 units
    MINI = 10000        # 1 mini lot = 10,000 units
    MICRO = 1000        # 1 micro lot = 1,000 units
    NANO = 100          # 1 nano lot = 100 units


@dataclass
class LotSizer:
    """
    Calculate position size based on risk management rules.
    
    Usage:
        sizer = LotSizer(account_balance=10000, risk_percent=1.0)
        lots = sizer.calculate_lots("EUR/USD", stop_loss_pips=20)
    """
    account_balance: float
    risk_percent: float = 1.0       # Risk per trade as percentage
    account_currency: str = "USD"
    lot_type: LotType = LotType.MINI
    max_lots: float = 10.0          # Maximum position size
    
    def calculate_lots(
        self,
        pair: ForexPair,
        stop_loss_pips: float,
        current_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate position size based on stop loss and risk.
        
        Args:
            pair: Currency pair
            stop_loss_pips: Stop loss distance in pips
            current_price: Current price (for pip value conversion)
        
        Returns:
            Dict with lots, units, risk amount, and details
        """
        if stop_loss_pips <= 0:
            return {"error": "Stop loss must be positive"}
        
        # Calculate risk amount in account currency
        risk_amount = self.account_balance * (self.risk_percent / 100)
        
        # Calculate pip value per unit
        # For USD account trading EUR/USD: 1 pip = $0.0001 per unit
        pip_value_per_unit = pair.pip_value
        
        # Adjust for quote currency if not USD
        if pair.quote_currency != self.account_currency and current_price:
            # Need to convert pip value to account currency
            # This is simplified - full implementation would use cross rates
            pip_value_per_unit *= current_price
        
        # Calculate lot size based on lot type
        lot_units = self.lot_type.value
        pip_value_per_lot = pip_value_per_unit * lot_units
        
        # Risk per pip = pip_value_per_lot * lots
        # Risk amount = Risk per pip * stop_loss_pips
        # Lots = Risk amount / (pip_value_per_lot * stop_loss_pips)
        
        lots = risk_amount / (pip_value_per_lot * stop_loss_pips)
        
        # Apply maximum
        lots = min(lots, self.max_lots)
        
        # Round to 2 decimal places
        lots = round(lots, 2)
        
        return {
            "lots": lots,
            "lot_type": self.lot_type.name.lower(),
            "units": int(lots * lot_units),
            "risk_amount": round(risk_amount, 2),
            "risk_percent": self.risk_percent,
            "stop_loss_pips": stop_loss_pips,
            "pip_value_per_lot": round(pip_value_per_lot, 4),
            "potential_loss": round(lots * pip_value_per_lot * stop_loss_pips, 2),
        }
    
    def calculate_by_units(self, units: int) -> Dict[str, float]:
        """Convert units to lots for different lot types."""
        return {
            "standard_lots": round(units / LotType.STANDARD.value, 4),
            "mini_lots": round(units / LotType.MINI.value, 4),
            "micro_lots": round(units / LotType.MICRO.value, 4),
            "nano_lots": round(units / LotType.NANO.value, 4),
        }


class PipCalculator:
    """
    Comprehensive pip calculation utilities.
    
    Usage:
        calc = PipCalculator()
        pips = calc.price_to_pips("EUR/USD", 1.0850, 1.0875)  # = 25 pips
        value = calc.pip_value("EUR/USD", 10000)  # Pip value for 10k units
    """
    
    def __init__(self):
        self._pairs = get_forex_pairs()
        self._pair_lookup = {p.symbol: p for p in self._pairs}
    
    def get_pair(self, symbol: str) -> Optional[ForexPair]:
        """Get pair by symbol."""
        # Normalize symbol (EUR/USD or EURUSD)
        normalized = symbol.upper().replace("/", "")
        if len(normalized) == 6:
            formatted = f"{normalized[:3]}/{normalized[3:]}"
            return self._pair_lookup.get(formatted)
        return self._pair_lookup.get(symbol.upper())
    
    def price_to_pips(self, symbol: str, entry_price: float, exit_price: float) -> float:
        """Calculate pips between two prices."""
        pair = self.get_pair(symbol)
        if not pair:
            # Default to 4 decimal places
            return (exit_price - entry_price) / 0.0001
        
        return pair.calculate_pips(exit_price - entry_price)
    
    def pips_to_price(self, symbol: str, pips: float) -> float:
        """Convert pips to price movement."""
        pair = self.get_pair(symbol)
        if not pair:
            return pips * 0.0001
        return pair.pips_to_price(pips)
    
    def pip_value(
        self,
        symbol: str,
        units: int,
        account_currency: str = "USD",
        current_rate: Optional[float] = None,
    ) -> float:
        """
        Calculate the pip value for a given position size.
        
        Args:
            symbol: Currency pair symbol
            units: Position size in units
            account_currency: Account base currency
            current_rate: Current exchange rate (for conversion)
        
        Returns:
            Value of 1 pip movement in account currency
        """
        pair = self.get_pair(symbol)
        if not pair:
            # Default calculation
            return units * 0.0001
        
        # Base pip value in quote currency
        pip_value = units * pair.pip_value
        
        # Convert to account currency if needed
        if pair.quote_currency != account_currency and current_rate:
            if pair.quote_currency == "JPY":
                pip_value = pip_value / current_rate
            else:
                pip_value = pip_value * current_rate
        
        return round(pip_value, 4)
    
    def calculate_profit_loss(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        units: int,
        is_long: bool = True,
    ) -> Dict[str, float]:
        """Calculate profit/loss for a trade."""
        pips = self.price_to_pips(symbol, entry_price, exit_price)
        
        if not is_long:
            pips = -pips
        
        pip_val = self.pip_value(symbol, units)
        profit_loss = pips * pip_val
        
        return {
            "pips": round(pips, 1),
            "pip_value": pip_val,
            "profit_loss": round(profit_loss, 2),
            "profit_loss_percent": round((profit_loss / (entry_price * units)) * 100, 4),
        }


# =============================================================================
# Trading Sessions
# =============================================================================

FOREX_SESSIONS = [
    ForexSession(
        name=SessionName.SYDNEY,
        open_time=time(22, 0),   # 10 PM UTC
        close_time=time(7, 0),   # 7 AM UTC
        timezone="Australia/Sydney",
        major_pairs=["AUD/USD", "NZD/USD", "AUD/JPY", "AUD/NZD"],
        typical_volatility="low",
    ),
    ForexSession(
        name=SessionName.TOKYO,
        open_time=time(0, 0),    # Midnight UTC
        close_time=time(9, 0),   # 9 AM UTC
        timezone="Asia/Tokyo",
        major_pairs=["USD/JPY", "EUR/JPY", "GBP/JPY", "AUD/JPY"],
        typical_volatility="medium",
    ),
    ForexSession(
        name=SessionName.LONDON,
        open_time=time(8, 0),    # 8 AM UTC
        close_time=time(17, 0),  # 5 PM UTC
        timezone="Europe/London",
        major_pairs=["EUR/USD", "GBP/USD", "EUR/GBP", "EUR/CHF"],
        typical_volatility="high",
    ),
    ForexSession(
        name=SessionName.NEW_YORK,
        open_time=time(13, 0),   # 1 PM UTC
        close_time=time(22, 0),  # 10 PM UTC
        timezone="America/New_York",
        major_pairs=["EUR/USD", "GBP/USD", "USD/JPY", "USD/CAD"],
        typical_volatility="high",
    ),
]


def get_current_session(current_time: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Get currently active trading sessions.
    
    Returns:
        Dict with active sessions, overlaps, and recommendations
    """
    now = current_time or datetime.now(timezone.utc)
    
    active_sessions = []
    for session in FOREX_SESSIONS:
        if session.is_active(now):
            active_sessions.append({
                "name": session.name.value,
                "timezone": session.timezone,
                "volatility": session.typical_volatility,
                "major_pairs": session.major_pairs,
            })
    
    # Detect overlaps
    overlaps = []
    if len(active_sessions) >= 2:
        session_names = [s["name"] for s in active_sessions]
        if "london" in session_names and "new_york" in session_names:
            overlaps.append({
                "sessions": ["london", "new_york"],
                "description": "London-New York Overlap (Highest Volatility)",
                "best_pairs": ["EUR/USD", "GBP/USD", "USD/CHF"],
            })
        if "london" in session_names and "tokyo" in session_names:
            overlaps.append({
                "sessions": ["london", "tokyo"],
                "description": "London-Tokyo Overlap",
                "best_pairs": ["EUR/JPY", "GBP/JPY"],
            })
        if "sydney" in session_names and "tokyo" in session_names:
            overlaps.append({
                "sessions": ["sydney", "tokyo"],
                "description": "Sydney-Tokyo Overlap",
                "best_pairs": ["AUD/JPY", "AUD/USD", "NZD/JPY"],
            })
    
    # Trading recommendation
    if overlaps:
        recommendation = "HIGH ACTIVITY: Session overlap - ideal for breakout strategies"
    elif active_sessions:
        rec_session = active_sessions[0]
        recommendation = f"{rec_session['name'].upper()} SESSION: Focus on {', '.join(rec_session['major_pairs'][:3])}"
    else:
        recommendation = "LOW ACTIVITY: Weekend or inter-session period - avoid trading or use tight stops"
    
    return {
        "current_time_utc": now.isoformat(),
        "active_sessions": active_sessions,
        "overlaps": overlaps,
        "recommendation": recommendation,
        "is_weekend": now.weekday() >= 5,
    }


# =============================================================================
# Currency Pair Database
# =============================================================================

def get_forex_pairs() -> List[ForexPair]:
    """Get all supported Forex pairs."""
    return [
        # Major Pairs (7)
        ForexPair("EUR/USD", "EUR", "USD", PairType.MAJOR, 4, 0.8, 85, -0.5, -0.3, 0.02),
        ForexPair("GBP/USD", "GBP", "USD", PairType.MAJOR, 4, 1.0, 100, -0.4, -0.4, 0.02),
        ForexPair("USD/JPY", "USD", "JPY", PairType.MAJOR, 2, 0.9, 75, 0.2, -0.6, 0.02),
        ForexPair("USD/CHF", "USD", "CHF", PairType.MAJOR, 4, 1.2, 65, 0.3, -0.5, 0.02),
        ForexPair("AUD/USD", "AUD", "USD", PairType.COMMODITY, 4, 1.0, 70, -0.3, -0.4, 0.02),
        ForexPair("USD/CAD", "USD", "CAD", PairType.COMMODITY, 4, 1.2, 70, -0.2, -0.3, 0.02),
        ForexPair("NZD/USD", "NZD", "USD", PairType.COMMODITY, 4, 1.5, 65, -0.4, -0.3, 0.02),
        
        # Minor/Cross Pairs
        ForexPair("EUR/GBP", "EUR", "GBP", PairType.MINOR, 4, 1.2, 50, -0.3, -0.3, 0.02),
        ForexPair("EUR/JPY", "EUR", "JPY", PairType.MINOR, 2, 1.5, 90, -0.1, -0.5, 0.02),
        ForexPair("GBP/JPY", "GBP", "JPY", PairType.MINOR, 2, 2.0, 120, 0.0, -0.6, 0.02),
        ForexPair("EUR/CHF", "EUR", "CHF", PairType.MINOR, 4, 1.5, 45, -0.4, -0.2, 0.02),
        ForexPair("EUR/AUD", "EUR", "AUD", PairType.MINOR, 4, 2.0, 95, -0.2, -0.4, 0.02),
        ForexPair("EUR/CAD", "EUR", "CAD", PairType.MINOR, 4, 2.0, 85, -0.3, -0.3, 0.02),
        ForexPair("EUR/NZD", "EUR", "NZD", PairType.MINOR, 4, 2.5, 100, -0.2, -0.4, 0.02),
        ForexPair("GBP/CHF", "GBP", "CHF", PairType.MINOR, 4, 2.5, 80, 0.1, -0.5, 0.02),
        ForexPair("GBP/AUD", "GBP", "AUD", PairType.MINOR, 4, 3.0, 115, -0.1, -0.5, 0.02),
        ForexPair("GBP/CAD", "GBP", "CAD", PairType.MINOR, 4, 3.0, 100, -0.2, -0.4, 0.02),
        ForexPair("GBP/NZD", "GBP", "NZD", PairType.MINOR, 4, 3.5, 120, -0.1, -0.5, 0.02),
        ForexPair("AUD/JPY", "AUD", "JPY", PairType.MINOR, 2, 1.5, 75, 0.2, -0.5, 0.02),
        ForexPair("AUD/CHF", "AUD", "CHF", PairType.MINOR, 4, 2.0, 60, 0.1, -0.4, 0.02),
        ForexPair("AUD/CAD", "AUD", "CAD", PairType.MINOR, 4, 2.0, 55, -0.2, -0.3, 0.02),
        ForexPair("AUD/NZD", "AUD", "NZD", PairType.MINOR, 4, 2.0, 45, -0.1, -0.3, 0.02),
        ForexPair("CAD/JPY", "CAD", "JPY", PairType.MINOR, 2, 1.8, 70, 0.3, -0.5, 0.02),
        ForexPair("CAD/CHF", "CAD", "CHF", PairType.MINOR, 4, 2.5, 55, 0.2, -0.4, 0.02),
        ForexPair("CHF/JPY", "CHF", "JPY", PairType.MINOR, 2, 2.0, 60, -0.3, -0.3, 0.02),
        ForexPair("NZD/JPY", "NZD", "JPY", PairType.MINOR, 2, 2.0, 70, 0.1, -0.5, 0.02),
        ForexPair("NZD/CHF", "NZD", "CHF", PairType.MINOR, 4, 2.5, 55, 0.0, -0.4, 0.02),
        ForexPair("NZD/CAD", "NZD", "CAD", PairType.MINOR, 4, 2.5, 55, -0.2, -0.3, 0.02),
        
        # Exotic Pairs
        ForexPair("USD/TRY", "USD", "TRY", PairType.EXOTIC, 4, 15.0, 300, 8.0, -15.0, 0.05),
        ForexPair("EUR/TRY", "EUR", "TRY", PairType.EXOTIC, 4, 18.0, 350, 7.5, -16.0, 0.05),
        ForexPair("USD/ZAR", "USD", "ZAR", PairType.EXOTIC, 4, 80.0, 200, 5.0, -10.0, 0.05),
        ForexPair("EUR/ZAR", "EUR", "ZAR", PairType.EXOTIC, 4, 90.0, 220, 4.5, -11.0, 0.05),
        ForexPair("USD/MXN", "USD", "MXN", PairType.EXOTIC, 4, 50.0, 150, 6.0, -12.0, 0.05),
        ForexPair("EUR/MXN", "EUR", "MXN", PairType.EXOTIC, 4, 55.0, 160, 5.5, -13.0, 0.05),
        ForexPair("USD/PLN", "USD", "PLN", PairType.EXOTIC, 4, 20.0, 100, 1.0, -4.0, 0.03),
        ForexPair("EUR/PLN", "EUR", "PLN", PairType.EXOTIC, 4, 22.0, 90, 0.5, -4.5, 0.03),
        ForexPair("USD/SEK", "USD", "SEK", PairType.EXOTIC, 4, 30.0, 80, 0.3, -2.0, 0.03),
        ForexPair("EUR/SEK", "EUR", "SEK", PairType.EXOTIC, 4, 32.0, 75, 0.2, -2.5, 0.03),
        ForexPair("USD/NOK", "USD", "NOK", PairType.EXOTIC, 4, 35.0, 85, 0.4, -2.5, 0.03),
        ForexPair("EUR/NOK", "EUR", "NOK", PairType.EXOTIC, 4, 38.0, 80, 0.3, -3.0, 0.03),
        ForexPair("USD/DKK", "USD", "DKK", PairType.EXOTIC, 4, 15.0, 40, -0.5, -0.5, 0.02),
        ForexPair("EUR/DKK", "EUR", "DKK", PairType.EXOTIC, 4, 12.0, 15, -0.6, -0.4, 0.02),
        ForexPair("USD/HKD", "USD", "HKD", PairType.EXOTIC, 4, 5.0, 15, -0.8, -0.8, 0.02),
        ForexPair("USD/SGD", "USD", "SGD", PairType.EXOTIC, 4, 3.0, 40, -0.4, -0.6, 0.02),
        ForexPair("USD/CNH", "USD", "CNH", PairType.EXOTIC, 4, 10.0, 60, 1.0, -3.0, 0.03),
        ForexPair("USD/THB", "USD", "THB", PairType.EXOTIC, 2, 20.0, 50, 0.5, -2.0, 0.05),
        ForexPair("USD/INR", "USD", "INR", PairType.EXOTIC, 2, 25.0, 40, 2.0, -5.0, 0.05),
        ForexPair("USD/RUB", "USD", "RUB", PairType.EXOTIC, 4, 100.0, 250, 3.0, -8.0, 0.10),
        
        # Precious Metals (as Forex pairs)
        ForexPair("XAU/USD", "XAU", "USD", PairType.COMMODITY, 2, 30.0, 1500, -1.0, -0.5, 0.05),
        ForexPair("XAG/USD", "XAG", "USD", PairType.COMMODITY, 3, 3.0, 50, -0.8, -0.4, 0.05),
    ]


# Singleton calculator
_pip_calculator: Optional[PipCalculator] = None


def get_pip_calculator() -> PipCalculator:
    """Get or create the pip calculator singleton."""
    global _pip_calculator
    if _pip_calculator is None:
        _pip_calculator = PipCalculator()
    return _pip_calculator

