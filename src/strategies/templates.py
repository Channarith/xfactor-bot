"""
Strategy Templates Library

Pre-configured strategy templates that users can select and customize.
Inspired by Quantvue's strategy marketplace concept.

Templates include:
- Trend Following strategies
- Mean Reversion strategies
- Breakout strategies
- Scalping strategies
- Swing Trading strategies
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import json

from loguru import logger


class StrategyCategory(Enum):
    """Strategy template categories."""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    SWING = "swing"
    MOMENTUM = "momentum"
    ARBITRAGE = "arbitrage"
    MARKET_MAKING = "market_making"


class RiskLevel(Enum):
    """Risk level classification."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class TimeFrame(Enum):
    """Trading timeframe."""
    SCALPING = "1m-5m"
    INTRADAY = "15m-1h"
    SWING = "4h-1d"
    POSITION = "1d-1w"


@dataclass
class StrategyTemplate:
    """A pre-configured strategy template."""
    id: str
    name: str
    description: str
    category: StrategyCategory
    risk_level: RiskLevel
    timeframe: TimeFrame
    
    # Strategy parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Indicators used
    indicators: List[str] = field(default_factory=list)
    
    # Entry/Exit rules (human-readable)
    entry_rules: List[str] = field(default_factory=list)
    exit_rules: List[str] = field(default_factory=list)
    
    # Risk management
    stop_loss_type: str = "atr"  # fixed, atr, percent, trailing
    take_profit_type: str = "atr"
    max_position_size_pct: float = 5.0
    max_daily_trades: int = 10
    
    # Performance expectations
    expected_win_rate: float = 0.0
    expected_risk_reward: float = 0.0
    
    # Asset classes
    suitable_for: List[str] = field(default_factory=list)
    
    # Metadata
    author: str = "XFactor Bot"
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "timeframe": self.timeframe.value,
            "parameters": self.parameters,
            "indicators": self.indicators,
            "entry_rules": self.entry_rules,
            "exit_rules": self.exit_rules,
            "stop_loss_type": self.stop_loss_type,
            "take_profit_type": self.take_profit_type,
            "max_position_size_pct": self.max_position_size_pct,
            "expected_win_rate": self.expected_win_rate,
            "expected_risk_reward": self.expected_risk_reward,
            "suitable_for": self.suitable_for,
            "author": self.author,
            "version": self.version,
            "tags": self.tags,
        }


# =============================================================================
# Pre-built Strategy Templates
# =============================================================================

STRATEGY_TEMPLATES: Dict[str, StrategyTemplate] = {}


def register_template(template: StrategyTemplate) -> None:
    """Register a strategy template."""
    STRATEGY_TEMPLATES[template.id] = template
    logger.debug(f"Registered strategy template: {template.id}")


# --- Trend Following Templates ---

register_template(StrategyTemplate(
    id="trend_ma_crossover",
    name="Moving Average Crossover",
    description="Classic trend following using EMA crossovers. Buys when fast EMA crosses above slow EMA, sells on cross below.",
    category=StrategyCategory.TREND_FOLLOWING,
    risk_level=RiskLevel.MODERATE,
    timeframe=TimeFrame.SWING,
    parameters={
        "fast_ema": 20,
        "slow_ema": 50,
        "confirmation_ema": 200,
        "volume_filter": True,
    },
    indicators=["EMA(20)", "EMA(50)", "EMA(200)", "Volume"],
    entry_rules=[
        "Fast EMA (20) crosses above Slow EMA (50)",
        "Price above 200 EMA for trend confirmation",
        "Volume above 20-period average",
    ],
    exit_rules=[
        "Fast EMA crosses below Slow EMA",
        "Price closes below 200 EMA",
        "ATR-based trailing stop triggered",
    ],
    stop_loss_type="atr",
    take_profit_type="trailing",
    expected_win_rate=45.0,
    expected_risk_reward=2.5,
    suitable_for=["stocks", "etf", "forex", "crypto"],
    tags=["beginner", "trend", "ema", "crossover"],
))

register_template(StrategyTemplate(
    id="trend_adx_macd",
    name="ADX + MACD Trend Rider",
    description="Uses ADX to confirm trend strength and MACD for entry timing. Only trades in strong trends (ADX > 25).",
    category=StrategyCategory.TREND_FOLLOWING,
    risk_level=RiskLevel.MODERATE,
    timeframe=TimeFrame.SWING,
    parameters={
        "adx_period": 14,
        "adx_threshold": 25,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
    },
    indicators=["ADX(14)", "MACD(12,26,9)", "DI+", "DI-"],
    entry_rules=[
        "ADX > 25 (strong trend)",
        "MACD crosses above signal line",
        "DI+ > DI- for longs, DI- > DI+ for shorts",
    ],
    exit_rules=[
        "MACD crosses below signal line",
        "ADX falls below 20",
        "DI crossover against position",
    ],
    expected_win_rate=48.0,
    expected_risk_reward=2.0,
    suitable_for=["stocks", "futures", "forex"],
    tags=["intermediate", "trend", "adx", "macd"],
))

