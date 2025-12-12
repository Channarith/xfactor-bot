"""
Bot Manager for managing multiple trading bot instances.
"""

import threading
from datetime import datetime
from typing import Optional, Callable

from loguru import logger

from src.bot.bot_instance import BotInstance, BotConfig, BotStatus


class BotManager:
    """
    Manager for multiple trading bot instances.
    
    Features:
    - Create and manage up to 10 bot instances
    - Start/stop/pause individual bots
    - Monitor all bots status
    - Aggregate statistics
    """
    
    MAX_BOTS = 10
    
    def __init__(self):
        """Initialize the bot manager."""
        self._bots: dict[str, BotInstance] = {}
        self._lock = threading.Lock()
        self._global_callbacks: dict[str, list[Callable]] = {
            "on_bot_created": [],
            "on_bot_started": [],
            "on_bot_stopped": [],
            "on_bot_error": [],
        }
        
        logger.info("Bot Manager initialized")
    
    @property
    def bot_count(self) -> int:
        """Get number of bots."""
        return len(self._bots)
    
    @property
    def running_count(self) -> int:
        """Get number of running bots."""
        return sum(1 for bot in self._bots.values() if bot.is_running)
    
    @property
    def can_create_bot(self) -> bool:
        """Check if we can create more bots."""
        return self.bot_count < self.MAX_BOTS
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a global callback."""
        if event in self._global_callbacks:
            self._global_callbacks[event].append(callback)
    
    def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit a global event."""
        for callback in self._global_callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Bot Manager callback error: {e}")
    
    def create_bot(self, config: BotConfig, bot_id: str = None) -> Optional[BotInstance]:
        """
        Create a new bot instance.
        
        Args:
            config: Bot configuration
            bot_id: Optional custom bot ID
            
        Returns:
            BotInstance or None if max bots reached
        """
        with self._lock:
            if not self.can_create_bot:
                logger.warning(f"Cannot create bot: maximum of {self.MAX_BOTS} bots reached")
                return None
            
            # Check for duplicate ID
            if bot_id and bot_id in self._bots:
                logger.warning(f"Bot ID {bot_id} already exists")
                return None
            
            # Create bot
            bot = BotInstance(config, bot_id)
            
            # Register internal callbacks
            bot.register_callback("on_start", lambda b: self._emit("on_bot_started", b))
            bot.register_callback("on_stop", lambda b: self._emit("on_bot_stopped", b))
            bot.register_callback("on_error", lambda b, e: self._emit("on_bot_error", b, e))
            
            self._bots[bot.id] = bot
            self._emit("on_bot_created", bot)
            
            logger.info(f"Created bot {bot.id}: {config.name} ({self.bot_count}/{self.MAX_BOTS})")
            return bot
    
    def get_bot(self, bot_id: str) -> Optional[BotInstance]:
        """Get a bot by ID."""
        return self._bots.get(bot_id)
    
    def get_all_bots(self) -> list[BotInstance]:
        """Get all bots."""
        return list(self._bots.values())
    
    def delete_bot(self, bot_id: str) -> bool:
        """
        Delete a bot (stops it first if running).
        
        Args:
            bot_id: Bot ID to delete
            
        Returns:
            True if deleted
        """
        with self._lock:
            bot = self._bots.get(bot_id)
            if not bot:
                return False
            
            # Stop if running
            if bot.status in (BotStatus.RUNNING, BotStatus.PAUSED):
                bot.stop()
            
            del self._bots[bot_id]
            logger.info(f"Deleted bot {bot_id}")
            return True
    
    def start_bot(self, bot_id: str) -> bool:
        """Start a specific bot."""
        bot = self._bots.get(bot_id)
        if not bot:
            return False
        return bot.start()
    
    def stop_bot(self, bot_id: str) -> bool:
        """Stop a specific bot."""
        bot = self._bots.get(bot_id)
        if not bot:
            return False
        return bot.stop()
    
    def pause_bot(self, bot_id: str) -> bool:
        """Pause a specific bot."""
        bot = self._bots.get(bot_id)
        if not bot:
            return False
        return bot.pause()
    
    def resume_bot(self, bot_id: str) -> bool:
        """Resume a paused bot."""
        bot = self._bots.get(bot_id)
        if not bot:
            return False
        return bot.resume()
    
    def start_all(self) -> dict[str, bool]:
        """Start all stopped bots."""
        results = {}
        for bot_id, bot in self._bots.items():
            if bot.status in (BotStatus.CREATED, BotStatus.STOPPED):
                results[bot_id] = bot.start()
            else:
                results[bot_id] = False
        return results
    
    def stop_all(self) -> dict[str, bool]:
        """Stop all running bots."""
        results = {}
        for bot_id, bot in self._bots.items():
            if bot.status in (BotStatus.RUNNING, BotStatus.PAUSED):
                results[bot_id] = bot.stop()
            else:
                results[bot_id] = False
        return results
    
    def pause_all(self) -> dict[str, bool]:
        """Pause all running bots."""
        results = {}
        for bot_id, bot in self._bots.items():
            if bot.is_running:
                results[bot_id] = bot.pause()
            else:
                results[bot_id] = False
        return results
    
    def resume_all(self) -> dict[str, bool]:
        """Resume all paused bots."""
        results = {}
        for bot_id, bot in self._bots.items():
            if bot.is_paused:
                results[bot_id] = bot.resume()
            else:
                results[bot_id] = False
        return results
    
    def get_status(self) -> dict:
        """Get overall status of all bots."""
        bots_status = [bot.get_status() for bot in self._bots.values()]
        
        # Aggregate stats
        total_pnl = sum(b["stats"]["daily_pnl"] for b in bots_status)
        total_trades = sum(b["stats"]["trades_today"] for b in bots_status)
        total_positions = sum(b["stats"]["open_positions"] for b in bots_status)
        total_errors = sum(b["stats"]["errors_count"] for b in bots_status)
        
        return {
            "max_bots": self.MAX_BOTS,
            "total_bots": self.bot_count,
            "running_bots": self.running_count,
            "paused_bots": sum(1 for b in self._bots.values() if b.is_paused),
            "stopped_bots": sum(1 for b in self._bots.values() if b.status == BotStatus.STOPPED),
            "can_create_more": self.can_create_bot,
            "aggregate_stats": {
                "total_daily_pnl": total_pnl,
                "total_trades_today": total_trades,
                "total_open_positions": total_positions,
                "total_errors": total_errors,
            },
            "bots": bots_status,
        }
    
    def get_bot_summary(self) -> list[dict]:
        """Get summary of all bots (lightweight)."""
        return [
            {
                "id": bot.id,
                "name": bot.config.name,
                "status": bot.status.value,
                "symbols_count": len(bot.config.symbols),
                "strategies": bot.config.strategies,
                "daily_pnl": bot.stats.daily_pnl,
                "uptime_seconds": bot.uptime,
            }
            for bot in self._bots.values()
        ]


