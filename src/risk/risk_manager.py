"""
Risk Manager for controlling trading risk and enforcing limits.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from loguru import logger

from src.config.limits import RiskLimits, CircuitBreakerAction, get_risk_limits


class RiskCheckResult(str, Enum):
    """Result of a risk check."""
    APPROVED = "approved"
    REJECTED = "rejected"
    REDUCED = "reduced"
    PENDING_REVIEW = "pending_review"


@dataclass
class RiskDecision:
    """Decision from risk manager."""
    result: RiskCheckResult
    original_quantity: float
    approved_quantity: float
    reason: str = ""
    circuit_breaker: str = ""


class RiskManager:
    """
    Manages trading risk and enforces position limits.
    
    Features:
    - Position size limits
    - Daily/weekly/monthly loss limits
    - VIX-based volatility controls
    - Sector exposure limits
    - Maximum drawdown tracking
    """
    
    def __init__(self):
        """Initialize risk manager."""
        self.limits = get_risk_limits()
        
        # State tracking
        self._daily_pnl = 0.0
        self._weekly_pnl = 0.0
        self._monthly_pnl = 0.0
        self._peak_portfolio_value = 0.0
        self._current_portfolio_value = 0.0
        self._current_vix = 0.0
        
        # Position tracking
        self._positions: dict[str, float] = {}  # symbol -> value
        self._sector_exposure: dict[str, float] = {}  # sector -> value
        
        # Circuit breaker state
        self._paused = False
        self._killed = False
        self._pause_until: Optional[datetime] = None
    
    @property
    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed."""
        if self._killed:
            return False
        if self._paused:
            if self._pause_until and datetime.utcnow() > self._pause_until:
                self._paused = False
            else:
                return False
        return True
    
    def update_pnl(self, daily: float, weekly: float, monthly: float) -> None:
        """Update P&L values."""
        self._daily_pnl = daily
        self._weekly_pnl = weekly
        self._monthly_pnl = monthly
        
        # Check for circuit breakers
        self._check_loss_limits()
    
    def update_portfolio_value(self, value: float) -> None:
        """Update current portfolio value."""
        self._current_portfolio_value = value
        self._peak_portfolio_value = max(self._peak_portfolio_value, value)
        
        # Check drawdown
        self._check_drawdown()
    
    def update_vix(self, vix: float) -> None:
        """Update VIX value."""
        self._current_vix = vix
        self._check_volatility()
    
    def update_position(self, symbol: str, value: float, sector: str = None) -> None:
        """Update position for a symbol."""
        old_value = self._positions.get(symbol, 0)
        self._positions[symbol] = value
        
        # Update sector exposure
        if sector:
            delta = value - old_value
            self._sector_exposure[sector] = self._sector_exposure.get(sector, 0) + delta
    
    def check_order(
        self,
        symbol: str,
        quantity: float,
        price: float,
        side: str,
        sector: str = None,
    ) -> RiskDecision:
        """
        Check if an order passes risk checks.
        
        Args:
            symbol: Stock symbol
            quantity: Order quantity
            price: Expected price
            side: BUY or SELL
            sector: Stock sector
            
        Returns:
            RiskDecision with approval status
        """
        order_value = quantity * price
        
        # Check if trading is allowed
        if not self.is_trading_allowed:
            return RiskDecision(
                result=RiskCheckResult.REJECTED,
                original_quantity=quantity,
                approved_quantity=0,
                reason="Trading is paused or killed",
                circuit_breaker="trading_paused",
            )
        
        # Check max position size
        if order_value > self.limits.max_position_size_usd:
            max_qty = self.limits.max_position_size_usd / price
            return RiskDecision(
                result=RiskCheckResult.REDUCED,
                original_quantity=quantity,
                approved_quantity=max_qty,
                reason=f"Order value exceeds max position size ${self.limits.max_position_size_usd:,.0f}",
            )
        
        # Check portfolio concentration
        portfolio_pct = order_value / max(self._current_portfolio_value, 1) * 100
        if portfolio_pct > self.limits.max_position_pct:
            max_value = self._current_portfolio_value * (self.limits.max_position_pct / 100)
            max_qty = max_value / price
            return RiskDecision(
                result=RiskCheckResult.REDUCED,
                original_quantity=quantity,
                approved_quantity=max_qty,
                reason=f"Position would exceed {self.limits.max_position_pct}% of portfolio",
            )
        
        # Check sector exposure
        if sector:
            current_sector = self._sector_exposure.get(sector, 0)
            new_sector = current_sector + order_value
            sector_pct = new_sector / max(self._current_portfolio_value, 1) * 100
            
            if sector_pct > self.limits.max_sector_exposure_pct:
                return RiskDecision(
                    result=RiskCheckResult.REJECTED,
                    original_quantity=quantity,
                    approved_quantity=0,
                    reason=f"Sector {sector} would exceed {self.limits.max_sector_exposure_pct}% limit",
                )
        
        # Check max open positions
        if side == "BUY" and len(self._positions) >= self.limits.max_open_positions:
            return RiskDecision(
                result=RiskCheckResult.REJECTED,
                original_quantity=quantity,
                approved_quantity=0,
                reason=f"Maximum {self.limits.max_open_positions} positions reached",
                circuit_breaker="max_positions",
            )
        
        # Check VIX-based reduction
        if self._current_vix >= self.limits.vix_extreme_threshold:
            return RiskDecision(
                result=RiskCheckResult.REJECTED,
                original_quantity=quantity,
                approved_quantity=0,
                reason=f"VIX at {self._current_vix:.1f} exceeds extreme threshold",
                circuit_breaker="vix_extreme",
            )
        
        if self._current_vix >= self.limits.vix_pause_threshold:
            reduced_qty = quantity * 0.5
            return RiskDecision(
                result=RiskCheckResult.REDUCED,
                original_quantity=quantity,
                approved_quantity=reduced_qty,
                reason=f"VIX at {self._current_vix:.1f} - reducing position by 50%",
                circuit_breaker="vix_spike",
            )
        
        # All checks passed
        return RiskDecision(
            result=RiskCheckResult.APPROVED,
            original_quantity=quantity,
            approved_quantity=quantity,
        )
    
    def _check_loss_limits(self) -> None:
        """Check loss limits and trigger circuit breakers."""
        portfolio = max(self._current_portfolio_value, 1)
        
        # Daily loss
        daily_pct = abs(self._daily_pnl) / portfolio * 100
        if self._daily_pnl < 0 and daily_pct >= self.limits.daily_loss_limit_pct:
            self._trigger_pause(f"Daily loss limit hit ({daily_pct:.1f}%)")
        
        # Weekly loss
        weekly_pct = abs(self._weekly_pnl) / portfolio * 100
        if self._weekly_pnl < 0 and weekly_pct >= self.limits.weekly_loss_limit_pct:
            self._trigger_pause(f"Weekly loss limit hit ({weekly_pct:.1f}%)", hours=24)
        
        # Monthly loss
        monthly_pct = abs(self._monthly_pnl) / portfolio * 100
        if self._monthly_pnl < 0 and monthly_pct >= self.limits.monthly_loss_limit_pct:
            self._trigger_kill(f"Monthly loss limit hit ({monthly_pct:.1f}%)")
    
    def _check_drawdown(self) -> None:
        """Check maximum drawdown."""
        if self._peak_portfolio_value == 0:
            return
        
        drawdown = (self._peak_portfolio_value - self._current_portfolio_value) / self._peak_portfolio_value * 100
        
        if drawdown >= self.limits.max_drawdown_pct:
            self._trigger_kill(f"Maximum drawdown hit ({drawdown:.1f}%)")
    
    def _check_volatility(self) -> None:
        """Check VIX-based volatility controls."""
        if self._current_vix >= self.limits.vix_extreme_threshold:
            logger.warning(f"VIX extreme: {self._current_vix:.1f} - no new entries allowed")
        elif self._current_vix >= self.limits.vix_pause_threshold:
            logger.warning(f"VIX elevated: {self._current_vix:.1f} - positions reduced")
    
    def _trigger_pause(self, reason: str, hours: int = 0) -> None:
        """Trigger trading pause."""
        self._paused = True
        if hours > 0:
            self._pause_until = datetime.utcnow() + timedelta(hours=hours)
        logger.warning(f"Trading PAUSED: {reason}")
    
    def _trigger_kill(self, reason: str) -> None:
        """Trigger kill switch - stop all trading."""
        self._killed = True
        logger.error(f"KILL SWITCH ACTIVATED: {reason}")
    
    def resume_trading(self) -> bool:
        """Resume trading after pause (not after kill)."""
        if self._killed:
            logger.warning("Cannot resume - kill switch is active")
            return False
        
        self._paused = False
        self._pause_until = None
        logger.info("Trading resumed")
        return True
    
    def reset_kill_switch(self) -> None:
        """Reset kill switch (requires manual action)."""
        self._killed = False
        self._paused = False
        self._pause_until = None
        logger.warning("Kill switch reset - trading can resume")
    
    def get_status(self) -> dict:
        """Get current risk status."""
        portfolio = max(self._current_portfolio_value, 1)
        
        return {
            "trading_allowed": self.is_trading_allowed,
            "paused": self._paused,
            "killed": self._killed,
            "pause_until": self._pause_until.isoformat() if self._pause_until else None,
            "daily_pnl": self._daily_pnl,
            "daily_pnl_pct": self._daily_pnl / portfolio * 100,
            "weekly_pnl": self._weekly_pnl,
            "weekly_pnl_pct": self._weekly_pnl / portfolio * 100,
            "current_drawdown_pct": (self._peak_portfolio_value - self._current_portfolio_value) / max(self._peak_portfolio_value, 1) * 100,
            "vix": self._current_vix,
            "open_positions": len(self._positions),
            "limits": {
                "daily_loss_limit": self.limits.daily_loss_limit_pct,
                "weekly_loss_limit": self.limits.weekly_loss_limit_pct,
                "max_drawdown": self.limits.max_drawdown_pct,
                "vix_pause": self.limits.vix_pause_threshold,
                "max_positions": self.limits.max_open_positions,
            }
        }