register_template(StrategyTemplate(
    id="trend_supertrend",
    name="SuperTrend Strategy",
    description="Simple yet effective trend following using the SuperTrend indicator. Great for catching major moves.",
    category=StrategyCategory.TREND_FOLLOWING,
    risk_level=RiskLevel.CONSERVATIVE,
    timeframe=TimeFrame.SWING,
    parameters={
        "atr_period": 10,
        "atr_multiplier": 3.0,
        "trend_filter_period": 200,
    },
    indicators=["SuperTrend(10,3)", "EMA(200)"],
    entry_rules=[
        "SuperTrend flips bullish (green)",
        "Price above 200 EMA for longs",
        "Wait for first pullback to SuperTrend line",
    ],
    exit_rules=[
        "SuperTrend flips bearish (red)",
        "Price closes below SuperTrend line",
    ],
    expected_win_rate=42.0,
    expected_risk_reward=3.0,
    suitable_for=["stocks", "crypto", "futures"],
    tags=["beginner", "trend", "supertrend"],
))

# --- Mean Reversion Templates ---

register_template(StrategyTemplate(
    id="reversion_rsi_bb",
    name="RSI + Bollinger Bands Mean Reversion",
    description="Buys oversold conditions and sells overbought. Uses BB for range and RSI for momentum confirmation.",
    category=StrategyCategory.MEAN_REVERSION,
    risk_level=RiskLevel.MODERATE,
    timeframe=TimeFrame.INTRADAY,
    parameters={
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "bb_period": 20,
        "bb_std": 2.0,
    },
    indicators=["RSI(14)", "BB(20,2)"],
    entry_rules=[
        "Price touches lower Bollinger Band",
        "RSI < 30 (oversold)",
        "Look for bullish candlestick pattern",
    ],
    exit_rules=[
        "Price reaches middle or upper BB",
        "RSI > 50 or reaches overbought",
        "Fixed profit target of 1.5x risk",
    ],
    expected_win_rate=55.0,
    expected_risk_reward=1.5,
    suitable_for=["stocks", "etf", "forex"],
    tags=["intermediate", "mean-reversion", "rsi", "bollinger"],
))

register_template(StrategyTemplate(
    id="reversion_zscore",
    name="Z-Score Mean Reversion",
    description="Statistical mean reversion using Z-score. Trades when price deviates significantly from average.",
    category=StrategyCategory.MEAN_REVERSION,
    risk_level=RiskLevel.AGGRESSIVE,
    timeframe=TimeFrame.INTRADAY,
    parameters={
        "lookback_period": 20,
        "entry_zscore": 2.0,
        "exit_zscore": 0.5,
        "max_zscore": 3.5,
    },
    indicators=["Z-Score(20)", "SMA(20)", "StdDev(20)"],
    entry_rules=[
        "Z-Score < -2 (buy) or > 2 (sell)",
        "Check for no major news/events",
        "Volume not abnormally high",
    ],
    exit_rules=[
        "Z-Score returns to ±0.5",
        "Time-based exit after 5 bars",
        "Stop at Z-Score ±3.5",
    ],
    expected_win_rate=60.0,
    expected_risk_reward=1.2,
    suitable_for=["stocks", "etf", "pairs"],
    tags=["advanced", "statistical", "mean-reversion"],
))

# --- Breakout Templates ---

register_template(StrategyTemplate(
    id="breakout_donchian",
    name="Donchian Channel Breakout",
    description="Classic turtle trading breakout. Enters on new 20-day highs, exits on 10-day lows.",
    category=StrategyCategory.BREAKOUT,
    risk_level=RiskLevel.AGGRESSIVE,
    timeframe=TimeFrame.SWING,
    parameters={
        "entry_period": 20,
        "exit_period": 10,
        "atr_multiplier": 2.0,
    },
    indicators=["Donchian(20)", "Donchian(10)", "ATR(14)"],
    entry_rules=[
        "Price breaks above 20-day high (long)",
        "Price breaks below 20-day low (short)",
        "Volume confirmation above average",
    ],
    exit_rules=[
        "Price breaks below 10-day low (long exit)",
        "Price breaks above 10-day high (short exit)",
        "Trailing stop at 2x ATR",
    ],
    expected_win_rate=35.0,
    expected_risk_reward=3.5,
    suitable_for=["futures", "commodities", "forex"],
    tags=["intermediate", "breakout", "turtle", "donchian"],
))

