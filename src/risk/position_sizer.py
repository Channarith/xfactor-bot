"""
Position Sizer for calculating optimal position sizes.
"""

from dataclasses import dataclass
from typing import Optional

from src.config.settings import get_settings
from src.utils.helpers import kelly_criterion


@dataclass
class PositionSize:
    """Calculated position size."""
    shares: int
    value: float
    risk_amount: float
    method: str
    
    @property
    def is_valid(self) -> bool:
        return self.shares > 0


class PositionSizer:
    """
    Calculate optimal position sizes using various methods.
    
    Methods:
    - Fixed fractional (risk X% per trade)
    - Kelly criterion (optimal based on win rate)
    - Volatility-based (ATR-adjusted)
    - Equal weight (simple allocation)
    """
    
    def __init__(self):
        """Initialize position sizer."""
        self.settings = get_settings()
        
        # Default parameters
        self.default_risk_per_trade = 0.02  # 2%
        self.max_position_pct = 0.05  # 5% max per position
        self.kelly_fraction = 0.5  # Half-Kelly for safety
    
    def calculate_fixed_fractional(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss: float,
        risk_per_trade: float = None,
    ) -> PositionSize:
        """
        Calculate position size using fixed fractional method.
        
        Args:
            portfolio_value: Total portfolio value
            entry_price: Expected entry price
            stop_loss: Stop loss price
            risk_per_trade: Risk per trade as decimal (default 2%)
            
        Returns:
            PositionSize object
        """
        if risk_per_trade is None:
            risk_per_trade = self.default_risk_per_trade
        
        risk_amount = portfolio_value * risk_per_trade
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share <= 0:
            return PositionSize(0, 0, 0, "fixed_fractional")
        
        shares = int(risk_amount / risk_per_share)
        
        # Apply max position limit
        max_value = portfolio_value * self.max_position_pct
        max_shares = int(max_value / entry_price)
        shares = min(shares, max_shares)
        
        # Apply absolute max
        max_abs = int(self.settings.max_position_size / entry_price)
        shares = min(shares, max_abs)
        
        value = shares * entry_price
        
        return PositionSize(
            shares=shares,
            value=value,
            risk_amount=shares * risk_per_share,
            method="fixed_fractional",
        )
    
    def calculate_kelly(
        self,
        portfolio_value: float,
        entry_price: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
    ) -> PositionSize:
        """
        Calculate position size using Kelly criterion.
        
        Args:
            portfolio_value: Total portfolio value
            entry_price: Expected entry price
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount
            
        Returns:
            PositionSize object
        """
        kelly = kelly_criterion(win_rate, avg_win, avg_loss)
        
        # Apply half-Kelly for safety
        kelly *= self.kelly_fraction
        
        # Cap at max position
        kelly = min(kelly, self.max_position_pct)
        
        value = portfolio_value * kelly
        shares = int(value / entry_price)
        
        # Apply absolute max
        max_abs = int(self.settings.max_position_size / entry_price)
        shares = min(shares, max_abs)
        
        return PositionSize(
            shares=shares,
            value=shares * entry_price,
            risk_amount=shares * entry_price * kelly,
            method="kelly",
        )
    
    def calculate_volatility_based(
        self,
        portfolio_value: float,
        entry_price: float,
        atr: float,
        atr_multiplier: float = 2.0,
        risk_per_trade: float = None,
    ) -> PositionSize:
        """
        Calculate position size based on volatility (ATR).
        
        Args:
            portfolio_value: Total portfolio value
            entry_price: Expected entry price
            atr: Average True Range
            atr_multiplier: Multiplier for ATR-based stop
            risk_per_trade: Risk per trade as decimal
            
        Returns:
            PositionSize object
        """
        if risk_per_trade is None:
            risk_per_trade = self.default_risk_per_trade
        
        # Stop distance based on ATR
        stop_distance = atr * atr_multiplier
        stop_loss = entry_price - stop_distance
        
        return self.calculate_fixed_fractional(
            portfolio_value,
            entry_price,
            stop_loss,
            risk_per_trade,
        )
    
    def calculate_equal_weight(
        self,
        portfolio_value: float,
        entry_price: float,
        num_positions: int,
    ) -> PositionSize:
        """
        Calculate equal-weight position size.
        
        Args:
            portfolio_value: Total portfolio value
            entry_price: Expected entry price
            num_positions: Target number of positions
            
        Returns:
            PositionSize object
        """
        if num_positions <= 0:
            return PositionSize(0, 0, 0, "equal_weight")
        
        value_per_position = portfolio_value / num_positions
        
        # Apply max position limit
        max_value = portfolio_value * self.max_position_pct
        value = min(value_per_position, max_value)
        
        shares = int(value / entry_price)
        
        return PositionSize(
            shares=shares,
            value=shares * entry_price,
            risk_amount=0,  # No specific risk amount for equal weight
            method="equal_weight",
        )
    
    def calculate_signal_weighted(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss: float,
        signal_strength: float,
        base_risk_per_trade: float = None,
    ) -> PositionSize:
        """
        Calculate position size weighted by signal strength.
        
        Args:
            portfolio_value: Total portfolio value
            entry_price: Expected entry price
            stop_loss: Stop loss price
            signal_strength: Signal strength (0-1)
            base_risk_per_trade: Base risk per trade
            
        Returns:
            PositionSize object
        """
        if base_risk_per_trade is None:
            base_risk_per_trade = self.default_risk_per_trade
        
        # Scale risk by signal strength
        adjusted_risk = base_risk_per_trade * signal_strength
        
        result = self.calculate_fixed_fractional(
            portfolio_value,
            entry_price,
            stop_loss,
            adjusted_risk,
        )
        result.method = "signal_weighted"
        
        return result

