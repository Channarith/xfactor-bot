"""
Volatility-Adaptive Stop Loss / Take Profit Module

Uses ATR (Average True Range) to dynamically adjust stop losses and take profits
based on current market volatility. Inspired by Quantvue's Qkronos_EVO strategy.

Features:
- ATR-based dynamic stop loss
- Volatility multipliers for different market conditions
- Trailing stops that adapt to volatility
- Time-decay adjustments for longer holds
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger


class VolatilityLevel(Enum):
    """Market volatility classification."""
    LOW = "low"           # ATR < 1 std below mean
    NORMAL = "normal"     # ATR within 1 std of mean
    HIGH = "high"         # ATR > 1 std above mean
    EXTREME = "extreme"   # ATR > 2 std above mean


@dataclass
class VolatilityAdaptiveConfig:
    """Configuration for volatility-adaptive stops."""
    # ATR settings
    atr_period: int = 14
    atr_multiplier_sl: float = 2.0      # Stop loss = ATR * this multiplier
    atr_multiplier_tp: float = 3.0      # Take profit = ATR * this multiplier
    
    # Volatility adjustments
    low_vol_multiplier: float = 0.8     # Tighter stops in low volatility
    high_vol_multiplier: float = 1.5    # Wider stops in high volatility
    extreme_vol_multiplier: float = 2.0 # Much wider stops in extreme volatility
    
    # Trailing stop settings
    enable_trailing: bool = True
    trailing_activation_pct: float = 0.5  # Activate trailing at 50% of TP
    trailing_step_atr: float = 0.5        # Trail by 0.5 ATR
    
    # Time decay (optional)
    enable_time_decay: bool = False
    time_decay_hours: int = 24            # Start decaying after 24 hours
    time_decay_rate: float = 0.1          # Tighten by 10% per decay period
    
    # Risk limits
    max_sl_percent: float = 5.0           # Maximum 5% stop loss
    min_sl_percent: float = 0.5           # Minimum 0.5% stop loss
    max_tp_percent: float = 20.0          # Maximum 20% take profit
    min_tp_percent: float = 1.0           # Minimum 1% take profit


@dataclass
class AdaptiveStopLevels:
    """Calculated stop loss and take profit levels."""
    entry_price: float
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float] = None
    atr_value: float = 0.0
    volatility_level: VolatilityLevel = VolatilityLevel.NORMAL
    sl_percent: float = 0.0
    tp_percent: float = 0.0
    risk_reward_ratio: float = 0.0


class VolatilityAdaptiveEngine:
    """
    Engine for calculating volatility-adaptive stop losses and take profits.
    
    Usage:
        engine = VolatilityAdaptiveEngine(config)
        levels = engine.calculate_stops(price_data, entry_price, is_long=True)
        print(f"SL: {levels.stop_loss}, TP: {levels.take_profit}")
    """
    
    def __init__(self, config: Optional[VolatilityAdaptiveConfig] = None):
        self.config = config or VolatilityAdaptiveConfig()
        self._atr_history: List[float] = []
        self._atr_mean: float = 0.0
        self._atr_std: float = 0.0
    
    def calculate_atr(self, df: pd.DataFrame, period: Optional[int] = None) -> float:
        """
        Calculate Average True Range.
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            period: ATR period (uses config default if not specified)
        
        Returns:
            Current ATR value
        """
        period = period or self.config.atr_period
        
        if len(df) < period + 1:
            logger.warning(f"Insufficient data for ATR calculation (need {period + 1}, have {len(df)})")
            # Fallback: use simple range
            return (df['high'].iloc[-1] - df['low'].iloc[-1])
        
        # True Range calculation
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR is the EMA of True Range
        atr = true_range.ewm(span=period, adjust=False).mean()
        
        return atr.iloc[-1]
    
    def classify_volatility(self, current_atr: float, historical_atrs: Optional[List[float]] = None) -> VolatilityLevel:
        """
        Classify current volatility level based on ATR history.
        
        Args:
            current_atr: Current ATR value
            historical_atrs: List of historical ATR values (uses internal history if not provided)
        
        Returns:
            VolatilityLevel classification
        """
        atrs = historical_atrs or self._atr_history
        
        if len(atrs) < 20:
            # Not enough history, assume normal
            return VolatilityLevel.NORMAL
        
        mean_atr = np.mean(atrs)
        std_atr = np.std(atrs)
        
        # Store for later use
        self._atr_mean = mean_atr
        self._atr_std = std_atr
        
        if std_atr == 0:
            return VolatilityLevel.NORMAL
        
        z_score = (current_atr - mean_atr) / std_atr
        
        if z_score > 2:
            return VolatilityLevel.EXTREME
        elif z_score > 1:
            return VolatilityLevel.HIGH
        elif z_score < -1:
            return VolatilityLevel.LOW
        else:
            return VolatilityLevel.NORMAL
    
    def get_volatility_multiplier(self, vol_level: VolatilityLevel) -> float:
        """Get the appropriate multiplier for the volatility level."""
        multipliers = {
            VolatilityLevel.LOW: self.config.low_vol_multiplier,
            VolatilityLevel.NORMAL: 1.0,
            VolatilityLevel.HIGH: self.config.high_vol_multiplier,
            VolatilityLevel.EXTREME: self.config.extreme_vol_multiplier,
        }
        return multipliers.get(vol_level, 1.0)
    
    def calculate_stops(
        self,
        df: pd.DataFrame,
        entry_price: float,
        is_long: bool = True,
        custom_atr: Optional[float] = None,
    ) -> AdaptiveStopLevels:
        """
        Calculate volatility-adaptive stop loss and take profit levels.
        
        Args:
            df: Price DataFrame with 'high', 'low', 'close' columns
            entry_price: Entry price of the position
            is_long: True for long positions, False for short
            custom_atr: Optional custom ATR value (skips calculation if provided)
        
        Returns:
            AdaptiveStopLevels with calculated levels
        """
        # Calculate or use provided ATR
        atr = custom_atr if custom_atr is not None else self.calculate_atr(df)
        
        # Update ATR history
        self._atr_history.append(atr)
        if len(self._atr_history) > 100:
            self._atr_history = self._atr_history[-100:]
        
        # Classify volatility
        vol_level = self.classify_volatility(atr)
        vol_multiplier = self.get_volatility_multiplier(vol_level)
        
        # Calculate base distances
        sl_distance = atr * self.config.atr_multiplier_sl * vol_multiplier
        tp_distance = atr * self.config.atr_multiplier_tp * vol_multiplier
        
        # Calculate percentages
        sl_percent = (sl_distance / entry_price) * 100
        tp_percent = (tp_distance / entry_price) * 100
        
        # Apply limits
        sl_percent = max(self.config.min_sl_percent, min(sl_percent, self.config.max_sl_percent))
        tp_percent = max(self.config.min_tp_percent, min(tp_percent, self.config.max_tp_percent))
        
        # Recalculate distances based on limited percentages
        sl_distance = entry_price * (sl_percent / 100)
        tp_distance = entry_price * (tp_percent / 100)
        
        # Calculate actual levels based on direction
        if is_long:
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        
        # Calculate risk/reward ratio
        risk_reward = tp_distance / sl_distance if sl_distance > 0 else 0
        
        return AdaptiveStopLevels(
            entry_price=entry_price,
            stop_loss=round(stop_loss, 4),
            take_profit=round(take_profit, 4),
            atr_value=round(atr, 4),
            volatility_level=vol_level,
            sl_percent=round(sl_percent, 2),
            tp_percent=round(tp_percent, 2),
            risk_reward_ratio=round(risk_reward, 2),
        )
    
    def update_trailing_stop(
        self,
        levels: AdaptiveStopLevels,
        current_price: float,
        is_long: bool = True,
    ) -> AdaptiveStopLevels:
        """
        Update trailing stop based on current price movement.
        
        Args:
            levels: Current stop levels
            current_price: Current market price
            is_long: True for long positions
        
        Returns:
            Updated AdaptiveStopLevels with new trailing stop
        """
        if not self.config.enable_trailing:
            return levels
        
        entry = levels.entry_price
        tp = levels.take_profit
        current_sl = levels.trailing_stop or levels.stop_loss
        
        # Calculate progress towards take profit
        if is_long:
            total_distance = tp - entry
            current_distance = current_price - entry
        else:
            total_distance = entry - tp
            current_distance = entry - current_price
        
        if total_distance <= 0:
            return levels
        
        progress = current_distance / total_distance
        
        # Only activate trailing after reaching activation threshold
        if progress < self.config.trailing_activation_pct:
            return levels
        
        # Calculate new trailing stop
        trail_distance = levels.atr_value * self.config.trailing_step_atr
        
        if is_long:
            new_trailing_stop = current_price - trail_distance
            # Only move stop up, never down
            if new_trailing_stop > current_sl:
                levels.trailing_stop = round(new_trailing_stop, 4)
        else:
            new_trailing_stop = current_price + trail_distance
            # Only move stop down, never up
            if new_trailing_stop < current_sl:
                levels.trailing_stop = round(new_trailing_stop, 4)
        
        return levels


# Singleton instance for easy access
_engine: Optional[VolatilityAdaptiveEngine] = None


def get_volatility_engine(config: Optional[VolatilityAdaptiveConfig] = None) -> VolatilityAdaptiveEngine:
    """Get or create the volatility adaptive engine singleton."""
    global _engine
    if _engine is None or config is not None:
        _engine = VolatilityAdaptiveEngine(config)
    return _engine


def calculate_adaptive_stops(
    df: pd.DataFrame,
    entry_price: float,
    is_long: bool = True,
    atr_period: int = 14,
    sl_multiplier: float = 2.0,
    tp_multiplier: float = 3.0,
) -> Tuple[float, float, dict]:
    """
    Convenience function to calculate adaptive stops.
    
    Args:
        df: Price DataFrame
        entry_price: Entry price
        is_long: Long or short position
        atr_period: ATR period
        sl_multiplier: Stop loss ATR multiplier
        tp_multiplier: Take profit ATR multiplier
    
    Returns:
        Tuple of (stop_loss, take_profit, details_dict)
    """
    config = VolatilityAdaptiveConfig(
        atr_period=atr_period,
        atr_multiplier_sl=sl_multiplier,
        atr_multiplier_tp=tp_multiplier,
    )
    engine = VolatilityAdaptiveEngine(config)
    levels = engine.calculate_stops(df, entry_price, is_long)
    
    details = {
        "atr": levels.atr_value,
        "volatility": levels.volatility_level.value,
        "sl_percent": levels.sl_percent,
        "tp_percent": levels.tp_percent,
        "risk_reward": levels.risk_reward_ratio,
    }
    
    return levels.stop_loss, levels.take_profit, details

