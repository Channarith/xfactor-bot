"""
Market Data Providers - Multi-source data fetching with automatic failover.

ALL providers are FREE and require NO API keys - uses web scraping.

Provider Priority:
1. yfinance (primary - library)
2. Yahoo Finance direct HTTP (fallback)
3. Google Finance scraping (fallback)
4. MarketWatch scraping (fallback)

All providers implement the same interface for seamless failover.
"""

import asyncio
import aiohttp
import re
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
                    
                    # Handle None or empty data from yfinance
                    if data is None or data.empty:
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
            
            # Handle None or empty data from yfinance
            if data is None or data.empty:
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


class GoogleFinanceProvider(MarketDataProvider):
    """Google Finance web scraper - NO API key required."""
    
    name = "google_finance"
    requires_api_key = False
    
    def is_available(self) -> bool:
        return True
    
    async def get_quotes(self, symbols: List[str]) -> List[Quote]:
        quotes = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            for symbol in symbols:
                try:
                    # Google Finance URL
                    url = f"https://www.google.com/finance/quote/{symbol}:NASDAQ"
                    
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status != 200:
                            # Try NYSE
                            url = f"https://www.google.com/finance/quote/{symbol}:NYSE"
                            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp2:
                                if resp2.status != 200:
                                    continue
                                text = await resp2.text()
                        else:
                            text = await resp.text()
                        
                        # Parse price from HTML
                        # Look for data-last-price attribute or price in specific div
                        price_match = re.search(r'data-last-price="([0-9.]+)"', text)
                        if not price_match:
                            price_match = re.search(r'class="YMlKec fxKbKc">([0-9,.]+)', text)
                        
                        if not price_match:
                            continue
                        
                        price_str = price_match.group(1).replace(',', '')
                        price = float(price_str)
                        
                        # Parse change
                        change = 0.0
                        change_pct = 0.0
                        change_match = re.search(r'data-price-change="([0-9.-]+)"', text)
                        change_pct_match = re.search(r'data-price-change-percent="([0-9.-]+)"', text)
                        
                        if change_match:
                            change = float(change_match.group(1))
                        if change_pct_match:
                            change_pct = float(change_pct_match.group(1))
                        
                        prev_close = price - change if change else price
                        
                        quotes.append(Quote(
                            symbol=symbol,
                            price=price,
                            change=change,
                            change_pct=change_pct,
                            volume=0,  # Not easily available from Google
                            prev_close=prev_close,
                            source="google_finance",
                        ))
                        
                except Exception as e:
                    logger.debug(f"Google Finance error for {symbol}: {e}")
                
                await asyncio.sleep(0.2)  # Rate limiting
        
        return quotes
    
    async def get_history(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[HistoricalBar]:
        # Google Finance doesn't provide easy historical data access
        return []


class MarketWatchProvider(MarketDataProvider):
    """MarketWatch web scraper - NO API key required."""
    
    name = "marketwatch"
    requires_api_key = False
    
    def is_available(self) -> bool:
        return True
    
    async def get_quotes(self, symbols: List[str]) -> List[Quote]:
        quotes = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            for symbol in symbols:
                try:
                    url = f"https://www.marketwatch.com/investing/stock/{symbol.lower()}"
                    
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status != 200:
                            continue
                        
                        text = await resp.text()
                        
                        # Parse price - look for intraday__price
                        price_match = re.search(r'class="intraday__price[^"]*"[^>]*>.*?<bg-quote[^>]*>([0-9,.]+)', text, re.DOTALL)
                        if not price_match:
                            price_match = re.search(r'<meta\s+name="price"\s+content="([0-9.]+)"', text)
                        
                        if not price_match:
                            continue
                        
                        price_str = price_match.group(1).replace(',', '')
                        price = float(price_str)
                        
                        # Parse change
                        change = 0.0
                        change_pct = 0.0
                        
                        change_match = re.search(r'class="change--point--[^"]*"[^>]*>([+-]?[0-9,.]+)', text)
                        change_pct_match = re.search(r'class="change--percent--[^"]*"[^>]*>([+-]?[0-9,.]+)%', text)
                        
                        if change_match:
                            change = float(change_match.group(1).replace(',', ''))
                        if change_pct_match:
                            change_pct = float(change_pct_match.group(1).replace(',', ''))
                        
                        # Parse volume
                        volume = 0
                        vol_match = re.search(r'Volume.*?<span[^>]*>([0-9,.]+[MKB]?)', text, re.DOTALL | re.IGNORECASE)
                        if vol_match:
                            vol_str = vol_match.group(1).replace(',', '')
                            if 'M' in vol_str.upper():
                                volume = int(float(vol_str.replace('M', '').replace('m', '')) * 1_000_000)
                            elif 'K' in vol_str.upper():
                                volume = int(float(vol_str.replace('K', '').replace('k', '')) * 1_000)
                            elif 'B' in vol_str.upper():
                                volume = int(float(vol_str.replace('B', '').replace('b', '')) * 1_000_000_000)
                            else:
                                volume = int(float(vol_str))
                        
                        prev_close = price - change if change else price
                        
                        quotes.append(Quote(
                            symbol=symbol,
                            price=price,
                            change=change,
                            change_pct=change_pct,
                            volume=volume,
                            prev_close=prev_close,
                            source="marketwatch",
                        ))
                        
                except Exception as e:
                    logger.debug(f"MarketWatch error for {symbol}: {e}")
                
                await asyncio.sleep(0.3)  # Rate limiting
        
        return quotes
    
    async def get_history(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[HistoricalBar]:
        # MarketWatch has historical data but requires more complex scraping
        return []


class CNBCProvider(MarketDataProvider):
    """CNBC web scraper - NO API key required."""
    
    name = "cnbc"
    requires_api_key = False
    
    def is_available(self) -> bool:
        return True
    
    async def get_quotes(self, symbols: List[str]) -> List[Quote]:
        quotes = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            for symbol in symbols:
                try:
                    # CNBC has a JSON API
                    url = f"https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols={symbol}&requestMethod=itv&no498s=1&partnerId=2&fund=1&exthrs=1&output=json"
                    
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status != 200:
                            continue
                        
                        data = await resp.json()
                        
                        # Navigate the response structure
                        quick_quote = data.get('FormattedQuoteResult', {}).get('FormattedQuote', [])
                        if not quick_quote:
                            continue
                        
                        quote_data = quick_quote[0] if isinstance(quick_quote, list) else quick_quote
                        
                        price = float(quote_data.get('last', 0) or 0)
                        change = float(quote_data.get('change', 0) or 0)
                        change_pct = float(quote_data.get('change_pct', '0').replace('%', '') or 0)
                        
                        vol_str = quote_data.get('volume', '0')
                        if isinstance(vol_str, str):
                            vol_str = vol_str.replace(',', '')
                        volume = int(float(vol_str)) if vol_str else 0
                        
                        prev_close = float(quote_data.get('previous_day_closing', price) or price)
                        high = float(quote_data.get('high', price) or price)
                        low = float(quote_data.get('low', price) or price)
                        open_price = float(quote_data.get('open', price) or price)
                        
                        quotes.append(Quote(
                            symbol=symbol,
                            price=price,
                            change=change,
                            change_pct=change_pct,
                            volume=volume,
                            prev_close=prev_close,
                            high=high,
                            low=low,
                            open=open_price,
                            source="cnbc",
                        ))
                        
                except Exception as e:
                    logger.debug(f"CNBC error for {symbol}: {e}")
                
                await asyncio.sleep(0.1)
        
        return quotes
    
    async def get_history(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[HistoricalBar]:
        return []


class MarketDataManager:
    """
    Unified market data manager with automatic provider failover.
    
    Tries providers in order of preference and caches results.
    """
    
    def __init__(self):
        # Initialize providers in priority order (all FREE, no API keys)
        self._providers: List[MarketDataProvider] = [
            YFinanceProvider(),      # Primary - library
            YahooDirectProvider(),   # Fallback - direct HTTP
            CNBCProvider(),          # Fallback - has JSON API
            GoogleFinanceProvider(), # Fallback - web scraping
            MarketWatchProvider(),   # Last resort - web scraping
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