register_template(StrategyTemplate(
    id="breakout_squeeze",
    name="Bollinger Squeeze Breakout",
    description="Identifies low volatility squeeze and trades the breakout. Uses Keltner Channels for squeeze detection.",
    category=StrategyCategory.BREAKOUT,
    risk_level=RiskLevel.MODERATE,
    timeframe=TimeFrame.INTRADAY,
    parameters={
        "bb_period": 20,
        "bb_std": 2.0,
        "kc_period": 20,
        "kc_atr_mult": 1.5,
        "momentum_period": 12,
    },
    indicators=["BB(20,2)", "KC(20,1.5)", "Momentum(12)"],
    entry_rules=[
        "BB inside KC (squeeze)",
        "Wait for squeeze to release",
        "Enter direction of momentum",
    ],
    exit_rules=[
        "Momentum changes direction",
        "Price reaches 2x ATR target",
        "New squeeze forms",
    ],
    expected_win_rate=50.0,
    expected_risk_reward=2.0,
    suitable_for=["stocks", "etf", "futures"],
    tags=["intermediate", "breakout", "squeeze", "volatility"],
))

# --- Scalping Templates ---

register_template(StrategyTemplate(
    id="scalp_vwap_reversion",
    name="VWAP Scalping",
    description="Scalp trades around VWAP. Buys below VWAP in uptrend, sells above VWAP in downtrend.",
    category=StrategyCategory.SCALPING,
    risk_level=RiskLevel.AGGRESSIVE,
    timeframe=TimeFrame.SCALPING,
    parameters={
        "vwap_bands": 2,
        "ema_fast": 9,
        "ema_slow": 21,
        "min_distance_pct": 0.1,
    },
    indicators=["VWAP", "VWAP Bands", "EMA(9)", "EMA(21)"],
    entry_rules=[
        "Price at lower VWAP band in uptrend",
        "Price at upper VWAP band in downtrend",
        "Fast EMA confirms direction",
    ],
    exit_rules=[
        "Price reaches VWAP (mean)",
        "Quick 0.2% profit target",
        "Tight 0.1% stop loss",
    ],
    max_daily_trades=20,
    expected_win_rate=58.0,
    expected_risk_reward=1.0,
    suitable_for=["stocks", "futures"],
    tags=["advanced", "scalping", "vwap", "intraday"],
))

# --- Momentum Templates ---

register_template(StrategyTemplate(
    id="momentum_rsi_divergence",
    name="RSI Divergence",
    description="Trades hidden and regular RSI divergences. Great for catching reversals and continuations.",
    category=StrategyCategory.MOMENTUM,
    risk_level=RiskLevel.MODERATE,
    timeframe=TimeFrame.SWING,
    parameters={
        "rsi_period": 14,
        "divergence_bars": 5,
        "confirmation_bars": 2,
    },
    indicators=["RSI(14)", "Price Action"],
    entry_rules=[
        "Regular bullish divergence: Lower lows in price, higher lows in RSI",
        "Wait for price confirmation (higher high)",
        "Enter on pullback",
    ],
    exit_rules=[
        "Bearish divergence forms",
        "RSI reaches overbought (70+)",
        "2x ATR profit target",
    ],
    expected_win_rate=52.0,
    expected_risk_reward=2.0,
    suitable_for=["stocks", "forex", "crypto"],
    tags=["intermediate", "momentum", "divergence", "rsi"],
))


# =============================================================================
# Template Library Functions
# =============================================================================

def get_all_templates() -> List[Dict[str, Any]]:
    """Get all available strategy templates."""
    return [t.to_dict() for t in STRATEGY_TEMPLATES.values()]


def get_template(template_id: str) -> Optional[StrategyTemplate]:
    """Get a specific template by ID."""
    return STRATEGY_TEMPLATES.get(template_id)


def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
    """Get templates filtered by category."""
    cat = StrategyCategory(category) if category in [c.value for c in StrategyCategory] else None
    if not cat:
        return []
    return [t.to_dict() for t in STRATEGY_TEMPLATES.values() if t.category == cat]


def get_templates_by_risk(risk_level: str) -> List[Dict[str, Any]]:
    """Get templates filtered by risk level."""
    risk = RiskLevel(risk_level) if risk_level in [r.value for r in RiskLevel] else None
    if not risk:
        return []
    return [t.to_dict() for t in STRATEGY_TEMPLATES.values() if t.risk_level == risk]


def search_templates(query: str) -> List[Dict[str, Any]]:
    """Search templates by name, description, or tags."""
    query = query.lower()
    results = []
    
    for template in STRATEGY_TEMPLATES.values():
        if (query in template.name.lower() or
            query in template.description.lower() or
            any(query in tag for tag in template.tags)):
            results.append(template.to_dict())
    
    return results


def get_template_stats() -> Dict[str, Any]:
    """Get statistics about available templates."""
    categories = {}
    risk_levels = {}
    
    for template in STRATEGY_TEMPLATES.values():
        cat = template.category.value
        risk = template.risk_level.value
        
        categories[cat] = categories.get(cat, 0) + 1
        risk_levels[risk] = risk_levels.get(risk, 0) + 1
    
    return {
        "total_templates": len(STRATEGY_TEMPLATES),
        "by_category": categories,
        "by_risk_level": risk_levels,
    }

