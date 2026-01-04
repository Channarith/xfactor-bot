"""
Market Data Providers - Multi-source data fetching with automatic failover.

Provider Priority:
1. yfinance (primary - no API key required)
2. Yahoo Finance direct HTTP (fallback - no API key)
3. Alpha Vantage (if API key configured)
4. Finnhub (if API key configured)

All providers implement the same interface for seamless failover.
"""

import asyncio
import aiohttp
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger

# Cache for market data (shared across providers)
_quote_cache: Dict[str, Dict[str, Any]] = {}
_quote_cache_ttl = 30  # seconds


@dataclass
class Quote:
    """Standard quote format across all providers."""
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    prev_close: float
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0
    timestamp: Optional[str] = None
    source: str = "unknown"
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "price": round(self.price, 2),
            "change": round(self.change, 2),
            "changePct": round(self.change_pct, 2),
            "volume": self.volume,
            "prevClose": round(self.prev_close, 2),
            "high": round(self.high, 2),
            "low": round(self.low, 2),
            "open": round(self.open, 2),
            "timestamp": self.timestamp or datetime.now().isoformat(),
            "source": self.source,
        }


@dataclass
class HistoricalBar:
    """Standard OHLCV bar format."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""
    
    name: str = "base"
    requires_api_key: bool = False
    
    @abstractmethod
    async def get_quotes(self, symbols: List[str]) -> List[Quote]:
        """Get real-time quotes for symbols."""
        pass
    
    @abstractmethod
    async def get_history(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[HistoricalBar]:
        """Get historical OHLCV data."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (has required API keys, etc.)."""
        pass


class YFinanceProvider(MarketDataProvider):
    """Primary provider using yfinance library."""
    
    name = "yfinance"
    requires_api_key = False
    
    def __init__(self):
        self._available = True
        try:
            import yfinance
            self._yf = yfinance
        except ImportError:
            self._available = False
            self._yf = None
    
    def is_available(self) -> bool:
        return self._available
    
    async def get_quotes(self, symbols: List[str]) -> List[Quote]:
        if not self._available:
            return []
        
        quotes = []
        
        try:
            loop = asyncio.get_event_loop()
            
            # Fetch in small batches to avoid thread issues
            batch_size = 5
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                
                try:
                    data = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda b=batch: self._yf.download(
                                " ".join(b),
                                period="2d",
                                interval="1d",
                                progress=False,
                                threads=False,
                            )
                        ),
                        timeout=15
                    )
                    
                    if data.empty:
                        continue
                    
                    # Process each symbol
                    for sym in batch:
                        try:
                            if len(batch) == 1:
                                close = data['Close'].iloc[-1]
                                prev = data['Close'].iloc[-2] if len(data) > 1 else close
                                vol = data['Volume'].iloc[-1]
                                high = data['High'].iloc[-1]
                                low = data['Low'].iloc[-1]
                                open_price = data['Open'].iloc[-1]
                            else:
                                close = data[('Close', sym)].iloc[-1]
                                prev = data[('Close', sym)].iloc[-2] if len(data) > 1 else close
                                vol = data[('Volume', sym)].iloc[-1]
                                high = data[('High', sym)].iloc[-1]
                                low = data[('Low', sym)].iloc[-1]
                                open_price = data[('Open', sym)].iloc[-1]
                            
                            change = close - prev
                            change_pct = (change / prev) * 100 if prev > 0 else 0
                            
                            quotes.append(Quote(
                                symbol=sym,
                                price=float(close),
                                change=float(change),
                                change_pct=float(change_pct),
                                volume=int(vol),
                                prev_close=float(prev),
                                high=float(high),
                                low=float(low),
                                open=float(open_price),
                                source="yfinance",
                            ))
                        except Exception as e:
                            logger.debug(f"yfinance quote error for {sym}: {e}")
                    
                except asyncio.TimeoutError:
                    logger.warning(f"yfinance timeout for batch {batch}")
                except Exception as e:
                    logger.debug(f"yfinance batch error: {e}")
                
                # Small delay between batches
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"yfinance provider error: {e}")
        
        return quotes
    
    async def get_history(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[HistoricalBar]:
        if not self._available:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            
            data = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._yf.Ticker(symbol).history(period=period, interval=interval)
                ),
                timeout=15
            )
            
            if data.empty:
                return []
            
            bars = []
            for idx, row in data.iterrows():
                bars.append(HistoricalBar(
                    timestamp=idx.isoformat(),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume']),
                ))
            
            return bars
            
        except Exception as e:
            logger.debug(f"yfinance history error for {symbol}: {e}")
            return []


