"""
Forex Trading Strategies

Specialized strategies for the Forex market:
- Carry Trade: Profit from interest rate differentials
- Session Breakout: Trade session open breakouts
- News Trade: Trade around economic news releases
- Asian Range Breakout: Trade breaks of Asian session range
- Currency Correlation: Trade correlated/inverse pairs
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, time, timezone, timedelta
from enum import Enum
from abc import ABC, abstractmethod

import pandas as pd
from loguru import logger

from src.forex.core import (
    ForexPair,
    ForexSession,
    get_forex_pairs,
    get_current_session,
    PipCalculator,
    LotSizer,
)
from src.forex.currency_strength import get_currency_strength
from src.forex.economic_calendar import get_economic_calendar, EventImpact


class SignalType(Enum):
    """Trading signal type."""
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    NONE = "none"


@dataclass
class ForexSignal:
    """A Forex trading signal."""
    pair: str
    signal_type: SignalType
    strategy: str
    confidence: float              # 0-100
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    lot_size: Optional[float] = None
    reason: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair": self.pair,
            "signal_type": self.signal_type.value,
            "strategy": self.strategy,
            "confidence": round(self.confidence, 1),
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "lot_size": self.lot_size,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class BaseForexStrategy(ABC):
    """Base class for Forex strategies."""
    
    def __init__(self, name: str):
        self.name = name
        self._signals: List[ForexSignal] = []
    
    @abstractmethod
    def analyze(self, pair: str, price_data: pd.DataFrame) -> Optional[ForexSignal]:
        """Analyze market and generate signals."""
        pass
    
    def get_recent_signals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent signals."""
        return [s.to_dict() for s in self._signals[-limit:]]


class CarryTradeStrategy(BaseForexStrategy):
    """
    Carry Trade Strategy
    
    Profits from interest rate differentials between currencies.
    Goes long on high-yield currencies vs low-yield currencies.
    
    Best pairs:
    - AUD/JPY, NZD/JPY (high yield vs low yield)
    - USD/TRY, USD/MXN (emerging market carries)
    
    Risks:
    - Sudden risk-off moves can cause sharp reversals
    - Swap rates can change with central bank policy
    """
    
    # Interest rate estimates (simplified - would use real rates in production)
    INTEREST_RATES = {
        "USD": 5.25,
        "EUR": 4.00,
        "GBP": 5.00,
        "JPY": -0.10,
        "CHF": 1.50,
        "AUD": 4.10,
        "NZD": 5.50,
        "CAD": 4.50,
        "TRY": 45.00,
        "MXN": 11.00,
        "ZAR": 8.25,
    }
    
    def __init__(self, min_rate_differential: float = 2.0):
        super().__init__("Carry Trade")
        self.min_rate_differential = min_rate_differential
    
    def analyze(self, pair: str, price_data: pd.DataFrame) -> Optional[ForexSignal]:
        """
        Analyze carry trade opportunity.
        
        Args:
            pair: Currency pair
            price_data: OHLCV data with technical indicators
        
        Returns:
            ForexSignal if carry trade opportunity found
        """
        try:
            base, quote = pair.upper().split("/")
        except ValueError:
            return None
        
        base_rate = self.INTEREST_RATES.get(base, 0)
        quote_rate = self.INTEREST_RATES.get(quote, 0)
        
        rate_diff = base_rate - quote_rate
        
        # Check minimum differential
        if abs(rate_diff) < self.min_rate_differential:
            return None
        
        # Determine direction (long high-yield, short low-yield)
        if rate_diff > 0:
            signal_type = SignalType.BUY
            reason = f"Positive carry: {base} ({base_rate}%) vs {quote} ({quote_rate}%)"
        else:
            signal_type = SignalType.SELL
            reason = f"Negative carry: Short {base} ({base_rate}%) vs {quote} ({quote_rate}%)"
        
        # Calculate confidence based on rate differential
        confidence = min(100, abs(rate_diff) * 15)
        
        # Add trend filter if we have price data
        if len(price_data) >= 50:
            sma20 = price_data['close'].rolling(20).mean().iloc[-1]
            sma50 = price_data['close'].rolling(50).mean().iloc[-1]
            current_price = price_data['close'].iloc[-1]
            
            # Confirm trend aligns with carry direction
            is_uptrend = current_price > sma20 > sma50
            is_downtrend = current_price < sma20 < sma50
            
            if signal_type == SignalType.BUY and not is_uptrend:
                confidence *= 0.7  # Reduce confidence if trend doesn't align
                reason += " (Warning: Trend not aligned)"
            elif signal_type == SignalType.SELL and not is_downtrend:
                confidence *= 0.7
                reason += " (Warning: Trend not aligned)"
            else:
                confidence = min(100, confidence * 1.2)  # Boost if trend aligns
                reason += " (Trend confirmed)"
        
        signal = ForexSignal(
            pair=pair,
            signal_type=signal_type,
            strategy=self.name,
            confidence=confidence,
            reason=reason,
            entry_price=price_data['close'].iloc[-1] if len(price_data) > 0 else None,
        )
        
        self._signals.append(signal)
        return signal
    
    def get_best_carry_pairs(self) -> List[Dict[str, Any]]:
        """Get best carry trade pairs ranked by rate differential."""
        pairs = get_forex_pairs()
        carry_pairs = []
        
        for pair in pairs:
            base_rate = self.INTEREST_RATES.get(pair.base_currency, 0)
            quote_rate = self.INTEREST_RATES.get(pair.quote_currency, 0)
            diff = base_rate - quote_rate
            
            if abs(diff) >= self.min_rate_differential:
                carry_pairs.append({
                    "pair": pair.symbol,
                    "base_rate": base_rate,
                    "quote_rate": quote_rate,
                    "differential": round(diff, 2),
                    "direction": "LONG" if diff > 0 else "SHORT",
                    "annual_carry_pct": abs(diff),
                })
        
        carry_pairs.sort(key=lambda x: abs(x["differential"]), reverse=True)
        return carry_pairs


