"""
Market data management module.
Handles real-time and historical market data from multiple sources.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from dataclasses import dataclass
from collections import defaultdict

import pandas as pd
from loguru import logger

from src.connectors.ibkr_connector import IBKRConnector
from src.data.redis_cache import RedisCache
from src.data.timescale_client import TimescaleClient


@dataclass
class Quote:
    """Real-time quote data."""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    timestamp: datetime
    
    @property
    def mid(self) -> float:
        """Get mid price."""
        if self.bid and self.ask:
            return (self.bid + self.ask) / 2
        return self.last
    
    @property
    def spread(self) -> float:
        """Get bid-ask spread."""
        if self.bid and self.ask:
            return self.ask - self.bid
        return 0.0
    
    @property
    def spread_pct(self) -> float:
        """Get spread as percentage of mid."""
        mid = self.mid
        if mid > 0:
            return self.spread / mid * 100
        return 0.0


@dataclass
class Bar:
    """OHLCV bar data."""
    symbol: str
    timeframe: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "time": self.time.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class MarketDataManager:
    """
    Manages market data from various sources.
    
    Features:
    - Real-time quote subscriptions
    - Historical data retrieval
    - Data caching with Redis
    - Data persistence with TimescaleDB
    - Multiple timeframe aggregation
    """
    
    def __init__(
        self,
        ibkr: IBKRConnector,
        cache: RedisCache,
        db: TimescaleClient,
    ):
        """Initialize market data manager."""
        self.ibkr = ibkr
        self.cache = cache
        self.db = db
        
        self._subscriptions: dict[str, list[Callable]] = defaultdict(list)
        self._quotes: dict[str, Quote] = {}
        self._bars: dict[str, dict[str, list[Bar]]] = defaultdict(lambda: defaultdict(list))
    
    # =========================================================================
    # Real-time Data
    # =========================================================================
    
    async def subscribe(
        self,
        symbol: str,
        callback: Callable[[Quote], None] = None,
    ) -> bool:
        """
        Subscribe to real-time quotes for a symbol.
        
        Args:
            symbol: Stock symbol
            callback: Optional callback for quote updates
            
        Returns:
            True if subscription successful
        """
        try:
            contract = self.ibkr.create_stock_contract(symbol)
            qualified = await self.ibkr.qualify_contract(contract)
            
            if not qualified:
                logger.error(f"Failed to qualify contract for {symbol}")
                return False
            
            # Subscribe to market data
            self.ibkr.subscribe_market_data(
                qualified,
                lambda ticker: self._on_tick_update(symbol, ticker),
            )
            
            if callback:
                self._subscriptions[symbol].append(callback)
            
            logger.info(f"Subscribed to market data for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {symbol}: {e}")
            return False
    
    def unsubscribe(self, symbol: str) -> None:
        """Unsubscribe from real-time quotes."""
        contract = self.ibkr.create_stock_contract(symbol)
        self.ibkr.unsubscribe_market_data(contract)
        self._subscriptions.pop(symbol, None)
        logger.info(f"Unsubscribed from market data for {symbol}")
    
    def _on_tick_update(self, symbol: str, ticker: Any) -> None:
        """Handle tick update from IBKR."""
        try:
            quote = Quote(
                symbol=symbol,
                bid=ticker.bid or 0,
                ask=ticker.ask or 0,
                last=ticker.last or ticker.marketPrice() or 0,
                volume=ticker.volume or 0,
                timestamp=datetime.utcnow(),
            )
            
            self._quotes[symbol] = quote
            
            # Cache in Redis
            asyncio.create_task(
                self.cache.cache_market_price(
                    symbol,
                    quote.last,
                    quote.bid,
                    quote.ask,
                    quote.volume,
                )
            )
            
            # Notify callbacks
            for callback in self._subscriptions.get(symbol, []):
                try:
                    callback(quote)
                except Exception as e:
                    logger.error(f"Error in quote callback for {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing tick for {symbol}: {e}")
    
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get the latest quote for a symbol."""
        return self._quotes.get(symbol)
    
    async def get_price(self, symbol: str) -> Optional[float]:
        """Get the current price for a symbol."""
        # Check memory cache first
        quote = self._quotes.get(symbol)
        if quote:
            return quote.last
        
        # Check Redis cache
        cached = await self.cache.get_market_price(symbol)
        if cached:
            return cached.get("price")
        
        # Fetch from IBKR
        contract = self.ibkr.create_stock_contract(symbol)
        return await self.ibkr.get_market_price(contract)
    
    # =========================================================================
    # Historical Data
    # =========================================================================
    
    async def get_historical_bars(
        self,
        symbol: str,
        timeframe: str = "1 day",
        duration: str = "1 M",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Get historical bar data.
        
        Args:
            symbol: Stock symbol
            timeframe: Bar size (e.g., "1 min", "5 mins", "1 hour", "1 day")
            duration: Duration string (e.g., "1 D", "1 W", "1 M", "1 Y")
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{symbol}:{timeframe}"
        
        # Check Redis cache
        if use_cache:
            cached = await self.cache.get_ohlcv(symbol, timeframe)
            if cached:
                logger.debug(f"Using cached bars for {symbol}")
                return pd.DataFrame(cached)
        
        # Fetch from IBKR
        contract = self.ibkr.create_stock_contract(symbol)
        qualified = await self.ibkr.qualify_contract(contract)
        
        if not qualified:
            logger.error(f"Failed to qualify contract for {symbol}")
            return pd.DataFrame()
        
        bars = await self.ibkr.get_historical_data(
            qualified,
            duration=duration,
            bar_size=timeframe,
        )
        
        if not bars:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            "time": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        } for bar in bars])
        
        # Set time as index
        if not df.empty:
            df["time"] = pd.to_datetime(df["time"])
            df.set_index("time", inplace=True)
            
            # Cache the result
            await self.cache.cache_ohlcv(symbol, timeframe, df.reset_index().to_dict("records"))
            
            # Store in database
            for _, row in df.iterrows():
                await self.db.insert_ohlcv_bar(
                    symbol=symbol,
                    timeframe=timeframe,
                    open_price=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                    time=row.name,
                )
        
        return df
    
    async def get_multiple_symbols(
        self,
        symbols: list[str],
        timeframe: str = "1 day",
        duration: str = "1 M",
    ) -> dict[str, pd.DataFrame]:
        """Get historical data for multiple symbols concurrently."""
        tasks = [
            self.get_historical_bars(symbol, timeframe, duration)
            for symbol in symbols
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: result
            for symbol, result in zip(symbols, results)
            if isinstance(result, pd.DataFrame) and not result.empty
        }
    
    # =========================================================================
    # Analysis Helpers
    # =========================================================================
    
    async def get_price_change(
        self,
        symbol: str,
        period_days: int = 1,
    ) -> Optional[float]:
        """Get price change over a period."""
        df = await self.get_historical_bars(
            symbol,
            timeframe="1 day",
            duration=f"{period_days + 5} D",  # Extra days for weekends
        )
        
        if df.empty or len(df) < 2:
            return None
        
        current = df["close"].iloc[-1]
        previous = df["close"].iloc[0]
        
        return (current - previous) / previous
    
    async def get_volume_ratio(
        self,
        symbol: str,
        period_days: int = 20,
    ) -> Optional[float]:
        """Get current volume relative to average."""
        df = await self.get_historical_bars(
            symbol,
            timeframe="1 day",
            duration=f"{period_days + 5} D",
        )
        
        if df.empty or len(df) < period_days:
            return None
        
        current_volume = df["volume"].iloc[-1]
        avg_volume = df["volume"].iloc[:-1].mean()
        
        if avg_volume > 0:
            return current_volume / avg_volume
        return None
    
    async def get_atr(
        self,
        symbol: str,
        period: int = 14,
    ) -> Optional[float]:
        """Calculate Average True Range."""
        df = await self.get_historical_bars(
            symbol,
            timeframe="1 day",
            duration=f"{period + 10} D",
        )
        
        if df.empty or len(df) < period:
            return None
        
        high = df["high"]
        low = df["low"]
        close = df["close"]
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr

