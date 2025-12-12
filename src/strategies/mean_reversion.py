"""
Mean Reversion Strategy.

Identifies overbought/oversold conditions and trades the reversion to mean.
"""

from typing import Optional, Any

import pandas as pd
import pandas_ta as ta
from loguru import logger

from src.strategies.base_strategy import BaseStrategy, Signal, SignalType


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy that fades extreme moves.
    
    Key concepts:
    - Buy when oversold, sell when overbought
    - Use Bollinger Bands and Z-score for extremes
    - Shorter holding periods than momentum
    """
    
    def __init__(self, weight: float = 0.4):
        """Initialize mean reversion strategy."""
        super().__init__(name="MeanReversion", weight=weight)
        
        self._parameters = {
            # Bollinger Bands
            "bb_period": 20,
            "bb_std": 2.0,
            "bb_extreme_std": 2.5,  # For strong signals
            
            # Z-Score
            "zscore_period": 20,
            "zscore_threshold": 2.0,
            "zscore_extreme": 2.5,
            
            # RSI for confirmation
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            
            # Mean reversion timing
            "lookback_for_extreme": 5,  # Days to detect extreme
            "max_hold_days": 10,  # Maximum holding period
            
            # Risk
            "max_loss_percent": 0.03,  # 3% stop loss
            "target_percent": 0.02,  # 2% target
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
        Analyze mean reversion opportunity.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with OHLCV data
            
        Returns:
            Signal or None
        """
        if not self.is_enabled:
            return None
        
        if data.empty or len(data) < self._parameters["bb_period"]:
            return None
        
        try:
            # Calculate indicators
            bb_signal = self._analyze_bollinger(data)
            zscore_signal = self._analyze_zscore(data)
            rsi_signal = self._analyze_rsi(data)
            
            # Generate combined signal
            signal_type, strength, confidence = self._combine_signals(
                bb_signal,
                zscore_signal,
                rsi_signal,
            )
            
            if signal_type == SignalType.HOLD:
                return None
            
            current_price = data["close"].iloc[-1]
            
            # Calculate mean target
            sma = data["close"].rolling(self._parameters["bb_period"]).mean().iloc[-1]
            
            # Set stops based on direction
            if signal_type.is_bullish:
                stop_loss = current_price * (1 - self._parameters["max_loss_percent"])
                take_profit = min(sma, current_price * (1 + self._parameters["target_percent"]))
            else:
                stop_loss = current_price * (1 + self._parameters["max_loss_percent"])
                take_profit = max(sma, current_price * (1 - self._parameters["target_percent"]))
            
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
                    "bb_signal": bb_signal,
                    "zscore_signal": zscore_signal,
                    "rsi_signal": rsi_signal,
                    "mean_target": sma,
                }
            )
            
            self.on_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing mean reversion for {symbol}: {e}")
            return None
    
    def _analyze_bollinger(self, data: pd.DataFrame) -> dict[str, Any]:
        """Analyze Bollinger Bands position."""
        bb = ta.bbands(
            data["close"],
            length=self._parameters["bb_period"],
            std=self._parameters["bb_std"],
        )
        
        if bb is None or bb.empty:
            return {"signal": SignalType.HOLD, "position": 0, "strength": 0}
        
        current_price = data["close"].iloc[-1]
        lower = bb.iloc[-1, 0]
        mid = bb.iloc[-1, 1]
        upper = bb.iloc[-1, 2]
        
        # Calculate position within bands (-1 to 1)
        band_range = upper - lower
        if band_range > 0:
            position = (current_price - mid) / (band_range / 2)
        else:
            position = 0
        
        # Determine signal
        extreme_std = self._parameters["bb_extreme_std"] / self._parameters["bb_std"]
        
        if position <= -1:
            signal = SignalType.STRONG_BUY if position <= -extreme_std else SignalType.BUY
            strength = min(1.0, abs(position))
        elif position >= 1:
            signal = SignalType.STRONG_SELL if position >= extreme_std else SignalType.SELL
            strength = min(1.0, abs(position))
        else:
            signal = SignalType.HOLD
            strength = 0
        
        return {
            "signal": signal,
            "position": position,
            "strength": strength,
            "lower": lower,
            "mid": mid,
            "upper": upper,
        }
    
    def _analyze_zscore(self, data: pd.DataFrame) -> dict[str, Any]:
        """Analyze Z-score of price."""
        period = self._parameters["zscore_period"]
        
        zscore = ta.zscore(data["close"], length=period)
        
        if zscore is None or zscore.empty:
            return {"signal": SignalType.HOLD, "zscore": 0, "strength": 0}
        
        current_zscore = zscore.iloc[-1]
        threshold = self._parameters["zscore_threshold"]
        extreme = self._parameters["zscore_extreme"]
        
        if current_zscore <= -threshold:
            signal = SignalType.STRONG_BUY if current_zscore <= -extreme else SignalType.BUY
            strength = min(1.0, abs(current_zscore) / extreme)
        elif current_zscore >= threshold:
            signal = SignalType.STRONG_SELL if current_zscore >= extreme else SignalType.SELL
            strength = min(1.0, abs(current_zscore) / extreme)
        else:
            signal = SignalType.HOLD
            strength = 0
        
        return {
            "signal": signal,
            "zscore": current_zscore,
            "strength": strength,
        }
    
    def _analyze_rsi(self, data: pd.DataFrame) -> dict[str, Any]:
        """Analyze RSI for confirmation."""
        rsi = ta.rsi(data["close"], length=self._parameters["rsi_period"])
        
        if rsi is None or rsi.empty:
            return {"signal": SignalType.HOLD, "rsi": 50, "confirms": True}
        
        current_rsi = rsi.iloc[-1]
        oversold = self._parameters["rsi_oversold"]
        overbought = self._parameters["rsi_overbought"]
        
        if current_rsi <= oversold:
            signal = SignalType.BUY
        elif current_rsi >= overbought:
            signal = SignalType.SELL
        else:
            signal = SignalType.HOLD
        
        return {
            "signal": signal,
            "rsi": current_rsi,
            "confirms": signal != SignalType.HOLD,
        }
    
    def _combine_signals(
        self,
        bb: dict,
        zscore: dict,
        rsi: dict,
    ) -> tuple[SignalType, float, float]:
        """Combine signals from different indicators."""
        
        signals = [bb["signal"], zscore["signal"], rsi["signal"]]
        
        # Count bullish and bearish signals
        bullish = sum(1 for s in signals if s in (SignalType.BUY, SignalType.STRONG_BUY))
        bearish = sum(1 for s in signals if s in (SignalType.SELL, SignalType.STRONG_SELL))
        
        # Need at least 2 of 3 signals agreeing
        if bullish >= 2:
            # Check for strong signals
            if bb["signal"] == SignalType.STRONG_BUY or zscore["signal"] == SignalType.STRONG_BUY:
                signal_type = SignalType.STRONG_BUY
            else:
                signal_type = SignalType.BUY
            
            strength = (bb["strength"] + zscore["strength"]) / 2
            confidence = bullish / 3.0
            
        elif bearish >= 2:
            if bb["signal"] == SignalType.STRONG_SELL or zscore["signal"] == SignalType.STRONG_SELL:
                signal_type = SignalType.STRONG_SELL
            else:
                signal_type = SignalType.SELL
            
            strength = (bb["strength"] + zscore["strength"]) / 2
            confidence = bearish / 3.0
            
        else:
            signal_type = SignalType.HOLD
            strength = 0
            confidence = 0
        
        # Boost confidence if RSI confirms
        if rsi["confirms"]:
            confidence = min(1.0, confidence * 1.2)
        
        return signal_type, strength, confidence

