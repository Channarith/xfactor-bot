"""
Growth Screener - Find top growth stocks across all exchanges.

Screens for stocks with the highest growth metrics:
- Price change percentage
- Volume surge
- Momentum score
- RSI trending

Supports multiple timeframes:
- Real-time (1 minute)
- Daily
- Weekly
- Monthly
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import threading

from loguru import logger

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    yf = None
    pd = None


@dataclass
class GrowthCandidate:
    """A stock that meets growth criteria."""
    symbol: str
    name: str
    exchange: str
    
    # Price metrics
    current_price: float
    previous_price: float
    price_change: float
    price_change_pct: float
    
    # Volume metrics
    volume: int
    avg_volume: int
    volume_ratio: float  # Current volume / average volume
    
    # Technical metrics
    momentum_score: float  # 0-100
    rsi: Optional[float] = None
    
    # Metadata
    timeframe: str = "1d"
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "current_price": self.current_price,
            "previous_price": self.previous_price,
            "price_change": self.price_change,
            "price_change_pct": self.price_change_pct,
            "volume": self.volume,
            "avg_volume": self.avg_volume,
            "volume_ratio": self.volume_ratio,
            "momentum_score": self.momentum_score,
            "rsi": self.rsi,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class GrowthScreener:
    """
    Screen for top growth stocks across all exchanges.
    
    Features:
    - Multi-timeframe analysis (1m, 1d, 1w, 1M)
    - Volume confirmation
    - Momentum scoring
    - Caching to reduce API calls
    """
    
    # Cache TTL by timeframe
    CACHE_TTL = {
        "1m": 60,      # 1 minute
        "5m": 300,     # 5 minutes
        "1d": 3600,    # 1 hour
        "1w": 7200,    # 2 hours
        "1M": 14400,   # 4 hours
    }
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}  # {key: {"data": [...], "timestamp": datetime}}
        self._lock = threading.Lock()
        
        # Default screening universe (can be expanded)
        self._screening_universe: List[str] = []
    
    async def screen_top_growth(
        self,
        count: int = 12,
        timeframe: str = "1d",
        exchange: Optional[str] = None,
        universe: Optional[List[str]] = None,
        min_price: float = 1.0,
        min_volume: int = 100000,
    ) -> List[GrowthCandidate]:
        """
        Find top N stocks by growth metrics.
        
        Args:
            count: Number of top stocks to return
            timeframe: "1m", "5m", "1d", "1w", "1M"
            exchange: Filter by exchange (NASDAQ, NYSE, etc.)
            universe: List of symbols to screen (None = use default)
            min_price: Minimum stock price filter
            min_volume: Minimum average volume filter
        
        Returns:
            List of top growth candidates sorted by growth score
        """
        if yf is None or pd is None:
            logger.error("yfinance/pandas not available for growth screening")
            return []
        
        # Check cache
        cache_key = f"{timeframe}_{exchange or 'all'}_{count}"
        cached = self._get_cached(cache_key, timeframe)
        if cached:
            return cached
        
        # Get screening universe
        symbols = universe or await self._get_screening_universe(exchange)
        
        if not symbols:
            logger.warning("No symbols available for screening")
            return []
        
        logger.info(f"Screening {len(symbols)} symbols for top {count} growth ({timeframe})")
        
        # Analyze stocks in batches
        candidates = []
        batch_size = 50
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            try:
                batch_candidates = await self._analyze_batch(
                    batch, timeframe, min_price, min_volume
                )
                candidates.extend(batch_candidates)
            except Exception as e:
                logger.error(f"Error analyzing batch: {e}")
            
            # Rate limit
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.5)
        
        # Sort by growth score (price_change_pct * volume_ratio * momentum)
        candidates.sort(
            key=lambda x: x.price_change_pct * (1 + x.volume_ratio) * (x.momentum_score / 100),
            reverse=True
        )
        
        # Get top N
        top_candidates = candidates[:count]
        
        # Cache results
        self._set_cache(cache_key, top_candidates, timeframe)
        
        logger.info(f"Found {len(top_candidates)} top growth stocks")
        return top_candidates
    
    async def _get_screening_universe(self, exchange: Optional[str] = None) -> List[str]:
        """Get the default screening universe."""
        from src.data.symbol_universe import get_symbol_universe, ensure_symbols_loaded
        
        try:
            universe = await ensure_symbols_loaded()
            
            if exchange:
                symbols = universe.get_by_exchange(exchange)
            else:
                symbols = universe.get_all_symbols()
            
            # Limit to tradeable symbols (filter out weird ones)
            symbols = [s for s in symbols if self._is_valid_symbol(s)]
            
            # Prioritize liquid stocks - limit for API efficiency
            if len(symbols) > 500:
                # Use a mix of popular + random sample
                from src.data.symbol_universe import ALL_POPULAR_ETFS, LEVERAGED_ETFS
                priority = set(ALL_POPULAR_ETFS + LEVERAGED_ETFS)
                
                # Add top stocks by exchange
                top_nasdaq = symbols[:200] if 'AAPL' in symbols else symbols[:200]
                
                import random
                random.shuffle(symbols)
                sample = symbols[:300]
                
                symbols = list(priority) + sample
                symbols = list(set(symbols))[:500]
            
            return symbols
            
        except Exception as e:
            logger.error(f"Error getting screening universe: {e}")
            # Fallback to basic list
            return [
                "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                "AMD", "SOXL", "TQQQ", "JPM", "BAC", "XOM", "CVX", "JNJ", "UNH",
            ]
    
    def _is_valid_symbol(self, symbol: str) -> bool:
        """Check if a symbol is valid for screening."""
        # Filter out weird symbols
        if len(symbol) > 5:
            return False
        if not symbol.isalpha():
            # Allow some numbers (like BRK.B)
            if not all(c.isalnum() or c in '.^' for c in symbol):
                return False
        return True
    
    async def _analyze_batch(
        self,
        symbols: List[str],
        timeframe: str,
        min_price: float,
        min_volume: int,
    ) -> List[GrowthCandidate]:
        """Analyze a batch of symbols."""
        candidates = []
        
        # Map timeframe to yfinance period/interval
        period_map = {
            "1m": ("1d", "1m"),
            "5m": ("1d", "5m"),
            "1d": ("5d", "1d"),
            "1w": ("1mo", "1d"),
            "1M": ("3mo", "1d"),
        }
        period, interval = period_map.get(timeframe, ("5d", "1d"))
        
        try:
            # Download data for batch
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    " ".join(symbols),
                    period=period,
                    interval=interval,
                    progress=False,
                    threads=True,
                )
            )
            
            if data.empty:
                return candidates
            
            # Handle single vs multiple symbols
            if len(symbols) == 1:
                data.columns = pd.MultiIndex.from_product([data.columns, symbols])
            
            for symbol in symbols:
                try:
                    # Get symbol data
                    if ('Close', symbol) not in data.columns:
                        continue
                    
                    close = data[('Close', symbol)].dropna()
                    volume = data[('Volume', symbol)].dropna()
                    
                    if len(close) < 2:
                        continue
                    
                    current_price = close.iloc[-1]
                    previous_price = close.iloc[0]
                    
                    # Apply filters
                    if current_price < min_price:
                        continue
                    
                    avg_volume = volume.mean() if len(volume) > 0 else 0
                    if avg_volume < min_volume:
                        continue
                    
                    # Calculate metrics
                    price_change = current_price - previous_price
                    price_change_pct = (price_change / previous_price) * 100 if previous_price > 0 else 0
                    
                    current_volume = volume.iloc[-1] if len(volume) > 0 else 0
                    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                    
                    # Calculate momentum score
                    momentum_score = self._calculate_momentum(close)
                    
                    # Calculate RSI
                    rsi = self._calculate_rsi(close) if len(close) >= 14 else None
                    
                    # Only include positive growth
                    if price_change_pct <= 0:
                        continue
                    
                    candidates.append(GrowthCandidate(
                        symbol=symbol,
                        name=symbol,  # Would need separate lookup for full name
                        exchange="",
                        current_price=round(current_price, 2),
                        previous_price=round(previous_price, 2),
                        price_change=round(price_change, 2),
                        price_change_pct=round(price_change_pct, 2),
                        volume=int(current_volume),
                        avg_volume=int(avg_volume),
                        volume_ratio=round(volume_ratio, 2),
                        momentum_score=round(momentum_score, 1),
                        rsi=round(rsi, 1) if rsi else None,
                        timeframe=timeframe,
                        timestamp=datetime.now(),
                    ))
                    
                except Exception as e:
                    logger.debug(f"Error analyzing {symbol}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error downloading batch data: {e}")
        
        return candidates
    
    def _calculate_momentum(self, prices: "pd.Series") -> float:
        """
        Calculate momentum score (0-100).
        
        Based on:
        - Rate of change
        - Trend consistency
        - Position relative to moving averages
        """
        if len(prices) < 5:
            return 50.0
        
        try:
            # Rate of change
            roc = ((prices.iloc[-1] / prices.iloc[0]) - 1) * 100
            roc_score = min(max(roc * 5, -50), 50) + 50  # Normalize to 0-100
            
            # Trend consistency (% of up days)
            returns = prices.pct_change().dropna()
            up_ratio = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0.5
            consistency_score = up_ratio * 100
            
            # Position relative to SMA
            sma5 = prices.rolling(5).mean().iloc[-1]
            sma_score = 75 if prices.iloc[-1] > sma5 else 25
            
            # Weighted average
            momentum = (roc_score * 0.5) + (consistency_score * 0.3) + (sma_score * 0.2)
            
            return max(0, min(100, momentum))
            
        except Exception:
            return 50.0
    
    def _calculate_rsi(self, prices: "pd.Series", period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return None
        
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 0
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception:
            return None
    
    def _get_cached(self, key: str, timeframe: str) -> Optional[List[GrowthCandidate]]:
        """Get cached results if still valid."""
        with self._lock:
            if key in self._cache:
                cached = self._cache[key]
                ttl = self.CACHE_TTL.get(timeframe, 3600)
                age = (datetime.now() - cached["timestamp"]).total_seconds()
                
                if age < ttl:
                    return cached["data"]
        return None
    
    def _set_cache(self, key: str, data: List[GrowthCandidate], timeframe: str) -> None:
        """Cache results."""
        with self._lock:
            self._cache[key] = {
                "data": data,
                "timestamp": datetime.now(),
            }


# Global instance
_screener: Optional[GrowthScreener] = None


def get_growth_screener() -> GrowthScreener:
    """Get the global growth screener instance."""
    global _screener
    if _screener is None:
        _screener = GrowthScreener()
    return _screener

