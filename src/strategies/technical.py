"""
Technical Analysis Strategy.

Uses indicators like RSI, MACD, Moving Averages, and Bollinger Bands
to generate trading signals.
"""

from typing import Optional, Any

import pandas as pd
import pandas_ta as ta
from loguru import logger

from src.strategies.base_strategy import BaseStrategy, Signal, SignalType
from src.config.settings import get_settings


class TechnicalStrategy(BaseStrategy):
    """
    Technical analysis strategy using multiple indicators.
    
    Indicators used:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Moving Averages (SMA/EMA crossovers)
    - Bollinger Bands
    - Volume analysis
    """
    
    def __init__(self, weight: float = 0.6):
        """Initialize technical strategy."""
        super().__init__(name="Technical", weight=weight)
        
        settings = get_settings()
        self._parameters = {
            # RSI
            "rsi_period": 14,
            "rsi_oversold": settings.rsi_oversold,
            "rsi_overbought": settings.rsi_overbought,
            
            # MACD
            "macd_fast": settings.macd_fast,
            "macd_slow": settings.macd_slow,
            "macd_signal": settings.macd_signal,
            
            # Moving Averages
            "ma_fast": settings.ma_fast_period,
            "ma_slow": settings.ma_slow_period,
            
            # Bollinger Bands
            "bb_period": 20,
            "bb_std": 2.0,
            
            # Volume
            "volume_ma_period": 20,
            "volume_threshold": 1.5,  # Volume must be 1.5x average
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
        Analyze a symbol using technical indicators.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with OHLCV data
            
        Returns:
            Signal or None
        """
        if not self.is_enabled:
            return None
        
        if data.empty or len(data) < self._parameters["ma_slow"]:
            logger.warning(f"Insufficient data for {symbol}")
            return None
        
        try:
            # Calculate indicators
            signals = self._calculate_signals(data)
            
            # Aggregate signals
            signal_type, strength, confidence = self._aggregate_signals(signals)
            
            if signal_type == SignalType.HOLD:
                return None
            
            # Calculate entry, stop loss, take profit
            current_price = data["close"].iloc[-1]
            atr = self._calculate_atr(data)
            
            if signal_type.is_bullish:
                stop_loss = current_price - (2 * atr)
                take_profit = current_price + (3 * atr)
            else:
                stop_loss = current_price + (2 * atr)
                take_profit = current_price - (3 * atr)
            
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
                    "indicators": signals,
                    "atr": atr,
                }
            )
            
            self.on_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def _calculate_signals(self, data: pd.DataFrame) -> dict[str, dict]:
        """Calculate all technical indicator signals."""
        signals = {}
        
        # RSI
        rsi = ta.rsi(data["close"], length=self._parameters["rsi_period"])
        if rsi is not None and not rsi.empty:
            current_rsi = rsi.iloc[-1]
            signals["rsi"] = {
                "value": current_rsi,
                "signal": self._rsi_signal(current_rsi),
                "weight": 0.25,
            }
        
        # MACD
        macd = ta.macd(
            data["close"],
            fast=self._parameters["macd_fast"],
            slow=self._parameters["macd_slow"],
            signal=self._parameters["macd_signal"],
        )
        if macd is not None and not macd.empty:
            macd_line = macd.iloc[-1, 0]  # MACD line
            signal_line = macd.iloc[-1, 2]  # Signal line
            histogram = macd.iloc[-1, 1]  # Histogram
            signals["macd"] = {
                "macd": macd_line,
                "signal": signal_line,
                "histogram": histogram,
                "signal": self._macd_signal(macd_line, signal_line, histogram),
                "weight": 0.25,
            }
        
        # Moving Average Crossover
        sma_fast = ta.sma(data["close"], length=self._parameters["ma_fast"])
        sma_slow = ta.sma(data["close"], length=self._parameters["ma_slow"])
        if sma_fast is not None and sma_slow is not None:
            signals["ma_crossover"] = {
                "fast": sma_fast.iloc[-1],
                "slow": sma_slow.iloc[-1],
                "signal": self._ma_signal(sma_fast, sma_slow),
                "weight": 0.25,
            }
        
        # Bollinger Bands
        bb = ta.bbands(
            data["close"],
            length=self._parameters["bb_period"],
            std=self._parameters["bb_std"],
        )
        if bb is not None and not bb.empty:
            current_price = data["close"].iloc[-1]
            lower = bb.iloc[-1, 0]  # Lower band
            mid = bb.iloc[-1, 1]  # Middle band
            upper = bb.iloc[-1, 2]  # Upper band
            signals["bollinger"] = {
                "lower": lower,
                "mid": mid,
                "upper": upper,
                "price": current_price,
                "signal": self._bb_signal(current_price, lower, mid, upper),
                "weight": 0.15,
            }
        
        # Volume Confirmation
        volume_sma = ta.sma(data["volume"], length=self._parameters["volume_ma_period"])
        if volume_sma is not None:
            current_volume = data["volume"].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            signals["volume"] = {
                "current": current_volume,
                "average": avg_volume,
                "ratio": volume_ratio,
                "confirms": volume_ratio >= self._parameters["volume_threshold"],
                "weight": 0.10,
            }
        
        return signals
    
    def _rsi_signal(self, rsi: float) -> SignalType:
        """Determine signal from RSI."""
        if rsi <= self._parameters["rsi_oversold"]:
            return SignalType.STRONG_BUY if rsi <= 20 else SignalType.BUY
        elif rsi >= self._parameters["rsi_overbought"]:
            return SignalType.STRONG_SELL if rsi >= 80 else SignalType.SELL
        return SignalType.HOLD
    
    def _macd_signal(self, macd: float, signal: float, histogram: float) -> SignalType:
        """Determine signal from MACD."""
        # Bullish crossover
        if macd > signal and histogram > 0:
            return SignalType.BUY
        # Bearish crossover
        elif macd < signal and histogram < 0:
            return SignalType.SELL
        return SignalType.HOLD
    
    def _ma_signal(self, fast: pd.Series, slow: pd.Series) -> SignalType:
        """Determine signal from MA crossover."""
        if len(fast) < 2 or len(slow) < 2:
            return SignalType.HOLD
        
        # Current state
        fast_above = fast.iloc[-1] > slow.iloc[-1]
        # Previous state
        was_fast_above = fast.iloc[-2] > slow.iloc[-2]
        
        # Bullish crossover
        if fast_above and not was_fast_above:
            return SignalType.BUY
        # Bearish crossover
        elif not fast_above and was_fast_above:
            return SignalType.SELL
        # Trending up
        elif fast_above:
            return SignalType.BUY
        # Trending down
        else:
            return SignalType.SELL
    
    def _bb_signal(
        self,
        price: float,
        lower: float,
        mid: float,
        upper: float,
    ) -> SignalType:
        """Determine signal from Bollinger Bands."""
        # Price below lower band (oversold)
        if price <= lower:
            return SignalType.BUY
        # Price above upper band (overbought)
        elif price >= upper:
            return SignalType.SELL
        # Price between mid and upper (bullish momentum)
        elif price > mid:
            return SignalType.HOLD  # Slight bullish bias
        # Price between lower and mid (bearish momentum)
        else:
            return SignalType.HOLD  # Slight bearish bias
    
    def _aggregate_signals(
        self,
        signals: dict[str, dict],
    ) -> tuple[SignalType, float, float]:
        """
        Aggregate individual signals into final signal.
        
        Returns:
            Tuple of (signal_type, strength, confidence)
        """
        if not signals:
            return SignalType.HOLD, 0.0, 0.0
        
        bullish_score = 0.0
        bearish_score = 0.0
        total_weight = 0.0
        
        for name, data in signals.items():
            if "signal" not in data or "weight" not in data:
                continue
            
            sig = data["signal"]
            weight = data["weight"]
            total_weight += weight
            
            if sig == SignalType.STRONG_BUY:
                bullish_score += weight * 1.0
            elif sig == SignalType.BUY:
                bullish_score += weight * 0.5
            elif sig == SignalType.STRONG_SELL:
                bearish_score += weight * 1.0
            elif sig == SignalType.SELL:
                bearish_score += weight * 0.5
        
        if total_weight == 0:
            return SignalType.HOLD, 0.0, 0.0
        
        # Normalize scores
        bullish_score /= total_weight
        bearish_score /= total_weight
        
        # Check volume confirmation
        volume_confirms = signals.get("volume", {}).get("confirms", True)
        
        # Determine signal
        net_score = bullish_score - bearish_score
        
        if net_score >= 0.6 and volume_confirms:
            signal_type = SignalType.STRONG_BUY
        elif net_score >= 0.3:
            signal_type = SignalType.BUY
        elif net_score <= -0.6 and volume_confirms:
            signal_type = SignalType.STRONG_SELL
        elif net_score <= -0.3:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD
        
        strength = abs(net_score)
        confidence = min(1.0, len(signals) / 5.0)  # More indicators = higher confidence
        
        return signal_type, strength, confidence
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        atr = ta.atr(data["high"], data["low"], data["close"], length=period)
        if atr is not None and not atr.empty:
            return atr.iloc[-1]
        return data["close"].iloc[-1] * 0.02  # Default to 2% of price

