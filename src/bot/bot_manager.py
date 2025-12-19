"""
Bot Manager for managing multiple trading bot instances.
"""

import threading
from datetime import datetime
from typing import Optional, Callable

from loguru import logger

from src.bot.bot_instance import BotInstance, BotConfig, BotStatus, InstrumentType
from src.bot.auto_optimizer import (
    get_auto_optimizer_manager,
    BotAutoOptimizer,
    OptimizationConfig,
    OptimizationMode,
)


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
        
        # Auto-optimizer integration
        self._optimizer_manager = get_auto_optimizer_manager()
        
        logger.info("Bot Manager initialized with auto-optimizer support")
    
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
            
            # Register trade callback for auto-optimizer
            bot.register_callback("on_trade", lambda b, trade: self._on_trade_completed(b, trade))
            
            self._bots[bot.id] = bot
            self._emit("on_bot_created", bot)
            
            # Register with auto-optimizer
            self._register_bot_optimizer(bot)
            
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
            
            # Unregister from auto-optimizer
            self._optimizer_manager.unregister_bot(bot_id)
            
            logger.info(f"Deleted bot {bot_id}")
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
        BotConfig(
            name="High Volatility",
            description="Trade high volatility momentum plays",
            symbols=["COIN", "MSTR", "RIVN", "LCID"],
            strategies=["Momentum", "Technical"],
            max_position_size=15000,
            max_positions=3,
        ),
        BotConfig(
            name="Dividend Growth",
            description="Swing trade dividend aristocrats",
            symbols=["JNJ", "PG", "KO", "PEP", "MMM"],
            strategies=["MeanReversion", "Technical"],
            max_position_size=25000,
            max_positions=5,
        ),
        BotConfig(
            name="Semiconductor Focus",
            description="Semiconductor sector specialist",
            symbols=["NVDA", "AMD", "INTC", "MU", "AVGO", "QCOM"],
            strategies=["Technical", "Momentum", "NewsSentiment"],
            max_position_size=30000,
            max_positions=6,
            enable_news_trading=True,
        ),
        BotConfig(
            name="Energy Sector",
            description="Trade energy and commodities",
            symbols=["XOM", "CVX", "OXY", "SLB", "USO"],
            strategies=["Technical", "MeanReversion"],
            max_position_size=20000,
            max_positions=4,
        ),
        BotConfig(
            name="Biotech Catalyst",
            description="Biotech news and catalyst plays",
            symbols=["MRNA", "BNTX", "REGN", "VRTX", "GILD"],
            strategies=["NewsSentiment", "Momentum"],
            max_position_size=15000,
            max_positions=4,
            enable_news_trading=True,
        ),
        # =====================================================================
        # OPTIONS TRADING BOTS - High Growth, Short Term
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
            trade_frequency_seconds=30,
            enable_momentum_bursts=True,
            leverage_multiplier=2.0,
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
            trade_frequency_seconds=15,
            enable_scalping=True,
            leverage_multiplier=3.0,
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
        ),
        # =====================================================================
        # FUTURES TRADING BOTS - High Leverage, Fast Profits
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
            trade_frequency_seconds=10,
            enable_scalping=True,
            scalp_profit_ticks=8,
            scalp_stop_ticks=4,
            leverage_multiplier=5.0,
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
            trade_frequency_seconds=30,
            enable_news_trading=True,
            enable_momentum_bursts=True,
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
            trade_frequency_seconds=20,
            enable_momentum_bursts=True,
            leverage_multiplier=3.0,
        ),
        # =====================================================================
        # LEVERAGED ETF SWING TRADING BOTS
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
            max_daily_loss_pct=5.0,  # Higher tolerance for leveraged ETFs
            trade_frequency_seconds=300,  # 5-minute checks for swing trades
            enable_news_trading=True,
            news_sentiment_threshold=0.6,
            enable_momentum_bursts=True,
            leverage_multiplier=1.0,  # Already 3x leveraged
        ),
        BotConfig(
            name="🔥 SOXL Semiconductor Swing",
            description="3x Leveraged Semiconductor swing trading",
            instrument_type=InstrumentType.STOCK,
            symbols=["SOXL", "SOXS"],  # Include inverse for bearish plays
            strategies=["Technical", "Momentum", "NewsSentiment"],
            strategy_weights={
                "Technical": 0.7,
                "Momentum": 0.6,
                "NewsSentiment": 0.5,
            },
            max_position_size=40000,
            max_positions=2,
            max_daily_loss_pct=5.0,
            trade_frequency_seconds=300,
            enable_news_trading=True,
            news_sentiment_threshold=0.55,
            enable_momentum_bursts=True,
        ),
        # =====================================================================
        # COMMODITY & RESOURCE TRADING BOTS
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
            commodity_macro_alerts=True,  # Fed, inflation, USD signals
            commodity_geopolitical_alerts=True,
            max_position_size=30000,
            max_positions=6,
            trade_frequency_seconds=300,
            enable_news_trading=True,
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
                "NewsSentiment": 0.7,  # Oil is news-sensitive
            },
            commodity_type="energy",
            commodity_trade_etfs=True,
            commodity_trade_miners=False,
            commodity_macro_alerts=True,
            commodity_geopolitical_alerts=True,  # OPEC, wars, sanctions
            max_position_size=35000,
            max_positions=7,
            trade_frequency_seconds=120,
            enable_news_trading=True,
            news_sentiment_threshold=0.4,  # More sensitive to news
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
            trade_frequency_seconds=300,
            enable_news_trading=True,
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
            commodity_macro_alerts=True,  # Infrastructure spending, China
            max_position_size=30000,
            max_positions=6,
            enable_news_trading=True,
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
            commodity_seasonal_trading=True,  # Planting/harvest seasons
            commodity_geopolitical_alerts=True,  # Weather, trade wars
            max_position_size=20000,
            max_positions=6,
            trade_frequency_seconds=600,  # Less frequent for agriculture
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
            trade_frequency_seconds=900,  # 15-min for broad exposure
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
                "NewsSentiment": 0.7,  # Very news-sensitive
            },
            commodity_type="rare_earth",
            commodity_trade_etfs=True,
            commodity_trade_miners=True,
            commodity_geopolitical_alerts=True,  # China supply, defense
            max_position_size=20000,
            max_positions=5,
            enable_news_trading=True,
            news_sentiment_threshold=0.4,
        ),
        # =====================================================================
        # CRYPTOCURRENCY TRADING BOTS
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
            trade_frequency_seconds=60,
            enable_news_trading=True,
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
            trade_frequency_seconds=30,
            enable_momentum_bursts=True,
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
            crypto_trailing_stop_pct=15.0,  # Wide stops for volatility
            crypto_take_profit_pct=50.0,  # Quick profits
            max_position_size=5000,  # Small positions
            max_positions=3,
            max_daily_loss_pct=10.0,  # Accept high risk
            trade_frequency_seconds=15,
            enable_scalping=True,
            enable_momentum_bursts=True,
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
            trade_frequency_seconds=300,
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
        ),
        # =====================================================================
        # FOREX TRADING BOTS - Currency Pairs
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
            trade_frequency_seconds=60,
            enable_news_trading=True,
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
            trade_frequency_seconds=120,
            enable_news_trading=True,
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
            trade_frequency_seconds=180,
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

