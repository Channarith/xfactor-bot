"""
Market Hours Manager for XFactor Bot.

Centralizes market hours logic and provides an "active trading window" that
runs from 40 minutes before market open to 40 minutes after market close.

During off-hours (outside the active window), background polling and analytics
are reduced to save computing resources.

IMPORTANT: Quiet mode ONLY affects:
- Trading bot cycles (paused during off-hours unless extended hours enabled)
- News aggregator polling (reduced from 1 min to 10 min)
- Momentum scanner cycles (paused)
- Scheduler intervals (increased)

Quiet mode does NOT affect:
- Broker connections (maintained 24/7 for autonomous trading)
- BrokerRegistry connection monitor (runs independently every 2 minutes)
- Reconnection logic (always active)
- Health checks (always active)

This design enables seamless day-after-day autonomous trading.

@version 2.1.13
"""

from datetime import datetime, time, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
from loguru import logger

# US Eastern timezone for market hours
ET = ZoneInfo("America/New_York")

# Core market hours
MARKET_OPEN = time(9, 30)   # 9:30 AM ET
MARKET_CLOSE = time(16, 0)  # 4:00 PM ET

# Extended hours
PRE_MARKET_OPEN = time(4, 0)     # 4:00 AM ET
AFTER_HOURS_CLOSE = time(20, 0)  # 8:00 PM ET

# Active window buffer (minutes before/after regular market hours)
ACTIVE_WINDOW_BUFFER_MINUTES = 40

# Calculated active window times
# Market open: 9:30 AM - 40 min = 8:50 AM
# Market close: 4:00 PM + 40 min = 4:40 PM
ACTIVE_WINDOW_START = time(8, 50)   # 40 min before open
ACTIVE_WINDOW_END = time(16, 40)    # 40 min after close

# Quiet mode settings - reduced polling intervals during off-hours
QUIET_MODE_POLL_INTERVAL = 300  # 5 minutes between checks during quiet mode
NORMAL_MODE_POLL_INTERVAL = 30   # 30 seconds during active hours

# Market holidays (US stock market) - 2025-2026
MARKET_HOLIDAYS = {
    # 2025
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # MLK Day
    "2025-02-17",  # Presidents Day
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving
    "2025-12-25",  # Christmas
    # 2026
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # MLK Day
    "2026-02-16",  # Presidents Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day (observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Christmas
}


