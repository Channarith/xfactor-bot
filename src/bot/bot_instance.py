"""
Individual bot instance that runs in its own thread.
"""

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Callable
import uuid

from loguru import logger


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
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BotConfig":
        # Handle instrument_type conversion
        if "instrument_type" in data and isinstance(data["instrument_type"], str):
            data["instrument_type"] = InstrumentType(data["instrument_type"])
        return cls(**data)


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
        """Execute one trading cycle."""
        # This is where the actual trading logic would run
        # For now, it's a placeholder that would integrate with:
        # - Market data
        # - Strategy analysis
        # - Signal generation
        # - Order execution
        
        for symbol in self.config.symbols:
            # Simulate signal generation
            # In production, this would call the actual strategies
            pass
    
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
            },
        }

