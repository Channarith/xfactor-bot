"""
Martingale Position Sizing Module

Implements the Martingale betting strategy for trading, where position size
increases after losses to recover previous losses when a win occurs.

WARNING: Martingale is a high-risk strategy that can lead to significant losses.
Use with strict limits and proper risk management.

Features:
- Classic Martingale (2x after loss)
- Anti-Martingale (increase after wins)
- Modified Martingale (configurable multiplier)
- Maximum level limits to prevent unlimited scaling
- Drawdown-based kill switch
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import json

from loguru import logger


class MartingaleType(Enum):
    """Type of Martingale strategy."""
    CLASSIC = "classic"           # Double after each loss
    ANTI = "anti"                 # Double after each win (pyramid)
    MODIFIED = "modified"         # Custom multiplier
    FIBONACCI = "fibonacci"       # Use Fibonacci sequence
    DALEMBERT = "dalembert"       # Add/subtract fixed amount


@dataclass
class MartingaleConfig:
    """Configuration for Martingale position sizing."""
    # Strategy type
    strategy_type: MartingaleType = MartingaleType.CLASSIC
    
    # Base settings
    base_position_size: float = 100.0      # Starting position size
    multiplier: float = 2.0                 # Classic: 2x, can be customized
    
    # Limits
    max_levels: int = 4                     # Maximum consecutive increases
    max_position_size: float = 1000.0       # Maximum position size
    max_total_risk: float = 5000.0          # Maximum total capital at risk
    
    # Reset conditions
    reset_on_win: bool = True               # Reset to base after win
    reset_after_levels: bool = True         # Force reset after max_levels
    
    # Risk controls
    max_drawdown_percent: float = 20.0      # Kill switch at 20% drawdown
    cool_down_after_max_level: int = 3      # Wait N trades after hitting max
    
    # Anti-Martingale specific
    profit_lock_percent: float = 50.0       # Lock 50% of profits in Anti
    
    # D'Alembert specific
    increment_amount: float = 10.0          # Fixed increment for D'Alembert


@dataclass
class MartingaleState:
    """Current state of Martingale progression."""
    current_level: int = 0
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    current_position_size: float = 0.0
    total_invested: float = 0.0
    total_pnl: float = 0.0
    peak_equity: float = 0.0
    current_drawdown: float = 0.0
    trades_history: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = True
    cool_down_remaining: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_level": self.current_level,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_wins": self.consecutive_wins,
            "current_position_size": self.current_position_size,
            "total_invested": self.total_invested,
            "total_pnl": self.total_pnl,
            "current_drawdown": round(self.current_drawdown, 2),
            "is_active": self.is_active,
            "trades_count": len(self.trades_history),
        }


class MartingalePositionSizer:
    """
    Martingale position sizing engine.
    
    Usage:
        sizer = MartingalePositionSizer(config)
        size = sizer.get_next_size()  # Get position size for next trade
        sizer.record_result(won=False, pnl=-100)  # Record trade result
        size = sizer.get_next_size()  # Size will be increased after loss
    """
    
    # Fibonacci sequence for Fibonacci Martingale
    FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
    
    def __init__(self, config: Optional[MartingaleConfig] = None):
        self.config = config or MartingaleConfig()
        self.state = MartingaleState()
        self.state.current_position_size = self.config.base_position_size
        
        logger.info(f"Martingale sizer initialized: {self.config.strategy_type.value}")
    
    def get_next_size(self) -> float:
        """
        Calculate the next position size based on Martingale strategy.
        
        Returns:
            Position size for the next trade
        """
        # Check if in cool down
        if self.state.cool_down_remaining > 0:
            logger.info(f"Martingale in cool down: {self.state.cool_down_remaining} trades remaining")
            self.state.cool_down_remaining -= 1
            return self.config.base_position_size
        
        # Check if deactivated due to drawdown
        if not self.state.is_active:
            logger.warning("Martingale deactivated due to risk limits")
            return self.config.base_position_size
        
        # Calculate size based on strategy type
        if self.config.strategy_type == MartingaleType.CLASSIC:
            size = self._calculate_classic_size()
        elif self.config.strategy_type == MartingaleType.ANTI:
            size = self._calculate_anti_size()
        elif self.config.strategy_type == MartingaleType.FIBONACCI:
            size = self._calculate_fibonacci_size()
        elif self.config.strategy_type == MartingaleType.DALEMBERT:
            size = self._calculate_dalembert_size()
        else:  # MODIFIED
            size = self._calculate_modified_size()
        
        # Apply limits
        size = min(size, self.config.max_position_size)
        
        # Check total risk
        if self.state.total_invested + size > self.config.max_total_risk:
            logger.warning(f"Position size limited by total risk: {size} -> {self.config.max_total_risk - self.state.total_invested}")
            size = max(0, self.config.max_total_risk - self.state.total_invested)
        
        self.state.current_position_size = size
        return size
    
    def _calculate_classic_size(self) -> float:
        """Classic Martingale: double after each loss."""
        level = min(self.state.current_level, self.config.max_levels)
        return self.config.base_position_size * (self.config.multiplier ** level)
    
    def _calculate_anti_size(self) -> float:
        """Anti-Martingale: double after each win."""
        level = min(self.state.consecutive_wins, self.config.max_levels)
        return self.config.base_position_size * (self.config.multiplier ** level)
    
    def _calculate_fibonacci_size(self) -> float:
        """Fibonacci Martingale: use Fibonacci sequence multipliers."""
        level = min(self.state.current_level, len(self.FIBONACCI) - 1)
        return self.config.base_position_size * self.FIBONACCI[level]
    
    def _calculate_dalembert_size(self) -> float:
        """D'Alembert: add fixed amount after loss, subtract after win."""
        adjustment = self.state.consecutive_losses * self.config.increment_amount
        adjustment -= self.state.consecutive_wins * self.config.increment_amount
        return max(self.config.base_position_size, self.config.base_position_size + adjustment)
    
    def _calculate_modified_size(self) -> float:
        """Modified Martingale with custom multiplier."""
        level = min(self.state.current_level, self.config.max_levels)
        return self.config.base_position_size * (self.config.multiplier ** level)
    
    def record_result(self, won: bool, pnl: float) -> None:
        """
        Record the result of a trade.
        
        Args:
            won: True if trade was profitable
            pnl: Profit/loss amount
        """
        # Update PnL tracking
        self.state.total_pnl += pnl
        
        # Update peak and drawdown
        if self.state.total_pnl > self.state.peak_equity:
            self.state.peak_equity = self.state.total_pnl
        
        if self.state.peak_equity > 0:
            self.state.current_drawdown = ((self.state.peak_equity - self.state.total_pnl) / self.state.peak_equity) * 100
        
        # Check drawdown limit
        if self.state.current_drawdown >= self.config.max_drawdown_percent:
            logger.warning(f"Martingale KILLED: Drawdown {self.state.current_drawdown:.1f}% exceeds limit")
            self.state.is_active = False
        
        # Record trade
        self.state.trades_history.append({
            "timestamp": datetime.now().isoformat(),
            "won": won,
            "pnl": pnl,
            "level": self.state.current_level,
            "position_size": self.state.current_position_size,
        })
        
        # Update consecutive counters and level
        if won:
            self.state.consecutive_wins += 1
            self.state.consecutive_losses = 0
            
            if self.config.strategy_type == MartingaleType.CLASSIC:
                # Reset level on win for classic Martingale
                if self.config.reset_on_win:
                    self.state.current_level = 0
            elif self.config.strategy_type == MartingaleType.ANTI:
                # Increase level on win for Anti-Martingale
                self.state.current_level = min(self.state.current_level + 1, self.config.max_levels)
        else:
            self.state.consecutive_losses += 1
            self.state.consecutive_wins = 0
            
            if self.config.strategy_type in [MartingaleType.CLASSIC, MartingaleType.MODIFIED, MartingaleType.FIBONACCI]:
                # Increase level on loss
                self.state.current_level += 1
                
                # Check if hit max level
                if self.state.current_level >= self.config.max_levels:
                    if self.config.reset_after_levels:
                        logger.warning(f"Hit max Martingale level {self.config.max_levels}, resetting")
                        self.state.current_level = 0
                        self.state.cool_down_remaining = self.config.cool_down_after_max_level
            elif self.config.strategy_type == MartingaleType.ANTI:
                # Reset on loss for Anti-Martingale
                self.state.current_level = 0
        
        # Update invested tracking
        self.state.total_invested += self.state.current_position_size
        
        logger.info(f"Martingale recorded: {'WIN' if won else 'LOSS'} PnL={pnl:.2f} Level={self.state.current_level}")
    
    def reset(self) -> None:
        """Reset Martingale state to initial values."""
        self.state = MartingaleState()
        self.state.current_position_size = self.config.base_position_size
        self.state.is_active = True
        logger.info("Martingale state reset")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current Martingale status."""
        return {
            "strategy_type": self.config.strategy_type.value,
            "base_size": self.config.base_position_size,
            "current_size": self.state.current_position_size,
            "max_size": self.config.max_position_size,
            "state": self.state.to_dict(),
            "config": {
                "multiplier": self.config.multiplier,
                "max_levels": self.config.max_levels,
                "max_drawdown_percent": self.config.max_drawdown_percent,
            }
        }
    
    def get_risk_warning(self) -> str:
        """Get risk warning based on current state."""
        warnings = []
        
        if self.state.current_level >= self.config.max_levels - 1:
            warnings.append("⚠️ NEAR MAX LEVEL: Position size at maximum")
        
        if self.state.current_drawdown >= self.config.max_drawdown_percent * 0.8:
            warnings.append(f"⚠️ DRAWDOWN WARNING: {self.state.current_drawdown:.1f}% (limit: {self.config.max_drawdown_percent}%)")
        
        if self.state.current_position_size >= self.config.max_position_size * 0.8:
            warnings.append("⚠️ POSITION SIZE WARNING: Near maximum position size")
        
        if not self.state.is_active:
            warnings.append("🛑 MARTINGALE DEACTIVATED: Risk limits exceeded")
        
        if not warnings:
            return "✅ Martingale operating within normal parameters"
        
        return "\n".join(warnings)


# Factory function for creating pre-configured Martingale sizers
def create_martingale_sizer(
    strategy_type: str = "classic",
    base_size: float = 100.0,
    multiplier: float = 2.0,
    max_levels: int = 4,
    max_drawdown: float = 20.0,
) -> MartingalePositionSizer:
    """
    Create a Martingale position sizer with common settings.
    
    Args:
        strategy_type: "classic", "anti", "modified", "fibonacci", "dalembert"
        base_size: Base position size
        multiplier: Position multiplier after loss/win
        max_levels: Maximum Martingale levels
        max_drawdown: Maximum drawdown before kill switch
    
    Returns:
        Configured MartingalePositionSizer
    """
    config = MartingaleConfig(
        strategy_type=MartingaleType(strategy_type),
        base_position_size=base_size,
        multiplier=multiplier,
        max_levels=max_levels,
        max_drawdown_percent=max_drawdown,
    )
    return MartingalePositionSizer(config)