class SessionBreakoutStrategy(BaseForexStrategy):
    """
    Session Breakout Strategy
    
    Trades breakouts at the start of major trading sessions.
    Particularly effective at London and New York opens.
    
    Method:
    1. Calculate the range of the previous session (e.g., Asian range)
    2. Enter long on break above range high
    3. Enter short on break below range low
    4. Stop loss at opposite end of range
    5. Target 1:1.5 or 1:2 risk/reward
    """
    
    def __init__(
        self,
        range_period_hours: int = 4,
        breakout_buffer_pips: float = 5.0,
        min_range_pips: float = 20.0,
        max_range_pips: float = 80.0,
    ):
        super().__init__("Session Breakout")
        self.range_period_hours = range_period_hours
        self.breakout_buffer_pips = breakout_buffer_pips
        self.min_range_pips = min_range_pips
        self.max_range_pips = max_range_pips
    
    def calculate_session_range(
        self,
        price_data: pd.DataFrame,
        session_hours: int = 4,
    ) -> Tuple[float, float, float]:
        """
        Calculate the range of the previous session.
        
        Returns:
            Tuple of (range_high, range_low, range_pips)
        """
        if len(price_data) < session_hours:
            return 0, 0, 0
        
        # Get last N hours of data
        session_data = price_data.tail(session_hours * 4)  # Assuming 15-min candles
        
        range_high = session_data['high'].max()
        range_low = session_data['low'].min()
        range_pips = (range_high - range_low) / 0.0001  # Convert to pips
        
        return range_high, range_low, range_pips
    
    def analyze(self, pair: str, price_data: pd.DataFrame) -> Optional[ForexSignal]:
        """
        Analyze for session breakout opportunity.
        """
        if len(price_data) < 20:
            return None
        
        range_high, range_low, range_pips = self.calculate_session_range(
            price_data, self.range_period_hours
        )
        
        # Check if range is suitable
        if range_pips < self.min_range_pips:
            return None  # Range too tight
        if range_pips > self.max_range_pips:
            return None  # Range too wide
        
        current_price = price_data['close'].iloc[-1]
        
        # Check for JPY pairs (2 decimal places)
        is_jpy = "JPY" in pair.upper()
        pip_value = 0.01 if is_jpy else 0.0001
        buffer = self.breakout_buffer_pips * pip_value
        
        # Check for breakout
        if current_price > range_high + buffer:
            signal_type = SignalType.BUY
            entry = current_price
            stop_loss = range_low - buffer
            take_profit = entry + (entry - stop_loss) * 1.5
            reason = f"Bullish breakout above {range_high:.5f} (range: {range_pips:.0f} pips)"
            
        elif current_price < range_low - buffer:
            signal_type = SignalType.SELL
            entry = current_price
            stop_loss = range_high + buffer
            take_profit = entry - (stop_loss - entry) * 1.5
            reason = f"Bearish breakout below {range_low:.5f} (range: {range_pips:.0f} pips)"
            
        else:
            return None  # No breakout
        
        # Calculate confidence
        sessions = get_current_session()
        confidence = 60.0
        
        # Boost confidence during session overlaps (high volatility)
        if sessions.get("overlaps"):
            confidence += 15
            reason += " (Session overlap - high volatility)"
        
        # Check if during preferred sessions
        active_sessions = [s["name"] for s in sessions.get("active_sessions", [])]
        if "london" in active_sessions or "new_york" in active_sessions:
            confidence += 10
        
        signal = ForexSignal(
            pair=pair,
            signal_type=signal_type,
            strategy=self.name,
            confidence=min(100, confidence),
            entry_price=entry,
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            reason=reason,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        
        self._signals.append(signal)
        return signal


class NewsTradeStrategy(BaseForexStrategy):
    """
    News Trading Strategy
    
    Trades around high-impact economic news releases.
    Uses straddle or fade strategies depending on event type.
    
    Approaches:
    1. Straddle: Place orders above and below price before release
    2. Fade: Trade against the initial spike after release
    3. Breakout: Trade in direction of the move after volatility settles
    
    Risk warnings:
    - Spreads widen significantly during news
    - Slippage can be substantial
    - Stop losses may not execute at exact price
    """
    
    def __init__(
        self,
        pre_news_minutes: int = 5,
        post_news_minutes: int = 30,
        straddle_distance_pips: float = 20.0,
    ):
        super().__init__("News Trade")
        self.pre_news_minutes = pre_news_minutes
        self.post_news_minutes = post_news_minutes
        self.straddle_distance_pips = straddle_distance_pips
    
    def analyze(self, pair: str, price_data: pd.DataFrame) -> Optional[ForexSignal]:
        """
        Analyze for news trading opportunity.
        """
        try:
            base, quote = pair.upper().split("/")
        except ValueError:
            return None
        
        calendar = get_economic_calendar()
        
        # Check for imminent high-impact news
        should_avoid = calendar.should_avoid_trading(pair)
        
        if not should_avoid.get("avoid"):
            return None  # No imminent news
        
        event = should_avoid.get("event")
        if not event:
            return None
        
        minutes_until = should_avoid.get("minutes_until", 0)
        current_price = price_data['close'].iloc[-1] if len(price_data) > 0 else None
        
        if current_price is None:
            return None
        
        # Determine strategy based on timing
        if minutes_until > 0:
            # Pre-news: Suggest straddle setup
            pip_value = 0.01 if "JPY" in pair else 0.0001
            distance = self.straddle_distance_pips * pip_value
            
            signal = ForexSignal(
                pair=pair,
                signal_type=SignalType.NONE,  # Straddle = both directions
                strategy=f"{self.name} - Straddle",
                confidence=70.0,
                entry_price=current_price,
                reason=f"Straddle setup for {event['title']} in {minutes_until:.0f} minutes",
            )
            
            signal.reason += f"\nBUY STOP: {current_price + distance:.5f}"
            signal.reason += f"\nSELL STOP: {current_price - distance:.5f}"
            signal.reason += f"\nExpected move: {event.get('typical_pip_move', 50)} pips"
            
        else:
            # Post-news: Suggest fade if large spike, or follow if sustained
            # This would need real-time price comparison
            signal = ForexSignal(
                pair=pair,
                signal_type=SignalType.NONE,
                strategy=f"{self.name} - Fade/Follow",
                confidence=50.0,
                reason=f"Monitor {pair} after {event['title']} release",
            )
        
        signal.expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.post_news_minutes)
        
        self._signals.append(signal)
        return signal
    
    def get_tradeable_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming events suitable for news trading."""
        calendar = get_economic_calendar()
        events = calendar.get_high_impact_events(hours)
        
        tradeable = []
        for event in events:
            setup = calendar.get_news_trade_setup(event["id"])
            if setup and setup.get("tradeable"):
                tradeable.append(setup)
        
        return tradeable


class AsianRangeBreakoutStrategy(BaseForexStrategy):
    """
    Asian Range Breakout Strategy
    
    The Asian session (Tokyo) typically has lower volatility.
    This strategy trades the breakout when London session opens.
    
    Method:
    1. Mark the high and low of Asian session (00:00 - 08:00 UTC)
    2. Wait for London open (08:00 UTC)
    3. Enter on breakout of Asian range
    4. Stop at opposite end of range
    """
    
    def __init__(
        self,
        asian_start_utc: int = 0,    # 00:00 UTC
        asian_end_utc: int = 8,       # 08:00 UTC
        min_range_pips: float = 20.0,
        max_range_pips: float = 60.0,
    ):
        super().__init__("Asian Range Breakout")
        self.asian_start = time(asian_start_utc, 0)
        self.asian_end = time(asian_end_utc, 0)
        self.min_range_pips = min_range_pips
        self.max_range_pips = max_range_pips
    
    def is_london_session(self) -> bool:
        """Check if currently in London session."""
        now = datetime.now(timezone.utc).time()
        london_start = time(8, 0)
        london_end = time(17, 0)
        return london_start <= now <= london_end
    
    def analyze(self, pair: str, price_data: pd.DataFrame) -> Optional[ForexSignal]:
        """Analyze for Asian range breakout."""
        if not self.is_london_session():
            return None  # Only trade during London
        
        # Would need to filter price_data by Asian session
        # For now, use recent range as approximation
        if len(price_data) < 32:  # ~8 hours of 15-min candles
            return None
        
        asian_data = price_data.tail(32)
        range_high = asian_data['high'].max()
        range_low = asian_data['low'].min()
        
        pip_value = 0.01 if "JPY" in pair.upper() else 0.0001
        range_pips = (range_high - range_low) / pip_value
        
        if range_pips < self.min_range_pips or range_pips > self.max_range_pips:
            return None
        
        current_price = price_data['close'].iloc[-1]
        buffer = 3 * pip_value  # 3 pip buffer
        
        if current_price > range_high + buffer:
            signal = ForexSignal(
                pair=pair,
                signal_type=SignalType.BUY,
                strategy=self.name,
                confidence=65.0,
                entry_price=current_price,
                stop_loss=round(range_low - buffer, 5),
                take_profit=round(current_price + (current_price - range_low), 5),
                reason=f"Bullish Asian breakout (range: {range_pips:.0f} pips)",
            )
            self._signals.append(signal)
            return signal
        
        elif current_price < range_low - buffer:
            signal = ForexSignal(
                pair=pair,
                signal_type=SignalType.SELL,
                strategy=self.name,
                confidence=65.0,
                entry_price=current_price,
                stop_loss=round(range_high + buffer, 5),
                take_profit=round(current_price - (range_high - current_price), 5),
                reason=f"Bearish Asian breakout (range: {range_pips:.0f} pips)",
            )
            self._signals.append(signal)
            return signal
        
        return None


class CurrencyCorrelationStrategy(BaseForexStrategy):
    """
    Currency Correlation Strategy
    
    Uses currency strength analysis to find divergence opportunities.
    Trades strongest vs weakest currencies.
    
    Method:
    1. Calculate real-time currency strength for all majors
    2. Find the strongest and weakest currencies
    3. Trade the pair combining these two
    4. Monitor for divergences (strength changing direction)
    """
    
    def __init__(self, min_strength_differential: float = 30.0):
        super().__init__("Currency Correlation")
        self.min_strength_differential = min_strength_differential
    
    def analyze(self, pair: str, price_data: pd.DataFrame) -> Optional[ForexSignal]:
        """Analyze using currency strength."""
        strength_meter = get_currency_strength()
        
        # Update with recent price data
        if len(price_data) >= 2:
            prev_price = price_data['close'].iloc[-2]
            curr_price = price_data['close'].iloc[-1]
            strength_meter.update_price(pair, prev_price, curr_price)
        
        # Get best pair recommendation
        best_pair = strength_meter.get_best_pair()
        
        if "error" in best_pair:
            return None
        
        if best_pair.get("strength_differential", 0) < self.min_strength_differential:
            return None
        
        recommended_pair = best_pair["recommended_pair"]
        direction = best_pair["direction"]
        
        signal = ForexSignal(
            pair=recommended_pair,
            signal_type=SignalType.BUY if direction == "BUY" else SignalType.SELL,
            strategy=self.name,
            confidence=min(100, 50 + best_pair["strength_differential"]),
            reason=best_pair["analysis"],
        )
        
        self._signals.append(signal)
        return signal
    
    def get_divergences(self) -> List[Dict[str, Any]]:
        """Get current currency divergences."""
        strength_meter = get_currency_strength()
        return strength_meter.get_divergences()


# Strategy factory
def get_forex_strategy(strategy_name: str) -> Optional[BaseForexStrategy]:
    """Get a Forex strategy by name."""
    strategies = {
        "carry_trade": CarryTradeStrategy,
        "session_breakout": SessionBreakoutStrategy,
        "news_trade": NewsTradeStrategy,
        "asian_breakout": AsianRangeBreakoutStrategy,
        "correlation": CurrencyCorrelationStrategy,
    }
    
    strategy_class = strategies.get(strategy_name.lower())
    if strategy_class:
        return strategy_class()
    return None


def list_forex_strategies() -> List[Dict[str, Any]]:
    """List all available Forex strategies."""
    return [
        {
            "id": "carry_trade",
            "name": "Carry Trade",
            "description": "Profit from interest rate differentials between currencies",
            "best_pairs": ["AUD/JPY", "NZD/JPY", "USD/TRY"],
            "timeframe": "Daily/Weekly",
            "risk_level": "Medium",
        },
        {
            "id": "session_breakout",
            "name": "Session Breakout",
            "description": "Trade breakouts at major session opens (London, New York)",
            "best_pairs": ["EUR/USD", "GBP/USD", "USD/JPY"],
            "timeframe": "15min-1H",
            "risk_level": "Medium",
        },
        {
            "id": "news_trade",
            "name": "News Trading",
            "description": "Trade around high-impact economic releases",
            "best_pairs": ["All majors during news"],
            "timeframe": "1min-15min",
            "risk_level": "High",
        },
        {
            "id": "asian_breakout",
            "name": "Asian Range Breakout",
            "description": "Trade breakouts of Asian session range at London open",
            "best_pairs": ["EUR/USD", "GBP/USD", "EUR/JPY"],
            "timeframe": "15min-1H",
            "risk_level": "Medium",
        },
        {
            "id": "correlation",
            "name": "Currency Correlation",
            "description": "Trade strongest vs weakest currencies using strength analysis",
            "best_pairs": ["Dynamic based on strength"],
            "timeframe": "4H-Daily",
            "risk_level": "Low-Medium",
        },
    ]

