"""
Bot Manager for managing multiple trading bot instances.

Features:
- Create and manage up to 100 bot instances
- Persistent storage of bot configurations and state
- Resume bots on app restart with saved positions
"""

import threading
from datetime import datetime
from typing import Optional, Callable

from loguru import logger

from src.bot.bot_instance import BotInstance, BotConfig, BotStatus, InstrumentType, SignalPreset
from src.bot.auto_optimizer import (
    get_auto_optimizer_manager,
    BotAutoOptimizer,
    OptimizationConfig,
    OptimizationMode,
)
from src.bot.saved_bots import get_saved_bots_manager, SavedBotsManager


class BotManager:
    """
    Manager for multiple trading bot instances.
    
    Features:
    - Create and manage up to 100 bot instances
    - Start/stop/pause individual bots
    - Monitor all bots status
    - Aggregate statistics
    - Auto-optimization integration for dynamic parameter tuning
    """
    
    MAX_BOTS = 100  # Support for stocks, options, futures, crypto, and commodity bots
    
    # Global settings - can be overridden per-bot
    DEFAULT_MULTI_BROKER = True  # When True, bots trade on ALL connected brokers by default
    
    def __init__(self):
        """Initialize the bot manager."""
        self._bots: dict[str, BotInstance] = {}
        self._lock = threading.Lock()
        self._global_callbacks: dict[str, list[Callable]] = {
            "on_bot_created": [],
            "on_bot_started": [],
            "on_bot_stopped": [],
            "on_bot_error": [],
            "on_trade_completed": [],
        }
        
        # Position tracking: maps (symbol, broker) -> {bot_id, bot_name, opened_at, quantity}
        self._position_tracking: dict[tuple, dict] = {}
        self._position_lock = threading.Lock()
        
        # Auto-optimizer integration
        self._optimizer_manager = get_auto_optimizer_manager()
        
        # Persistence manager for saving/loading bot state
        self._saved_bots_manager: SavedBotsManager = get_saved_bots_manager()
        
        # Auto-save settings
        self._auto_save_enabled = True
        self._last_save_time: Optional[datetime] = None
        
        logger.info(f"Bot Manager initialized with auto-optimizer support (multi_broker={self.DEFAULT_MULTI_BROKER})")
    
    def track_position_open(self, symbol: str, broker: str, bot_id: str, bot_name: str, quantity: float) -> None:
        """Track which bot opened a position."""
        with self._position_lock:
            key = (symbol.upper(), broker.upper())
            self._position_tracking[key] = {
                "bot_id": bot_id,
                "bot_name": bot_name,
                "opened_at": datetime.now().isoformat(),
                "quantity": quantity,
            }
            logger.debug(f"Position tracked: {symbol} on {broker} opened by bot {bot_name} ({bot_id})")
        
        # Save position tracking to disk
        self.save_position_tracking()
    
    def track_position_close(self, symbol: str, broker: str) -> None:
        """Remove position tracking when closed."""
        with self._position_lock:
            key = (symbol.upper(), broker.upper())
            if key in self._position_tracking:
                del self._position_tracking[key]
                logger.debug(f"Position tracking removed: {symbol} on {broker}")
        
        # Save position tracking to disk
        self.save_position_tracking()
    
    def get_position_bot(self, symbol: str, broker: str) -> Optional[dict]:
        """Get the bot that opened a position."""
        with self._position_lock:
            key = (symbol.upper(), broker.upper())
            return self._position_tracking.get(key)
    
    def get_all_position_tracking(self) -> dict:
        """Get all position tracking info."""
        with self._position_lock:
            return {
                f"{symbol}@{broker}": info 
                for (symbol, broker), info in self._position_tracking.items()
            }
    
    async def sync_positions_from_broker(self, broker_type: str = None) -> int:
        """
        Sync position tracking with actual broker positions.
        
        For positions that exist in the broker but aren't tracked,
        marks them as 'pre-existing' (opened before bot tracking started).
        
        Returns count of positions synced.
        """
        try:
            from src.brokers.registry import get_broker_registry
            registry = get_broker_registry()
            
            synced = 0
            
            for bt in registry.connected_brokers:
                if broker_type and bt.value.lower() != broker_type.lower():
                    continue
                    
                broker = registry.get_broker(bt)
                if not broker or not broker.is_connected:
                    continue
                
                try:
                    accounts = await broker.get_accounts()
                    if not accounts:
                        continue
                    
                    account_id = accounts[0].account_id
                    positions = await broker.get_positions(account_id)
                    
                    with self._position_lock:
                        for pos in positions:
                            key = (pos.symbol.upper(), bt.value.upper())
                            
                            # Only add if not already tracked
                            if key not in self._position_tracking:
                                self._position_tracking[key] = {
                                    "bot_id": "pre-existing",
                                    "bot_name": "Pre-existing Position",
                                    "opened_at": None,  # Unknown
                                    "quantity": pos.quantity,
                                    "synced": True,  # Mark as synced, not bot-opened
                                }
                                synced += 1
                                logger.debug(f"Synced pre-existing position: {pos.symbol} on {bt.value}")
                    
                except Exception as e:
                    logger.error(f"Error syncing positions from {bt.value}: {e}")
            
            if synced > 0:
                logger.info(f"Synced {synced} pre-existing positions from brokers")
            
            return synced
            
        except Exception as e:
            logger.error(f"Error in sync_positions_from_broker: {e}")
            return 0
    
    async def get_position_across_brokers(self, symbol: str) -> dict:
        """
        Get position for a symbol across ALL connected brokers.
        
        This helps identify which broker(s) hold a position.
        
        Returns:
            Dict mapping broker name to position info:
            {
                "IBKR": {"quantity": 100, "avg_cost": 150.25, ...},
                "ALPACA": {"quantity": 0, "error": None},
                ...
            }
        """
        try:
            from src.brokers.registry import get_broker_registry
            registry = get_broker_registry()
            
            results = {}
            symbol = symbol.upper()
            
            for bt in registry.connected_brokers:
                broker = registry.get_broker(bt)
                if not broker or not broker.is_connected:
                    results[bt.value.upper()] = {
                        "quantity": 0,
                        "connected": False,
                        "error": "Not connected"
                    }
                    continue
                
                try:
                    accounts = await broker.get_accounts()
                    if not accounts:
                        results[bt.value.upper()] = {
                            "quantity": 0,
                            "connected": True,
                            "error": "No accounts"
                        }
                        continue
                    
                    account_id = accounts[0].account_id
                    position = await broker.get_position(account_id, symbol)
                    
                    if position:
                        results[bt.value.upper()] = {
                            "quantity": position.quantity,
                            "avg_cost": position.avg_cost,
                            "current_price": position.current_price,
                            "market_value": position.market_value,
                            "unrealized_pnl": position.unrealized_pnl,
                            "connected": True,
                            "error": None
                        }
                    else:
                        results[bt.value.upper()] = {
                            "quantity": 0,
                            "connected": True,
                            "error": None
                        }
                        
                except Exception as e:
                    results[bt.value.upper()] = {
                        "quantity": 0,
                        "connected": True,
                        "error": str(e)
                    }
                    logger.debug(f"Error getting position for {symbol} from {bt.value}: {e}")
            
            # Log summary
            brokers_with_position = [
                f"{b}: {info['quantity']}" 
                for b, info in results.items() 
                if info.get('quantity', 0) > 0
            ]
            
            if brokers_with_position:
                logger.info(f"Position {symbol} found on: {', '.join(brokers_with_position)}")
            else:
                logger.debug(f"Position {symbol}: Not held on any connected broker")
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting positions across brokers for {symbol}: {e}")
            return {}
    
    async def validate_sell_across_brokers(
        self, 
        symbol: str, 
        quantity: float,
        target_broker: str = None
    ) -> dict:
        """
        Validate a sell order across brokers.
        
        Checks if the position exists on the target broker (or any broker if not specified).
        Returns detailed information about where the position exists.
        
        Args:
            symbol: Stock symbol to sell
            quantity: Quantity to sell
            target_broker: Specific broker to check (e.g., "ibkr", "alpaca")
            
        Returns:
            Dict with validation result and details
        """
        positions = await self.get_position_across_brokers(symbol)
        
        result = {
            "symbol": symbol,
            "requested_quantity": quantity,
            "can_sell": False,
            "target_broker": target_broker,
            "positions_by_broker": positions,
            "brokers_with_position": [],
            "total_quantity_available": 0,
            "recommendation": ""
        }
        
        # Calculate totals
        for broker, info in positions.items():
            qty = info.get("quantity", 0)
            if qty > 0:
                result["brokers_with_position"].append(broker)
                result["total_quantity_available"] += qty
        
        # Validate
        if target_broker:
            target_upper = target_broker.upper()
            target_info = positions.get(target_upper, {})
            target_qty = target_info.get("quantity", 0)
            
            if target_qty >= quantity:
                result["can_sell"] = True
                result["recommendation"] = f"OK: {target_upper} has {target_qty} shares (selling {quantity})"
            elif target_qty > 0:
                result["can_sell"] = False
                result["recommendation"] = (
                    f"PARTIAL: {target_upper} only has {target_qty} of {quantity} requested. "
                    f"Reduce quantity or check other brokers."
                )
            else:
                # Check if position exists elsewhere
                if result["brokers_with_position"]:
                    result["recommendation"] = (
                        f"WRONG BROKER: No position on {target_upper}. "
                        f"Position exists on: {', '.join(result['brokers_with_position'])}. "
                        f"Configure bot for correct broker."
                    )
                else:
                    result["recommendation"] = (
                        f"NO POSITION: {symbol} not held on any connected broker"
                    )
        else:
            if result["total_quantity_available"] >= quantity:
                result["can_sell"] = True
                result["recommendation"] = (
                    f"OK: Total {result['total_quantity_available']} shares available "
                    f"on {', '.join(result['brokers_with_position'])}"
                )
            else:
                result["recommendation"] = f"INSUFFICIENT: Only {result['total_quantity_available']} shares available"
        
        # Log the validation result
        if not result["can_sell"]:
            logger.warning(f"Sell validation failed for {symbol}: {result['recommendation']}")
        
        return result
    
    @property
    def bot_count(self) -> int:
        """Get number of bots."""
        return len(self._bots)
    
    @property
    def bots(self) -> dict:
        """Get all bots dict (for backwards compatibility)."""
        return self._bots
    
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
            
            # Apply default multi-broker setting if not explicitly set
            # This ensures trades go to ALL connected brokers by default
            if config.broker_type is None and not config.multi_broker:
                config.multi_broker = self.DEFAULT_MULTI_BROKER
                logger.debug(f"Applied default multi_broker={self.DEFAULT_MULTI_BROKER} to bot '{config.name}'")
            
            # Create bot
            bot = BotInstance(config, bot_id)
            
            # Register internal callbacks
            bot.register_callback("on_start", lambda b: self._emit("on_bot_started", b))
            bot.register_callback("on_stop", lambda b: self._emit("on_bot_stopped", b))
            bot.register_callback("on_error", lambda b, e: self._emit("on_bot_error", b, e))
            
            # Register trade callback for auto-optimizer
            bot.register_callback("on_trade", lambda b, trade: self._on_trade_completed(b, trade))
            
            self._bots[bot.id] = bot
            self._emit("on_bot_created", bot)
            
            # Register with auto-optimizer
            self._register_bot_optimizer(bot)
            
            logger.info(f"Created bot {bot.id}: {config.name} ({self.bot_count}/{self.MAX_BOTS})")
            
            # Auto-save after creating bot
            self._auto_save()
            
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
            
            # Unregister from auto-optimizer
            self._optimizer_manager.unregister_bot(bot_id)
            
            # Remove from saved bots
            self._saved_bots_manager.delete_bot(bot_id)
            
            logger.info(f"Deleted bot {bot_id}")
            
            # Auto-save after deletion
            self._auto_save()
            
            return True
    
    def _register_bot_optimizer(self, bot: BotInstance) -> None:
        """Register a bot with the auto-optimizer."""
        def get_params() -> dict:
            """Get current bot parameters - uses actual BotConfig fields."""
            return {
                "options_stop_loss_pct": getattr(bot.config, 'options_stop_loss_pct', 30.0),
                "options_profit_target_pct": getattr(bot.config, 'options_profit_target_pct', 50.0),
                "crypto_trailing_stop_pct": getattr(bot.config, 'crypto_trailing_stop_pct', 5.0),
                "crypto_take_profit_pct": getattr(bot.config, 'crypto_take_profit_pct', 15.0),
                "max_position_size": bot.config.max_position_size,
                "max_positions": bot.config.max_positions,
                "max_daily_loss_pct": bot.config.max_daily_loss_pct,
                "news_sentiment_threshold": getattr(bot.config, 'news_sentiment_threshold', 0.5),
                "trade_frequency_seconds": bot.config.trade_frequency_seconds,
            }
        
        def set_params(params: dict) -> None:
            """Set bot parameters - uses actual BotConfig fields."""
            if "options_stop_loss_pct" in params:
                bot.config.options_stop_loss_pct = params["options_stop_loss_pct"]
            if "options_profit_target_pct" in params:
                bot.config.options_profit_target_pct = params["options_profit_target_pct"]
            if "crypto_trailing_stop_pct" in params:
                bot.config.crypto_trailing_stop_pct = params["crypto_trailing_stop_pct"]
            if "crypto_take_profit_pct" in params:
                bot.config.crypto_take_profit_pct = params["crypto_take_profit_pct"]
            if "max_position_size" in params:
                bot.config.max_position_size = params["max_position_size"]
            if "max_positions" in params:
                bot.config.max_positions = params["max_positions"]
            if "max_daily_loss_pct" in params:
                bot.config.max_daily_loss_pct = params["max_daily_loss_pct"]
            
            logger.info(f"Bot {bot.id} parameters updated by auto-optimizer")
        
        self._optimizer_manager.register_bot(
            bot_id=bot.id,
            get_params=get_params,
            set_params=set_params,
        )
    
    def _on_trade_completed(self, bot: BotInstance, trade: dict) -> None:
        """Handle trade completion - record for auto-optimizer."""
        self._optimizer_manager.record_trade(bot.id, trade)
        self._emit("on_trade_completed", bot, trade)
    
    async def enable_auto_optimization(
        self,
        bot_id: str,
        mode: str = "moderate"
    ) -> bool:
        """
        Enable auto-optimization for a bot.
        
        Args:
            bot_id: Bot to optimize
            mode: conservative, moderate, or aggressive
            
        Returns:
            True if enabled successfully
        """
        try:
            opt_mode = OptimizationMode(mode.lower())
        except ValueError:
            logger.error(f"Invalid optimization mode: {mode}")
            return False
        
        return await self._optimizer_manager.enable_bot(bot_id, opt_mode)
    
    async def disable_auto_optimization(self, bot_id: str) -> bool:
        """Disable auto-optimization for a bot."""
        return await self._optimizer_manager.disable_bot(bot_id)
    
    def get_optimizer_status(self, bot_id: str = None) -> dict:
        """
        Get auto-optimizer status.
        
        Args:
            bot_id: Specific bot or None for all
        """
        if bot_id:
            optimizer = self._optimizer_manager.get_optimizer(bot_id)
            return optimizer.get_status() if optimizer else {}
        return self._optimizer_manager.get_all_status()
    
    def get_optimization_recommendations(self) -> list[dict]:
        """Get optimization recommendations for all bots."""
        return self._optimizer_manager.get_recommendations()
    
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
    
    # =========================================================================
    # Persistence Methods - Save/Load bots and position tracking
    # =========================================================================
    
    def save_all_bots(self) -> bool:
        """
        Save all bot configurations and state to disk.
        
        This should be called:
        - When app is closing
        - After creating/deleting bots
        - Periodically for safety
        
        Returns:
            True if saved successfully
        """
        try:
            bots_data = []
            for bot in self._bots.values():
                bot_data = {
                    'bot_id': bot.id,
                    'config': bot.config.to_dict(),
                    'is_running': bot.is_running,
                    'auto_start': bot.is_running,  # Auto-start bots that were running
                    'stats': {
                        'trades_today': bot.stats.trades_today,
                        'daily_pnl': bot.stats.daily_pnl,
                        'total_pnl': getattr(bot.stats, 'total_pnl', 0.0),
                        'win_rate': getattr(bot.stats, 'win_rate_pct', 50.0),
                    },
                }
                bots_data.append(bot_data)
            
            success = self._saved_bots_manager.save_bots(bots_data)
            
            if success:
                self._last_save_time = datetime.now()
                logger.info(f"Saved {len(bots_data)} bots to persistent storage")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving bots: {e}")
            return False
    
    def save_single_bot(self, bot_id: str) -> bool:
        """
        Save a single bot's configuration and state.
        
        Args:
            bot_id: ID of bot to save
            
        Returns:
            True if saved successfully
        """
        bot = self._bots.get(bot_id)
        if not bot:
            return False
        
        try:
            stats = {
                'trades_today': bot.stats.trades_today,
                'daily_pnl': bot.stats.daily_pnl,
                'total_pnl': getattr(bot.stats, 'total_pnl', 0.0),
            }
            
            return self._saved_bots_manager.save_single_bot(
                bot_id=bot.id,
                config=bot.config.to_dict(),
                is_running=bot.is_running,
                stats=stats,
            )
        except Exception as e:
            logger.error(f"Error saving single bot {bot_id}: {e}")
            return False
    
    def load_saved_bots(self, auto_start: bool = True) -> int:
        """
        Load saved bot configurations from disk and recreate bots.
        
        Args:
            auto_start: If True, start bots that were running when saved
            
        Returns:
            Number of bots loaded
        """
        try:
            saved_states = self._saved_bots_manager.load_bots()
            
            if not saved_states:
                logger.info("No saved bots found")
                return 0
            
            loaded_count = 0
            auto_started = 0
            
            for saved_state in saved_states:
                try:
                    # Reconstruct BotConfig from saved dict
                    config = BotConfig.from_dict(saved_state.config)
                    
                    # Create the bot with the saved ID
                    bot = self.create_bot(config, saved_state.bot_id)
                    
                    if bot:
                        loaded_count += 1
                        
                        # Auto-start if was running and auto_start enabled
                        if auto_start and saved_state.auto_start:
                            if bot.start():
                                auto_started += 1
                                logger.info(f"Auto-started saved bot: {bot.config.name}")
                    
                except Exception as e:
                    logger.error(f"Error loading bot {saved_state.bot_id}: {e}")
            
            logger.info(f"Loaded {loaded_count} saved bots ({auto_started} auto-started)")
            return loaded_count
            
        except Exception as e:
            logger.error(f"Error loading saved bots: {e}")
            return 0
    
    def has_saved_bots(self) -> bool:
        """Check if there are saved bots to load."""
        return self._saved_bots_manager.has_saved_bots()
    
    def save_position_tracking(self) -> bool:
        """Save position tracking data to disk."""
        try:
            positions = self.get_all_position_tracking()
            return self._saved_bots_manager.save_position_tracking(positions)
        except Exception as e:
            logger.error(f"Error saving position tracking: {e}")
            return False
    
    def load_position_tracking(self) -> int:
        """
        Load position tracking data from disk.
        
        Returns:
            Number of positions loaded
        """
        try:
            saved_positions = self._saved_bots_manager.load_position_tracking()
            
            if not saved_positions:
                return 0
            
            with self._position_lock:
                for key, tracking in saved_positions.items():
                    # Parse key "SYMBOL@BROKER"
                    parts = key.split('@')
                    if len(parts) == 2:
                        symbol, broker = parts
                        self._position_tracking[(symbol.upper(), broker.upper())] = {
                            'bot_id': tracking.bot_id,
                            'bot_name': tracking.bot_name,
                            'opened_at': tracking.opened_at,
                            'quantity': tracking.quantity,
                            'synced': tracking.synced,
                        }
            
            logger.info(f"Loaded {len(saved_positions)} position tracking entries")
            return len(saved_positions)
            
        except Exception as e:
            logger.error(f"Error loading position tracking: {e}")
            return 0
    
    def _auto_save(self) -> None:
        """Trigger auto-save if enabled."""
        if self._auto_save_enabled:
            # Don't save too frequently (min 5 seconds between saves)
            if self._last_save_time:
                elapsed = (datetime.now() - self._last_save_time).total_seconds()
                if elapsed < 5:
                    return
            
            self.save_all_bots()
            self.save_position_tracking()
    
    def set_auto_save(self, enabled: bool) -> None:
        """Enable or disable auto-save."""
        self._auto_save_enabled = enabled
        logger.info(f"Bot auto-save {'enabled' if enabled else 'disabled'}")
    
    def get_persistence_status(self) -> dict:
        """Get status of persistence system."""
        return {
            'auto_save_enabled': self._auto_save_enabled,
            'last_save_time': self._last_save_time.isoformat() if self._last_save_time else None,
            'has_saved_bots': self.has_saved_bots(),
            'saved_bots_info': self._saved_bots_manager.to_dict(),
        }
    
    def clear_saved_data(self) -> bool:
        """Clear all saved bot data (use with caution)."""
        return self._saved_bots_manager.clear_all()


