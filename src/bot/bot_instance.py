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

import numpy as np
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
# Use threading.Semaphore for cross-thread concurrency control
# asyncio.Semaphore doesn't work across event loops in different threads
_yfinance_semaphore: Optional[threading.Semaphore] = None  # Limit concurrent yfinance calls


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


# =============================================================================
# STRATEGY-SPECIFIC THRESHOLD PRESETS
# =============================================================================
# Different bot types need different signal thresholds:
# - Dividend bots: Conservative, need fewer signals
# - Momentum bots: Aggressive, quick entry/exit
# - Swing bots: Moderate thresholds
# - Scalping: Ultra-sensitive
# =============================================================================

class SignalPreset:
    """Preset signal thresholds for different trading styles."""
    
    # CONSERVATIVE - Dividend/Value bots (fewer symbols, careful entry)
    # These bots focus on stable income, need fewer confirming signals
    CONSERVATIVE = {
        "buy_signal_threshold": 1.5,       # Lower bar to enter
        "strong_buy_threshold": 3.0,       # Lower bar for strong signal
        "sell_signal_threshold": -1.5,     # Quicker to protect gains
        "strong_sell_threshold": -3.0,
        "trade_frequency_seconds": 300,    # 5 min checks
    }
    
    # MODERATE - ETF Swing, Mean Reversion bots
    # Balanced approach for medium-term trades
    MODERATE = {
        "buy_signal_threshold": 2.0,
        "strong_buy_threshold": 4.0,
        "sell_signal_threshold": -2.0,
        "strong_sell_threshold": -4.0,
        "trade_frequency_seconds": 120,    # 2 min checks
    }
    
    # AGGRESSIVE - Momentum, Tech, High Volatility bots
    # Need stronger confirmation to avoid whipsaws
    AGGRESSIVE = {
        "buy_signal_threshold": 2.5,
        "strong_buy_threshold": 4.8,
        "sell_signal_threshold": -2.5,
        "strong_sell_threshold": -4.8,
        "trade_frequency_seconds": 60,     # 1 min checks
    }
    
    # ULTRA_AGGRESSIVE - Scalping, 0DTE options, Meme coins
    # Very quick trades, sensitive signals
    ULTRA_AGGRESSIVE = {
        "buy_signal_threshold": 1.0,       # Very low bar
        "strong_buy_threshold": 2.5,
        "sell_signal_threshold": -1.0,
        "strong_sell_threshold": -2.5,
        "trade_frequency_seconds": 15,     # 15 sec checks
    }
    
    # NEWS_DRIVEN - News sentiment bots
    # Sensitive to news, quick reaction needed
    NEWS_DRIVEN = {
        "buy_signal_threshold": 1.5,
        "strong_buy_threshold": 3.5,
        "sell_signal_threshold": -1.5,
        "strong_sell_threshold": -3.5,
        "trade_frequency_seconds": 30,     # 30 sec checks
    }
    
    # INCOME - Dividend, Bond, REIT bots
    # Very conservative, focus on stability
    INCOME = {
        "buy_signal_threshold": 1.2,       # Easy entry for income positions
        "strong_buy_threshold": 2.5,
        "sell_signal_threshold": -2.5,     # Reluctant to sell income positions
        "strong_sell_threshold": -4.0,
        "trade_frequency_seconds": 600,    # 10 min checks (long-term focus)
    }
    
    # CRYPTO - 24/7 trading, high volatility
    CRYPTO = {
        "buy_signal_threshold": 1.8,
        "strong_buy_threshold": 3.5,
        "sell_signal_threshold": -1.8,
        "strong_sell_threshold": -3.5,
        "trade_frequency_seconds": 30,
    }
    
    # COMMODITY - Macro-driven, geopolitical sensitive
    COMMODITY = {
        "buy_signal_threshold": 1.5,
        "strong_buy_threshold": 3.5,
        "sell_signal_threshold": -1.5,
        "strong_sell_threshold": -3.5,
        "trade_frequency_seconds": 180,
    }
    
    @classmethod
    def get_preset(cls, preset_name: str) -> dict:
        """Get preset by name (case-insensitive)."""
        presets = {
            "conservative": cls.CONSERVATIVE,
            "moderate": cls.MODERATE,
            "aggressive": cls.AGGRESSIVE,
            "ultra_aggressive": cls.ULTRA_AGGRESSIVE,
            "news_driven": cls.NEWS_DRIVEN,
            "income": cls.INCOME,
            "crypto": cls.CRYPTO,
            "commodity": cls.COMMODITY,
        }
        return presets.get(preset_name.lower(), cls.MODERATE)
    
    @classmethod
    def suggest_preset(cls, strategies: list, instrument_type: str = "stock") -> dict:
        """Suggest appropriate preset based on strategies and instrument type."""
        strategies_lower = [s.lower() for s in strategies]
        
        # Crypto instruments
        if instrument_type == "crypto":
            return cls.CRYPTO
        
        # Commodity instruments
        if instrument_type == "commodity":
            return cls.COMMODITY
        
        # Scalping / 0DTE
        if "scalping" in strategies_lower or any("0dte" in s.lower() for s in strategies):
            return cls.ULTRA_AGGRESSIVE
        
        # News-driven
        if "newssentiment" in strategies_lower or "socialsentiment" in strategies_lower:
            return cls.NEWS_DRIVEN
        
        # Momentum / High volatility
        if "momentum" in strategies_lower:
            if "technical" in strategies_lower:
                return cls.AGGRESSIVE
            return cls.AGGRESSIVE
        
        # Mean Reversion / Swing
        if "meanreversion" in strategies_lower or "swingtrading" in strategies_lower:
            return cls.MODERATE
        
        # Dividend / Income
        if any(kw in " ".join(strategies_lower) for kw in ["dividend", "income", "bond"]):
            return cls.INCOME
        
        # Trend following
        if "trendfollowing" in strategies_lower:
            return cls.MODERATE
        
        # Default to moderate
        return cls.MODERATE


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
    
    # Risk parameters (per bot) - Dynamic based on broker limits
    max_position_size: float = 0.0       # 0 = auto-calculate as 10% of broker limit
    max_position_pct: float = 10.0       # % of broker buying power per position
    max_positions: int = 50              # Allow up to 50 positions per bot
    max_daily_loss_pct: float = 3.0      # Allow 3% daily loss
    
    # Execution settings
    trade_frequency_seconds: int = 30    # Check every 30 seconds (was 60)
    use_paper_trading: bool = True
    
    # Signal sensitivity (LOWER = MORE TRADES)
    buy_signal_threshold: float = 2.0      # Points needed for BUY signal
    strong_buy_threshold: float = 4.8      # Points needed for STRONG BUY (user requested)
    sell_signal_threshold: float = -2.0    # Points needed for SELL signal
    strong_sell_threshold: float = -4.8    # Points needed for STRONG SELL
    
    # Extended hours trading
    enable_extended_hours: bool = True  # Allow pre-market and after-hours trading
    enable_premarket: bool = True       # 4:00 AM - 9:30 AM ET
    enable_afterhours: bool = True      # 4:00 PM - 8:00 PM ET
    
    # Fractional trading
    enable_fractional_shares: bool = True  # Allow buying fractional shares (broker dependent)
    min_trade_amount: float = 1.0          # Minimum $ amount per trade (for fractional)
    
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
            "max_position_pct": self.max_position_pct,
            "max_positions": self.max_positions,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "trade_frequency_seconds": self.trade_frequency_seconds,
            "use_paper_trading": self.use_paper_trading,
            # Signal thresholds (per-bot overrides)
            "buy_signal_threshold": self.buy_signal_threshold,
            "strong_buy_threshold": self.strong_buy_threshold,
            "sell_signal_threshold": self.sell_signal_threshold,
            "strong_sell_threshold": self.strong_sell_threshold,
            # Extended hours
            "enable_extended_hours": self.enable_extended_hours,
            "enable_premarket": self.enable_premarket,
            "enable_afterhours": self.enable_afterhours,
            # Fractional
            "enable_fractional_shares": self.enable_fractional_shares,
            "min_trade_amount": self.min_trade_amount,
            # News
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
                    # Calculate position size based on % of buying power
                    # If max_position_size is 0, use percentage-based calculation
                    if self.config.max_position_size > 0:
                        max_position = min(
                            self.config.max_position_size,
                            buying_power * (self.config.max_position_pct / 100)
                        )
                    else:
                        # Dynamic: use configured percentage of buying power
                        max_position = buying_power * (self.config.max_position_pct / 100)
                    
                    # Support fractional shares if enabled
                    if self.config.enable_fractional_shares and price > 0:
                        # Calculate fractional quantity (round to 6 decimal places)
                        quantity = round(max_position / price, 6)
                        # Ensure minimum trade amount
                        if quantity * price < self.config.min_trade_amount:
                            quantity = round(self.config.min_trade_amount / price, 6)
                    else:
                        # Whole shares only
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
            
            # Fetch sentiment indicators (news, social, top traders)
            sentiment = await self._get_sentiment_indicators(symbol)
            
            # Merge sentiment into indicators for logging
            indicators.update(sentiment)
            
            # Generate signal based on indicator confluence (18 indicators)
            signal_type, confidence, reasoning = self._evaluate_indicators(indicators, sentiment)
            
            if signal_type == 'hold':
                return None
            
            # Count contributing indicators
            indicator_count = sum(1 for k, v in indicators.items() if isinstance(v, bool) and v)
            
            return {
                'type': signal_type,
                'symbol': symbol,
                'price': current_price,
                'confidence': confidence,
                'strategy': 'multi_indicator_18',
                'indicators': indicators,
                'reasoning': reasoning,
                'timestamp': datetime.now().isoformat(),
                'indicator_count': indicator_count,
            }
            
        except Exception as e:
            self._log_activity("signal_error", f"Error generating signal for {symbol}: {e}", {
                "symbol": symbol,
                "error": str(e),
            })
            return None
    
    async def _get_cached_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get market data with caching and automatic provider failover.
        
        Uses MarketDataManager which tries multiple providers:
        1. yfinance (primary)
        2. Yahoo Finance direct HTTP (fallback)
        3. Alpha Vantage (if configured)
        
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
        
        # Initialize semaphore if needed (limit concurrent calls)
        # Use threading.Semaphore since bots run in different threads with different event loops
        if _yfinance_semaphore is None:
            _yfinance_semaphore = threading.Semaphore(3)  # Max 3 concurrent requests
        
        # Fetch with semaphore to limit concurrency (blocking acquire, not async)
        _yfinance_semaphore.acquire()
        try:
            # Double-check cache after acquiring semaphore
            with _market_data_lock:
                if cache_key in _market_data_cache:
                    entry = _market_data_cache[cache_key]
                    age = (now - entry["timestamp"]).total_seconds()
                    if age < _market_data_cache_ttl:
                        return entry.get("data")
            
            # Try using market data manager with failover
            try:
                from src.data.market_data_providers import get_market_data_manager
                
                manager = get_market_data_manager()
                bars = await manager.get_history(symbol, period="60d", interval="1d")
                
                if bars:
                    # Convert bars to DataFrame format expected by indicators
                    df = pd.DataFrame([
                        {
                            'Open': b.open,
                            'High': b.high,
                            'Low': b.low,
                            'Close': b.close,
                            'Volume': b.volume,
                        }
                        for b in bars
                    ])
                    df.index = pd.to_datetime([b.timestamp for b in bars])
                    
                    with _market_data_lock:
                        _market_data_cache[cache_key] = {
                            "data": df,
                            "timestamp": datetime.now(),
                            "error": None,
                        }
                    
                    return df
                    
            except Exception as e:
                logger.debug(f"Market data manager failed for {symbol}: {e}")
            
            # Fallback: Try yfinance directly
            try:
                import yfinance as yf
                
                loop = asyncio.get_event_loop()
                hist = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: yf.Ticker(symbol).history(period="60d", interval="1d")),
                    timeout=15
                )
                
                with _market_data_lock:
                    _market_data_cache[cache_key] = {
                        "data": hist if not hist.empty else None,
                        "timestamp": datetime.now(),
                        "error": None,
                    }
                
                return hist if not hist.empty else None
                
            except asyncio.TimeoutError:
                logger.warning(f"Market data timeout for {symbol}")
                with _market_data_lock:
                    _market_data_cache[cache_key] = {
                        "data": None,
                        "timestamp": datetime.now(),
                        "error": "timeout",
                    }
                return None
                
            except Exception as e:
                logger.warning(f"Market data error for {symbol}: {e}")
                with _market_data_lock:
                    _market_data_cache[cache_key] = {
                        "data": None,
                        "timestamp": datetime.now(),
                        "error": str(e),
                    }
                return None
        finally:
            # Always release the semaphore
            _yfinance_semaphore.release()
    
    def _calculate_indicators(self, data: pd.DataFrame) -> Optional[dict]:
        """
        Calculate 18 indicators across 6 categories for comprehensive signal generation.
        
        Categories:
        1. Momentum Indicators (RSI, Stochastic, Williams %R)
        2. Trend Indicators (MA Crossover, ADX, Parabolic SAR)
        3. Volatility Indicators (Bollinger Bands, ATR, Keltner Channels)
        4. Volume Indicators (OBV, Volume Ratio, VWAP)
        5. Chart Patterns (Pivot Points, Support/Resistance, Price Channels)
        6. Market Sentiment (fetched separately - news, social, top traders)
        """
        try:
            close = data['Close']
            high = data['High']
            low = data['Low']
            volume = data['Volume']
            current_price = close.iloc[-1]
            
            # =====================================================================
            # 1. MOMENTUM INDICATORS
            # =====================================================================
            
            # 1a. RSI (14-period)
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # 1b. Stochastic Oscillator (14-period)
            low_14 = low.rolling(window=14).min()
            high_14 = high.rolling(window=14).max()
            stoch_k = ((close - low_14) / (high_14 - low_14)) * 100
            stoch_d = stoch_k.rolling(window=3).mean()
            current_stoch_k = stoch_k.iloc[-1]
            current_stoch_d = stoch_d.iloc[-1]
            stoch_bullish = current_stoch_k < 20 and current_stoch_k > current_stoch_d
            stoch_bearish = current_stoch_k > 80 and current_stoch_k < current_stoch_d
            
            # 1c. Williams %R
            williams_r = ((high_14 - close) / (high_14 - low_14)) * -100
            current_williams = williams_r.iloc[-1]
            williams_bullish = current_williams < -80  # Oversold
            williams_bearish = current_williams > -20  # Overbought
            
            # =====================================================================
            # 2. TREND INDICATORS
            # =====================================================================
            
            # 2a. Moving Averages (SMA 20, 50, 200)
            sma_20 = close.rolling(window=20).mean().iloc[-1]
            sma_50 = close.rolling(window=50).mean().iloc[-1] if len(close) >= 50 else sma_20
            sma_200 = close.rolling(window=200).mean().iloc[-1] if len(close) >= 200 else sma_50
            ma_bullish = current_price > sma_20 > sma_50
            ma_bearish = current_price < sma_20 < sma_50
            golden_cross = sma_50 > sma_200 and sma_20 > sma_50
            death_cross = sma_50 < sma_200 and sma_20 < sma_50
            
            # 2b. MACD
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
            
            # 2c. ADX (Average Directional Index) - Trend Strength
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_14 = true_range.rolling(window=14).mean()
            
            plus_dm = high.diff()
            minus_dm = -low.diff()
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
            
            plus_di = 100 * (plus_dm.rolling(14).mean() / atr_14)
            minus_di = 100 * (minus_dm.rolling(14).mean() / atr_14)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(14).mean()
            current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 25
            strong_trend = current_adx > 25
            
            # =====================================================================
            # 3. VOLATILITY INDICATORS
            # =====================================================================
            
            # 3a. Bollinger Bands
            bb_sma = close.rolling(window=20).mean()
            bb_std = close.rolling(window=20).std()
            bb_upper = bb_sma + (bb_std * 2)
            bb_lower = bb_sma - (bb_std * 2)
            current_bb_upper = bb_upper.iloc[-1]
            current_bb_lower = bb_lower.iloc[-1]
            bb_position = (current_price - current_bb_lower) / (current_bb_upper - current_bb_lower) if (current_bb_upper - current_bb_lower) > 0 else 0.5
            bb_squeeze = (current_bb_upper - current_bb_lower) < bb_std.iloc[-1] * 3  # Volatility squeeze
            
            # 3b. ATR (Average True Range) - Volatility measure
            current_atr = atr_14.iloc[-1]
            atr_pct = (current_atr / current_price) * 100  # ATR as % of price
            high_volatility = atr_pct > 3
            
            # 3c. Keltner Channels
            keltner_mid = close.ewm(span=20).mean()
            keltner_upper = keltner_mid + (atr_14 * 2)
            keltner_lower = keltner_mid - (atr_14 * 2)
            above_keltner = current_price > keltner_upper.iloc[-1]
            below_keltner = current_price < keltner_lower.iloc[-1]
            
            # =====================================================================
            # 4. VOLUME INDICATORS
            # =====================================================================
            
            # 4a. Volume Ratio
            avg_volume = volume.rolling(window=20).mean().iloc[-1]
            current_volume = volume.iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volume_surge = volume_ratio > 2.0
            
            # 4b. OBV (On-Balance Volume) - Volume trend
            obv = (volume * (~close.diff().le(0) * 2 - 1)).cumsum()
            obv_sma = obv.rolling(window=20).mean()
            obv_bullish = obv.iloc[-1] > obv_sma.iloc[-1]
            obv_bearish = obv.iloc[-1] < obv_sma.iloc[-1]
            
            # 4c. VWAP (Volume Weighted Average Price) - Intraday fair value
            typical_price = (high + low + close) / 3
            vwap = (typical_price * volume).cumsum() / volume.cumsum()
            current_vwap = vwap.iloc[-1]
            above_vwap = current_price > current_vwap
            below_vwap = current_price < current_vwap
            
            # =====================================================================
            # 5. CHART PATTERNS & PIVOTS
            # =====================================================================
            
            # 5a. Pivot Points (Classic)
            prev_high = high.iloc[-2]
            prev_low = low.iloc[-2]
            prev_close = close.iloc[-2]
            pivot = (prev_high + prev_low + prev_close) / 3
            r1 = (2 * pivot) - prev_low
            s1 = (2 * pivot) - prev_high
            r2 = pivot + (prev_high - prev_low)
            s2 = pivot - (prev_high - prev_low)
            
            near_support = current_price <= s1 * 1.02  # Within 2% of S1
            near_resistance = current_price >= r1 * 0.98  # Within 2% of R1
            
            # 5b. Price Channels (Donchian Channels)
            channel_high = high.rolling(window=20).max().iloc[-1]
            channel_low = low.rolling(window=20).min().iloc[-1]
            channel_breakout_up = current_price >= channel_high
            channel_breakout_down = current_price <= channel_low
            
            # 5c. Momentum (5-day and 10-day returns)
            momentum_5d = (current_price - close.iloc[-5]) / close.iloc[-5] * 100 if len(close) >= 5 else 0
            momentum_10d = (current_price - close.iloc[-10]) / close.iloc[-10] * 100 if len(close) >= 10 else 0
            
            # 5d. Rate of Change (ROC)
            roc = ((current_price - close.iloc[-10]) / close.iloc[-10]) * 100 if len(close) >= 10 else 0
            
            # =====================================================================
            # 6. MARKET SENTIMENT (placeholder - fetched async)
            # =====================================================================
            # These are populated by _get_sentiment_indicators() method
            
            return {
                # Momentum
                'rsi': round(current_rsi, 2),
                'stoch_k': round(current_stoch_k, 2),
                'stoch_d': round(current_stoch_d, 2),
                'stoch_bullish': stoch_bullish,
                'stoch_bearish': stoch_bearish,
                'williams_r': round(current_williams, 2),
                'williams_bullish': williams_bullish,
                'williams_bearish': williams_bearish,
                
                # Trend
                'price': round(current_price, 2),
                'sma_20': round(sma_20, 2),
                'sma_50': round(sma_50, 2),
                'sma_200': round(sma_200, 2),
                'ma_bullish': ma_bullish,
                'ma_bearish': ma_bearish,
                'golden_cross': golden_cross,
                'death_cross': death_cross,
                'macd': round(current_macd, 4),
                'macd_signal': round(current_signal, 4),
                'macd_histogram': round(current_histogram, 4),
                'macd_bullish': macd_bullish,
                'macd_bearish': macd_bearish,
                'adx': round(current_adx, 2),
                'strong_trend': strong_trend,
                
                # Volatility
                'bb_position': round(bb_position, 2),
                'bb_upper': round(current_bb_upper, 2),
                'bb_lower': round(current_bb_lower, 2),
                'bb_squeeze': bb_squeeze,
                'atr': round(current_atr, 2),
                'atr_pct': round(atr_pct, 2),
                'high_volatility': high_volatility,
                'above_keltner': above_keltner,
                'below_keltner': below_keltner,
                
                # Volume
                'volume_ratio': round(volume_ratio, 2),
                'volume_surge': volume_surge,
                'obv_bullish': obv_bullish,
                'obv_bearish': obv_bearish,
                'vwap': round(current_vwap, 2),
                'above_vwap': above_vwap,
                'below_vwap': below_vwap,
                
                # Pivots & Patterns
                'pivot': round(pivot, 2),
                'r1': round(r1, 2),
                's1': round(s1, 2),
                'r2': round(r2, 2),
                's2': round(s2, 2),
                'near_support': near_support,
                'near_resistance': near_resistance,
                'channel_breakout_up': channel_breakout_up,
                'channel_breakout_down': channel_breakout_down,
                'momentum_5d': round(momentum_5d, 2),
                'momentum_10d': round(momentum_10d, 2),
                'roc': round(roc, 2),
            }
            
            # =====================================================================
            # 7. CHART PATTERNS (detect classic patterns)
            # =====================================================================
            chart_patterns = self._detect_chart_patterns(data)
            result.update(chart_patterns)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return None
    
    def _detect_chart_patterns(self, data: pd.DataFrame) -> dict:
        """
        Detect classic chart patterns in price data.
        
        Bullish Patterns:
        - Inverted Head & Shoulders
        - Falling Wedge
        - Bullish Flag
        - Cup and Handle
        - Double Bottom
        - Ascending Triangle
        
        Bearish Patterns:
        - Head & Shoulders
        - Rising Wedge
        - Bearish Flag
        - Double Top
        - Descending Triangle
        - Expanding Triangle
        
        Neutral Patterns (breakout direction unknown):
        - Pennant
        - Symmetrical Triangle
        """
        try:
            close = data['Close'].values
            high = data['High'].values
            low = data['Low'].values
            n = len(close)
            
            if n < 20:
                return self._empty_patterns()
            
            patterns = {
                'pattern_detected': False,
                'pattern_name': None,
                'pattern_type': None,  # 'bullish', 'bearish', 'neutral'
                'pattern_confidence': 0,
                'pattern_description': None,
            }
            
            detected = []
            
            # Find local highs and lows (pivots)
            highs, lows = self._find_pivots(high, low, close)
            
            # =====================================================================
            # BULLISH PATTERNS
            # =====================================================================
            
            # 1. Double Bottom (W pattern)
            if len(lows) >= 2:
                last_lows = lows[-2:]
                if abs(last_lows[0][1] - last_lows[1][1]) / last_lows[0][1] < 0.03:  # Within 3%
                    if last_lows[1][0] - last_lows[0][0] >= 5:  # At least 5 bars apart
                        neckline = max(close[last_lows[0][0]:last_lows[1][0]])
                        if close[-1] > neckline:
                            detected.append({
                                'name': 'Double Bottom',
                                'type': 'bullish',
                                'confidence': 0.75,
                                'description': f'W-pattern with neckline break at ${neckline:.2f}'
                            })
            
            # 2. Inverted Head and Shoulders
            if len(lows) >= 3:
                last_lows = lows[-3:]
                head = last_lows[1][1]  # Middle should be lowest
                left_shoulder = last_lows[0][1]
                right_shoulder = last_lows[2][1]
                
                if head < left_shoulder and head < right_shoulder:
                    if abs(left_shoulder - right_shoulder) / left_shoulder < 0.05:  # Shoulders within 5%
                        neckline = (high[last_lows[0][0]] + high[last_lows[2][0]]) / 2
                        if close[-1] > neckline:
                            detected.append({
                                'name': 'Inverted Head & Shoulders',
                                'type': 'bullish',
                                'confidence': 0.85,
                                'description': f'Classic reversal pattern, neckline at ${neckline:.2f}'
                            })
            
            # 3. Falling Wedge (bullish)
            if n >= 15:
                upper_trend = self._calculate_trendline(high[-15:], 'upper')
                lower_trend = self._calculate_trendline(low[-15:], 'lower')
                
                if upper_trend['slope'] < 0 and lower_trend['slope'] < 0:
                    if upper_trend['slope'] < lower_trend['slope']:  # Converging downward
                        if close[-1] > upper_trend['end_value']:
                            detected.append({
                                'name': 'Falling Wedge Breakout',
                                'type': 'bullish',
                                'confidence': 0.80,
                                'description': 'Bullish breakout from falling wedge'
                            })
            
            # 4. Bullish Flag
            if n >= 10:
                # Strong uptrend before flag (pole)
                pole_start = -15 if n >= 15 else -n
                pole_move = (close[-10] - close[pole_start]) / close[pole_start] * 100
                
                if pole_move > 5:  # At least 5% upward pole
                    # Flag consolidation (lower highs and lows but shallow)
                    recent_range = (max(high[-5:]) - min(low[-5:])) / close[-5] * 100
                    if recent_range < 3 and close[-1] > close[-2]:  # Tight consolidation breaking up
                        detected.append({
                            'name': 'Bullish Flag',
                            'type': 'bullish',
                            'confidence': 0.70,
                            'description': f'Flag after {pole_move:.1f}% rally, breaking out'
                        })
            
            # 5. Ascending Triangle
            if len(highs) >= 3 and len(lows) >= 3:
                recent_highs = [h[1] for h in highs[-3:]]
                recent_lows = [l[1] for l in lows[-3:]]
                
                # Flat top, rising bottom
                high_range = (max(recent_highs) - min(recent_highs)) / max(recent_highs)
                low_trend = recent_lows[-1] > recent_lows[0]
                
                if high_range < 0.02 and low_trend:  # Flat resistance, rising support
                    resistance = max(recent_highs)
                    if close[-1] > resistance:
                        detected.append({
                            'name': 'Ascending Triangle Breakout',
                            'type': 'bullish',
                            'confidence': 0.75,
                            'description': f'Breakout above ${resistance:.2f} resistance'
                        })
            
            # 6. Cup and Handle
            if n >= 30:
                mid_point = n // 2
                left_high = max(high[:mid_point])
                cup_low = min(low[mid_point-5:mid_point+5])
                right_high = max(high[mid_point:])
                
                if abs(left_high - right_high) / left_high < 0.05:  # Similar highs
                    if cup_low < left_high * 0.85:  # Cup depth at least 15%
                        # Handle is recent small pullback
                        handle_pullback = (max(high[-10:-3]) - close[-1]) / max(high[-10:-3])
                        if 0.02 < handle_pullback < 0.10:
                            detected.append({
                                'name': 'Cup and Handle',
                                'type': 'bullish',
                                'confidence': 0.80,
                                'description': f'Classic accumulation pattern forming'
                            })
            
            # =====================================================================
            # BEARISH PATTERNS
            # =====================================================================
            
            # 7. Double Top (M pattern)
            if len(highs) >= 2:
                last_highs = highs[-2:]
                if abs(last_highs[0][1] - last_highs[1][1]) / last_highs[0][1] < 0.03:
                    if last_highs[1][0] - last_highs[0][0] >= 5:
                        neckline = min(close[last_highs[0][0]:last_highs[1][0]])
                        if close[-1] < neckline:
                            detected.append({
                                'name': 'Double Top',
                                'type': 'bearish',
                                'confidence': 0.75,
                                'description': f'M-pattern with neckline break at ${neckline:.2f}'
                            })
            
            # 8. Head and Shoulders
            if len(highs) >= 3:
                last_highs = highs[-3:]
                head = last_highs[1][1]
                left_shoulder = last_highs[0][1]
                right_shoulder = last_highs[2][1]
                
                if head > left_shoulder and head > right_shoulder:
                    if abs(left_shoulder - right_shoulder) / left_shoulder < 0.05:
                        neckline = (low[last_highs[0][0]] + low[last_highs[2][0]]) / 2
                        if close[-1] < neckline:
                            detected.append({
                                'name': 'Head & Shoulders',
                                'type': 'bearish',
                                'confidence': 0.85,
                                'description': f'Classic reversal, neckline broken at ${neckline:.2f}'
                            })
            
            # 9. Rising Wedge (bearish)
            if n >= 15:
                upper_trend = self._calculate_trendline(high[-15:], 'upper')
                lower_trend = self._calculate_trendline(low[-15:], 'lower')
                
                if upper_trend['slope'] > 0 and lower_trend['slope'] > 0:
                    if upper_trend['slope'] < lower_trend['slope']:  # Converging upward
                        if close[-1] < lower_trend['end_value']:
                            detected.append({
                                'name': 'Rising Wedge Breakdown',
                                'type': 'bearish',
                                'confidence': 0.80,
                                'description': 'Bearish breakdown from rising wedge'
                            })
            
            # 10. Bearish Flag
            if n >= 10:
                pole_start = -15 if n >= 15 else -n
                pole_move = (close[-10] - close[pole_start]) / close[pole_start] * 100
                
                if pole_move < -5:  # At least 5% downward pole
                    recent_range = (max(high[-5:]) - min(low[-5:])) / close[-5] * 100
                    if recent_range < 3 and close[-1] < close[-2]:
                        detected.append({
                            'name': 'Bearish Flag',
                            'type': 'bearish',
                            'confidence': 0.70,
                            'description': f'Flag after {abs(pole_move):.1f}% drop, breaking down'
                        })
            
            # 11. Descending Triangle
            if len(highs) >= 3 and len(lows) >= 3:
                recent_highs = [h[1] for h in highs[-3:]]
                recent_lows = [l[1] for l in lows[-3:]]
                
                low_range = (max(recent_lows) - min(recent_lows)) / max(recent_lows)
                high_trend = recent_highs[-1] < recent_highs[0]
                
                if low_range < 0.02 and high_trend:  # Flat support, falling resistance
                    support = min(recent_lows)
                    if close[-1] < support:
                        detected.append({
                            'name': 'Descending Triangle Breakdown',
                            'type': 'bearish',
                            'confidence': 0.75,
                            'description': f'Breakdown below ${support:.2f} support'
                        })
            
            # 12. Expanding Triangle (bearish - indicates instability)
            if len(highs) >= 3 and len(lows) >= 3:
                recent_highs = [h[1] for h in highs[-3:]]
                recent_lows = [l[1] for l in lows[-3:]]
                
                highs_expanding = recent_highs[-1] > recent_highs[0]
                lows_expanding = recent_lows[-1] < recent_lows[0]
                
                if highs_expanding and lows_expanding:
                    detected.append({
                        'name': 'Expanding Triangle',
                        'type': 'bearish',
                        'confidence': 0.65,
                        'description': 'Volatility expansion pattern (often bearish)'
                    })
            
            # =====================================================================
            # NEUTRAL PATTERNS (breakout direction unknown)
            # =====================================================================
            
            # 13. Symmetrical Triangle
            if len(highs) >= 3 and len(lows) >= 3:
                recent_highs = [h[1] for h in highs[-3:]]
                recent_lows = [l[1] for l in lows[-3:]]
                
                highs_falling = recent_highs[-1] < recent_highs[0]
                lows_rising = recent_lows[-1] > recent_lows[0]
                
                if highs_falling and lows_rising:
                    apex = (recent_highs[-1] + recent_lows[-1]) / 2
                    detected.append({
                        'name': 'Symmetrical Triangle',
                        'type': 'neutral',
                        'confidence': 0.60,
                        'description': f'Converging pattern, apex near ${apex:.2f}'
                    })
            
            # 14. Pennant
            if n >= 8:
                # Sharp move followed by tight consolidation
                pre_move = abs(close[-8] - close[-5]) / close[-8] * 100
                recent_range = (max(high[-4:]) - min(low[-4:])) / close[-4] * 100
                
                if pre_move > 4 and recent_range < 2:
                    direction = 'bullish' if close[-5] > close[-8] else 'bearish'
                    detected.append({
                        'name': 'Pennant',
                        'type': direction,
                        'confidence': 0.65,
                        'description': f'Tight pennant after {pre_move:.1f}% move'
                    })
            
            # Select highest confidence pattern
            if detected:
                best = max(detected, key=lambda x: x['confidence'])
                patterns['pattern_detected'] = True
                patterns['pattern_name'] = best['name']
                patterns['pattern_type'] = best['type']
                patterns['pattern_confidence'] = best['confidence']
                patterns['pattern_description'] = best['description']
                patterns['all_patterns'] = detected
            
            return patterns
            
        except Exception as e:
            logger.debug(f"Pattern detection error: {e}")
            return self._empty_patterns()
    
    def _empty_patterns(self) -> dict:
        """Return empty pattern dict."""
        return {
            'pattern_detected': False,
            'pattern_name': None,
            'pattern_type': None,
            'pattern_confidence': 0,
            'pattern_description': None,
            'all_patterns': [],
        }
    
    def _find_pivots(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, window: int = 3) -> tuple:
        """Find local high and low pivot points."""
        highs = []
        lows = []
        n = len(close)
        
        for i in range(window, n - window):
            # Local high
            if high[i] == max(high[i-window:i+window+1]):
                highs.append((i, high[i]))
            # Local low
            if low[i] == min(low[i-window:i+window+1]):
                lows.append((i, low[i]))
        
        return highs, lows
    
    def _calculate_trendline(self, prices: np.ndarray, line_type: str) -> dict:
        """Calculate simple trendline slope and values."""
        import numpy as np
        n = len(prices)
        x = np.arange(n)
        
        # Simple linear regression
        slope = (prices[-1] - prices[0]) / n if n > 0 else 0
        
        return {
            'slope': slope,
            'start_value': prices[0],
            'end_value': prices[-1],
        }
    
    async def _get_sentiment_indicators(self, symbol: str) -> dict:
        """
        Fetch sentiment indicators from news, social media, and top traders.
        
        Returns sentiment scores for:
        - News sentiment (-1 to 1)
        - Social media buzz (0 to 100)
        - Top trader activity (bullish/bearish count)
        - Insider trading signals
        """
        try:
            from src.data.momentum_screener import get_momentum_screener
            from src.data.news_momentum import get_news_momentum
            
            screener = get_momentum_screener()
            news_momentum = get_news_momentum()
            
            # Get news sentiment
            news_score = await news_momentum.get_symbol_sentiment(symbol)
            
            # Get social buzz score
            social_score = screener.get_social_score(symbol)
            
            # Get momentum score
            momentum_score = screener.get_momentum_score(symbol)
            
            return {
                'news_sentiment': news_score.get('sentiment', 0),
                'news_volume': news_score.get('article_count', 0),
                'news_bullish': news_score.get('sentiment', 0) > 0.3,
                'news_bearish': news_score.get('sentiment', 0) < -0.3,
                'social_buzz': social_score,
                'social_trending': social_score > 70,
                'momentum_rank': momentum_score.get('rank', 0),
                'momentum_bullish': momentum_score.get('score', 0) > 70,
            }
        except Exception as e:
            logger.debug(f"Could not fetch sentiment for {symbol}: {e}")
            return {
                'news_sentiment': 0,
                'news_volume': 0,
                'news_bullish': False,
                'news_bearish': False,
                'social_buzz': 0,
                'social_trending': False,
                'momentum_rank': 0,
                'momentum_bullish': False,
            }
    
    def _evaluate_indicators(self, indicators: dict, sentiment: dict = None) -> tuple[str, float, str]:
        """
        Evaluate 22+ indicators across 7 categories and return (signal_type, confidence, reasoning).
        
        Categories and their max contributions:
        1. Momentum Indicators (3 points): RSI, Stochastic, Williams %R
        2. Trend Indicators (4 points): MA Crossover, MACD, ADX, Golden/Death Cross
        3. Volatility Indicators (2 points): Bollinger Bands, Keltner Channels
        4. Volume Indicators (2 points): Volume Ratio, OBV, VWAP
        5. Technical Patterns (3 points): Pivots, Support/Resistance, Breakouts, Momentum
        6. Market Sentiment (4 points): News, Social Media, Top Traders
        7. Chart Patterns (4 points): H&S, Wedges, Flags, Triangles, Double Top/Bottom, Pennants
        
        Total max score: 22 points per side (bullish/bearish)
        """
        bullish_score = 0.0
        bearish_score = 0.0
        max_score = 22.0  # Maximum possible score (updated for chart patterns)
        
        # Track reasons for the decision
        bullish_reasons = []
        bearish_reasons = []
        
        sentiment = sentiment or {}
        
        # =====================================================================
        # 1. MOMENTUM INDICATORS (max 3 points)
        # =====================================================================
        
        # 1a. RSI (14-period)
        rsi = indicators.get('rsi', 50)
        if rsi < 30:
            bullish_score += 1.0
            bullish_reasons.append(f"📊 RSI oversold ({rsi:.1f}<30)")
        elif rsi > 70:
            bearish_score += 1.0
            bearish_reasons.append(f"📊 RSI overbought ({rsi:.1f}>70)")
        elif rsi < 40:
            bullish_score += 0.5
            bullish_reasons.append(f"RSI approaching oversold ({rsi:.1f})")
        elif rsi > 60:
            bearish_score += 0.5
            bearish_reasons.append(f"RSI approaching overbought ({rsi:.1f})")
        
        # 1b. Stochastic Oscillator
        if indicators.get('stoch_bullish'):
            bullish_score += 1.0
            stoch_k = indicators.get('stoch_k', 0)
            bullish_reasons.append(f"📈 Stochastic bullish crossover (K={stoch_k:.1f})")
        elif indicators.get('stoch_bearish'):
            bearish_score += 1.0
            stoch_k = indicators.get('stoch_k', 0)
            bearish_reasons.append(f"📉 Stochastic bearish crossover (K={stoch_k:.1f})")
        
        # 1c. Williams %R
        if indicators.get('williams_bullish'):
            bullish_score += 1.0
            williams = indicators.get('williams_r', 0)
            bullish_reasons.append(f"📊 Williams %R oversold ({williams:.1f})")
        elif indicators.get('williams_bearish'):
            bearish_score += 1.0
            williams = indicators.get('williams_r', 0)
            bearish_reasons.append(f"📊 Williams %R overbought ({williams:.1f})")
        
        # =====================================================================
        # 2. TREND INDICATORS (max 4 points)
        # =====================================================================
        
        # 2a. Moving Average Alignment
        if indicators.get('ma_bullish'):
            bullish_score += 1.0
            bullish_reasons.append("📈 Price > SMA20 > SMA50 (bullish MA stack)")
        elif indicators.get('ma_bearish'):
            bearish_score += 1.0
            bearish_reasons.append("📉 Price < SMA20 < SMA50 (bearish MA stack)")
        
        # 2b. Golden Cross / Death Cross
        if indicators.get('golden_cross'):
            bullish_score += 1.5
            bullish_reasons.append("⭐ GOLDEN CROSS detected (SMA50 > SMA200)")
        elif indicators.get('death_cross'):
            bearish_score += 1.5
            bearish_reasons.append("💀 DEATH CROSS detected (SMA50 < SMA200)")
        
        # 2c. MACD
        if indicators.get('macd_bullish'):
            bullish_score += 1.0
            bullish_reasons.append("📈 MACD bullish crossover, histogram rising")
        elif indicators.get('macd_bearish'):
            bearish_score += 1.0
            bearish_reasons.append("📉 MACD bearish crossover, histogram falling")
        
        # 2d. ADX Trend Strength
        adx = indicators.get('adx', 20)
        if indicators.get('strong_trend') and adx > 30:
            # Strong trend amplifies other signals
            if bullish_score > bearish_score:
                bullish_score += 0.5
                bullish_reasons.append(f"💪 Strong trend (ADX={adx:.1f})")
            elif bearish_score > bullish_score:
                bearish_score += 0.5
                bearish_reasons.append(f"💪 Strong downtrend (ADX={adx:.1f})")
        
        # =====================================================================
        # 3. VOLATILITY INDICATORS (max 2 points)
        # =====================================================================
        
        # 3a. Bollinger Bands
        bb_position = indicators.get('bb_position', 0.5)
        if bb_position < 0.15:
            bullish_score += 1.0
            bullish_reasons.append(f"📊 Price at lower Bollinger Band ({bb_position:.0%})")
        elif bb_position > 0.85:
            bearish_score += 1.0
            bearish_reasons.append(f"📊 Price at upper Bollinger Band ({bb_position:.0%})")
        elif bb_position < 0.3:
            bullish_score += 0.5
            bullish_reasons.append(f"Price near lower BB ({bb_position:.0%})")
        elif bb_position > 0.7:
            bearish_score += 0.5
            bearish_reasons.append(f"Price near upper BB ({bb_position:.0%})")
        
        # Bollinger Band squeeze (low volatility breakout potential)
        if indicators.get('bb_squeeze'):
            bullish_reasons.append("⚡ BB Squeeze (breakout imminent)")
        
        # 3b. Keltner Channels
        if indicators.get('below_keltner'):
            bullish_score += 1.0
            bullish_reasons.append("📉 Below Keltner Channel (oversold)")
        elif indicators.get('above_keltner'):
            bearish_score += 1.0
            bearish_reasons.append("📈 Above Keltner Channel (extended)")
        
        # =====================================================================
        # 4. VOLUME INDICATORS (max 2 points)
        # =====================================================================
        
        volume_ratio = indicators.get('volume_ratio', 1.0)
        
        # 4a. Volume Surge
        if indicators.get('volume_surge'):
            # High volume confirms direction
            if bullish_score > bearish_score:
                bullish_score += 0.5
                bullish_reasons.append(f"🔊 Volume surge confirms ({volume_ratio:.1f}x avg)")
            elif bearish_score > bullish_score:
                bearish_score += 0.5
                bearish_reasons.append(f"🔊 Volume surge confirms selling ({volume_ratio:.1f}x avg)")
        elif volume_ratio > 1.3:
            if bullish_score > bearish_score:
                bullish_score += 0.25
                bullish_reasons.append(f"📊 Above avg volume ({volume_ratio:.1f}x)")
        
        # 4b. OBV (On-Balance Volume)
        if indicators.get('obv_bullish'):
            bullish_score += 0.5
            bullish_reasons.append("📈 OBV rising (accumulation)")
        elif indicators.get('obv_bearish'):
            bearish_score += 0.5
            bearish_reasons.append("📉 OBV falling (distribution)")
        
        # 4c. VWAP
        if indicators.get('above_vwap'):
            bullish_score += 0.5
            vwap = indicators.get('vwap', 0)
            bullish_reasons.append(f"📈 Price above VWAP (${vwap:.2f})")
        elif indicators.get('below_vwap'):
            bearish_score += 0.5
            vwap = indicators.get('vwap', 0)
            bearish_reasons.append(f"📉 Price below VWAP (${vwap:.2f})")
        
        # =====================================================================
        # 5. CHART PATTERNS & PIVOTS (max 3 points)
        # =====================================================================
        
        # 5a. Pivot Point Support/Resistance
        if indicators.get('near_support'):
            bullish_score += 1.0
            s1 = indicators.get('s1', 0)
            bullish_reasons.append(f"🎯 Near pivot support S1 (${s1:.2f})")
        elif indicators.get('near_resistance'):
            bearish_score += 1.0
            r1 = indicators.get('r1', 0)
            bearish_reasons.append(f"🎯 Near pivot resistance R1 (${r1:.2f})")
        
        # 5b. Channel Breakouts (Donchian)
        if indicators.get('channel_breakout_up'):
            bullish_score += 1.0
            bullish_reasons.append("🚀 20-day high breakout!")
        elif indicators.get('channel_breakout_down'):
            bearish_score += 1.0
            bearish_reasons.append("💥 20-day low breakdown!")
        
        # 5c. Momentum (5-day and 10-day)
        momentum_5d = indicators.get('momentum_5d', 0)
        momentum_10d = indicators.get('momentum_10d', 0)
        if momentum_5d > 5 and momentum_10d > 8:
            bullish_score += 0.5
            bullish_reasons.append(f"🚀 Strong momentum (5d: +{momentum_5d:.1f}%, 10d: +{momentum_10d:.1f}%)")
        elif momentum_5d < -5 and momentum_10d < -8:
            bearish_score += 0.5
            bearish_reasons.append(f"📉 Weak momentum (5d: {momentum_5d:.1f}%, 10d: {momentum_10d:.1f}%)")
        elif momentum_5d > 3:
            bullish_score += 0.25
            bullish_reasons.append(f"📈 5-day momentum +{momentum_5d:.1f}%")
        elif momentum_5d < -3:
            bearish_score += 0.25
            bearish_reasons.append(f"📉 5-day momentum {momentum_5d:.1f}%")
        
        # 5d. Rate of Change (ROC)
        roc = indicators.get('roc', 0)
        if roc > 10:
            bullish_score += 0.5
            bullish_reasons.append(f"📈 High ROC (+{roc:.1f}%)")
        elif roc < -10:
            bearish_score += 0.5
            bearish_reasons.append(f"📉 Negative ROC ({roc:.1f}%)")
        
        # =====================================================================
        # 6. MARKET SENTIMENT (max 4 points)
        # =====================================================================
        
        # 6a. News Sentiment
        if sentiment.get('news_bullish'):
            bullish_score += 1.0
            news_sent = sentiment.get('news_sentiment', 0)
            bullish_reasons.append(f"📰 Positive news sentiment (+{news_sent:.2f})")
        elif sentiment.get('news_bearish'):
            bearish_score += 1.0
            news_sent = sentiment.get('news_sentiment', 0)
            bearish_reasons.append(f"📰 Negative news sentiment ({news_sent:.2f})")
        
        # 6b. Social Media Buzz
        if sentiment.get('social_trending'):
            social_buzz = sentiment.get('social_buzz', 0)
            bullish_score += 1.0
            bullish_reasons.append(f"🔥 Social media trending (buzz: {social_buzz})")
        
        # 6c. Top Trader / Momentum Following
        if sentiment.get('momentum_bullish'):
            bullish_score += 1.0
            rank = sentiment.get('momentum_rank', 0)
            bullish_reasons.append(f"👑 Top momentum rank #{rank}")
        
        # 6d. High news volume (catalyst)
        news_volume = sentiment.get('news_volume', 0)
        if news_volume >= 5:
            if bullish_score > bearish_score:
                bullish_score += 0.5
                bullish_reasons.append(f"📢 High news volume ({news_volume} articles)")
        
        # =====================================================================
        # 7. CHART PATTERNS (max 4 points)
        # =====================================================================
        
        if indicators.get('pattern_detected'):
            pattern_name = indicators.get('pattern_name', '')
            pattern_type = indicators.get('pattern_type', '')
            pattern_confidence = indicators.get('pattern_confidence', 0)
            pattern_desc = indicators.get('pattern_description', '')
            
            # Score based on pattern confidence and type
            pattern_score = pattern_confidence * 3  # Max ~2.5 points per pattern
            
            if pattern_type == 'bullish':
                bullish_score += pattern_score
                bullish_reasons.append(f"📐 {pattern_name}: {pattern_desc}")
            elif pattern_type == 'bearish':
                bearish_score += pattern_score
                bearish_reasons.append(f"📐 {pattern_name}: {pattern_desc}")
            elif pattern_type == 'neutral':
                # Neutral patterns add to momentum direction
                if bullish_score > bearish_score:
                    bullish_score += pattern_score * 0.5
                    bullish_reasons.append(f"📐 {pattern_name} (momentum bias)")
                elif bearish_score > bullish_score:
                    bearish_score += pattern_score * 0.5
                    bearish_reasons.append(f"📐 {pattern_name} (momentum bias)")
            
            # Check for multiple patterns
            all_patterns = indicators.get('all_patterns', [])
            if len(all_patterns) > 1:
                bullish_patterns = [p for p in all_patterns if p['type'] == 'bullish']
                bearish_patterns = [p for p in all_patterns if p['type'] == 'bearish']
                
                if len(bullish_patterns) >= 2:
                    bullish_score += 1.0
                    bullish_reasons.append(f"🎯 Multiple bullish patterns ({len(bullish_patterns)})")
                if len(bearish_patterns) >= 2:
                    bearish_score += 1.0
                    bearish_reasons.append(f"🎯 Multiple bearish patterns ({len(bearish_patterns)})")
        
        # =====================================================================
        # SIGNAL DETERMINATION
        # =====================================================================
        
        net_score = bullish_score - bearish_score
        total_signals = len(bullish_reasons) + len(bearish_reasons)
        
        # Calculate confidence based on score and number of confirming signals
        # Use configurable thresholds (lower = more aggressive trading)
        strong_buy_thresh = self.config.strong_buy_threshold  # Default 4.0
        buy_thresh = self.config.buy_signal_threshold          # Default 2.0
        sell_thresh = self.config.sell_signal_threshold        # Default -2.0
        strong_sell_thresh = self.config.strong_sell_threshold # Default -4.0
        
        if net_score >= strong_buy_thresh:
            signal_type = 'strong_buy'
            confidence = min(0.95, 0.6 + (net_score / max_score) * 0.35)
            reasoning = f"🚀 STRONG BUY ({net_score:.1f}/{max_score} points, {len(bullish_reasons)} signals): {' | '.join(bullish_reasons[:5])}"
        elif net_score >= buy_thresh:
            signal_type = 'buy'
            confidence = min(0.80, 0.45 + (net_score / max_score) * 0.35)
            reasoning = f"📈 BUY ({net_score:.1f}/{max_score} points, {len(bullish_reasons)} signals): {' | '.join(bullish_reasons[:4])}"
        elif net_score <= strong_sell_thresh:
            signal_type = 'strong_sell'
            confidence = min(0.95, 0.6 + (abs(net_score) / max_score) * 0.35)
            reasoning = f"💥 STRONG SELL ({abs(net_score):.1f}/{max_score} points, {len(bearish_reasons)} signals): {' | '.join(bearish_reasons[:5])}"
        elif net_score <= sell_thresh:
            signal_type = 'sell'
            confidence = min(0.80, 0.45 + (abs(net_score) / max_score) * 0.35)
            reasoning = f"📉 SELL ({abs(net_score):.1f}/{max_score} points, {len(bearish_reasons)} signals): {' | '.join(bearish_reasons[:4])}"
        else:
            signal_type = 'hold'
            confidence = 0
            reasoning = f"⏸️ HOLD: Mixed signals (net score: {net_score:.1f}, bullish: {bullish_score:.1f}, bearish: {bearish_score:.1f})"
        
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