# Global bot manager instance
_bot_manager: Optional[BotManager] = None
_initialized: bool = False


def _create_default_bots(manager: BotManager) -> None:
    """Create default bot configurations."""
    default_bots = [
        BotConfig(
            name="Tech Momentum",
            description="Momentum trading on tech stocks",
            symbols=["NVDA", "AMD", "TSLA", "META", "GOOGL"],
            strategies=["Technical", "Momentum"],
            max_position_size=25000,
            max_positions=5,
        ),
        BotConfig(
            name="ETF Swing Trader",
            description="Swing trading on major ETFs",
            symbols=["SPY", "QQQ", "IWM", "DIA"],
            strategies=["Technical", "MeanReversion"],
            max_position_size=30000,
            max_positions=4,
        ),
        BotConfig(
            name="News Sentiment Bot",
            description="React to breaking news",
            symbols=["AAPL", "MSFT", "AMZN", "NVDA"],
            strategies=["NewsSentiment", "Momentum"],
            max_position_size=20000,
            max_positions=4,
            enable_news_trading=True,
        ),
        BotConfig(
            name="Mean Reversion",
            description="Fade extreme moves",
            symbols=["SPY", "QQQ", "XLF", "XLE"],
            strategies=["MeanReversion"],
            max_position_size=15000,
            max_positions=4,
        ),
        BotConfig(
            name="International ADR",
            description="Trade international stocks",
            symbols=["BABA", "TSM", "NVO", "ASML"],
            strategies=["Technical", "NewsSentiment"],
            max_position_size=20000,
            max_positions=4,
        ),
    ]
    
    for config in default_bots:
        manager.create_bot(config)
    
    logger.info(f"Created {len(default_bots)} default bots")


def get_bot_manager() -> BotManager:
    """Get or create the global bot manager."""
    global _bot_manager, _initialized
    if _bot_manager is None:
        _bot_manager = BotManager()
    
    # Initialize with default bots on first access
    if not _initialized and _bot_manager.bot_count == 0:
        _initialized = True
        _create_default_bots(_bot_manager)
    
    return _bot_manager