# Global bot manager instance
_bot_manager: Optional[BotManager] = None
_initialized: bool = False


def _create_default_bots(manager: BotManager) -> None:
    """Create default bot configurations with strategy-appropriate thresholds."""
    
    # Get presets for different trading styles
    aggressive = SignalPreset.AGGRESSIVE
    moderate = SignalPreset.MODERATE
    conservative = SignalPreset.CONSERVATIVE
    income = SignalPreset.INCOME
    news_driven = SignalPreset.NEWS_DRIVEN
    ultra_aggressive = SignalPreset.ULTRA_AGGRESSIVE
    crypto_preset = SignalPreset.CRYPTO
    commodity_preset = SignalPreset.COMMODITY
    
    default_bots = [
        # =====================================================================
        # STOCK TRADING BOTS (1-10) - Each with strategy-specific thresholds
        # =====================================================================
        BotConfig(
            name="Tech Momentum",
            description="Momentum trading on tech stocks",
            symbols=["NVDA", "AMD", "TSLA", "META", "GOOGL"],
            strategies=["Technical", "Momentum"],
            max_position_size=25000,
            max_positions=5,
            # AGGRESSIVE thresholds - momentum needs confirmation
            buy_signal_threshold=aggressive["buy_signal_threshold"],
            strong_buy_threshold=aggressive["strong_buy_threshold"],
            sell_signal_threshold=aggressive["sell_signal_threshold"],
            strong_sell_threshold=aggressive["strong_sell_threshold"],
            trade_frequency_seconds=aggressive["trade_frequency_seconds"],
        ),
        BotConfig(
            name="ETF Swing Trader",
            description="Swing trading on major ETFs",
            symbols=["SPY", "QQQ", "IWM", "DIA"],
            strategies=["Technical", "MeanReversion"],
            max_position_size=30000,
            max_positions=4,
            # MODERATE thresholds - ETFs are less volatile
            buy_signal_threshold=moderate["buy_signal_threshold"],
            strong_buy_threshold=moderate["strong_buy_threshold"],
            sell_signal_threshold=moderate["sell_signal_threshold"],
            strong_sell_threshold=moderate["strong_sell_threshold"],
            trade_frequency_seconds=moderate["trade_frequency_seconds"],
        ),
        BotConfig(
            name="News Sentiment Bot",
            description="React to breaking news",
            symbols=["AAPL", "MSFT", "AMZN", "NVDA"],
            strategies=["NewsSentiment", "Momentum"],
            max_position_size=20000,
            max_positions=4,
            enable_news_trading=True,
            # NEWS-DRIVEN thresholds - quick reaction to news
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=news_driven["trade_frequency_seconds"],
        ),
        BotConfig(
            name="Mean Reversion",
            description="Fade extreme moves",
            symbols=["SPY", "QQQ", "XLF", "XLE"],
            strategies=["MeanReversion"],
            max_position_size=15000,
            max_positions=4,
            # MODERATE thresholds - wait for mean reversion setup
            buy_signal_threshold=moderate["buy_signal_threshold"],
            strong_buy_threshold=moderate["strong_buy_threshold"],
            sell_signal_threshold=moderate["sell_signal_threshold"],
            strong_sell_threshold=moderate["strong_sell_threshold"],
            trade_frequency_seconds=moderate["trade_frequency_seconds"],
        ),
        BotConfig(
            name="International ADR",
            description="Trade international stocks",
            symbols=["BABA", "TSM", "NVO", "ASML"],
            strategies=["Technical", "NewsSentiment"],
            max_position_size=20000,
            max_positions=4,
            # NEWS-DRIVEN - ADRs are news sensitive (geopolitics)
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=60,
        ),
        BotConfig(
            name="High Volatility",
            description="Trade high volatility momentum plays",
            symbols=["COIN", "MSTR", "RIVN", "LCID"],
            strategies=["Momentum", "Technical"],
            max_position_size=15000,
            max_positions=3,
            # AGGRESSIVE - volatile stocks need more confirmation
            buy_signal_threshold=aggressive["buy_signal_threshold"],
            strong_buy_threshold=aggressive["strong_buy_threshold"],
            sell_signal_threshold=aggressive["sell_signal_threshold"],
            strong_sell_threshold=aggressive["strong_sell_threshold"],
            trade_frequency_seconds=30,
        ),
        BotConfig(
            name="Dividend Growth",
            description="Swing trade dividend aristocrats",
            symbols=["JNJ", "PG", "KO", "PEP", "MMM"],
            strategies=["MeanReversion", "Technical"],
            max_position_size=25000,
            max_positions=5,
            # INCOME thresholds - conservative, stable positions
            buy_signal_threshold=income["buy_signal_threshold"],
            strong_buy_threshold=income["strong_buy_threshold"],
            sell_signal_threshold=income["sell_signal_threshold"],
            strong_sell_threshold=income["strong_sell_threshold"],
            trade_frequency_seconds=income["trade_frequency_seconds"],
        ),
        BotConfig(
            name="Semiconductor Focus",
            description="Semiconductor sector specialist",
            symbols=["NVDA", "AMD", "INTC", "MU", "AVGO", "QCOM"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            max_position_size=30000,
            max_positions=6,
            enable_news_trading=True,
            # NEWS-DRIVEN - semis are news sensitive (earnings, guidance)
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=45,
        ),
        BotConfig(
            name="Energy Sector",
            description="Trade energy and commodities",
            symbols=["XOM", "CVX", "OXY", "SLB", "USO"],
            strategies=["Technical", "MeanReversion"],
            max_position_size=20000,
            max_positions=4,
            # COMMODITY thresholds - macro sensitive
            buy_signal_threshold=commodity_preset["buy_signal_threshold"],
            strong_buy_threshold=commodity_preset["strong_buy_threshold"],
            sell_signal_threshold=commodity_preset["sell_signal_threshold"],
            strong_sell_threshold=commodity_preset["strong_sell_threshold"],
            trade_frequency_seconds=commodity_preset["trade_frequency_seconds"],
        ),
        BotConfig(
            name="Biotech Catalyst",
            description="Biotech news and catalyst plays",
            symbols=["MRNA", "BNTX", "REGN", "VRTX", "GILD"],
            strategies=["NewsSentiment", "Momentum"],
            max_position_size=15000,
            max_positions=4,
            enable_news_trading=True,
            # NEWS-DRIVEN - catalyst dependent
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=30,
        ),
        # =====================================================================
        # OPTIONS TRADING BOTS - High Growth, Short Term (AGGRESSIVE thresholds)
        # =====================================================================
        BotConfig(
            name="🚀 SPY Calls Momentum",
            description="Aggressive SPY call options on momentum breakouts",
            instrument_type=InstrumentType.OPTIONS,
            symbols=["SPY"],
            strategies=["Momentum", "Technical"],
            options_type="call",
            options_dte_min=5,
            options_dte_max=21,
            options_delta_min=0.30,
            options_delta_max=0.50,
            options_max_contracts=20,
            options_profit_target_pct=75.0,
            options_stop_loss_pct=40.0,
            max_position_size=10000,
            max_positions=5,
            enable_momentum_bursts=True,
            leverage_multiplier=2.0,
            # AGGRESSIVE for options momentum
            buy_signal_threshold=aggressive["buy_signal_threshold"],
            strong_buy_threshold=aggressive["strong_buy_threshold"],
            sell_signal_threshold=aggressive["sell_signal_threshold"],
            strong_sell_threshold=aggressive["strong_sell_threshold"],
            trade_frequency_seconds=30,
        ),
        BotConfig(
            name="🔥 QQQ Tech Calls",
            description="QQQ call options for tech momentum plays",
            instrument_type=InstrumentType.OPTIONS,
            symbols=["QQQ"],
            strategies=["Momentum", "Technical", "NewsSentiment"],
            options_type="call",
            options_dte_min=7,
            options_dte_max=30,
            options_delta_min=0.35,
            options_delta_max=0.55,
            options_max_contracts=15,
            options_profit_target_pct=100.0,
            options_stop_loss_pct=50.0,
            max_position_size=8000,
            max_positions=4,
            enable_news_trading=True,
            enable_momentum_bursts=True,
            # NEWS-DRIVEN for QQQ
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=30,
        ),
        BotConfig(
            name="⚡ 0DTE Scalper",
            description="Same-day expiration options scalping",
            instrument_type=InstrumentType.OPTIONS,
            symbols=["SPY", "QQQ"],
            strategies=["Momentum", "Technical"],
            options_type="both",
            options_dte_min=0,
            options_dte_max=1,
            options_delta_min=0.40,
            options_delta_max=0.60,
            options_max_contracts=10,
            options_profit_target_pct=25.0,
            options_stop_loss_pct=15.0,
            max_position_size=5000,
            max_positions=3,
            enable_scalping=True,
            leverage_multiplier=3.0,
            # ULTRA-AGGRESSIVE for 0DTE scalping
            buy_signal_threshold=ultra_aggressive["buy_signal_threshold"],
            strong_buy_threshold=ultra_aggressive["strong_buy_threshold"],
            sell_signal_threshold=ultra_aggressive["sell_signal_threshold"],
            strong_sell_threshold=ultra_aggressive["strong_sell_threshold"],
            trade_frequency_seconds=15,
        ),
        BotConfig(
            name="💰 NVDA Earnings Plays",
            description="NVDA options around earnings and news",
            instrument_type=InstrumentType.OPTIONS,
            symbols=["NVDA"],
            strategies=["NewsSentiment", "Momentum"],
            options_type="call",
            options_dte_min=14,
            options_dte_max=45,
            options_delta_min=0.25,
            options_delta_max=0.45,
            options_max_contracts=10,
            options_profit_target_pct=150.0,
            options_stop_loss_pct=60.0,
            max_position_size=10000,
            max_positions=3,
            enable_news_trading=True,
            # NEWS-DRIVEN for earnings plays
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=45,
        ),
        BotConfig(
            name="🎯 Multi-Stock Calls",
            description="Call options on high-momentum mega caps",
            instrument_type=InstrumentType.OPTIONS,
            symbols=["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA"],
            strategies=["Technical", "Momentum"],
            options_type="call",
            options_dte_min=14,
            options_dte_max=45,
            options_delta_min=0.30,
            options_delta_max=0.50,
            options_max_contracts=10,
            options_profit_target_pct=80.0,
            options_stop_loss_pct=40.0,
            max_position_size=15000,
            max_positions=6,
            # AGGRESSIVE for multi-stock options
            buy_signal_threshold=aggressive["buy_signal_threshold"],
            strong_buy_threshold=aggressive["strong_buy_threshold"],
            sell_signal_threshold=aggressive["sell_signal_threshold"],
            strong_sell_threshold=aggressive["strong_sell_threshold"],
            trade_frequency_seconds=60,
        ),
        # =====================================================================
        # FUTURES TRADING BOTS - High Leverage, Fast Profits (ULTRA-AGGRESSIVE)
        # =====================================================================
        BotConfig(
            name="📈 ES Futures Scalper",
            description="E-mini S&P 500 futures scalping",
            instrument_type=InstrumentType.FUTURES,
            symbols=["ES"],
            futures_contracts=["ES"],
            strategies=["Technical", "Momentum"],
            futures_max_contracts=5,
            futures_use_micro=False,
            futures_session="rth",
            max_position_size=50000,
            max_positions=2,
            enable_scalping=True,
            scalp_profit_ticks=8,
            scalp_stop_ticks=4,
            leverage_multiplier=5.0,
            # ULTRA-AGGRESSIVE for futures scalping
            buy_signal_threshold=ultra_aggressive["buy_signal_threshold"],
            strong_buy_threshold=ultra_aggressive["strong_buy_threshold"],
            sell_signal_threshold=ultra_aggressive["sell_signal_threshold"],
            strong_sell_threshold=ultra_aggressive["strong_sell_threshold"],
            trade_frequency_seconds=10,
        ),
        BotConfig(
            name="🌙 NQ Micro Futures",
            description="Micro Nasdaq futures overnight trades",
            instrument_type=InstrumentType.FUTURES,
            symbols=["MNQ"],
            futures_contracts=["MNQ"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            futures_max_contracts=10,
            futures_use_micro=True,
            futures_session="eth",
            max_position_size=20000,
            max_positions=3,
            enable_news_trading=True,
            enable_momentum_bursts=True,
            # AGGRESSIVE for overnight micro futures
            buy_signal_threshold=aggressive["buy_signal_threshold"],
            strong_buy_threshold=aggressive["strong_buy_threshold"],
            sell_signal_threshold=aggressive["sell_signal_threshold"],
            strong_sell_threshold=aggressive["strong_sell_threshold"],
            trade_frequency_seconds=30,
        ),
        BotConfig(
            name="🛢️ Crude Oil Futures",
            description="CL crude oil futures momentum trading",
            instrument_type=InstrumentType.FUTURES,
            symbols=["CL"],
            futures_contracts=["CL"],
            strategies=["Technical", "NewsSentiment"],
            futures_max_contracts=3,
            futures_use_micro=False,
            max_position_size=30000,
            max_positions=2,
            enable_news_trading=True,
            # COMMODITY for oil futures
            buy_signal_threshold=commodity_preset["buy_signal_threshold"],
            strong_buy_threshold=commodity_preset["strong_buy_threshold"],
            sell_signal_threshold=commodity_preset["sell_signal_threshold"],
            strong_sell_threshold=commodity_preset["strong_sell_threshold"],
            trade_frequency_seconds=60,
        ),
        BotConfig(
            name="⚡ MES Momentum",
            description="Micro E-mini S&P momentum trades",
            instrument_type=InstrumentType.FUTURES,
            symbols=["MES"],
            futures_contracts=["MES"],
            strategies=["Momentum", "Technical"],
            futures_max_contracts=20,
            futures_use_micro=True,
            max_position_size=15000,
            max_positions=5,
            enable_momentum_bursts=True,
            leverage_multiplier=3.0,
            # AGGRESSIVE for momentum futures
            buy_signal_threshold=aggressive["buy_signal_threshold"],
            strong_buy_threshold=aggressive["strong_buy_threshold"],
            sell_signal_threshold=aggressive["sell_signal_threshold"],
            strong_sell_threshold=aggressive["strong_sell_threshold"],
            trade_frequency_seconds=20,
        ),
        # =====================================================================
        # LEVERAGED ETF SWING TRADING BOTS (AGGRESSIVE)
        # =====================================================================
        BotConfig(
            name="🔄 TQQQ/SQQQ Swing Trader",
            description="3x Leveraged Nasdaq swing trading - TQQQ for bullish, SQQQ for bearish",
            instrument_type=InstrumentType.STOCK,
            symbols=["TQQQ", "SQQQ"],
            strategies=["Technical", "Momentum", "MeanReversion"],
            strategy_weights={
                "Technical": 0.7,
                "Momentum": 0.6,
                "MeanReversion": 0.5,
            },
            max_position_size=50000,
            max_positions=2,
            max_daily_loss_pct=5.0,
            enable_news_trading=True,
            news_sentiment_threshold=0.6,
            enable_momentum_bursts=True,
            leverage_multiplier=1.0,
            # AGGRESSIVE for leveraged ETFs
            buy_signal_threshold=aggressive["buy_signal_threshold"],
            strong_buy_threshold=aggressive["strong_buy_threshold"],
            sell_signal_threshold=aggressive["sell_signal_threshold"],
            strong_sell_threshold=aggressive["strong_sell_threshold"],
            trade_frequency_seconds=120,
        ),
        BotConfig(
            name="🔥 SOXL Semiconductor Swing",
            description="3x Leveraged Semiconductor swing trading",
            instrument_type=InstrumentType.STOCK,
            symbols=["SOXL", "SOXS"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.7,
                "Momentum": 0.6,
                "NewsSentiment": 0.5,
            },
            max_position_size=40000,
            max_positions=2,
            max_daily_loss_pct=5.0,
            enable_news_trading=True,
            news_sentiment_threshold=0.55,
            enable_momentum_bursts=True,
            # NEWS-DRIVEN for semiconductor leveraged
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=120,
        ),
        # =====================================================================
        # COMMODITY & RESOURCE TRADING BOTS (COMMODITY thresholds)
        # =====================================================================
        BotConfig(
            name="🥇 Gold & Precious Metals",
            description="Trade gold, silver, platinum via ETFs and miners",
            instrument_type=InstrumentType.COMMODITY,
            symbols=["GLD", "SLV", "PPLT", "GDX", "NEM", "GOLD"],
            strategies=["Technical", "MeanReversion", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.7,
                "MeanReversion": 0.6,
                "NewsSentiment": 0.5,
            },
            commodity_type="precious_metals",
            commodity_trade_etfs=True,
            commodity_trade_miners=True,
            commodity_macro_alerts=True,
            commodity_geopolitical_alerts=True,
            max_position_size=30000,
            max_positions=6,
            enable_news_trading=True,
            # COMMODITY thresholds
            buy_signal_threshold=commodity_preset["buy_signal_threshold"],
            strong_buy_threshold=commodity_preset["strong_buy_threshold"],
            sell_signal_threshold=commodity_preset["sell_signal_threshold"],
            strong_sell_threshold=commodity_preset["strong_sell_threshold"],
            trade_frequency_seconds=180,
        ),
        BotConfig(
            name="🛢️ Oil & Natural Gas",
            description="Trade crude oil and natural gas via ETFs and energy stocks",
            instrument_type=InstrumentType.COMMODITY,
            symbols=["USO", "UNG", "XOM", "CVX", "OXY", "COP", "SLB"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.7,
                "Momentum": 0.6,
                "NewsSentiment": 0.7,
            },
            commodity_type="energy",
            commodity_trade_etfs=True,
            commodity_trade_miners=False,
            commodity_macro_alerts=True,
            commodity_geopolitical_alerts=True,
            max_position_size=35000,
            max_positions=7,
            enable_news_trading=True,
            news_sentiment_threshold=0.4,
            # NEWS-DRIVEN for oil (very news sensitive)
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=60,
        ),
        BotConfig(
            name="⚡ Uranium & Nuclear Energy",
            description="Trade uranium miners and nuclear energy plays",
            instrument_type=InstrumentType.COMMODITY,
            symbols=["URA", "CCJ", "UEC", "UUUU", "DNN", "NNE"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.6,
                "Momentum": 0.7,
                "NewsSentiment": 0.6,
            },
            commodity_type="uranium",
            commodity_trade_etfs=True,
            commodity_trade_miners=True,
            commodity_geopolitical_alerts=True,
            max_position_size=25000,
            max_positions=5,
            enable_news_trading=True,
            # NEWS-DRIVEN for uranium (policy sensitive)
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=120,
        ),
        BotConfig(
            name="🔋 Lithium & Battery Metals",
            description="Trade lithium and battery metal miners",
            instrument_type=InstrumentType.COMMODITY,
            symbols=["LIT", "ALB", "SQM", "LAC", "LTHM", "MP"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.6,
                "Momentum": 0.7,
                "NewsSentiment": 0.5,
            },
            commodity_type="lithium",
            commodity_trade_etfs=True,
            commodity_trade_miners=True,
            max_position_size=25000,
            max_positions=5,
            enable_news_trading=True,
            # COMMODITY thresholds
            buy_signal_threshold=commodity_preset["buy_signal_threshold"],
            strong_buy_threshold=commodity_preset["strong_buy_threshold"],
            sell_signal_threshold=commodity_preset["sell_signal_threshold"],
            strong_sell_threshold=commodity_preset["strong_sell_threshold"],
            trade_frequency_seconds=180,
        ),
        BotConfig(
            name="🏭 Industrial Metals",
            description="Trade copper, aluminum, steel - infrastructure plays",
            instrument_type=InstrumentType.COMMODITY,
            symbols=["CPER", "FCX", "SCCO", "AA", "NUE", "STLD", "X"],
            strategies=["Technical", "MeanReversion", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.6,
                "MeanReversion": 0.5,
                "NewsSentiment": 0.5,
            },
            commodity_type="industrial_metals",
            commodity_trade_etfs=True,
            commodity_trade_miners=True,
            commodity_macro_alerts=True,
            max_position_size=30000,
            max_positions=6,
            enable_news_trading=True,
            # COMMODITY thresholds
            buy_signal_threshold=commodity_preset["buy_signal_threshold"],
            strong_buy_threshold=commodity_preset["strong_buy_threshold"],
            sell_signal_threshold=commodity_preset["sell_signal_threshold"],
            strong_sell_threshold=commodity_preset["strong_sell_threshold"],
            trade_frequency_seconds=180,
        ),
        BotConfig(
            name="🌾 Agriculture & Soft Commodities",
            description="Trade corn, wheat, soybeans via ETFs",
            instrument_type=InstrumentType.COMMODITY,
            symbols=["CORN", "WEAT", "SOYB", "DBA", "ADM", "BG", "DE"],
            strategies=["Technical", "MeanReversion", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.6,
                "MeanReversion": 0.6,
                "NewsSentiment": 0.5,
            },
            commodity_type="agriculture",
            commodity_trade_etfs=True,
            commodity_seasonal_trading=True,
            commodity_geopolitical_alerts=True,
            max_position_size=20000,
            max_positions=6,
            # CONSERVATIVE for agriculture (seasonal, less volatile)
            buy_signal_threshold=conservative["buy_signal_threshold"],
            strong_buy_threshold=conservative["strong_buy_threshold"],
            sell_signal_threshold=conservative["sell_signal_threshold"],
            strong_sell_threshold=conservative["strong_sell_threshold"],
            trade_frequency_seconds=300,
        ),
        BotConfig(
            name="💎 Diversified Commodities",
            description="Broad commodity exposure across all sectors",
            instrument_type=InstrumentType.COMMODITY,
            symbols=["DBC", "GSG", "PDBC", "COM"],
            strategies=["Technical", "MeanReversion"],
            strategy_weights={
                "Technical": 0.7,
                "MeanReversion": 0.5,
            },
            commodity_type="broad",
            commodity_trade_etfs=True,
            commodity_macro_alerts=True,
            max_position_size=40000,
            max_positions=4,
            # MODERATE for diversified
            buy_signal_threshold=moderate["buy_signal_threshold"],
            strong_buy_threshold=moderate["strong_buy_threshold"],
            sell_signal_threshold=moderate["sell_signal_threshold"],
            strong_sell_threshold=moderate["strong_sell_threshold"],
            trade_frequency_seconds=600,
        ),
        BotConfig(
            name="🔩 Rare Earth & Strategic Metals",
            description="Trade rare earth elements and strategic metals",
            instrument_type=InstrumentType.COMMODITY,
            symbols=["REMX", "MP", "LYSCF", "VALE", "BHP"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.6,
                "Momentum": 0.6,
                "NewsSentiment": 0.7,
            },
            commodity_type="rare_earth",
            commodity_trade_etfs=True,
            commodity_trade_miners=True,
            commodity_geopolitical_alerts=True,
            max_position_size=20000,
            max_positions=5,
            enable_news_trading=True,
            news_sentiment_threshold=0.4,
            # NEWS-DRIVEN for rare earth (very geopolitical)
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=120,
        ),
        # =====================================================================
        # CRYPTOCURRENCY TRADING BOTS (CRYPTO thresholds)
        # =====================================================================
        BotConfig(
            name="₿ Bitcoin & Ethereum Core",
            description="Major crypto assets - BTC & ETH spot and ETFs",
            instrument_type=InstrumentType.CRYPTO,
            symbols=["BTC-USD", "ETH-USD", "IBIT", "FBTC", "ETHE"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.7,
                "Momentum": 0.6,
                "NewsSentiment": 0.7,
            },
            crypto_category="major",
            crypto_exchange="coinbase",
            crypto_trade_spot=True,
            crypto_trade_etfs=True,
            crypto_dca_enabled=True,
            crypto_whale_alerts=True,
            crypto_on_chain_analysis=True,
            max_position_size=50000,
            max_positions=5,
            enable_news_trading=True,
            # CRYPTO thresholds
            buy_signal_threshold=crypto_preset["buy_signal_threshold"],
            strong_buy_threshold=crypto_preset["strong_buy_threshold"],
            sell_signal_threshold=crypto_preset["sell_signal_threshold"],
            strong_sell_threshold=crypto_preset["strong_sell_threshold"],
            trade_frequency_seconds=30,
        ),
        BotConfig(
            name="🌐 Altcoin Momentum",
            description="High-momentum altcoin trading - SOL, AVAX, DOT, ADA",
            instrument_type=InstrumentType.CRYPTO,
            symbols=["SOL-USD", "AVAX-USD", "DOT-USD", "ADA-USD", "MATIC-USD"],
            strategies=["Momentum", "Technical", "NewsSentiment"],
            strategy_weights={
                "Momentum": 0.8,
                "Technical": 0.6,
                "NewsSentiment": 0.5,
            },
            crypto_category="major",
            crypto_exchange="coinbase",
            crypto_trade_spot=True,
            crypto_trailing_stop_pct=8.0,
            crypto_take_profit_pct=25.0,
            max_position_size=25000,
            max_positions=5,
            enable_momentum_bursts=True,
            # AGGRESSIVE for altcoin momentum
            buy_signal_threshold=aggressive["buy_signal_threshold"],
            strong_buy_threshold=aggressive["strong_buy_threshold"],
            sell_signal_threshold=aggressive["sell_signal_threshold"],
            strong_sell_threshold=aggressive["strong_sell_threshold"],
            trade_frequency_seconds=30,
        ),
        BotConfig(
            name="🔗 DeFi Protocol Tokens",
            description="Decentralized finance tokens - UNI, AAVE, LINK, MKR",
            instrument_type=InstrumentType.CRYPTO,
            symbols=["UNI-USD", "AAVE-USD", "LINK-USD", "MKR-USD", "COMP-USD"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.6,
                "Momentum": 0.7,
                "NewsSentiment": 0.6,
            },
            crypto_category="defi",
            crypto_exchange="coinbase",
            crypto_trade_spot=True,
            crypto_on_chain_analysis=True,
            max_position_size=20000,
            max_positions=5,
            enable_news_trading=True,
            # CRYPTO thresholds
            buy_signal_threshold=crypto_preset["buy_signal_threshold"],
            strong_buy_threshold=crypto_preset["strong_buy_threshold"],
            sell_signal_threshold=crypto_preset["sell_signal_threshold"],
            strong_sell_threshold=crypto_preset["strong_sell_threshold"],
            trade_frequency_seconds=45,
        ),
        BotConfig(
            name="🤖 AI & Compute Tokens",
            description="AI-focused crypto - RNDR, FET, OCEAN, AKT",
            instrument_type=InstrumentType.CRYPTO,
            symbols=["RNDR-USD", "FET-USD", "OCEAN-USD", "AKT-USD"],
            strategies=["Momentum", "NewsSentiment", "Technical"],
            strategy_weights={
                "Momentum": 0.8,
                "NewsSentiment": 0.7,
                "Technical": 0.5,
            },
            crypto_category="ai",
            crypto_exchange="coinbase",
            crypto_trade_spot=True,
            crypto_trailing_stop_pct=10.0,
            crypto_take_profit_pct=30.0,
            max_position_size=15000,
            max_positions=4,
            enable_news_trading=True,
            news_sentiment_threshold=0.4,
            # NEWS-DRIVEN for AI tokens (hype driven)
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=30,
        ),
        BotConfig(
            name="🐕 Meme Coin Scalper",
            description="High-risk meme coins - DOGE, SHIB, PEPE (small positions)",
            instrument_type=InstrumentType.CRYPTO,
            symbols=["DOGE-USD", "SHIB-USD", "PEPE-USD"],
            strategies=["Momentum", "NewsSentiment"],
            strategy_weights={
                "Momentum": 0.9,
                "NewsSentiment": 0.8,
            },
            crypto_category="meme",
            crypto_exchange="coinbase",
            crypto_trade_spot=True,
            crypto_trailing_stop_pct=15.0,
            crypto_take_profit_pct=50.0,
            max_position_size=5000,
            max_positions=3,
            max_daily_loss_pct=10.0,
            enable_scalping=True,
            enable_momentum_bursts=True,
            # ULTRA-AGGRESSIVE for meme coins
            buy_signal_threshold=ultra_aggressive["buy_signal_threshold"],
            strong_buy_threshold=ultra_aggressive["strong_buy_threshold"],
            sell_signal_threshold=ultra_aggressive["sell_signal_threshold"],
            strong_sell_threshold=ultra_aggressive["strong_sell_threshold"],
            trade_frequency_seconds=15,
        ),
        BotConfig(
            name="🏛️ Crypto ETF Portfolio",
            description="Crypto exposure via ETFs - IBIT, FBTC, GBTC, COIN, MARA",
            instrument_type=InstrumentType.CRYPTO,
            symbols=["IBIT", "FBTC", "GBTC", "COIN", "MARA", "RIOT", "MSTR"],
            strategies=["Technical", "Momentum", "MeanReversion"],
            strategy_weights={
                "Technical": 0.7,
                "Momentum": 0.6,
                "MeanReversion": 0.5,
            },
            crypto_category="major",
            crypto_trade_spot=False,
            crypto_trade_etfs=True,
            max_position_size=35000,
            max_positions=7,
            # MODERATE for ETFs (less volatile than spot)
            buy_signal_threshold=moderate["buy_signal_threshold"],
            strong_buy_threshold=moderate["strong_buy_threshold"],
            sell_signal_threshold=moderate["sell_signal_threshold"],
            strong_sell_threshold=moderate["strong_sell_threshold"],
            trade_frequency_seconds=180,
        ),
        BotConfig(
            name="🎮 Gaming & Metaverse",
            description="Gaming and metaverse tokens - IMX, GALA, SAND, AXS",
            instrument_type=InstrumentType.CRYPTO,
            symbols=["IMX-USD", "GALA-USD", "SAND-USD", "AXS-USD"],
            strategies=["Momentum", "Technical", "NewsSentiment"],
            strategy_weights={
                "Momentum": 0.7,
                "Technical": 0.6,
                "NewsSentiment": 0.6,
            },
            crypto_category="gaming",
            crypto_exchange="coinbase",
            crypto_trade_spot=True,
            max_position_size=15000,
            max_positions=4,
            enable_news_trading=True,
            # CRYPTO thresholds
            buy_signal_threshold=crypto_preset["buy_signal_threshold"],
            strong_buy_threshold=crypto_preset["strong_buy_threshold"],
            sell_signal_threshold=crypto_preset["sell_signal_threshold"],
            strong_sell_threshold=crypto_preset["strong_sell_threshold"],
            trade_frequency_seconds=45,
        ),
        BotConfig(
            name="⚡ Layer 2 Scalability",
            description="Layer 2 solutions - ARB, OP, MATIC",
            instrument_type=InstrumentType.CRYPTO,
            symbols=["ARB-USD", "OP-USD", "MATIC-USD"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.6,
                "Momentum": 0.7,
                "NewsSentiment": 0.6,
            },
            crypto_category="layer2",
            crypto_exchange="coinbase",
            crypto_trade_spot=True,
            crypto_on_chain_analysis=True,
            max_position_size=20000,
            max_positions=3,
            enable_news_trading=True,
            # CRYPTO thresholds
            buy_signal_threshold=crypto_preset["buy_signal_threshold"],
            strong_buy_threshold=crypto_preset["strong_buy_threshold"],
            sell_signal_threshold=crypto_preset["sell_signal_threshold"],
            strong_sell_threshold=crypto_preset["strong_sell_threshold"],
            trade_frequency_seconds=45,
        ),
        # =====================================================================
        # FOREX TRADING BOTS - Currency Pairs (MODERATE thresholds)
        # =====================================================================
        BotConfig(
            name="💱 Major Forex Pairs",
            description="Trade major currency pairs - EUR/USD, GBP/USD, USD/JPY",
            instrument_type=InstrumentType.FOREX,
            symbols=["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"],
            strategies=["Technical", "MeanReversion", "Momentum"],
            strategy_weights={
                "Technical": 0.7,
                "MeanReversion": 0.6,
                "Momentum": 0.5,
            },
            max_position_size=50000,
            max_positions=4,
            enable_news_trading=True,
            # MODERATE for major forex
            buy_signal_threshold=moderate["buy_signal_threshold"],
            strong_buy_threshold=moderate["strong_buy_threshold"],
            sell_signal_threshold=moderate["sell_signal_threshold"],
            strong_sell_threshold=moderate["strong_sell_threshold"],
            trade_frequency_seconds=60,
        ),
        BotConfig(
            name="🌏 Asia-Pacific FX",
            description="Trade Asian currency pairs - AUD/USD, NZD/USD, USD/SGD",
            instrument_type=InstrumentType.FOREX,
            symbols=["AUD/USD", "NZD/USD", "USD/SGD", "USD/HKD"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.6,
                "Momentum": 0.7,
                "NewsSentiment": 0.5,
            },
            max_position_size=30000,
            max_positions=4,
            enable_news_trading=True,
            # MODERATE for APAC forex
            buy_signal_threshold=moderate["buy_signal_threshold"],
            strong_buy_threshold=moderate["strong_buy_threshold"],
            sell_signal_threshold=moderate["sell_signal_threshold"],
            strong_sell_threshold=moderate["strong_sell_threshold"],
            trade_frequency_seconds=120,
        ),
        BotConfig(
            name="🇪🇺 Euro Crosses",
            description="Trade EUR cross pairs - EUR/GBP, EUR/JPY, EUR/CHF",
            instrument_type=InstrumentType.FOREX,
            symbols=["EUR/GBP", "EUR/JPY", "EUR/CHF", "EUR/AUD"],
            strategies=["Technical", "MeanReversion"],
            strategy_weights={
                "Technical": 0.7,
                "MeanReversion": 0.6,
            },
            max_position_size=35000,
            max_positions=4,
            # MODERATE for euro crosses
            buy_signal_threshold=moderate["buy_signal_threshold"],
            strong_buy_threshold=moderate["strong_buy_threshold"],
            sell_signal_threshold=moderate["sell_signal_threshold"],
            strong_sell_threshold=moderate["strong_sell_threshold"],
            trade_frequency_seconds=180,
        ),
        
        # =========================================================================
        # ETF SPECIALISTS (41-45) - Various thresholds based on strategy
        # =========================================================================
        
        # 41. Top S&P 500 ETFs
        BotConfig(
            name="🏆 Top S&P 500 ETFs",
            description="Core holdings - VOO, SPY, IVV tracking S&P 500",
            instrument_type=InstrumentType.STOCK,
            symbols=["VOO", "SPY", "IVV", "SPLG", "VTI"],
            strategies=["Technical", "TrendFollowing"],
            strategy_weights={
                "Technical": 0.6,
                "TrendFollowing": 0.7,
            },
            max_position_size=50000,
            max_positions=5,
            # CONSERVATIVE for core holdings
            buy_signal_threshold=conservative["buy_signal_threshold"],
            strong_buy_threshold=conservative["strong_buy_threshold"],
            sell_signal_threshold=conservative["sell_signal_threshold"],
            strong_sell_threshold=conservative["strong_sell_threshold"],
            trade_frequency_seconds=300,
        ),
        
        # 42. Inverse & Leveraged ETF Trader
        BotConfig(
            name="📉📈 Inverse/Leveraged ETFs",
            description="TQQQ, SQQQ, SPXU, UPRO - high volatility plays",
            instrument_type=InstrumentType.STOCK,
            symbols=["TQQQ", "SQQQ", "UPRO", "SPXU", "SOXL", "SOXS", "LABU", "LABD"],
            strategies=["Momentum", "Technical", "MeanReversion"],
            strategy_weights={
                "Momentum": 0.8,
                "Technical": 0.7,
                "MeanReversion": 0.5,
            },
            max_position_size=15000,
            max_positions=4,
            # AGGRESSIVE for leveraged ETFs
            buy_signal_threshold=aggressive["buy_signal_threshold"],
            strong_buy_threshold=aggressive["strong_buy_threshold"],
            sell_signal_threshold=aggressive["sell_signal_threshold"],
            strong_sell_threshold=aggressive["strong_sell_threshold"],
            trade_frequency_seconds=60,
        ),
        
        # 43. International Developed Markets
        BotConfig(
            name="🌍 International Developed Markets",
            description="EFA, VEA, IEFA - Europe, Japan, Australia",
            instrument_type=InstrumentType.STOCK,
            symbols=["EFA", "VEA", "IEFA", "VGK", "EWJ", "EWG", "EWU"],
            strategies=["TrendFollowing", "Technical"],
            strategy_weights={
                "TrendFollowing": 0.7,
                "Technical": 0.6,
            },
            max_position_size=30000,
            max_positions=5,
            # MODERATE for international developed
            buy_signal_threshold=moderate["buy_signal_threshold"],
            strong_buy_threshold=moderate["strong_buy_threshold"],
            sell_signal_threshold=moderate["sell_signal_threshold"],
            strong_sell_threshold=moderate["strong_sell_threshold"],
            trade_frequency_seconds=300,
        ),
        
        # 44. Emerging Markets ETFs
        BotConfig(
            name="🌏 Emerging Markets ETFs",
            description="EEM, VWO, IEMG - China, India, Brazil, etc.",
            instrument_type=InstrumentType.STOCK,
            symbols=["EEM", "VWO", "IEMG", "FXI", "INDA", "EWZ", "EWT"],
            strategies=["Momentum", "Technical", "NewsSentiment"],
            strategy_weights={
                "Momentum": 0.7,
                "Technical": 0.6,
                "NewsSentiment": 0.5,
            },
            max_position_size=25000,
            max_positions=5,
            # NEWS-DRIVEN for emerging markets (geopolitical risk)
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=120,
        ),
        
        # 45. Thematic Growth ETFs
        BotConfig(
            name="🚀 Thematic Growth ETFs",
            description="ARK Innovation, Clean Energy, Genomics, AI",
            instrument_type=InstrumentType.STOCK,
            symbols=["ARKK", "ARKG", "ARKF", "ARKW", "ICLN", "QCLN", "BOTZ", "ROBO"],
            strategies=["Momentum", "TrendFollowing", "NewsSentiment"],
            strategy_weights={
                "Momentum": 0.8,
                "TrendFollowing": 0.6,
                "NewsSentiment": 0.7,
            },
            max_position_size=20000,
            max_positions=6,
            # AGGRESSIVE for thematic growth
            buy_signal_threshold=aggressive["buy_signal_threshold"],
            strong_buy_threshold=aggressive["strong_buy_threshold"],
            sell_signal_threshold=aggressive["sell_signal_threshold"],
            strong_sell_threshold=aggressive["strong_sell_threshold"],
            trade_frequency_seconds=90,
        ),
        
        # =========================================================================
        # INTERNATIONAL SPECIALISTS (46-48)
        # =========================================================================
        
        # 46. ADR Blue Chips
        BotConfig(
            name="🏢 ADR Blue Chips",
            description="Top international companies trading on US exchanges",
            instrument_type=InstrumentType.STOCK,
            symbols=["TSM", "ASML", "NVO", "SAP", "TM", "UL", "SONY", "BHP"],
            strategies=["Technical", "TrendFollowing"],
            strategy_weights={
                "Technical": 0.7,
                "TrendFollowing": 0.6,
            },
            max_position_size=30000,
            max_positions=6,
            # MODERATE for blue chips
            buy_signal_threshold=moderate["buy_signal_threshold"],
            strong_buy_threshold=moderate["strong_buy_threshold"],
            sell_signal_threshold=moderate["sell_signal_threshold"],
            strong_sell_threshold=moderate["strong_sell_threshold"],
            trade_frequency_seconds=180,
        ),
        
        # 47. China Tech ADRs
        BotConfig(
            name="🇨🇳 China Tech ADRs",
            description="BABA, JD, PDD, BIDU - Chinese tech giants",
            instrument_type=InstrumentType.STOCK,
            symbols=["BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "TME"],
            strategies=["Momentum", "Technical", "NewsSentiment"],
            strategy_weights={
                "Momentum": 0.7,
                "Technical": 0.6,
                "NewsSentiment": 0.8,
            },
            max_position_size=20000,
            max_positions=5,
            # NEWS-DRIVEN for China ADRs (very news sensitive)
            buy_signal_threshold=news_driven["buy_signal_threshold"],
            strong_buy_threshold=news_driven["strong_buy_threshold"],
            sell_signal_threshold=news_driven["sell_signal_threshold"],
            strong_sell_threshold=news_driven["strong_sell_threshold"],
            trade_frequency_seconds=60,
        ),
        
        # 48. European Luxury & Consumer
        BotConfig(
            name="🇪🇺 European Luxury Brands",
            description="LVMH, Ferrari, Hermes - European luxury ADRs",
            instrument_type=InstrumentType.STOCK,
            symbols=["LVMUY", "RACE", "HESAY", "PPRUY", "CFRUY", "DEO", "BUD"],
            strategies=["TrendFollowing", "Technical"],
            strategy_weights={
                "TrendFollowing": 0.7,
                "Technical": 0.6,
            },
            max_position_size=25000,
            max_positions=5,
            # MODERATE for luxury brands
            buy_signal_threshold=moderate["buy_signal_threshold"],
            strong_buy_threshold=moderate["strong_buy_threshold"],
            sell_signal_threshold=moderate["sell_signal_threshold"],
            strong_sell_threshold=moderate["strong_sell_threshold"],
            trade_frequency_seconds=240,
        ),
        
        # =========================================================================
        # BOND & FIXED INCOME ETFs (49-50)
        # =========================================================================
        
        # 49. Bond ETF Rotator
        BotConfig(
            name="💵 Bond ETF Rotator",
            description="AGG, BND, TLT - Interest rate sensitive bond plays",
            instrument_type=InstrumentType.STOCK,
            symbols=["AGG", "BND", "TLT", "IEF", "SHY", "LQD", "HYG", "JNK"],
            strategies=["TrendFollowing", "MeanReversion"],
            strategy_weights={
                "TrendFollowing": 0.7,
                "MeanReversion": 0.6,
            },
            max_position_size=40000,
            max_positions=5,
            # INCOME thresholds for bonds
            buy_signal_threshold=income["buy_signal_threshold"],
            strong_buy_threshold=income["strong_buy_threshold"],
            sell_signal_threshold=income["sell_signal_threshold"],
            strong_sell_threshold=income["strong_sell_threshold"],
            trade_frequency_seconds=600,
        ),
        
        # 50. Volatility ETFs
        BotConfig(
            name="📊 Volatility ETF Trader",
            description="VXX, UVXY, SVXY - VIX-based volatility plays",
            instrument_type=InstrumentType.STOCK,
            symbols=["VXX", "UVXY", "SVXY", "VIXY", "VIXM"],
            strategies=["Momentum", "Technical", "MeanReversion"],
            strategy_weights={
                "Momentum": 0.8,
                "Technical": 0.7,
                "MeanReversion": 0.6,
            },
            max_position_size=10000,
            max_positions=3,
            # ULTRA-AGGRESSIVE for volatility ETFs (very sensitive)
            buy_signal_threshold=ultra_aggressive["buy_signal_threshold"],
            strong_buy_threshold=ultra_aggressive["strong_buy_threshold"],
            sell_signal_threshold=ultra_aggressive["sell_signal_threshold"],
            strong_sell_threshold=ultra_aggressive["strong_sell_threshold"],
            trade_frequency_seconds=30,
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
    
    # Initialize on first access
    if not _initialized and _bot_manager.bot_count == 0:
        _initialized = True
        
        # Try to load saved bots first
        if _bot_manager.has_saved_bots():
            logger.info("Loading saved bot configurations...")
            loaded = _bot_manager.load_saved_bots(auto_start=True)
            
            # Also load saved position tracking
            _bot_manager.load_position_tracking()
            
            if loaded > 0:
                logger.info(f"Restored {loaded} bots from saved state")
            else:
                # Fall back to defaults if loading failed
                logger.warning("Failed to load saved bots, creating defaults...")
                _create_default_bots(_bot_manager)
        else:
            # No saved bots, create defaults
            logger.info("No saved bots found, creating default bots...")
            _create_default_bots(_bot_manager)
    
    return _bot_manager


def reset_bot_manager() -> None:
    """
    Reset the global bot manager (useful for testing or full reset).
    
    WARNING: This will stop all bots and clear the manager.
    """
    global _bot_manager, _initialized
    
    if _bot_manager is not None:
        # Stop all bots
        _bot_manager.stop_all()
        
        # Save state before reset
        _bot_manager.save_all_bots()
    
    _bot_manager = None
    _initialized = False
    logger.info("Bot manager reset")

