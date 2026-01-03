"""
Trading Scheduler for the XFactor Bot Service.

Manages scheduled bot execution based on:
- Market hours (9:30 AM - 4:00 PM ET)
- Custom schedules per bot
- Interval-based execution
- Pre-market and after-hours support
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional, Awaitable
from zoneinfo import ZoneInfo

from loguru import logger


# US Eastern timezone for market hours
ET = ZoneInfo("America/New_York")

# Market hours
MARKET_OPEN = time(9, 30)  # 9:30 AM ET
MARKET_CLOSE = time(16, 0)  # 4:00 PM ET
PRE_MARKET_OPEN = time(4, 0)  # 4:00 AM ET
AFTER_HOURS_CLOSE = time(20, 0)  # 8:00 PM ET

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


class ScheduleType(str, Enum):
    """Types of schedules."""
    CONTINUOUS = "continuous"  # Run continuously during market hours
    INTERVAL = "interval"  # Run every N minutes/hours
    SPECIFIC_TIMES = "specific_times"  # Run at specific times
    MARKET_EVENTS = "market_events"  # Run at market open/close


@dataclass
class ScheduleConfig:
    """Configuration for a bot's schedule."""
    schedule_type: ScheduleType = ScheduleType.CONTINUOUS
    
    # For interval schedule
    interval_minutes: int = 5  # Run every N minutes
    
    # For specific times schedule (in ET)
    specific_times: List[str] = field(default_factory=list)  # e.g., ["09:30", "10:00", "15:30"]
    
    # Market session options
    include_pre_market: bool = False
    include_after_hours: bool = False
    
    # Market event options
    run_at_open: bool = True
    run_at_close: bool = True
    
    # Days to run (0=Monday, 6=Sunday)
    active_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Mon-Fri
    
    # Timezone for specific times
    timezone: str = "America/New_York"
    
    def to_dict(self) -> dict:
        return {
            "schedule_type": self.schedule_type.value,
            "interval_minutes": self.interval_minutes,
            "specific_times": self.specific_times,
            "include_pre_market": self.include_pre_market,
            "include_after_hours": self.include_after_hours,
            "run_at_open": self.run_at_open,
            "run_at_close": self.run_at_close,
            "active_days": self.active_days,
            "timezone": self.timezone,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleConfig":
        if "schedule_type" in data:
            data["schedule_type"] = ScheduleType(data["schedule_type"])
        return cls(**data)


class TradingScheduler:
    """
    Scheduler for trading bot execution.
    
    Handles:
    - Market hours detection
    - Interval-based scheduling
    - Custom time schedules
    - Holiday handling
    """
    
    def __init__(
        self,
        on_schedule_trigger: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ):
        """
        Initialize the scheduler.
        
        Args:
            on_schedule_trigger: Async callback when a scheduled action triggers.
                                 Called with (bot_id, action) where action is
                                 "start", "stop", or "cycle".
        """
        self._on_trigger = on_schedule_trigger
        self._bot_schedules: Dict[str, ScheduleConfig] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_check: Optional[datetime] = None
        
        logger.info("TradingScheduler initialized")
    
    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("TradingScheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("TradingScheduler stopped")
    
    def add_bot_schedule(self, bot_id: str, schedule: dict | ScheduleConfig) -> None:
        """Add or update a bot's schedule."""
        if isinstance(schedule, dict):
            schedule = ScheduleConfig.from_dict(schedule)
        self._bot_schedules[bot_id] = schedule
        logger.info(f"Added schedule for bot {bot_id}: {schedule.schedule_type.value}")
    
    def remove_bot_schedule(self, bot_id: str) -> None:
        """Remove a bot's schedule."""
        if bot_id in self._bot_schedules:
            del self._bot_schedules[bot_id]
            logger.info(f"Removed schedule for bot {bot_id}")
    
    def get_bot_schedule(self, bot_id: str) -> Optional[ScheduleConfig]:
        """Get a bot's schedule configuration."""
        return self._bot_schedules.get(bot_id)
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.now(ET)
                self._last_check = now
                
                for bot_id, schedule in self._bot_schedules.items():
                    try:
                        action = self._check_schedule(bot_id, schedule, now)
                        if action and self._on_trigger:
                            await self._on_trigger(bot_id, action)
                    except Exception as e:
                        logger.error(f"Error checking schedule for {bot_id}: {e}")
                
                # Sleep until next check (every 30 seconds)
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    def _check_schedule(
        self,
        bot_id: str,
        schedule: ScheduleConfig,
        now: datetime,
    ) -> Optional[str]:
        """
        Check if a scheduled action should trigger.
        
        Returns: Action to take ("start", "stop", "cycle") or None.
        """
        # Check if today is an active day
        if now.weekday() not in schedule.active_days:
            return None
        
        # Check if today is a market holiday
        if now.strftime("%Y-%m-%d") in MARKET_HOLIDAYS:
            return None
        
        current_time = now.time()
        
        # Determine active trading window
        start_time = PRE_MARKET_OPEN if schedule.include_pre_market else MARKET_OPEN
        end_time = AFTER_HOURS_CLOSE if schedule.include_after_hours else MARKET_CLOSE
        
        is_market_hours = start_time <= current_time <= end_time
        
        # Handle different schedule types
        if schedule.schedule_type == ScheduleType.CONTINUOUS:
            # Start at market open, stop at close
            if self._is_near_time(current_time, start_time, tolerance_seconds=60):
                return "start"
            elif self._is_near_time(current_time, end_time, tolerance_seconds=60):
                return "stop"
        
        elif schedule.schedule_type == ScheduleType.INTERVAL:
            if is_market_hours:
                # Check if we should trigger based on interval
                minutes_since_open = self._minutes_since(start_time, current_time)
                if minutes_since_open % schedule.interval_minutes < 1:  # Within 1 minute of interval
                    return "cycle"
        
        elif schedule.schedule_type == ScheduleType.SPECIFIC_TIMES:
            for time_str in schedule.specific_times:
                try:
                    h, m = map(int, time_str.split(":"))
                    specific_time = time(h, m)
                    if self._is_near_time(current_time, specific_time, tolerance_seconds=60):
                        return "cycle"
                except ValueError:
                    logger.warning(f"Invalid time format: {time_str}")
        
        elif schedule.schedule_type == ScheduleType.MARKET_EVENTS:
            if schedule.run_at_open and self._is_near_time(current_time, MARKET_OPEN, tolerance_seconds=60):
                return "start"
            elif schedule.run_at_close and self._is_near_time(current_time, MARKET_CLOSE, tolerance_seconds=60):
                return "stop"
        
        return None
    
    def _is_near_time(self, current: time, target: time, tolerance_seconds: int = 60) -> bool:
        """Check if current time is near target time within tolerance."""
        current_seconds = current.hour * 3600 + current.minute * 60 + current.second
        target_seconds = target.hour * 3600 + target.minute * 60 + target.second
        return abs(current_seconds - target_seconds) <= tolerance_seconds
    
    def _minutes_since(self, start: time, current: time) -> int:
        """Calculate minutes since start time."""
        start_minutes = start.hour * 60 + start.minute
        current_minutes = current.hour * 60 + current.minute
        return current_minutes - start_minutes
    
    @staticmethod
    def is_market_open(include_extended: bool = False) -> bool:
        """Check if the US stock market is currently open."""
        now = datetime.now(ET)
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check if it's a holiday
        if now.strftime("%Y-%m-%d") in MARKET_HOLIDAYS:
            return False
        
        current_time = now.time()
        
        if include_extended:
            return PRE_MARKET_OPEN <= current_time <= AFTER_HOURS_CLOSE
        else:
            return MARKET_OPEN <= current_time <= MARKET_CLOSE
    
    @staticmethod
    def time_until_market_open() -> Optional[timedelta]:
        """Get time until market opens, or None if already open."""
        now = datetime.now(ET)
        
        if TradingScheduler.is_market_open():
            return None
        
        # Find next market open
        target = now.replace(hour=9, minute=30, second=0, microsecond=0)
        
        if now.time() > MARKET_CLOSE:
            # After close, next open is tomorrow
            target += timedelta(days=1)
        
        # Skip weekends
        while target.weekday() >= 5:
            target += timedelta(days=1)
        
        # Skip holidays
        while target.strftime("%Y-%m-%d") in MARKET_HOLIDAYS:
            target += timedelta(days=1)
        
        return target - now
    
    @staticmethod
    def get_next_trading_day() -> datetime:
        """Get the next trading day."""
        now = datetime.now(ET)
        target = now.replace(hour=9, minute=30, second=0, microsecond=0)
        
        if now.time() > MARKET_CLOSE or now.weekday() >= 5:
            target += timedelta(days=1)
        
        # Skip weekends
        while target.weekday() >= 5:
            target += timedelta(days=1)
        
        # Skip holidays
        while target.strftime("%Y-%m-%d") in MARKET_HOLIDAYS:
            target += timedelta(days=1)
        
        return target


# ============================================================================
# MOMENTUM SCAN SCHEDULER
# ============================================================================

class MomentumScanScheduler:
    """
    Dedicated scheduler for momentum universe scanning.
    
    Tiered refresh strategy:
    - Hot 100: Every 15 minutes during market hours
    - Active 1000: Every 60 minutes during market hours
    - Full Universe: 5:00 AM and 5:00 PM ET
    """
    
    # Scan times for full universe (ET)
    FULL_SCAN_TIMES = [
        time(5, 0),   # 5:00 AM pre-market
        time(17, 0),  # 5:00 PM after-hours
    ]
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_hot_scan: Optional[datetime] = None
        self._last_active_scan: Optional[datetime] = None
        self._last_full_scan: Optional[datetime] = None
        
        logger.info("MomentumScanScheduler initialized")
    
    def start(self) -> None:
        """Start the momentum scan scheduler."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info("MomentumScanScheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("MomentumScanScheduler stopped")
    
    async def _scan_loop(self) -> None:
        """Main scanning loop."""
        while self._running:
            try:
                now = datetime.now(ET)
                
                # Check if market day (not weekend/holiday)
                is_market_day = now.weekday() < 5 and now.strftime("%Y-%m-%d") not in MARKET_HOLIDAYS
                
                if is_market_day:
                    await self._check_and_run_scans(now)
                
                # Sleep for 1 minute between checks
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Momentum scan loop error: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_run_scans(self, now: datetime) -> None:
        """Check which scans need to run and execute them."""
        from src.data.universe_scanner import get_universe_scanner
        
        scanner = get_universe_scanner()
        current_time = now.time()
        is_market_hours = MARKET_OPEN <= current_time <= MARKET_CLOSE
        
        # Hot 100: Every 15 minutes during market hours
        if is_market_hours:
            if self._should_run_hot_scan(now):
                logger.info("Triggering Hot 100 scan")
                asyncio.create_task(self._run_hot_scan(scanner))
                self._last_hot_scan = now
        
        # Active 1000: Every 60 minutes during market hours
        if is_market_hours:
            if self._should_run_active_scan(now):
                logger.info("Triggering Active 1000 scan")
                asyncio.create_task(self._run_active_scan(scanner))
                self._last_active_scan = now
        
        # Full Universe: At scheduled times
        if self._should_run_full_scan(now):
            logger.info("Triggering Full Universe scan")
            asyncio.create_task(self._run_full_scan(scanner))
            self._last_full_scan = now
    
    def _should_run_hot_scan(self, now: datetime) -> bool:
        """Check if hot 100 scan should run."""
        if self._last_hot_scan is None:
            return True
        return (now - self._last_hot_scan) >= timedelta(minutes=15)
    
    def _should_run_active_scan(self, now: datetime) -> bool:
        """Check if active 1000 scan should run."""
        if self._last_active_scan is None:
            return True
        return (now - self._last_active_scan) >= timedelta(minutes=60)
    
    def _should_run_full_scan(self, now: datetime) -> bool:
        """Check if full universe scan should run."""
        current_time = now.time()
        
        for scan_time in self.FULL_SCAN_TIMES:
            # Within 5 minutes of scheduled time
            if self._is_near_time(current_time, scan_time, tolerance_seconds=300):
                # Haven't scanned in the last hour
                if self._last_full_scan is None:
                    return True
                if (now - self._last_full_scan) >= timedelta(hours=1):
                    return True
        
        return False
    
    def _is_near_time(self, current: time, target: time, tolerance_seconds: int) -> bool:
        """Check if current time is near target time."""
        current_seconds = current.hour * 3600 + current.minute * 60 + current.second
        target_seconds = target.hour * 3600 + target.minute * 60 + target.second
        return abs(current_seconds - target_seconds) <= tolerance_seconds
    
    async def _run_hot_scan(self, scanner) -> None:
        """Run hot 100 scan and refresh rankings."""
        try:
            await scanner.scan_hot_100()
            await self._refresh_rankings()
        except Exception as e:
            logger.error(f"Hot scan failed: {e}")
    
    async def _run_active_scan(self, scanner) -> None:
        """Run active 1000 scan and refresh rankings."""
        try:
            await scanner.scan_active_1000()
            await self._refresh_rankings()
        except Exception as e:
            logger.error(f"Active scan failed: {e}")
    
    async def _run_full_scan(self, scanner) -> None:
        """Run full universe scan and refresh rankings."""
        try:
            await scanner.scan_full_universe()
            await self._refresh_rankings()
        except Exception as e:
            logger.error(f"Full scan failed: {e}")
    
    async def _refresh_rankings(self) -> None:
        """Refresh momentum rankings after scan."""
        try:
            from src.data.momentum_screener import get_momentum_screener
            screener = get_momentum_screener()
            await screener.refresh_rankings()
        except Exception as e:
            logger.error(f"Rankings refresh failed: {e}")
    
    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self._running,
            "last_hot_scan": self._last_hot_scan.isoformat() if self._last_hot_scan else None,
            "last_active_scan": self._last_active_scan.isoformat() if self._last_active_scan else None,
            "last_full_scan": self._last_full_scan.isoformat() if self._last_full_scan else None,
        }


# Global momentum scan scheduler
_momentum_scheduler: Optional[MomentumScanScheduler] = None


def get_momentum_scan_scheduler() -> MomentumScanScheduler:
    """Get the global momentum scan scheduler."""
    global _momentum_scheduler
    if _momentum_scheduler is None:
        _momentum_scheduler = MomentumScanScheduler()
    return _momentum_scheduler