class YahooDirectProvider(MarketDataProvider):
    """Fallback provider using direct Yahoo Finance HTTP requests."""
    
    name = "yahoo_direct"
    requires_api_key = False
    
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    
    def is_available(self) -> bool:
        return True  # Always available as fallback
    
    async def get_quotes(self, symbols: List[str]) -> List[Quote]:
        quotes = []
        
        async with aiohttp.ClientSession() as session:
            for symbol in symbols:
                try:
                    url = f"{self.BASE_URL}/{symbol}"
                    params = {"interval": "1d", "range": "2d"}
                    
                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status != 200:
                            continue
                        
                        data = await resp.json()
                        
                        result = data.get("chart", {}).get("result", [])
                        if not result:
                            continue
                        
                        meta = result[0].get("meta", {})
                        indicators = result[0].get("indicators", {})
                        
                        price = meta.get("regularMarketPrice", 0)
                        prev = meta.get("previousClose", price)
                        change = price - prev
                        change_pct = (change / prev) * 100 if prev > 0 else 0
                        
                        quote_data = indicators.get("quote", [{}])[0]
                        volume = quote_data.get("volume", [0])[-1] if quote_data.get("volume") else 0
                        high = quote_data.get("high", [price])[-1] if quote_data.get("high") else price
                        low = quote_data.get("low", [price])[-1] if quote_data.get("low") else price
                        open_price = quote_data.get("open", [price])[-1] if quote_data.get("open") else price
                        
                        quotes.append(Quote(
                            symbol=symbol,
                            price=float(price),
                            change=float(change),
                            change_pct=float(change_pct),
                            volume=int(volume or 0),
                            prev_close=float(prev),
                            high=float(high or price),
                            low=float(low or price),
                            open=float(open_price or price),
                            source="yahoo_direct",
                        ))
                        
                except Exception as e:
                    logger.debug(f"Yahoo direct quote error for {symbol}: {e}")
                
                # Rate limiting
                await asyncio.sleep(0.1)
        
        return quotes
    
    async def get_history(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[HistoricalBar]:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/{symbol}"
                params = {"interval": interval, "range": period}
                
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return []
                    
                    data = await resp.json()
                    
                    result = data.get("chart", {}).get("result", [])
                    if not result:
                        return []
                    
                    timestamps = result[0].get("timestamp", [])
                    indicators = result[0].get("indicators", {})
                    quote = indicators.get("quote", [{}])[0]
                    
                    bars = []
                    for i, ts in enumerate(timestamps):
                        bars.append(HistoricalBar(
                            timestamp=datetime.fromtimestamp(ts).isoformat(),
                            open=float(quote.get("open", [0])[i] or 0),
                            high=float(quote.get("high", [0])[i] or 0),
                            low=float(quote.get("low", [0])[i] or 0),
                            close=float(quote.get("close", [0])[i] or 0),
                            volume=int(quote.get("volume", [0])[i] or 0),
                        ))
                    
                    return bars
                    
        except Exception as e:
            logger.debug(f"Yahoo direct history error for {symbol}: {e}")
            return []


class AlphaVantageProvider(MarketDataProvider):
    """Alpha Vantage provider (requires API key)."""
    
    name = "alphavantage"
    requires_api_key = True
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self):
        self._api_key = os.getenv("ALPHAVANTAGE_API_KEY", "")
    
    def is_available(self) -> bool:
        return bool(self._api_key)
    
    async def get_quotes(self, symbols: List[str]) -> List[Quote]:
        if not self.is_available():
            return []
        
        quotes = []
        
        async with aiohttp.ClientSession() as session:
            for symbol in symbols[:5]:  # Limit due to rate limits
                try:
                    params = {
                        "function": "GLOBAL_QUOTE",
                        "symbol": symbol,
                        "apikey": self._api_key,
                    }
                    
                    async with session.get(self.BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status != 200:
                            continue
                        
                        data = await resp.json()
                        quote_data = data.get("Global Quote", {})
                        
                        if not quote_data:
                            continue
                        
                        price = float(quote_data.get("05. price", 0))
                        prev = float(quote_data.get("08. previous close", price))
                        change = float(quote_data.get("09. change", 0))
                        change_pct = float(quote_data.get("10. change percent", "0").replace("%", ""))
                        
                        quotes.append(Quote(
                            symbol=symbol,
                            price=price,
                            change=change,
                            change_pct=change_pct,
                            volume=int(quote_data.get("06. volume", 0)),
                            prev_close=prev,
                            high=float(quote_data.get("03. high", price)),
                            low=float(quote_data.get("04. low", price)),
                            open=float(quote_data.get("02. open", price)),
                            source="alphavantage",
                        ))
                        
                except Exception as e:
                    logger.debug(f"Alpha Vantage quote error for {symbol}: {e}")
                
                # Rate limiting (5 calls/min for free tier)
                await asyncio.sleep(12)
        
        return quotes
    
    async def get_history(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[HistoricalBar]:
        # Alpha Vantage has different endpoints for different intervals
        # Simplified implementation for daily data
        if not self.is_available():
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "apikey": self._api_key,
                    "outputsize": "compact",
                }
                
                async with session.get(self.BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return []
                    
                    data = await resp.json()
                    time_series = data.get("Time Series (Daily)", {})
                    
                    bars = []
                    for date, values in sorted(time_series.items())[-30:]:
                        bars.append(HistoricalBar(
                            timestamp=date,
                            open=float(values.get("1. open", 0)),
                            high=float(values.get("2. high", 0)),
                            low=float(values.get("3. low", 0)),
                            close=float(values.get("4. close", 0)),
                            volume=int(values.get("5. volume", 0)),
                        ))
                    
                    return bars
                    
        except Exception as e:
            logger.debug(f"Alpha Vantage history error for {symbol}: {e}")
            return []


class MarketDataManager:
    """
    Unified market data manager with automatic provider failover.
    
    Tries providers in order of preference and caches results.
    """
    
    def __init__(self):
        # Initialize providers in priority order
        self._providers: List[MarketDataProvider] = [
            YFinanceProvider(),
            YahooDirectProvider(),
            AlphaVantageProvider(),
        ]
        
        # Filter to only available providers
        self._available_providers = [p for p in self._providers if p.is_available()]
        
        logger.info(f"Market data providers: {[p.name for p in self._available_providers]}")
    
    async def get_quotes(self, symbols: List[str], use_cache: bool = True) -> List[Quote]:
        """
        Get quotes with automatic failover.
        
        Tries each provider in order until one succeeds.
        """
        now = datetime.now()
        
        # Check cache first
        if use_cache:
            cached = []
            symbols_to_fetch = []
            
            for sym in symbols:
                if sym in _quote_cache:
                    entry = _quote_cache[sym]
                    if (now - entry['timestamp']).total_seconds() < _quote_cache_ttl:
                        cached.append(entry['quote'])
                        continue
                symbols_to_fetch.append(sym)
            
            if not symbols_to_fetch:
                return cached
        else:
            cached = []
            symbols_to_fetch = symbols
        
        # Try each provider
        quotes = []
        for provider in self._available_providers:
            try:
                logger.debug(f"Trying provider: {provider.name}")
                quotes = await provider.get_quotes(symbols_to_fetch)
                
                if quotes:
                    logger.debug(f"Got {len(quotes)} quotes from {provider.name}")
                    break
                    
            except Exception as e:
                logger.debug(f"Provider {provider.name} failed: {e}")
                continue
        
        # Cache results
        for quote in quotes:
            _quote_cache[quote.symbol] = {
                'quote': quote,
                'timestamp': now,
            }
        
        return cached + quotes
    
    async def get_history(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[HistoricalBar]:
        """
        Get historical data with automatic failover.
        """
        for provider in self._available_providers:
            try:
                bars = await provider.get_history(symbol, period, interval)
                if bars:
                    return bars
            except Exception as e:
                logger.debug(f"Provider {provider.name} history failed: {e}")
                continue
        
        return []
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return [p.name for p in self._available_providers]


# Singleton instance
_market_data_manager: Optional[MarketDataManager] = None


def get_market_data_manager() -> MarketDataManager:
    """Get or create the market data manager singleton."""
    global _market_data_manager
    if _market_data_manager is None:
        _market_data_manager = MarketDataManager()
    return _market_data_manager

