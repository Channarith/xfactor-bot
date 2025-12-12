"""
Momentum Trading Strategy.

Identifies stocks with strong price momentum and follows the trend.
"""

from typing import Optional, Any

import pandas as pd
import pandas_ta as ta
from loguru import logger

from src.strategies.base_strategy import BaseStrategy, Signal, SignalType
from src.config.settings import get_settings


class MomentumStrategy(BaseStrategy):
    """
    Momentum strategy that follows strong price trends.
    
    Key concepts:
    - Buy winners, sell losers
    - Relative strength ranking
    - Trend following with momentum confirmation
    """
    
    def __init__(self, weight: float = 0.5):
        """Initialize momentum strategy."""
        super().__init__(name="Momentum", weight=weight)
        
        self._parameters = {
            # Lookback periods
            "short_momentum_period": 5,    # 1 week
            "medium_momentum_period": 20,  # 1 month
            "long_momentum_period": 60,    # 3 months
            
            # Thresholds
            "momentum_threshold": 0.05,     # 5% minimum move
            "strong_momentum_threshold": 0.10,  # 10% for strong signal
            "top_percentile": 10,           # Top 10% performers
            
            # Volume confirmation
            "volume_ma_period": 20,
            "min_volume_ratio": 1.2,
            
            # Trend confirmation
            "adx_period": 14,
            "adx_threshold": 25,  # ADX > 25 indicates strong trend
            
            # Risk
            "max_drawdown_from_high": 0.08,  # Exit if 8% below recent high
        }
    
    def get_parameters(self) -> dict[str, Any]:
        """Get current parameters."""
        return self._parameters.copy()
    
    async def analyze(
        self,
        symbol: str,
        data: pd.DataFrame,
        **kwargs,
    ) -> Optional[Signal]:
        """
        Analyze momentum for a symbol.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with OHLCV data
            
        Returns:
            Signal or None
        """
        if not self.is_enabled:
            return None
        
        if data.empty or len(data) < self._parameters["long_momentum_period"]:
            return None
        
        try:
            # Calculate momentum scores
            momentum_scores = self._calculate_momentum(data)
            
            # Calculate trend strength
            trend_strength = self._calculate_trend_strength(data)
            
            # Check volume confirmation
            volume_confirms = self._check_volume(data)
            
            # Generate signal
            signal_type, strength, confidence = self._generate_signal(
                momentum_scores,
                trend_strength,
                volume_confirms,
            )
            
            if signal_type == SignalType.HOLD:
                return None
            
            current_price = data["close"].iloc[-1]
            atr = self._calculate_atr(data)
            
            # Calculate stops
            if signal_type.is_bullish:
                stop_loss = current_price - (2.5 * atr)
                take_profit = current_price + (4 * atr)
            else:
                stop_loss = current_price + (2.5 * atr)
                take_profit = current_price - (4 * atr)
            
            signal = Signal(
                symbol=symbol,
                signal_type=signal_type,
                strategy=self.name,
                strength=strength,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "momentum_scores": momentum_scores,
                    "trend_strength": trend_strength,
                    "volume_confirms": volume_confirms,
                    "atr": atr,
                }
            )
            
            self.on_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing momentum for {symbol}: {e}")
            return None
    
    def _calculate_momentum(self, data: pd.DataFrame) -> dict[str, float]:
        """Calculate momentum over different periods."""
        close = data["close"]
        
        # Price momentum (returns)
        short_return = (close.iloc[-1] / close.iloc[-self._parameters["short_momentum_period"]] - 1)
        medium_return = (close.iloc[-1] / close.iloc[-self._parameters["medium_momentum_period"]] - 1)
        long_return = (close.iloc[-1] / close.iloc[-self._parameters["long_momentum_period"]] - 1)
        
        # Rate of change
        roc = ta.roc(close, length=self._parameters["medium_momentum_period"])
        current_roc = roc.iloc[-1] if roc is not None and not roc.empty else 0
        
        # Momentum indicator
        mom = ta.mom(close, length=self._parameters["medium_momentum_period"])
        current_mom = mom.iloc[-1] if mom is not None and not mom.empty else 0
        
        return {
            "short": short_return,
            "medium": medium_return,
            "long": long_return,
            "roc": current_roc,
            "mom": current_mom,
            "composite": (short_return * 0.4 + medium_return * 0.35 + long_return * 0.25),
        }
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> dict[str, Any]:
        """Calculate trend strength using ADX."""
        adx = ta.adx(
            data["high"],
            data["low"],
            data["close"],
            length=self._parameters["adx_period"],
        )
        
        if adx is None or adx.empty:
            return {"adx": 0, "plus_di": 0, "minus_di": 0, "trending": False}
        
        current_adx = adx.iloc[-1, 0]  # ADX
        plus_di = adx.iloc[-1, 1]  # +DI
        minus_di = adx.iloc[-1, 2]  # -DI
        
        return {
            "adx": current_adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "trending": current_adx >= self._parameters["adx_threshold"],
            "bullish_trend": plus_di > minus_di,
            "bearish_trend": minus_di > plus_di,
        }
    
    def _check_volume(self, data: pd.DataFrame) -> bool:
        """Check if volume confirms the move."""
        volume_sma = ta.sma(data["volume"], length=self._parameters["volume_ma_period"])
        
        if volume_sma is None or volume_sma.empty:
            return True  # Assume confirmation if can't calculate
        
        current_volume = data["volume"].iloc[-1]
        avg_volume = volume_sma.iloc[-1]
        
        if avg_volume > 0:
            return current_volume / avg_volume >= self._parameters["min_volume_ratio"]
        return True
    
    def _generate_signal(
        self,
        momentum: dict[str, float],
        trend: dict[str, Any],
        volume_confirms: bool,
    ) -> tuple[SignalType, float, float]:
        """Generate signal from momentum analysis."""
        
        composite = momentum["composite"]
        threshold = self._parameters["momentum_threshold"]
        strong_threshold = self._parameters["strong_momentum_threshold"]
        
        # Default
        signal_type = SignalType.HOLD
        strength = abs(composite)
        confidence = 0.5
        
        # Strong upward momentum
        if composite >= strong_threshold:
            if trend["trending"] and trend["bullish_trend"] and volume_confirms:
                signal_type = SignalType.STRONG_BUY
                confidence = 0.85
            else:
                signal_type = SignalType.BUY
                confidence = 0.65
        
        # Moderate upward momentum
        elif composite >= threshold:
            if trend["bullish_trend"]:
                signal_type = SignalType.BUY
                confidence = 0.6
        
        # Strong downward momentum
        elif composite <= -strong_threshold:
            if trend["trending"] and trend["bearish_trend"] and volume_confirms:
                signal_type = SignalType.STRONG_SELL
                confidence = 0.85
            else:
                signal_type = SignalType.SELL
                confidence = 0.65
        
        # Moderate downward momentum
        elif composite <= -threshold:
            if trend["bearish_trend"]:
                signal_type = SignalType.SELL
                confidence = 0.6
        
        # Adjust confidence based on ADX
        if trend["trending"]:
            confidence = min(1.0, confidence * 1.2)
        
        # Reduce confidence if volume doesn't confirm
        if not volume_confirms:
            confidence *= 0.8
        
        return signal_type, strength, confidence
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        atr = ta.atr(data["high"], data["low"], data["close"], length=period)
        if atr is not None and not atr.empty:
            return atr.iloc[-1]
        return data["close"].iloc[-1] * 0.02
    
    async def rank_symbols(
        self,
        symbols: list[str],
        data: dict[str, pd.DataFrame],
    ) -> list[tuple[str, float]]:
        """
        Rank symbols by momentum.
        
        Args:
            symbols: List of symbols
            data: Dictionary of symbol -> DataFrame
            
        Returns:
            List of (symbol, momentum_score) sorted by score descending
        """
        rankings = []
        
        for symbol in symbols:
            if symbol not in data or data[symbol].empty:
                continue
            
            df = data[symbol]
            if len(df) < self._parameters["long_momentum_period"]:
                continue
            
            momentum = self._calculate_momentum(df)
            rankings.append((symbol, momentum["composite"]))
        
        # Sort by momentum score descending
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return rankings

