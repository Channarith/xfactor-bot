"""
Market Regime Detection Module

Automatically classifies market conditions as Trending or Ranging,
allowing strategies to adapt their behavior accordingly.

Features:
- ADX-based trend strength detection
- Bollinger Band squeeze detection for ranges
- Momentum regime classification
- Multi-timeframe regime analysis
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger


class MarketRegime(Enum):
    """Market regime classification."""
    STRONG_UPTREND = "strong_uptrend"     # Strong bullish trend
    WEAK_UPTREND = "weak_uptrend"         # Mild bullish bias
    RANGING = "ranging"                    # Sideways/consolidation
    WEAK_DOWNTREND = "weak_downtrend"     # Mild bearish bias
    STRONG_DOWNTREND = "strong_downtrend"  # Strong bearish trend
    BREAKOUT = "breakout"                  # Potential breakout forming
    VOLATILE = "volatile"                  # High volatility, unclear direction


class TrendDirection(Enum):
    """Simplified trend direction."""
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


@dataclass
class RegimeConfig:
    """Configuration for regime detection."""
    # ADX settings
    adx_period: int = 14
    adx_strong_threshold: float = 25.0    # ADX > 25 = trending
    adx_weak_threshold: float = 20.0      # ADX 20-25 = weak trend
    
    # Bollinger Band squeeze settings
    bb_period: int = 20
    bb_std: float = 2.0
    squeeze_threshold: float = 0.03       # BB width < 3% = squeeze
    
    # Moving average settings
    fast_ma_period: int = 20
    slow_ma_period: int = 50
    
    # Momentum settings
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    # Volatility settings
    atr_period: int = 14
    volatility_lookback: int = 20


@dataclass
class RegimeAnalysis:
    """Results of regime analysis."""
    regime: MarketRegime
    direction: TrendDirection
    confidence: float                      # 0-100%
    adx_value: float
    trend_strength: str                    # "strong", "moderate", "weak", "none"
    is_ranging: bool
    is_squeezing: bool
    bb_width_pct: float
    volatility_percentile: float           # Current vol vs historical
    signals: List[str]                     # List of detected signals
    recommendation: str                    # Trading recommendation


class MarketRegimeDetector:
    """
    Detects market regime (trending vs ranging) using multiple indicators.
    
    Usage:
        detector = MarketRegimeDetector()
        analysis = detector.analyze(price_df)
        print(f"Regime: {analysis.regime.value}")
        print(f"Direction: {analysis.direction.value}")
    """
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        self.config = config or RegimeConfig()
    
    def calculate_adx(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate ADX (Average Directional Index) and DI+/DI-."""
        period = self.config.adx_period
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate +DM and -DM
        plus_dm = high.diff()
        minus_dm = low.diff().abs() * -1
        
        plus_dm = plus_dm.where((plus_dm > minus_dm.abs()) & (plus_dm > 0), 0)
        minus_dm = minus_dm.abs().where((minus_dm.abs() > plus_dm) & (minus_dm < 0), 0)
        
        # Calculate True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Smooth with EMA
        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
        
        # Calculate DX and ADX
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx = dx.ewm(span=period, adjust=False).mean()
        
        result = df.copy()
        result['adx'] = adx
        result['plus_di'] = plus_di
        result['minus_di'] = minus_di
        
        return result
    
    def calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands and squeeze indicator."""
        period = self.config.bb_period
        std = self.config.bb_std
        
        close = df['close']
        
        sma = close.rolling(window=period).mean()
        rolling_std = close.rolling(window=period).std()
        
        upper = sma + (rolling_std * std)
        lower = sma - (rolling_std * std)
        
        # BB width as percentage
        bb_width = (upper - lower) / sma * 100
        
        result = df.copy()
        result['bb_upper'] = upper
        result['bb_lower'] = lower
        result['bb_middle'] = sma
        result['bb_width'] = bb_width
        result['bb_squeeze'] = bb_width < (self.config.squeeze_threshold * 100)
        
        return result
    
    def calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate fast and slow moving averages."""
        close = df['close']
        
        result = df.copy()
        result['ma_fast'] = close.ewm(span=self.config.fast_ma_period, adjust=False).mean()
        result['ma_slow'] = close.ewm(span=self.config.slow_ma_period, adjust=False).mean()
        result['ma_trend'] = result['ma_fast'] > result['ma_slow']
        
        return result
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI."""
        period = self.config.rsi_period
        close = df['close']
        
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        result = df.copy()
        result['rsi'] = rsi
        
        return result
    
    def analyze(self, df: pd.DataFrame) -> RegimeAnalysis:
        """
        Perform comprehensive regime analysis.
        
        Args:
            df: Price DataFrame with 'open', 'high', 'low', 'close', 'volume' columns
        
        Returns:
            RegimeAnalysis with detailed market regime information
        """
        if len(df) < max(self.config.slow_ma_period, self.config.bb_period) + 5:
            logger.warning("Insufficient data for regime analysis")
            return self._default_analysis()
        
        # Calculate all indicators
        df = self.calculate_adx(df)
        df = self.calculate_bollinger_bands(df)
        df = self.calculate_moving_averages(df)
        df = self.calculate_rsi(df)
        
        # Get current values
        current = df.iloc[-1]
        adx = current.get('adx', 0) or 0
        plus_di = current.get('plus_di', 0) or 0
        minus_di = current.get('minus_di', 0) or 0
        bb_width = current.get('bb_width', 5) or 5
        bb_squeeze = current.get('bb_squeeze', False)
        ma_trend_up = current.get('ma_trend', True)
        rsi = current.get('rsi', 50) or 50
        
        # Determine trend strength
        if adx >= self.config.adx_strong_threshold:
            trend_strength = "strong"
        elif adx >= self.config.adx_weak_threshold:
            trend_strength = "moderate"
        elif adx >= 15:
            trend_strength = "weak"
        else:
            trend_strength = "none"
        
        # Determine direction
        if plus_di > minus_di:
            direction = TrendDirection.UP
        elif minus_di > plus_di:
            direction = TrendDirection.DOWN
        else:
            direction = TrendDirection.SIDEWAYS
        
        # Check if ranging (BB squeeze or low ADX)
        is_ranging = bb_squeeze or adx < self.config.adx_weak_threshold
        is_squeezing = bb_squeeze
        
        # Calculate volatility percentile
        bb_width_history = df['bb_width'].dropna().tail(self.config.volatility_lookback)
        if len(bb_width_history) > 0:
            volatility_percentile = (bb_width_history < bb_width).mean() * 100
        else:
            volatility_percentile = 50.0
        
        # Determine regime
        regime = self._determine_regime(
            adx, direction, is_ranging, is_squeezing, 
            volatility_percentile, ma_trend_up, rsi
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(adx, bb_width, trend_strength)
        
        # Generate signals
        signals = self._generate_signals(
            adx, direction, is_ranging, is_squeezing, rsi, ma_trend_up
        )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(regime, confidence, signals)
        
        return RegimeAnalysis(
            regime=regime,
            direction=direction,
            confidence=round(confidence, 1),
            adx_value=round(adx, 2),
            trend_strength=trend_strength,
            is_ranging=is_ranging,
            is_squeezing=is_squeezing,
            bb_width_pct=round(bb_width, 2),
            volatility_percentile=round(volatility_percentile, 1),
            signals=signals,
            recommendation=recommendation,
        )
    
    def _determine_regime(
        self,
        adx: float,
        direction: TrendDirection,
        is_ranging: bool,
        is_squeezing: bool,
        volatility_percentile: float,
        ma_trend_up: bool,
        rsi: float,
    ) -> MarketRegime:
        """Determine the market regime based on indicators."""
        
        # Check for squeeze/breakout setup
        if is_squeezing:
            return MarketRegime.BREAKOUT
        
        # Check for high volatility
        if volatility_percentile > 90:
            return MarketRegime.VOLATILE
        
        # Check for ranging market
        if is_ranging:
            return MarketRegime.RANGING
        
        # Trending market classification
        if adx >= self.config.adx_strong_threshold:
            if direction == TrendDirection.UP:
                return MarketRegime.STRONG_UPTREND
            else:
                return MarketRegime.STRONG_DOWNTREND
        elif adx >= self.config.adx_weak_threshold:
            if direction == TrendDirection.UP:
                return MarketRegime.WEAK_UPTREND
            else:
                return MarketRegime.WEAK_DOWNTREND
        
        return MarketRegime.RANGING
    
    def _calculate_confidence(self, adx: float, bb_width: float, trend_strength: str) -> float:
        """Calculate confidence in the regime classification."""
        confidence = 50.0  # Base confidence
        
        # ADX contribution (higher ADX = more confident in trend)
        if trend_strength == "strong":
            confidence += 30
        elif trend_strength == "moderate":
            confidence += 20
        elif trend_strength == "weak":
            confidence += 10
        
        # BB width contribution (clearer signals when not squeezing)
        if bb_width > 5:
            confidence += 10
        elif bb_width < 2:
            confidence -= 10
        
        return min(100, max(0, confidence))
    
    def _generate_signals(
        self,
        adx: float,
        direction: TrendDirection,
        is_ranging: bool,
        is_squeezing: bool,
        rsi: float,
        ma_trend_up: bool,
    ) -> List[str]:
        """Generate list of detected signals."""
        signals = []
        
        if is_squeezing:
            signals.append("BB_SQUEEZE: Potential breakout forming")
        
        if adx > self.config.adx_strong_threshold:
            signals.append(f"STRONG_TREND: ADX at {adx:.1f}")
        
        if direction == TrendDirection.UP and ma_trend_up:
            signals.append("BULLISH_ALIGNMENT: Price and MA trending up")
        elif direction == TrendDirection.DOWN and not ma_trend_up:
            signals.append("BEARISH_ALIGNMENT: Price and MA trending down")
        
        if rsi > self.config.rsi_overbought:
            signals.append(f"OVERBOUGHT: RSI at {rsi:.1f}")
        elif rsi < self.config.rsi_oversold:
            signals.append(f"OVERSOLD: RSI at {rsi:.1f}")
        
        if is_ranging:
            signals.append("RANGE_BOUND: Consider mean-reversion strategies")
        
        return signals
    
    def _generate_recommendation(
        self,
        regime: MarketRegime,
        confidence: float,
        signals: List[str],
    ) -> str:
        """Generate trading recommendation based on regime."""
        recommendations = {
            MarketRegime.STRONG_UPTREND: "Trend following: Buy dips, trail stops, add on breakouts",
            MarketRegime.WEAK_UPTREND: "Cautious long bias: Smaller positions, tighter stops",
            MarketRegime.RANGING: "Mean reversion: Buy support, sell resistance, range-bound strategies",
            MarketRegime.WEAK_DOWNTREND: "Cautious short bias: Smaller positions, tighter stops",
            MarketRegime.STRONG_DOWNTREND: "Trend following: Sell rallies, trail stops, add on breakdowns",
            MarketRegime.BREAKOUT: "Prepare for breakout: Watch for direction, enter on confirmation",
            MarketRegime.VOLATILE: "Reduce exposure: Widen stops, smaller positions, wait for clarity",
        }
        
        base_rec = recommendations.get(regime, "Wait for clearer signals")
        
        if confidence < 50:
            base_rec = f"LOW CONFIDENCE - {base_rec}"
        
        return base_rec
    
    def _default_analysis(self) -> RegimeAnalysis:
        """Return default analysis when data is insufficient."""
        return RegimeAnalysis(
            regime=MarketRegime.RANGING,
            direction=TrendDirection.SIDEWAYS,
            confidence=0.0,
            adx_value=0.0,
            trend_strength="none",
            is_ranging=True,
            is_squeezing=False,
            bb_width_pct=0.0,
            volatility_percentile=50.0,
            signals=["INSUFFICIENT_DATA: Need more price history"],
            recommendation="Wait for more data before trading",
        )


# Singleton instance
_detector: Optional[MarketRegimeDetector] = None


def get_regime_detector(config: Optional[RegimeConfig] = None) -> MarketRegimeDetector:
    """Get or create the regime detector singleton."""
    global _detector
    if _detector is None or config is not None:
        _detector = MarketRegimeDetector(config)
    return _detector


def detect_regime(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Convenience function to detect market regime.
    
    Args:
        df: Price DataFrame
    
    Returns:
        Dictionary with regime information
    """
    detector = get_regime_detector()
    analysis = detector.analyze(df)
    
    return {
        "regime": analysis.regime.value,
        "direction": analysis.direction.value,
        "confidence": analysis.confidence,
        "adx": analysis.adx_value,
        "trend_strength": analysis.trend_strength,
        "is_ranging": analysis.is_ranging,
        "is_squeezing": analysis.is_squeezing,
        "signals": analysis.signals,
        "recommendation": analysis.recommendation,
    }