class MarketHoursManager:
    """
    Centralized manager for market hours and quiet mode.
    
    The active trading window runs from 40 minutes before market open
    to 40 minutes after market close. Outside this window, the system
    enters "quiet mode" where polling and analytics are reduced.
    
    Quiet mode can be enabled/disabled from the frontend.
    """
    
    _instance: Optional["MarketHoursManager"] = None
    
    def __new__(cls) -> "MarketHoursManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._quiet_mode_logged = False
        self._active_mode_logged = False
        self._quiet_mode_enabled = True  # Default: ON - quiet mode is enabled
        logger.info(f"MarketHoursManager initialized - Active window: {ACTIVE_WINDOW_START} to {ACTIVE_WINDOW_END} ET")
        logger.info(f"Quiet mode: {'ENABLED' if self._quiet_mode_enabled else 'DISABLED'}")
    
    def set_quiet_mode_enabled(self, enabled: bool) -> None:
        """Enable or disable quiet mode."""
        old_value = self._quiet_mode_enabled
        self._quiet_mode_enabled = enabled
        if old_value != enabled:
            status = "ENABLED" if enabled else "DISABLED"
            logger.info(f"Quiet mode {status} by user")
            # Reset logging flags to re-announce state
            self._quiet_mode_logged = False
            self._active_mode_logged = False
    
    def is_quiet_mode_enabled(self) -> bool:
        """Check if quiet mode is enabled (user setting)."""
        return self._quiet_mode_enabled
    
    def is_market_day(self, dt: Optional[datetime] = None) -> bool:
        """Check if the given date is a trading day (not weekend or holiday)."""
        if dt is None:
            dt = datetime.now(ET)
        
        # Weekend check
        if dt.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Holiday check
        if dt.strftime("%Y-%m-%d") in MARKET_HOLIDAYS:
            return False
        
        return True
    
    def is_market_open(self, include_extended: bool = False) -> bool:
        """Check if the US stock market is currently open."""
        now = datetime.now(ET)
        
        if not self.is_market_day(now):
            return False
        
        current_time = now.time()
        
        if include_extended:
            return PRE_MARKET_OPEN <= current_time <= AFTER_HOURS_CLOSE
        else:
            return MARKET_OPEN <= current_time <= MARKET_CLOSE
    
    def is_active_window(self) -> bool:
        """
        Check if we're in the active trading window.
        
        Active window is 40 minutes before market open to 40 minutes after close.
        This is when full polling and analytics should run.
        
        Outside this window, the system should enter "quiet mode".
        """
        now = datetime.now(ET)
        
        # Not a market day = quiet mode
        if not self.is_market_day(now):
            return False
        
        current_time = now.time()
        
        # Check if within active window (8:50 AM to 4:40 PM ET)
        is_active = ACTIVE_WINDOW_START <= current_time <= ACTIVE_WINDOW_END
        
        # Log state changes (once per transition)
        if is_active and not self._active_mode_logged:
            logger.info("🟢 Entering ACTIVE mode - full polling and analytics enabled")
            self._active_mode_logged = True
            self._quiet_mode_logged = False
        elif not is_active and not self._quiet_mode_logged:
            logger.info("🌙 Entering QUIET mode - reduced polling to save resources")
            self._quiet_mode_logged = True
            self._active_mode_logged = False
        
        return is_active
    
    def is_quiet_mode(self) -> bool:
        """
        Check if the system should be in quiet mode.
        
        Returns True if:
        - Quiet mode is enabled (user setting) AND we're outside the active window
        
        Returns False if:
        - Quiet mode is disabled by user, OR
        - We're within the active trading window
        """
        # If quiet mode is disabled by user, never enter quiet mode
        if not self._quiet_mode_enabled:
            return False
        
        # Otherwise, quiet mode is active outside the trading window
        return not self.is_active_window()
    
    def get_poll_interval(self) -> int:
        """
        Get the appropriate polling interval based on current mode.
        
        Returns:
            Poll interval in seconds:
            - 30 seconds during active window
            - 5 minutes during quiet mode
        """
        if self.is_active_window():
            return NORMAL_MODE_POLL_INTERVAL
        return QUIET_MODE_POLL_INTERVAL
    
    def get_status(self) -> dict:
        """Get current market hours status."""
        now = datetime.now(ET)
        current_time = now.time()
        
        return {
            "current_time_et": now.strftime("%Y-%m-%d %H:%M:%S"),
            "is_market_day": self.is_market_day(now),
            "is_market_open": self.is_market_open(),
            "is_active_window": self.is_active_window(),
            "is_quiet_mode": self.is_quiet_mode(),
            "quiet_mode_enabled": self._quiet_mode_enabled,  # User setting
            "active_window_start": str(ACTIVE_WINDOW_START),
            "active_window_end": str(ACTIVE_WINDOW_END),
            "market_open": str(MARKET_OPEN),
            "market_close": str(MARKET_CLOSE),
            "poll_interval_seconds": self.get_poll_interval(),
            "next_active_start": self._get_next_active_start(now),
        }
    
    def _get_next_active_start(self, now: datetime) -> Optional[str]:
        """Get the next time the active window starts."""
        current_time = now.time()
        
        # If before active window today, it starts later today
        if current_time < ACTIVE_WINDOW_START and self.is_market_day(now):
            target = now.replace(
                hour=ACTIVE_WINDOW_START.hour,
                minute=ACTIVE_WINDOW_START.minute,
                second=0,
                microsecond=0
            )
            return target.strftime("%Y-%m-%d %H:%M:%S")
        
        # Otherwise, find next market day
        target = now + timedelta(days=1)
        target = target.replace(
            hour=ACTIVE_WINDOW_START.hour,
            minute=ACTIVE_WINDOW_START.minute,
            second=0,
            microsecond=0
        )
        
        # Skip weekends
        while target.weekday() >= 5:
            target += timedelta(days=1)
        
        # Skip holidays
        while target.strftime("%Y-%m-%d") in MARKET_HOLIDAYS:
            target += timedelta(days=1)
            while target.weekday() >= 5:
                target += timedelta(days=1)
        
        return target.strftime("%Y-%m-%d %H:%M:%S")
    
    def time_until_active(self) -> Optional[timedelta]:
        """Get time until the active window starts, or None if already active."""
        if self.is_active_window():
            return None
        
        now = datetime.now(ET)
        next_start = self._get_next_active_start(now)
        if next_start:
            target = datetime.strptime(next_start, "%Y-%m-%d %H:%M:%S")
            target = target.replace(tzinfo=ET)
            return target - now
        return None


# Global singleton instance
_market_hours_manager: Optional[MarketHoursManager] = None


def get_market_hours_manager() -> MarketHoursManager:
    """Get the global market hours manager singleton."""
    global _market_hours_manager
    if _market_hours_manager is None:
        _market_hours_manager = MarketHoursManager()
    return _market_hours_manager


# Convenience functions
def is_active_window() -> bool:
    """Check if we're in the active trading window."""
    return get_market_hours_manager().is_active_window()


def is_quiet_mode() -> bool:
    """Check if the system should be in quiet mode."""
    return get_market_hours_manager().is_quiet_mode()


def get_poll_interval() -> int:
    """Get the appropriate polling interval for current mode."""
    return get_market_hours_manager().get_poll_interval()


def is_market_open(include_extended: bool = False) -> bool:
    """Check if the market is currently open."""
    return get_market_hours_manager().is_market_open(include_extended)


def is_market_day() -> bool:
    """Check if today is a trading day."""
    return get_market_hours_manager().is_market_day()


def set_quiet_mode_enabled(enabled: bool) -> None:
    """Enable or disable quiet mode."""
    get_market_hours_manager().set_quiet_mode_enabled(enabled)


def is_quiet_mode_enabled() -> bool:
    """Check if quiet mode is enabled (user setting)."""
    return get_market_hours_manager().is_quiet_mode_enabled()
