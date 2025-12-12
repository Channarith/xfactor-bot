"""
Risk limits configuration.
Defines hard limits and thresholds for the trading bot.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.config.settings import get_settings


class CircuitBreakerAction(str, Enum):
    """Actions to take when circuit breaker triggers."""
    PAUSE = "pause"  # Stop new orders, keep positions
    CLOSE_ALL = "close_all"  # Close all positions
    REDUCE = "reduce"  # Reduce position sizes
    ALERT = "alert"  # Alert only, no action
    HUMAN_REVIEW = "human_review"  # Require manual approval


@dataclass
class RiskLimit:
    """Individual risk limit configuration."""
    name: str
    threshold: float
    action: CircuitBreakerAction
    cooldown_minutes: int = 0
    description: str = ""


@dataclass
class RiskLimits:
    """All risk limits for the trading bot."""
    
    # Position Limits
    max_position_size_usd: float
    max_position_pct: float
    max_sector_exposure_pct: float
    max_single_stock_pct: float
    max_open_positions: int
    
    # Loss Limits
    daily_loss_limit_pct: float
    weekly_loss_limit_pct: float
    monthly_loss_limit_pct: float
    max_drawdown_pct: float
    
    # Volatility Limits
    vix_pause_threshold: float
    vix_extreme_threshold: float
    
    # Connection Limits
    connection_loss_pause_seconds: int
    connection_loss_close_seconds: int
    
    # Order Limits
    max_order_value_usd: float
    max_orders_per_minute: int
    max_orders_per_day: int
    
    @classmethod
    def from_settings(cls) -> "RiskLimits":
        """Load risk limits from settings."""
        settings = get_settings()
        return cls(
            # Position Limits
            max_position_size_usd=settings.max_position_size,
            max_position_pct=settings.max_portfolio_pct,
            max_sector_exposure_pct=25.0,
            max_single_stock_pct=10.0,
            max_open_positions=settings.max_open_positions,
            
            # Loss Limits
            daily_loss_limit_pct=settings.daily_loss_limit_pct,
            weekly_loss_limit_pct=settings.weekly_loss_limit_pct,
            monthly_loss_limit_pct=15.0,
            max_drawdown_pct=settings.max_drawdown_pct,
            
            # Volatility Limits
            vix_pause_threshold=settings.vix_pause_threshold,
            vix_extreme_threshold=50.0,
            
            # Connection Limits
            connection_loss_pause_seconds=30,
            connection_loss_close_seconds=300,
            
            # Order Limits
            max_order_value_usd=100000.0,
            max_orders_per_minute=10,
            max_orders_per_day=500,
        )


# Circuit Breaker Definitions
CIRCUIT_BREAKERS = [
    RiskLimit(
        name="daily_loss",
        threshold=3.0,
        action=CircuitBreakerAction.PAUSE,
        cooldown_minutes=0,
        description="Pause trading when daily loss exceeds 3%",
    ),
    RiskLimit(
        name="weekly_loss",
        threshold=7.0,
        action=CircuitBreakerAction.CLOSE_ALL,
        cooldown_minutes=1440,  # 24 hours
        description="Close all positions and lock out for 24h when weekly loss exceeds 7%",
    ),
    RiskLimit(
        name="monthly_loss",
        threshold=15.0,
        action=CircuitBreakerAction.CLOSE_ALL,
        cooldown_minutes=10080,  # 7 days
        description="Full shutdown when monthly loss exceeds 15%",
    ),
    RiskLimit(
        name="vix_spike",
        threshold=35.0,
        action=CircuitBreakerAction.REDUCE,
        cooldown_minutes=60,
        description="Reduce position sizes by 50% when VIX > 35",
    ),
    RiskLimit(
        name="vix_extreme",
        threshold=50.0,
        action=CircuitBreakerAction.PAUSE,
        cooldown_minutes=0,
        description="Pause all new entries when VIX > 50",
    ),
    RiskLimit(
        name="connection_loss_brief",
        threshold=30.0,
        action=CircuitBreakerAction.PAUSE,
        cooldown_minutes=0,
        description="Pause orders after 30s of connection loss",
    ),
    RiskLimit(
        name="connection_loss_extended",
        threshold=300.0,
        action=CircuitBreakerAction.CLOSE_ALL,
        cooldown_minutes=0,
        description="Close all positions after 5 minutes of connection loss",
    ),
    RiskLimit(
        name="max_positions",
        threshold=50.0,
        action=CircuitBreakerAction.PAUSE,
        cooldown_minutes=0,
        description="No new entries when 50+ positions open",
    ),
    RiskLimit(
        name="anomaly_detected",
        threshold=0.0,
        action=CircuitBreakerAction.HUMAN_REVIEW,
        cooldown_minutes=0,
        description="Require human approval for anomalous orders",
    ),
]


def get_risk_limits() -> RiskLimits:
    """Get current risk limits from settings."""
    return RiskLimits.from_settings()


def get_circuit_breaker(name: str) -> Optional[RiskLimit]:
    """Get a specific circuit breaker by name."""
    for cb in CIRCUIT_BREAKERS:
        if cb.name == name:
            return cb
    return None

