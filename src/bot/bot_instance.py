"""
Individual bot instance that runs in its own thread.
"""

import asyncio
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Callable, List
import uuid

import pandas as pd
from loguru import logger

# Global activity log for debugging (thread-safe circular buffer)
_bot_activity_log: deque = deque(maxlen=1000)
_activity_lock = threading.Lock()

# Shared market data cache to prevent yfinance thread exhaustion
# Each entry: {"data": DataFrame, "timestamp": datetime, "error": Optional[str]}
_market_data_cache: dict = {}
_market_data_lock = threading.Lock()
_market_data_cache_ttl = 60  # seconds - how long to cache market data
_yfinance_semaphore: Optional[asyncio.Semaphore] = None  # Limit concurrent yfinance calls


def get_bot_activity_log(bot_id: Optional[str] = None, limit: int = 100) -> list[dict]:
    """Get bot activity log entries, optionally filtered by bot_id."""
    with _activity_lock:
        entries = list(_bot_activity_log)
    if bot_id:
        entries = [e for e in entries if e.get("bot_id") == bot_id]
    return entries[-limit:]


def clear_bot_activity_log():
    """Clear the activity log."""
    with _activity_lock:
        _bot_activity_log.clear()


class BotStatus(str, Enum):
    """Bot status states."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class InstrumentType(str, Enum):
    """Types of tradeable instruments."""
    STOCK = "stock"
    OPTIONS = "options"
    FUTURES = "futures"
    CRYPTO = "crypto"
    COMMODITY = "commodity"  # Precious metals, energy, agriculture
    FOREX = "forex"  # Currency pairs


# Commodity symbols and their ETF proxies
COMMODITY_SYMBOLS = {
    # Precious Metals
    "gold": {"etf": "GLD", "futures": "GC", "miners": ["GDX", "GDXJ", "NEM", "GOLD", "AEM"]},
    "silver": {"etf": "SLV", "futures": "SI", "miners": ["SIL", "PAAS", "AG", "HL"]},
    "platinum": {"etf": "PPLT", "futures": "PL", "miners": ["SBSW", "IMPUY"]},
    "palladium": {"etf": "PALL", "futures": "PA", "related": ["SBSW"]},
    
    # Energy
    "oil": {"etf": "USO", "futures": "CL", "stocks": ["XOM", "CVX", "COP", "OXY", "SLB"]},
    "natural_gas": {"etf": "UNG", "futures": "NG", "stocks": ["EQT", "AR", "RRC", "SWN"]},
    "gasoline": {"etf": "UGA", "futures": "RB", "related": ["VLO", "MPC", "PSX"]},
    "heating_oil": {"futures": "HO", "related": ["VLO", "MPC"]},
    
    # Industrial Metals
    "copper": {"etf": "CPER", "futures": "HG", "miners": ["FCX", "SCCO", "TECK"]},
    "aluminum": {"futures": "ALI", "stocks": ["AA", "CENX"]},
    "nickel": {"futures": "NI", "stocks": ["VALE", "BHP"]},
    "zinc": {"futures": "ZN", "stocks": ["TECK", "VALE"]},
    "lithium": {"etf": "LIT", "stocks": ["ALB", "SQM", "LTHM", "LAC"]},
    "uranium": {"etf": "URA", "stocks": ["CCJ", "UEC", "UUUU", "DNN"]},
    
    # Rare/Strategic Metals
    "titanium": {"stocks": ["TIE", "RTX", "BA"]},  # Used in aerospace
    "cobalt": {"stocks": ["VALE", "GLNCY"]},
    "rare_earth": {"etf": "REMX", "stocks": ["MP", "LYSCF"]},
    
    # Agriculture
    "corn": {"etf": "CORN", "futures": "ZC", "stocks": ["ADM", "BG", "DE"]},
    "wheat": {"etf": "WEAT", "futures": "ZW", "stocks": ["ADM", "BG"]},
    "soybeans": {"etf": "SOYB", "futures": "ZS", "stocks": ["ADM", "BG"]},
    "coffee": {"etf": "JO", "futures": "KC", "stocks": ["SBUX", "KDP"]},
    "sugar": {"etf": "CANE", "futures": "SB", "stocks": []},
    
    # Broad Commodity ETFs
    "broad": {"etf": ["DBC", "GSG", "PDBC", "COM"], "description": "Diversified commodity exposure"},
}


# Cryptocurrency symbols and categories
CRYPTO_SYMBOLS = {
    # Major Cryptocurrencies
    "bitcoin": {"symbol": "BTC", "pairs": ["BTC-USD", "BTC-USDT"], "category": "major"},
    "ethereum": {"symbol": "ETH", "pairs": ["ETH-USD", "ETH-USDT"], "category": "major"},
    "solana": {"symbol": "SOL", "pairs": ["SOL-USD", "SOL-USDT"], "category": "major"},
    "xrp": {"symbol": "XRP", "pairs": ["XRP-USD", "XRP-USDT"], "category": "major"},
    "cardano": {"symbol": "ADA", "pairs": ["ADA-USD", "ADA-USDT"], "category": "major"},
    "avalanche": {"symbol": "AVAX", "pairs": ["AVAX-USD", "AVAX-USDT"], "category": "major"},
    "polkadot": {"symbol": "DOT", "pairs": ["DOT-USD", "DOT-USDT"], "category": "major"},
    "polygon": {"symbol": "MATIC", "pairs": ["MATIC-USD", "MATIC-USDT"], "category": "layer2"},
    
    # Layer 2 & Scaling
    "arbitrum": {"symbol": "ARB", "pairs": ["ARB-USD", "ARB-USDT"], "category": "layer2"},
    "optimism": {"symbol": "OP", "pairs": ["OP-USD", "OP-USDT"], "category": "layer2"},
    
    # DeFi Tokens
    "uniswap": {"symbol": "UNI", "pairs": ["UNI-USD", "UNI-USDT"], "category": "defi"},
    "aave": {"symbol": "AAVE", "pairs": ["AAVE-USD", "AAVE-USDT"], "category": "defi"},
    "chainlink": {"symbol": "LINK", "pairs": ["LINK-USD", "LINK-USDT"], "category": "defi"},
    "maker": {"symbol": "MKR", "pairs": ["MKR-USD", "MKR-USDT"], "category": "defi"},
    "compound": {"symbol": "COMP", "pairs": ["COMP-USD", "COMP-USDT"], "category": "defi"},
    
    # Meme Coins
    "dogecoin": {"symbol": "DOGE", "pairs": ["DOGE-USD", "DOGE-USDT"], "category": "meme"},
    "shiba": {"symbol": "SHIB", "pairs": ["SHIB-USD", "SHIB-USDT"], "category": "meme"},
    "pepe": {"symbol": "PEPE", "pairs": ["PEPE-USD", "PEPE-USDT"], "category": "meme"},
    
    # AI & Compute Tokens
    "render": {"symbol": "RNDR", "pairs": ["RNDR-USD", "RNDR-USDT"], "category": "ai"},
    "fetch": {"symbol": "FET", "pairs": ["FET-USD", "FET-USDT"], "category": "ai"},
    "ocean": {"symbol": "OCEAN", "pairs": ["OCEAN-USD", "OCEAN-USDT"], "category": "ai"},
    "akash": {"symbol": "AKT", "pairs": ["AKT-USD", "AKT-USDT"], "category": "ai"},
    
    # Gaming & Metaverse
    "immutablex": {"symbol": "IMX", "pairs": ["IMX-USD", "IMX-USDT"], "category": "gaming"},
    "gala": {"symbol": "GALA", "pairs": ["GALA-USD", "GALA-USDT"], "category": "gaming"},
    "sandbox": {"symbol": "SAND", "pairs": ["SAND-USD", "SAND-USDT"], "category": "gaming"},
    "axie": {"symbol": "AXS", "pairs": ["AXS-USD", "AXS-USDT"], "category": "gaming"},
    
    # Stablecoins (for pairs)
    "usdt": {"symbol": "USDT", "pairs": [], "category": "stablecoin"},
    "usdc": {"symbol": "USDC", "pairs": [], "category": "stablecoin"},
    
    # Crypto ETFs (tradeable on stock exchanges)
    "crypto_etfs": {
        "IBIT": "iShares Bitcoin Trust",
        "FBTC": "Fidelity Bitcoin ETF",
        "GBTC": "Grayscale Bitcoin Trust",
        "ETHE": "Grayscale Ethereum Trust",
        "BITO": "ProShares Bitcoin Strategy ETF",
        "COIN": "Coinbase Stock",
        "MSTR": "MicroStrategy (Bitcoin proxy)",
        "MARA": "Marathon Digital Holdings",
        "RIOT": "Riot Platforms",
        "CLSK": "CleanSpark",
    }
}


# All available strategies
ALL_STRATEGIES = [
    "Technical", "Momentum", "MeanReversion", "NewsSentiment",
    "Breakout", "TrendFollowing", "Scalping", "SwingTrading",
    "VWAP", "RSI", "MACD", "BollingerBands", "MovingAverageCrossover",
    "InsiderFollowing", "SocialSentiment", "AIAnalysis"
]

DEFAULT_STRATEGY_WEIGHTS = {
    "Technical": 0.6,
    "Momentum": 0.5,
    "MeanReversion": 0.4,
    "NewsSentiment": 0.4,
    "Breakout": 0.5,
    "TrendFollowing": 0.5,
    "Scalping": 0.3,
    "SwingTrading": 0.5,
    "VWAP": 0.4,
    "RSI": 0.5,
    "MACD": 0.5,
    "BollingerBands": 0.4,
    "MovingAverageCrossover": 0.5,
    "InsiderFollowing": 0.3,
    "SocialSentiment": 0.3,
    "AIAnalysis": 0.6,
}


@dataclass
class BotConfig:
    """Configuration for a bot instance."""
    name: str
    description: str = ""
    
    # AI Strategy Prompt - natural language strategy description
    ai_strategy_prompt: str = ""
    ai_interpreted_config: dict = field(default_factory=dict)  # AI-parsed configuration
    
    # Instrument type
    instrument_type: InstrumentType = InstrumentType.STOCK
    
    # Trading configuration
    symbols: list[str] = field(default_factory=list)
    strategies: list[str] = field(default_factory=lambda: ALL_STRATEGIES.copy())
    
    # Strategy weights
    strategy_weights: dict[str, float] = field(default_factory=lambda: DEFAULT_STRATEGY_WEIGHTS.copy())
    
    # Risk parameters (per bot)
    max_position_size: float = 25000.0
    max_positions: int = 10
    max_daily_loss_pct: float = 2.0
    
    # Execution settings
    trade_frequency_seconds: int = 60
    use_paper_trading: bool = True
    
    # News settings
    enable_news_trading: bool = True
    news_sentiment_threshold: float = 0.5
    
    # =========================================================================
    # Options-specific settings
    # =========================================================================
    options_type: str = "call"  # "call", "put", "both"
    options_dte_min: int = 7    # Minimum days to expiration
    options_dte_max: int = 45   # Maximum days to expiration
    options_delta_min: float = 0.20  # Minimum delta (OTM)
    options_delta_max: float = 0.50  # Maximum delta (ATM)
    options_max_contracts: int = 10  # Max contracts per position
    options_profit_target_pct: float = 50.0  # Take profit at 50% gain
    options_stop_loss_pct: float = 30.0  # Stop loss at 30% loss
    
    # =========================================================================
    # Futures-specific settings
    # =========================================================================
    futures_contracts: list[str] = field(default_factory=list)  # e.g., ["ES", "NQ", "CL"]
    futures_max_contracts: int = 5
    futures_use_micro: bool = True  # Use micro contracts for smaller size
    futures_session: str = "rth"  # "rth" (regular) or "eth" (extended)
    
    # =========================================================================
    # Commodity-specific settings
    # =========================================================================
    commodity_type: str = ""  # "gold", "silver", "oil", etc.
    commodity_trade_etfs: bool = True  # Trade ETFs like GLD, USO
    commodity_trade_miners: bool = False  # Trade mining stocks
    commodity_trade_futures: bool = False  # Trade commodity futures
    commodity_seasonal_trading: bool = True  # Consider seasonal patterns
    commodity_macro_alerts: bool = True  # Monitor Fed, inflation, USD
    commodity_geopolitical_alerts: bool = True  # Monitor supply disruptions
    
    # =========================================================================
    # Crypto-specific settings
    # =========================================================================
    crypto_category: str = ""  # "major", "defi", "layer2", "meme", "ai", "gaming"
    crypto_exchange: str = "coinbase"  # "coinbase", "binance", "kraken", "alpaca"
    crypto_trade_spot: bool = True  # Spot trading
    crypto_trade_perpetuals: bool = False  # Perpetual futures
    crypto_trade_etfs: bool = True  # Crypto ETFs like IBIT, GBTC
    crypto_use_leverage: bool = False  # Use leverage on perpetuals
    crypto_leverage_max: float = 2.0  # Maximum leverage multiplier
    crypto_dca_enabled: bool = True  # Dollar-cost averaging on entries
    crypto_dca_intervals: int = 4  # Split entry into X parts
    crypto_trailing_stop_pct: float = 5.0  # Trailing stop percentage
    crypto_take_profit_pct: float = 15.0  # Take profit percentage
    crypto_whale_alerts: bool = True  # Monitor large transactions
    crypto_on_chain_analysis: bool = True  # Use on-chain metrics
    crypto_fear_greed_threshold: int = 25  # Buy when fear < X
    crypto_24h_trading: bool = True  # Trade 24/7
    
    # =========================================================================
    # Aggressive trading settings
    # =========================================================================
    enable_scalping: bool = False  # Ultra short-term trades
    scalp_profit_ticks: int = 10   # Take profit after X ticks
    scalp_stop_ticks: int = 5      # Stop loss after X ticks
    enable_momentum_bursts: bool = False  # Chase momentum moves
    leverage_multiplier: float = 1.0  # Position size multiplier
    
    # =========================================================================
    # Multi-broker routing settings
    # =========================================================================
    broker_type: Optional[str] = None  # Specific broker (e.g., "alpaca", "ibkr"), None = use default
    failover_brokers: List[str] = field(default_factory=list)  # Backup brokers in priority order
    multi_broker: bool = False  # If True, execute trades on ALL connected brokers simultaneously
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "instrument_type": self.instrument_type.value if isinstance(self.instrument_type, InstrumentType) else self.instrument_type,
            "symbols": self.symbols,
            "strategies": self.strategies,
            "strategy_weights": self.strategy_weights,
            "max_position_size": self.max_position_size,
            "max_positions": self.max_positions,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "trade_frequency_seconds": self.trade_frequency_seconds,
            "use_paper_trading": self.use_paper_trading,
            "enable_news_trading": self.enable_news_trading,
            "news_sentiment_threshold": self.news_sentiment_threshold,
            # Options
            "options_type": self.options_type,
            "options_dte_min": self.options_dte_min,
            "options_dte_max": self.options_dte_max,
            "options_delta_min": self.options_delta_min,
            "options_delta_max": self.options_delta_max,
            "options_max_contracts": self.options_max_contracts,
            "options_profit_target_pct": self.options_profit_target_pct,
            "options_stop_loss_pct": self.options_stop_loss_pct,
            # Futures
            "futures_contracts": self.futures_contracts,
            "futures_max_contracts": self.futures_max_contracts,
            "futures_use_micro": self.futures_use_micro,
            "futures_session": self.futures_session,
            # Commodity
            "commodity_type": self.commodity_type,
            "commodity_trade_etfs": self.commodity_trade_etfs,
            "commodity_trade_miners": self.commodity_trade_miners,
            "commodity_trade_futures": self.commodity_trade_futures,
            "commodity_seasonal_trading": self.commodity_seasonal_trading,
            "commodity_macro_alerts": self.commodity_macro_alerts,
            "commodity_geopolitical_alerts": self.commodity_geopolitical_alerts,
            # Crypto
            "crypto_category": self.crypto_category,
            "crypto_exchange": self.crypto_exchange,
            "crypto_trade_spot": self.crypto_trade_spot,
            "crypto_trade_perpetuals": self.crypto_trade_perpetuals,
            "crypto_trade_etfs": self.crypto_trade_etfs,
            "crypto_use_leverage": self.crypto_use_leverage,
            "crypto_leverage_max": self.crypto_leverage_max,
            "crypto_dca_enabled": self.crypto_dca_enabled,
            "crypto_dca_intervals": self.crypto_dca_intervals,
            "crypto_trailing_stop_pct": self.crypto_trailing_stop_pct,
            "crypto_take_profit_pct": self.crypto_take_profit_pct,
            "crypto_whale_alerts": self.crypto_whale_alerts,
            "crypto_on_chain_analysis": self.crypto_on_chain_analysis,
            "crypto_fear_greed_threshold": self.crypto_fear_greed_threshold,
            "crypto_24h_trading": self.crypto_24h_trading,
            # Aggressive
            "enable_scalping": self.enable_scalping,
            "scalp_profit_ticks": self.scalp_profit_ticks,
            "scalp_stop_ticks": self.scalp_stop_ticks,
            "enable_momentum_bursts": self.enable_momentum_bursts,
            "leverage_multiplier": self.leverage_multiplier,
            # Multi-broker routing
            "broker_type": self.broker_type,
            "failover_brokers": self.failover_brokers,
            "multi_broker": self.multi_broker,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BotConfig":
        # Handle instrument_type conversion
        if "instrument_type" in data and isinstance(data["instrument_type"], str):
            data["instrument_type"] = InstrumentType(data["instrument_type"])
        return cls(**data)


@dataclass
class TradeRecord:
    """Record of a completed trade with reasoning."""
    timestamp: str
    symbol: str
    side: str  # buy or sell
    quantity: int
    price: float
    order_id: str
    broker: str
    reasoning: str
    confidence: float
    indicators: dict


@dataclass
class BotStats:
    """Runtime statistics for a bot."""
    trades_today: int = 0
    signals_generated: int = 0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    open_positions: int = 0
    last_trade_time: Optional[datetime] = None
    errors_count: int = 0
    uptime_seconds: float = 0.0
    cycles_completed: int = 0
    last_cycle_time: Optional[datetime] = None
    symbols_analyzed: int = 0
    orders_submitted: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    trade_history: List[TradeRecord] = field(default_factory=list)  # Track all trades with reasons


class BotInstance:
    """
    Individual trading bot instance that runs in its own thread.
    
    Each bot can:
    - Trade a specific set of symbols
    - Use different strategy combinations
    - Have its own risk limits
    - Run independently of other bots
    """
    
    MAX_BOTS = 100  # Maximum number of bots allowed (stocks, options, futures, crypto, commodities)
    
    def __init__(self, config: BotConfig, bot_id: str = None):
        """
        Initialize a bot instance.
        
        Args:
            config: Bot configuration
            bot_id: Optional bot ID (auto-generated if not provided)
        """
        self.id = bot_id or str(uuid.uuid4())[:8]
        self.config = config
        self.status = BotStatus.CREATED
        self.stats = BotStats()
        
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        
        self._created_at = datetime.utcnow()
        self._started_at: Optional[datetime] = None
        self._stopped_at: Optional[datetime] = None
        
        self._callbacks: dict[str, list[Callable]] = {
            "on_start": [],
            "on_stop": [],
            "on_trade": [],
            "on_signal": [],
            "on_error": [],
        }
        
        logger.info(f"Bot {self.id} created: {config.name}")
        self._log_activity("created", f"Bot created with {len(config.symbols)} symbols")
    
    def _log_activity(self, event_type: str, message: str, data: Optional[dict] = None) -> None:
        """Log bot activity for debugging."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "bot_id": self.id,
            "bot_name": self.config.name,
            "event_type": event_type,
            "message": message,
            "data": data or {},
        }
        with _activity_lock:
            _bot_activity_log.append(entry)
        
        # Also log to file at appropriate level
        if event_type in ("error", "order_rejected"):
            logger.error(f"[Bot {self.id}] {event_type}: {message}")
        elif event_type in ("trade", "order_submitted", "order_filled", "signal"):
            logger.info(f"[Bot {self.id}] {event_type}: {message}")
        else:
            logger.debug(f"[Bot {self.id}] {event_type}: {message}")
    
    @property
    def is_running(self) -> bool:
        return self.status == BotStatus.RUNNING
    
    @property
    def is_paused(self) -> bool:
        return self.status == BotStatus.PAUSED
    
    @property
    def uptime(self) -> float:
        """Get uptime in seconds."""
        if self._started_at:
            end_time = self._stopped_at or datetime.utcnow()
            return (end_time - self._started_at).total_seconds()
        return 0.0
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a callback for an event."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event to callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Bot {self.id} callback error: {e}")
    
    def start(self) -> bool:
        """Start the bot in a new thread."""
        if self.status in (BotStatus.RUNNING, BotStatus.STARTING):
            logger.warning(f"Bot {self.id} is already running")
            return False
        
        self.status = BotStatus.STARTING
        self._stop_event.clear()
        self._pause_event.clear()
        
        self._thread = threading.Thread(
            target=self._run_thread,
            name=f"Bot-{self.id}",
            daemon=True,
        )
        self._thread.start()
        
        return True
    
    def stop(self) -> bool:
        """Stop the bot."""
        if self.status not in (BotStatus.RUNNING, BotStatus.PAUSED):
            return False
        
        self.status = BotStatus.STOPPING
        self._stop_event.set()
        self._pause_event.set()  # Unpause if paused
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        
        self.status = BotStatus.STOPPED
        self._stopped_at = datetime.utcnow()
        self._emit("on_stop")
        
        logger.info(f"Bot {self.id} stopped")
        return True
    
    def pause(self) -> bool:
        """Pause the bot (keeps thread alive but stops trading)."""
        if self.status != BotStatus.RUNNING:
            return False
        
        self._pause_event.set()
        self.status = BotStatus.PAUSED
        logger.info(f"Bot {self.id} paused")
        return True
    
    def resume(self) -> bool:
        """Resume the bot from paused state."""
        if self.status != BotStatus.PAUSED:
            return False
        
        self._pause_event.clear()
        self.status = BotStatus.RUNNING
        logger.info(f"Bot {self.id} resumed")
        return True
    
    def _run_thread(self) -> None:
        """Main thread entry point."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._run_async())
        except Exception as e:
            self.status = BotStatus.ERROR
            self.stats.errors_count += 1
            logger.error(f"Bot {self.id} error: {e}")
            self._emit("on_error", e)
        finally:
            if self._loop:
                try:
                    # Cancel any pending tasks
                    pending = asyncio.all_tasks(self._loop)
                    for task in pending:
                        task.cancel()
                    # Run until all tasks are cancelled
                    if pending:
                        self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    # Stop the loop if running
                    if self._loop.is_running():
                        self._loop.stop()
                    # Close the loop
                    if not self._loop.is_closed():
                        self._loop.close()
                except Exception:
                    pass  # Ignore errors during cleanup
    
    async def _run_async(self) -> None:
        """Main async trading loop."""
        self.status = BotStatus.RUNNING
        self._started_at = datetime.utcnow()
        self._emit("on_start")
        
        logger.info(f"Bot {self.id} ({self.config.name}) started trading")
        logger.info(f"  Symbols: {self.config.symbols}")
        logger.info(f"  Strategies: {self.config.strategies}")
        
        while not self._stop_event.is_set():
            try:
                # Check if paused
                if self._pause_event.is_set():
                    await asyncio.sleep(1)
                    continue
                
                # Run trading cycle
                await self._trading_cycle()
                
                # Update stats
                self.stats.uptime_seconds = self.uptime
                
                # Wait for next cycle
                await asyncio.sleep(self.config.trade_frequency_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats.errors_count += 1
                logger.error(f"Bot {self.id} cycle error: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _trading_cycle(self) -> None:
        """Execute one trading cycle - analyze signals and execute trades."""
        from src.brokers.registry import get_broker_registry
        from src.brokers.base import OrderSide, OrderType, BrokerType
        
        cycle_start = datetime.utcnow()
        self.stats.cycles_completed += 1
        self.stats.last_cycle_time = cycle_start
        
        self._log_activity("cycle_start", f"Starting trading cycle #{self.stats.cycles_completed}", {
            "symbols": self.config.symbols,
            "strategies": self.config.strategies[:3],  # First 3
            "paper_trading": self.config.use_paper_trading,
            "broker_type": self.config.broker_type,
            "multi_broker": self.config.multi_broker,
        })
        
        registry = get_broker_registry()
        
        # Check if any broker is connected
        if not registry.connected_brokers:
            self._log_activity("no_broker", "No broker connected - waiting for connection", {
                "available_brokers": list(registry._brokers.keys()) if hasattr(registry, '_brokers') else [],
            })
            return
        
        # Get list of brokers to use based on configuration
        brokers_to_use = await self._get_brokers_for_trading(registry)
        
        if not brokers_to_use:
            self._log_activity("no_broker", "No suitable broker available for trading")
            return
        
        # Execute trading cycle on each broker
        for broker in brokers_to_use:
            if not broker.is_connected:
                self._log_activity("broker_disconnected", f"Broker {broker.name} is not connected, skipping")
                continue
            
            self._log_activity("broker_connected", f"Using broker: {broker.name}", {
                "broker_type": type(broker).__name__,
            })
            
            # Execute trades on this broker
            await self._execute_trades_on_broker(broker)
    
    async def _get_brokers_for_trading(self, registry) -> list:
        """
        Get list of brokers to use based on bot configuration.
        
        Supports:
        - Specific broker assignment (config.broker_type)
        - Multi-broker mode (execute on all connected brokers)
        - Failover brokers (try backup if primary fails)
        """
        from src.brokers.base import BrokerType
        
        brokers = []
        
        # Multi-broker mode: use all connected brokers
        if self.config.multi_broker:
            for broker_type in registry.connected_brokers:
                broker = registry.get_broker(broker_type)
                if broker and broker.is_connected:
                    brokers.append(broker)
            self._log_activity("multi_broker", f"Using {len(brokers)} brokers in multi-broker mode", {
                "brokers": [b.name for b in brokers],
            })
            return brokers
        
        # Specific broker assigned
        if self.config.broker_type:
            try:
                broker_type = BrokerType(self.config.broker_type)
                broker = registry.get_broker(broker_type)
                if broker and broker.is_connected:
                    brokers.append(broker)
                    return brokers
                else:
                    self._log_activity("broker_unavailable", f"Assigned broker {self.config.broker_type} not available")
                    
                    # Try failover brokers
                    for failover_type_str in self.config.failover_brokers:
                        try:
                            failover_type = BrokerType(failover_type_str)
                            failover_broker = registry.get_broker(failover_type)
                            if failover_broker and failover_broker.is_connected:
                                self._log_activity("failover", f"Using failover broker: {failover_type_str}")
                                brokers.append(failover_broker)
                                return brokers
                        except ValueError:
                            continue
                    
                    self._log_activity("no_failover", "No failover brokers available")
            except ValueError:
                self._log_activity("invalid_broker", f"Invalid broker type: {self.config.broker_type}")
        
        # Fall back to default broker
        default_broker = registry.get_default_broker()
        if default_broker and default_broker.is_connected:
            brokers.append(default_broker)
        
        return brokers
    
    async def _execute_trades_on_broker(self, broker) -> None:
        """Execute the trading logic on a specific broker."""
        from src.brokers.base import OrderSide, OrderType
        
        cycle_start = datetime.utcnow()
        
        # Get account info for position sizing
        try:
            accounts = await broker.get_accounts()
            if not accounts:
                self._log_activity("no_accounts", f"No accounts returned from broker {broker.name}")
                return
            account = accounts[0]
            account_id = account.account_id
            buying_power = account.buying_power
            portfolio_value = getattr(account, 'portfolio_value', buying_power)
            
            self._log_activity("account_info", f"Account: {account_id}", {
                "buying_power": buying_power,
                "portfolio_value": portfolio_value,
                "broker": broker.name,
            })
        except Exception as e:
            self._log_activity("error", f"Failed to get account info from {broker.name}: {e}", {"exception": str(e)})
            self.stats.errors_count += 1
            return
        
        # Note: Paper trading mode still executes trades - just on a paper/simulated account
        # The broker itself handles whether it's a paper or live account
        mode = "PAPER" if self.config.use_paper_trading else "LIVE"
        self._log_activity("trading_mode", f"Trading mode: {mode} on {broker.name}")
        
        symbols_analyzed = 0
        signals_generated = 0
        
        for symbol in self.config.symbols:
            try:
                symbols_analyzed += 1
                self._log_activity("analyzing", f"Analyzing {symbol}", {"symbol": symbol, "broker": broker.name})
                
                # Get current position for this symbol
                try:
                    current_position = await broker.get_position(account_id, symbol)
                    current_qty = current_position.quantity if current_position else 0
                    self._log_activity("position_check", f"{symbol}: current position = {current_qty}", {
                        "symbol": symbol,
                        "quantity": current_qty,
                    })
                except Exception as e:
                    current_qty = 0
                    self._log_activity("position_error", f"Could not get position for {symbol}: {e}")
                
                # Generate signal using technical analysis
                signal = await self._generate_signal(symbol)
                
                if not signal:
                    self._log_activity("no_signal", f"{symbol}: No actionable signal", {"symbol": symbol})
                    continue
                
                signals_generated += 1
                self.stats.signals_generated += 1
                self._emit("on_signal", signal)
                
                signal_type = signal.get('type', 'hold')
                price = signal.get('price', 0)
                confidence = signal.get('confidence', 0)
                
                reasoning = signal.get('reasoning', 'No reasoning provided')
                
                self._log_activity("signal", f"{symbol}: {signal_type.upper()} @ ${price:.2f} (confidence: {confidence:.1%})", {
                    "symbol": symbol,
                    "signal_type": signal_type,
                    "price": price,
                    "confidence": confidence,
                    "indicators": signal.get('indicators', {}),
                    "reasoning": reasoning,
                    "broker": broker.name,
                })
                
                # Log the AI reasoning
                logger.info(f"[Bot {self.id}] 🤖 Trade Reasoning for {symbol}: {reasoning}")
                
                # Determine action based on signal
                if signal_type in ('strong_buy', 'buy') and current_qty <= 0:
                    # Calculate position size
                    max_position = min(
                        self.config.max_position_size,
                        buying_power * 0.1  # Max 10% of buying power per position
                    )
                    quantity = int(max_position / price) if price > 0 else 0
                    
                    if quantity > 0:
                        self._log_activity("order_intent", f"BUY {quantity} {symbol} @ market via {broker.name}", {
                            "symbol": symbol,
                            "side": "buy",
                            "quantity": quantity,
                            "estimated_value": quantity * price,
                            "broker": broker.name,
                        })
                        
                        # Execute buy order
                        try:
                            self.stats.orders_submitted += 1
                            order = await broker.submit_order(
                                account_id=account_id,
                                symbol=symbol,
                                side=OrderSide.BUY,
                                quantity=quantity,
                                order_type=OrderType.MARKET,
                            )
                            self.stats.trades_today += 1
                            self.stats.orders_filled += 1
                            self.stats.last_trade_time = datetime.utcnow()
                            
                            # Track trade with reasoning
                            trade_record = TradeRecord(
                                timestamp=datetime.utcnow().isoformat(),
                                symbol=symbol,
                                side="buy",
                                quantity=quantity,
                                price=price,
                                order_id=order.order_id,
                                broker=broker.name,
                                reasoning=reasoning,
                                confidence=confidence,
                                indicators=signal.get('indicators', {}),
                            )
                            self.stats.trade_history.append(trade_record)
                            
                            self._log_activity("order_filled", f"BUY {quantity} {symbol} - Order {order.order_id} via {broker.name}", {
                                "order_id": order.order_id,
                                "symbol": symbol,
                                "side": "buy",
                                "quantity": quantity,
                                "broker": broker.name,
                                "reasoning": reasoning,
                            })
                            self._emit("on_trade", {"symbol": symbol, "side": "buy", "quantity": quantity, "order_id": order.order_id, "broker": broker.name, "reasoning": reasoning})
                        except Exception as e:
                            self.stats.orders_rejected += 1
                            self.stats.errors_count += 1
                            self._log_activity("order_rejected", f"Order failed for {symbol} on {broker.name}: {e}", {
                                "symbol": symbol,
                                "error": str(e),
                                "broker": broker.name,
                            })
                    else:
                        self._log_activity("skip_order", f"Quantity would be 0 for {symbol} (price={price})")
                
                elif signal_type in ('strong_sell', 'sell') and current_qty > 0:
                    self._log_activity("order_intent", f"SELL {abs(current_qty)} {symbol} @ market via {broker.name}", {
                        "symbol": symbol,
                        "side": "sell",
                        "quantity": abs(current_qty),
                        "broker": broker.name,
                        "reasoning": reasoning,
                    })
                    
                    # Sell existing position
                    try:
                        self.stats.orders_submitted += 1
                        order = await broker.submit_order(
                            account_id=account_id,
                            symbol=symbol,
                            side=OrderSide.SELL,
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                        )
                        self.stats.trades_today += 1
                        self.stats.orders_filled += 1
                        self.stats.last_trade_time = datetime.utcnow()
                        
                        # Track trade with reasoning
                        trade_record = TradeRecord(
                            timestamp=datetime.utcnow().isoformat(),
                            symbol=symbol,
                            side="sell",
                            quantity=abs(current_qty),
                            price=price,
                            order_id=order.order_id,
                            broker=broker.name,
                            reasoning=reasoning,
                            confidence=confidence,
                            indicators=signal.get('indicators', {}),
                        )
                        self.stats.trade_history.append(trade_record)
                        
                        self._log_activity("order_filled", f"SELL {abs(current_qty)} {symbol} - Order {order.order_id} via {broker.name}", {
                            "order_id": order.order_id,
                            "symbol": symbol,
                            "side": "sell",
                            "quantity": abs(current_qty),
                            "broker": broker.name,
                            "reasoning": reasoning,
                        })
                        self._emit("on_trade", {"symbol": symbol, "side": "sell", "quantity": abs(current_qty), "order_id": order.order_id, "broker": broker.name, "reasoning": reasoning})
                    except Exception as e:
                        self.stats.orders_rejected += 1
                        self.stats.errors_count += 1
                        self._log_activity("order_rejected", f"Order failed for {symbol} on {broker.name}: {e}", {
                            "symbol": symbol,
                            "error": str(e),
                            "broker": broker.name,
                        })
                else:
                    # Signal doesn't match position state
                    if signal_type in ('strong_buy', 'buy'):
                        self._log_activity("skip_trade", f"{symbol}: Already have position ({current_qty}), skipping buy")
                    elif signal_type in ('strong_sell', 'sell'):
                        self._log_activity("skip_trade", f"{symbol}: No position to sell")
                
            except Exception as e:
                self.stats.errors_count += 1
                self._log_activity("error", f"Error processing {symbol} on {broker.name}: {e}", {
                    "symbol": symbol,
                    "exception": str(e),
                    "broker": broker.name,
                })
        
        self.stats.symbols_analyzed += symbols_analyzed
        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
        
        self._log_activity("broker_cycle_complete", f"Completed trading on {broker.name}", {
            "symbols_analyzed": symbols_analyzed,
            "signals_generated": signals_generated,
            "duration_seconds": round(cycle_duration, 2),
            "trades_today": self.stats.trades_today,
            "broker": broker.name,
        })
    
    async def _generate_signal(self, symbol: str) -> Optional[dict]:
        """
        Generate trading signal for a symbol using technical analysis.
        
        Uses multiple indicators:
        - RSI (Relative Strength Index)
        - Moving Average crossovers (SMA 20/50)
        - MACD
        - Bollinger Bands
        
        Returns a signal if indicators align, None otherwise.
        """
        global _yfinance_semaphore
        
        try:
            # Get market data with caching to prevent thread exhaustion
            hist = await self._get_cached_market_data(symbol)
            
            if hist is None or hist.empty or len(hist) < 30:
                bars = len(hist) if hist is not None and not hist.empty else 0
                self._log_activity("insufficient_data", f"{symbol}: Not enough historical data ({bars} bars)", {
                    "symbol": symbol,
                    "bars": bars,
                })
                return None
            
            # Current price
            current_price = hist['Close'].iloc[-1]
            
            # Calculate indicators
            indicators = self._calculate_indicators(hist)
            
            if not indicators:
                return None
            
            # Generate signal based on indicator confluence
            signal_type, confidence, reasoning = self._evaluate_indicators(indicators)
            
            if signal_type == 'hold':
                return None
            
            return {
                'type': signal_type,
                'symbol': symbol,
                'price': current_price,
                'confidence': confidence,
                'strategy': 'multi_indicator',
                'indicators': indicators,
                'reasoning': reasoning,
                'timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self._log_activity("signal_error", f"Error generating signal for {symbol}: {e}", {
                "symbol": symbol,
                "error": str(e),
            })
            return None
    
    async def _get_cached_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get market data with caching to prevent yfinance thread exhaustion.
        
        Multiple bots requesting the same symbol will share cached data.
        """
        global _yfinance_semaphore
        
        cache_key = symbol.upper()
        now = datetime.now()
        
        # Check cache first (thread-safe)
        with _market_data_lock:
            if cache_key in _market_data_cache:
                entry = _market_data_cache[cache_key]
                age = (now - entry["timestamp"]).total_seconds()
                if age < _market_data_cache_ttl:
                    if entry.get("error"):
                        # Don't retry too quickly for errors
                        return None
                    return entry["data"]
        
        # Initialize semaphore if needed (limit concurrent yfinance calls)
        if _yfinance_semaphore is None:
            _yfinance_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent yfinance requests
        
        # Fetch with semaphore to limit concurrency
        async with _yfinance_semaphore:
            # Double-check cache after acquiring semaphore
            with _market_data_lock:
                if cache_key in _market_data_cache:
                    entry = _market_data_cache[cache_key]
                    age = (now - entry["timestamp"]).total_seconds()
                    if age < _market_data_cache_ttl:
                        return entry.get("data")
            
            try:
                import yfinance as yf
                
                # Run in executor to not block event loop
                loop = asyncio.get_event_loop()
                hist = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: yf.Ticker(symbol).history(period="60d", interval="1d")),
                    timeout=15  # 15 second timeout
                )
                
                # Cache the result
                with _market_data_lock:
                    _market_data_cache[cache_key] = {
                        "data": hist if not hist.empty else None,
                        "timestamp": datetime.now(),
                        "error": None,
                    }
                
                return hist if not hist.empty else None
                
            except asyncio.TimeoutError:
                logger.warning(f"yfinance timeout for {symbol}")
                with _market_data_lock:
                    _market_data_cache[cache_key] = {
                        "data": None,
                        "timestamp": datetime.now(),
                        "error": "timeout",
                    }
                return None
                
            except Exception as e:
                logger.warning(f"yfinance error for {symbol}: {e}")
                with _market_data_lock:
                    _market_data_cache[cache_key] = {
                        "data": None,
                        "timestamp": datetime.now(),
                        "error": str(e),
                    }
                return None
    
    def _calculate_indicators(self, data: pd.DataFrame) -> Optional[dict]:
        """Calculate technical indicators from OHLCV data."""
        try:
            close = data['Close']
            high = data['High']
            low = data['Low']
            volume = data['Volume']
            
            # RSI (14-period)
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Moving Averages
            sma_20 = close.rolling(window=20).mean().iloc[-1]
            sma_50 = close.rolling(window=50).mean().iloc[-1] if len(close) >= 50 else sma_20
            current_price = close.iloc[-1]
            
            # MA Crossover signals
            ma_bullish = current_price > sma_20 > sma_50
            ma_bearish = current_price < sma_20 < sma_50
            
            # MACD
            ema_12 = close.ewm(span=12, adjust=False).mean()
            ema_26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema_12 - ema_26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            macd_histogram = macd_line - signal_line
            
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_histogram = macd_histogram.iloc[-1]
            prev_histogram = macd_histogram.iloc[-2] if len(macd_histogram) > 1 else 0
            
            macd_bullish = current_macd > current_signal and current_histogram > prev_histogram
            macd_bearish = current_macd < current_signal and current_histogram < prev_histogram
            
            # Bollinger Bands
            bb_sma = close.rolling(window=20).mean()
            bb_std = close.rolling(window=20).std()
            bb_upper = bb_sma + (bb_std * 2)
            bb_lower = bb_sma - (bb_std * 2)
            
            current_bb_upper = bb_upper.iloc[-1]
            current_bb_lower = bb_lower.iloc[-1]
            bb_position = (current_price - current_bb_lower) / (current_bb_upper - current_bb_lower) if (current_bb_upper - current_bb_lower) > 0 else 0.5
            
            # Volume analysis
            avg_volume = volume.rolling(window=20).mean().iloc[-1]
            current_volume = volume.iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Price momentum (5-day return)
            momentum_5d = (current_price - close.iloc[-5]) / close.iloc[-5] * 100 if len(close) >= 5 else 0
            
            return {
                'rsi': round(current_rsi, 2),
                'sma_20': round(sma_20, 2),
                'sma_50': round(sma_50, 2),
                'price': round(current_price, 2),
                'ma_bullish': ma_bullish,
                'ma_bearish': ma_bearish,
                'macd': round(current_macd, 4),
                'macd_signal': round(current_signal, 4),
                'macd_histogram': round(current_histogram, 4),
                'macd_bullish': macd_bullish,
                'macd_bearish': macd_bearish,
                'bb_position': round(bb_position, 2),
                'bb_upper': round(current_bb_upper, 2),
                'bb_lower': round(current_bb_lower, 2),
                'volume_ratio': round(volume_ratio, 2),
                'momentum_5d': round(momentum_5d, 2),
            }
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return None
    
    def _evaluate_indicators(self, indicators: dict) -> tuple[str, float, str]:
        """
        Evaluate indicators and return (signal_type, confidence, reasoning).
        
        Uses a scoring system based on indicator confluence.
        Returns detailed reasoning for why the trade decision was made.
        """
        bullish_score = 0
        bearish_score = 0
        max_score = 5  # Number of indicators checked
        
        # Track reasons for the decision
        bullish_reasons = []
        bearish_reasons = []
        
        rsi = indicators.get('rsi', 50)
        bb_position = indicators.get('bb_position', 0.5)
        volume_ratio = indicators.get('volume_ratio', 1.0)
        momentum = indicators.get('momentum_5d', 0)
        
        # RSI signals
        if rsi < 30:  # Oversold - bullish
            bullish_score += 1
            bullish_reasons.append(f"RSI oversold ({rsi:.1f}<30)")
        elif rsi > 70:  # Overbought - bearish
            bearish_score += 1
            bearish_reasons.append(f"RSI overbought ({rsi:.1f}>70)")
        elif rsi < 40:  # Slightly oversold
            bullish_score += 0.5
            bullish_reasons.append(f"RSI approaching oversold ({rsi:.1f})")
        elif rsi > 60:  # Slightly overbought
            bearish_score += 0.5
            bearish_reasons.append(f"RSI approaching overbought ({rsi:.1f})")
        
        # Moving Average signals
        if indicators.get('ma_bullish'):
            bullish_score += 1
            bullish_reasons.append("Price above SMA20 > SMA50 (bullish MA alignment)")
        elif indicators.get('ma_bearish'):
            bearish_score += 1
            bearish_reasons.append("Price below SMA20 < SMA50 (bearish MA alignment)")
        
        # MACD signals
        if indicators.get('macd_bullish'):
            bullish_score += 1
            bullish_reasons.append("MACD bullish crossover with rising histogram")
        elif indicators.get('macd_bearish'):
            bearish_score += 1
            bearish_reasons.append("MACD bearish crossover with falling histogram")
        
        # Bollinger Band signals
        if bb_position < 0.2:  # Near lower band - bullish
            bullish_score += 1
            bullish_reasons.append(f"Price near lower Bollinger Band ({bb_position:.1%})")
        elif bb_position > 0.8:  # Near upper band - bearish
            bearish_score += 1
            bearish_reasons.append(f"Price near upper Bollinger Band ({bb_position:.1%})")
        
        # Momentum
        if momentum > 3:  # Strong upward momentum
            bullish_score += 0.5
            bullish_reasons.append(f"Strong 5-day momentum (+{momentum:.1f}%)")
        elif momentum < -3:  # Strong downward momentum
            bearish_score += 0.5
            bearish_reasons.append(f"Weak 5-day momentum ({momentum:.1f}%)")
        
        # Volume confirmation
        if volume_ratio > 1.5:
            # High volume amplifies the signal
            if bullish_score > bearish_score:
                bullish_score += 0.5
                bullish_reasons.append(f"High volume confirmation ({volume_ratio:.1f}x avg)")
            elif bearish_score > bullish_score:
                bearish_score += 0.5
                bearish_reasons.append(f"High volume confirms weakness ({volume_ratio:.1f}x avg)")
        
        # Determine signal
        net_score = bullish_score - bearish_score
        
        if net_score >= 2.5:
            signal_type = 'strong_buy'
            confidence = min(0.9, 0.5 + (net_score / max_score) * 0.4)
            reasoning = f"STRONG BUY: {' | '.join(bullish_reasons)}"
        elif net_score >= 1.5:
            signal_type = 'buy'
            confidence = min(0.75, 0.4 + (net_score / max_score) * 0.35)
            reasoning = f"BUY: {' | '.join(bullish_reasons)}"
        elif net_score <= -2.5:
            signal_type = 'strong_sell'
            confidence = min(0.9, 0.5 + (abs(net_score) / max_score) * 0.4)
            reasoning = f"STRONG SELL: {' | '.join(bearish_reasons)}"
        elif net_score <= -1.5:
            signal_type = 'sell'
            confidence = min(0.75, 0.4 + (abs(net_score) / max_score) * 0.35)
            reasoning = f"SELL: {' | '.join(bearish_reasons)}"
        else:
            signal_type = 'hold'
            confidence = 0
            reasoning = "HOLD: No clear signal (indicators mixed)"
        
        return signal_type, round(confidence, 2), reasoning
    
    def update_config(self, updates: dict) -> None:
        """Update bot configuration (while running or stopped)."""
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        logger.info(f"Bot {self.id} config updated: {list(updates.keys())}")
    
    def get_status(self) -> dict:
        """Get bot status and stats."""
        return {
            "id": self.id,
            "name": self.config.name,
            "description": self.config.description,
            "status": self.status.value,
            "created_at": self._created_at.isoformat(),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "stopped_at": self._stopped_at.isoformat() if self._stopped_at else None,
            "uptime_seconds": self.uptime,
            "config": self.config.to_dict(),
            "stats": {
                "trades_today": self.stats.trades_today,
                "signals_generated": self.stats.signals_generated,
                "daily_pnl": self.stats.daily_pnl,
                "total_pnl": self.stats.total_pnl,
                "win_rate": self.stats.win_rate,
                "open_positions": self.stats.open_positions,
                "errors_count": self.stats.errors_count,
                "cycles_completed": self.stats.cycles_completed,
                "last_cycle_time": self.stats.last_cycle_time.isoformat() if self.stats.last_cycle_time else None,
                "symbols_analyzed": self.stats.symbols_analyzed,
                "orders_submitted": self.stats.orders_submitted,
                "orders_filled": self.stats.orders_filled,
                "orders_rejected": self.stats.orders_rejected,
                "last_trade_time": self.stats.last_trade_time.isoformat() if self.stats.last_trade_time else None,
                "trade_history": [
                    {
                        "timestamp": t.timestamp,
                        "symbol": t.symbol,
                        "side": t.side,
                        "quantity": t.quantity,
                        "price": t.price,
                        "order_id": t.order_id,
                        "broker": t.broker,
                        "reasoning": t.reasoning,
                        "confidence": t.confidence,
                    }
                    for t in self.stats.trade_history[-20:]  # Last 20 trades
                ],
            },
        }
    
    def get_activity_log(self, limit: int = 50) -> list[dict]:
        """Get recent activity log entries for this bot."""
        return get_bot_activity_log(self.id, limit)

