"""
XFactor Bot Background Service.

Standalone service that runs trading bots independently of the desktop application.
Supports:
- Continuous running during market hours
- Scheduled execution
- Auto-start on system boot (via launchd)
"""

from src.service.bot_service import BotService, get_bot_service
from src.service.scheduler import TradingScheduler, ScheduleConfig

__all__ = [
    "BotService",
    "get_bot_service",
    "TradingScheduler",
    "ScheduleConfig",
]

