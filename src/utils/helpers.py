"""
Utility helper functions.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, TypeVar
from functools import wraps

from tenacity import retry, stop_after_attempt, wait_exponential


T = TypeVar("T")


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def round_price(price: float, decimals: int = 2) -> float:
    """Round price to specified decimals."""
    d = Decimal(str(price))
    return float(d.quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP))


def round_quantity(quantity: float, min_qty: float = 1.0) -> float:
    """Round quantity to valid trading quantity."""
    if quantity < min_qty:
        return 0.0
    return float(int(quantity))


def calculate_position_size(
    capital: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float,
) -> int:
    """
    Calculate position size based on risk.
    
    Args:
        capital: Total available capital
        risk_per_trade: Risk per trade as decimal (e.g., 0.02 for 2%)
        entry_price: Expected entry price
        stop_loss_price: Stop loss price
        
    Returns:
        Number of shares to buy
    """
    if entry_price <= 0 or stop_loss_price <= 0:
        return 0
    
    risk_amount = capital * risk_per_trade
    risk_per_share = abs(entry_price - stop_loss_price)
    
    if risk_per_share <= 0:
        return 0
    
    shares = risk_amount / risk_per_share
    return int(shares)


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Calculate Kelly Criterion for optimal position sizing.
    
    Args:
        win_rate: Probability of winning (0-1)
        avg_win: Average winning trade amount
        avg_loss: Average losing trade amount (positive number)
        
    Returns:
        Optimal fraction of capital to risk (0-1)
    """
    if avg_loss <= 0 or avg_win <= 0:
        return 0.0
    
    b = avg_win / avg_loss  # Win/loss ratio
    p = win_rate
    q = 1 - p
    
    kelly = (b * p - q) / b
    
    # Cap at 25% and floor at 0
    return max(0.0, min(0.25, kelly))


def async_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """Decorator for async retry with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        )
        async def wrapper(*args, **kwargs) -> T:
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def chunk_list(lst: list[T], chunk_size: int) -> list[list[T]]:
    """Split a list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency string."""
    if currency == "USD":
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format value as percentage string."""
    return f"{value * 100:.{decimals}f}%"


def is_market_hours(dt: datetime = None) -> bool:
    """
    Check if current time is during US market hours.
    
    Note: This is a simplified check. Real implementation should
    consider holidays and early closes.
    """
    if dt is None:
        dt = utc_now()
    
    # Convert to Eastern time (simplified, doesn't account for DST)
    eastern_hour = (dt.hour - 5) % 24  # UTC-5 for EST
    
    # Market hours: 9:30 AM - 4:00 PM ET
    if dt.weekday() >= 5:  # Weekend
        return False
    
    if eastern_hour < 9 or eastern_hour >= 16:
        return False
    
    if eastern_hour == 9 and dt.minute < 30:
        return False
    
    return True


def generate_order_id() -> str:
    """Generate a unique order ID."""
    import uuid
    timestamp = utc_now().strftime("%Y%m%d%H%M%S")
    unique = uuid.uuid4().hex[:8]
    return f"ORD-{timestamp}-{unique}"


class NetworkErrorTracker:
    """
    Track network errors across the system to reduce log spam.
    
    When network is down, logs a single warning then suppresses
    repeat errors until network recovers.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._last_error_time: dict[str, datetime] = {}
        self._error_counts: dict[str, int] = {}
        self._is_network_down = False
        self._last_network_warning: datetime | None = None
        self._warning_interval = 60  # Log warning every 60 seconds when network is down
        self._network_indicators = [
            'nodename nor servname',
            'name resolution',
            'failed to resolve',
            'connection refused',
            'network is unreachable',
            'no route to host',
            'temporary failure in name resolution',
            'getaddrinfo failed',
            'max retries exceeded',
            'connection reset',
            'connection timed out',
        ]
    
    def is_network_error(self, error: Exception) -> bool:
        """Check if an error is a network connectivity issue."""
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in self._network_indicators)
    
    def record_error(self, source: str, error: Exception) -> bool:
        """
        Record a network error.
        
        Returns True if this error should be logged, False if suppressed.
        """
        from loguru import logger
        
        if not self.is_network_error(error):
            return True  # Not a network error, should be logged normally
        
        now = datetime.now(timezone.utc)
        self._error_counts[source] = self._error_counts.get(source, 0) + 1
        
        # Check if we should log
        should_log = False
        
        if not self._is_network_down:
            # First network error - log it and mark network as down
            self._is_network_down = True
            self._last_network_warning = now
            should_log = True
            logger.warning(
                f"⚠️ NETWORK DOWN: Connection failed ({source}). "
                f"Trading paused until connectivity restored. "
                f"Check internet connection."
            )
        elif self._last_network_warning:
            elapsed = (now - self._last_network_warning).total_seconds()
            if elapsed >= self._warning_interval:
                self._last_network_warning = now
                total_errors = sum(self._error_counts.values())
                logger.warning(
                    f"⚠️ NETWORK STILL DOWN: {total_errors} errors since outage started. "
                    f"Waiting for connectivity..."
                )
        
        return should_log
    
    def record_success(self, source: str) -> None:
        """Record a successful network call - resets network down state."""
        from loguru import logger
        
        if self._is_network_down:
            total_errors = sum(self._error_counts.values())
            logger.info(
                f"✅ NETWORK RESTORED: Connectivity recovered via {source}. "
                f"Resuming normal operations. ({total_errors} errors during outage)"
            )
            self._is_network_down = False
            self._error_counts.clear()
            self._last_network_warning = None
    
    @property
    def is_network_available(self) -> bool:
        """Check if network appears to be available."""
        return not self._is_network_down


# Global singleton instance
_network_tracker: NetworkErrorTracker | None = None


def get_network_tracker() -> NetworkErrorTracker:
    """Get the global network error tracker instance."""
    global _network_tracker
    if _network_tracker is None:
        _network_tracker = NetworkErrorTracker()
    return _network_tracker

