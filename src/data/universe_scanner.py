"""
Universe Scanner - Background scanning of 12,000+ symbols with tiered refresh.

Tiered Refresh Strategy:
- Hot 100: Every 15 minutes (top movers + high volume)
- Active 1000: Every 60 minutes (volume > 100k, movement > 1%)
- Full Universe: 2x per day (pre-market 5:00 AM, after-hours 5:00 PM ET)
- Deep Analysis: Weekly (full historical patterns)

Results are cached for fast access during trading hours.
"""

import asyncio
import json
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable, Awaitable
from enum import Enum

from loguru import logger

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    yf = None
    pd = None


# Cache directory
CACHE_DIR = Path.home() / ".xfactor" / "momentum_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class ScanTier(str, Enum):
    """Scan tiers with different frequencies."""
    HOT_100 = "hot_100"           # Every 15 min
    ACTIVE_1000 = "active_1000"   # Every 60 min
    FULL_UNIVERSE = "full_universe"  # 2x per day
    DEEP_ANALYSIS = "deep_analysis"  # Weekly


@dataclass
class ScanResult:
    """Result from scanning a symbol."""
    symbol: str
    tier: str
    
    # Price data
    current_price: float = 0.0
    previous_close: float = 0.0
    price_change: float = 0.0
    price_change_pct: float = 0.0
    
    # Volume data
    volume: int = 0
    avg_volume: int = 0
    volume_ratio: float = 0.0
    
    # Momentum metrics
    momentum_score: float = 0.0  # 0-100 composite
    rsi: Optional[float] = None
    
    # Metadata
    sector: str = ""
    timestamp: Optional[str] = None
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result["timestamp"] = self.timestamp or datetime.now().isoformat()
        return result


@dataclass
class ScanStatus:
    """Status of scanning operations."""
    tier: str
    last_scan: Optional[datetime] = None
    next_scan: Optional[datetime] = None
    symbols_scanned: int = 0
    duration_seconds: float = 0.0
    errors: int = 0
    is_running: bool = False
    
    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "next_scan": self.next_scan.isoformat() if self.next_scan else None,
            "symbols_scanned": self.symbols_scanned,
            "duration_seconds": round(self.duration_seconds, 2),
            "errors": self.errors,
            "is_running": self.is_running,
        }


class UniverseScanner:
    """
    Background scanner with tiered refresh strategy.
    
    Scans different subsets of the universe at different frequencies:
    - Hot 100: Fast refresh for active trading
    - Active 1000: Hourly refresh for broader coverage
    - Full Universe: 2x daily for complete rankings
    """
    
    # Tier configurations
    TIER_CONFIG = {
        ScanTier.HOT_100: {
            "count": 100,
            "interval_minutes": 15,
            "batch_size": 50,
        },
        ScanTier.ACTIVE_1000: {
            "count": 1000,
            "interval_minutes": 60,
            "batch_size": 100,
        },
        ScanTier.FULL_UNIVERSE: {
            "count": 12000,
            "times": ["05:00", "17:00"],  # ET
            "batch_size": 100,
        },
    }
    
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Scan status tracking
        self._status: Dict[str, ScanStatus] = {
            tier.value: ScanStatus(tier=tier.value)
            for tier in ScanTier
        }
        
        # Cached results
        self._hot_100: List[ScanResult] = []
        self._active_1000: List[ScanResult] = []
        self._full_universe: List[ScanResult] = []
        
        # Hot list tracking (previous top movers)
        self._previous_hot: Set[str] = set()
        
        # Callbacks
        self._on_scan_complete: Optional[Callable[[str, List[ScanResult]], Awaitable[None]]] = None
        
        # Load cached results on init
        self._load_cache()
        
        logger.info("UniverseScanner initialized")
    
    def set_callback(self, callback: Callable[[str, List[ScanResult]], Awaitable[None]]) -> None:
        """Set callback for when scans complete."""
        self._on_scan_complete = callback
    
    def get_status(self) -> Dict[str, dict]:
        """Get status of all scan tiers."""
        return {tier: status.to_dict() for tier, status in self._status.items()}
    
    def get_hot_100(self) -> List[ScanResult]:
        """Get cached hot 100 results."""
        return self._hot_100.copy()
    
    def get_active_1000(self) -> List[ScanResult]:
        """Get cached active 1000 results."""
        return self._active_1000.copy()
    
    def get_full_universe(self) -> List[ScanResult]:
        """Get cached full universe results."""
        return self._full_universe.copy()
    
    def get_top(self, count: int = 12, tier: Optional[str] = None) -> List[ScanResult]:
        """Get top N results by momentum score."""
        if tier == ScanTier.HOT_100.value:
            results = self._hot_100
        elif tier == ScanTier.ACTIVE_1000.value:
            results = self._active_1000
        else:
            # Use best available data
            results = self._hot_100 or self._active_1000 or self._full_universe
        
        sorted_results = sorted(results, key=lambda x: x.momentum_score, reverse=True)
        return sorted_results[:count]
    
    async def scan_hot_100(self) -> List[ScanResult]:
        """
        Quick scan of top 100 movers.
        
        Includes:
        - Previous scan's top 50
        - Current highest volume stocks
        - Stocks with biggest price moves
        """
        tier = ScanTier.HOT_100
        status = self._status[tier.value]
        status.is_running = True
        status.errors = 0
        start_time = datetime.now()
        
        logger.info("Starting Hot 100 scan...")
        
        try:
            # Get hot list symbols
            symbols = await self._get_hot_list()
            
            # Scan symbols
            results = await self._scan_batch(symbols[:100], tier.value)
            
            # Sort by momentum score
            results.sort(key=lambda x: x.momentum_score, reverse=True)
            
            # Update cache
            self._hot_100 = results
            
            # Update previous hot set for next scan
            self._previous_hot = set(r.symbol for r in results[:50])
            
            # Save to disk
            self._save_cache(tier.value, results)
            
            # Update status
            status.last_scan = datetime.now()
            status.symbols_scanned = len(results)
            status.duration_seconds = (datetime.now() - start_time).total_seconds()
            status.next_scan = datetime.now() + timedelta(minutes=15)
            
            logger.info(f"Hot 100 scan complete: {len(results)} symbols in {status.duration_seconds:.1f}s")
            
            # Callback
            if self._on_scan_complete:
                await self._on_scan_complete(tier.value, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Hot 100 scan failed: {e}")
            status.errors += 1
            return []
        finally:
            status.is_running = False
    
    async def scan_active_1000(self) -> List[ScanResult]:
        """
        Hourly scan of 1000 most active stocks.
        
        Filters:
        - Volume > 100,000
        - Price movement > 0.5%
        """
        tier = ScanTier.ACTIVE_1000
        status = self._status[tier.value]
        status.is_running = True
        status.errors = 0
        start_time = datetime.now()
        
        logger.info("Starting Active 1000 scan...")
        
        try:
            # Get active symbols
            symbols = await self._get_active_symbols(1000)
            
            # Scan in batches
            results = await self._scan_batched(symbols, tier.value, batch_size=100)
            
            # Sort by momentum score
            results.sort(key=lambda x: x.momentum_score, reverse=True)
            
            # Update cache
            self._active_1000 = results
            
            # Save to disk
            self._save_cache(tier.value, results)
            
            # Update status
            status.last_scan = datetime.now()
            status.symbols_scanned = len(results)
            status.duration_seconds = (datetime.now() - start_time).total_seconds()
            status.next_scan = datetime.now() + timedelta(minutes=60)
            
            logger.info(f"Active 1000 scan complete: {len(results)} symbols in {status.duration_seconds:.1f}s")
            
            # Callback
            if self._on_scan_complete:
                await self._on_scan_complete(tier.value, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Active 1000 scan failed: {e}")
            status.errors += 1
            return []
        finally:
            status.is_running = False
    
    async def scan_full_universe(self) -> List[ScanResult]:
        """
        Full scan of 12,000+ symbols.
        
        Runs pre-market and after-hours.
        Takes ~15-20 minutes to complete.
        """
        tier = ScanTier.FULL_UNIVERSE
        status = self._status[tier.value]
        status.is_running = True
        status.errors = 0
        start_time = datetime.now()
        
        logger.info("Starting Full Universe scan (12,000+ symbols)...")
        
        try:
            # Get all symbols from universe
            from src.data.symbol_universe import ensure_symbols_loaded
            universe = await ensure_symbols_loaded()
            all_symbols = universe.get_all_symbols()
            
            logger.info(f"Scanning {len(all_symbols)} symbols...")
            
            # Scan in batches with rate limiting
            results = await self._scan_batched(all_symbols, tier.value, batch_size=100, delay=0.5)
            
            # Sort by momentum score
            results.sort(key=lambda x: x.momentum_score, reverse=True)
            
            # Update cache
            self._full_universe = results
            
            # Save to disk
            self._save_cache(tier.value, results)
            
            # Update status
            status.last_scan = datetime.now()
            status.symbols_scanned = len(results)
            status.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Full Universe scan complete: {len(results)} symbols in {status.duration_seconds:.1f}s")
            
            # Callback
            if self._on_scan_complete:
                await self._on_scan_complete(tier.value, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Full Universe scan failed: {e}")
            status.errors += 1
            return []
        finally:
            status.is_running = False
    
    async def _get_hot_list(self) -> List[str]:
        """Get symbols for hot 100 scan."""
        hot_symbols = set()
        
        # Include previous top movers
        hot_symbols.update(self._previous_hot)
        
        # Add major indices and ETFs (always scan these)
        hot_symbols.update([
            "SPY", "QQQ", "IWM", "DIA", "VTI",
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
            "AMD", "INTC", "AVGO", "NFLX", "CRM",
            "JPM", "BAC", "GS", "V", "MA",
            "XOM", "CVX", "COP",
            "JNJ", "UNH", "PFE",
            "SOXL", "TQQQ", "UPRO",
        ])
        
        # If we have previous active 1000 results, add top movers from there
        if self._active_1000:
            top_movers = sorted(self._active_1000, key=lambda x: abs(x.price_change_pct), reverse=True)
            hot_symbols.update(r.symbol for r in top_movers[:50])
        
        # If we have full universe results, add top momentum
        if self._full_universe:
            top_momentum = sorted(self._full_universe, key=lambda x: x.momentum_score, reverse=True)
            hot_symbols.update(r.symbol for r in top_momentum[:30])
        
        return list(hot_symbols)
    
    async def _get_active_symbols(self, count: int) -> List[str]:
        """Get most active symbols by volume and movement."""
        from src.data.symbol_universe import ensure_symbols_loaded
        
        try:
            universe = await ensure_symbols_loaded()
            all_symbols = universe.get_all_symbols()
            
            # Start with all ETFs (usually more liquid)
            etfs = universe.get_all_etfs()
            
            # If we have previous full scan, use that for filtering
            if self._full_universe:
                # Get symbols with good volume and movement
                active = [
                    r.symbol for r in self._full_universe
                    if r.avg_volume > 100000 and abs(r.price_change_pct) > 0.5
                ]
                return (active + etfs)[:count]
            
            # Otherwise return a mix of popular stocks and ETFs
            popular = [
                # Tech
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC", "AVGO",
                # Finance
                "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP",
                # Healthcare
                "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "BMY",
                # Energy
                "XOM", "CVX", "COP", "SLB", "OXY", "EOG",
                # Consumer
                "WMT", "HD", "COST", "NKE", "MCD", "SBUX", "DIS",
                # Industrial
                "CAT", "DE", "BA", "UPS", "FDX", "GE",
            ]
            
            return (popular + etfs + all_symbols[:count - len(popular) - len(etfs)])[:count]
            
        except Exception as e:
            logger.error(f"Error getting active symbols: {e}")
            return []
    
    async def _scan_batch(self, symbols: List[str], tier: str) -> List[ScanResult]:
        """Scan a batch of symbols."""
        if not yf or not pd:
            logger.error("yfinance/pandas not available")
            return []
        
        results = []
        
        try:
            # Download data for batch
            symbol_str = " ".join(symbols)
            loop = asyncio.get_event_loop()
            
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    symbol_str,
                    period="5d",
                    interval="1d",
                    progress=False,
                    threads=True,
                )
            )
            
            if data.empty:
                return results
            
            # Handle single vs multiple symbols
            if len(symbols) == 1:
                data.columns = pd.MultiIndex.from_product([data.columns, symbols])
            
            for symbol in symbols:
                try:
                    result = self._process_symbol_data(symbol, data, tier)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Error processing {symbol}: {e}")
            
        except Exception as e:
            logger.error(f"Batch scan error: {e}")
        
        return results
    
    async def _scan_batched(
        self,
        symbols: List[str],
        tier: str,
        batch_size: int = 100,
        delay: float = 0.3,
    ) -> List[ScanResult]:
        """Scan symbols in batches with rate limiting."""
        results = []
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            try:
                batch_results = await self._scan_batch(batch, tier)
                results.extend(batch_results)
                
                # Progress logging for large scans
                if tier == ScanTier.FULL_UNIVERSE.value and i > 0 and i % 500 == 0:
                    logger.info(f"Full scan progress: {i}/{len(symbols)} ({len(results)} results)")
                
            except Exception as e:
                logger.error(f"Batch {i}-{i+batch_size} failed: {e}")
            
            # Rate limiting
            if i + batch_size < len(symbols):
                await asyncio.sleep(delay)
        
        return results
    
    def _process_symbol_data(self, symbol: str, data: pd.DataFrame, tier: str) -> Optional[ScanResult]:
        """Process downloaded data for a single symbol."""
        try:
            if ('Close', symbol) not in data.columns:
                return None
            
            close = data[('Close', symbol)].dropna()
            volume = data[('Volume', symbol)].dropna()
            
            if len(close) < 2:
                return None
            
            current_price = float(close.iloc[-1])
            previous_close = float(close.iloc[-2]) if len(close) > 1 else current_price
            
            price_change = current_price - previous_close
            price_change_pct = (price_change / previous_close) * 100 if previous_close > 0 else 0
            
            current_volume = int(volume.iloc[-1]) if len(volume) > 0 else 0
            avg_volume = int(volume.mean()) if len(volume) > 0 else 0
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Calculate momentum score
            momentum_score = self._calculate_momentum_score(close, volume)
            
            # Calculate RSI if enough data
            rsi = self._calculate_rsi(close) if len(close) >= 14 else None
            
            return ScanResult(
                symbol=symbol,
                tier=tier,
                current_price=round(current_price, 2),
                previous_close=round(previous_close, 2),
                price_change=round(price_change, 2),
                price_change_pct=round(price_change_pct, 2),
                volume=current_volume,
                avg_volume=avg_volume,
                volume_ratio=round(volume_ratio, 2),
                momentum_score=round(momentum_score, 1),
                rsi=round(rsi, 1) if rsi else None,
                timestamp=datetime.now().isoformat(),
            )
            
        except Exception as e:
            logger.debug(f"Error processing {symbol}: {e}")
            return None
    
    def _calculate_momentum_score(self, prices: pd.Series, volumes: pd.Series) -> float:
        """
        Calculate composite momentum score (0-100).
        
        Components:
        - Price momentum (rate of change)
        - Trend consistency
        - Volume confirmation
        """
        if len(prices) < 2:
            return 50.0
        
        try:
            # Price momentum (ROC)
            roc = ((prices.iloc[-1] / prices.iloc[0]) - 1) * 100
            roc_score = min(max(roc * 5 + 50, 0), 100)  # Normalize
            
            # Trend consistency
            returns = prices.pct_change().dropna()
            up_ratio = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0.5
            consistency_score = up_ratio * 100
            
            # Volume momentum
            if len(volumes) >= 2:
                vol_change = (volumes.iloc[-1] / volumes.mean()) if volumes.mean() > 0 else 1
                vol_score = min(vol_change * 20, 100)  # Cap at 100
            else:
                vol_score = 50
            
            # Weighted composite
            momentum = (roc_score * 0.5) + (consistency_score * 0.3) + (vol_score * 0.2)
            
            return max(0, min(100, momentum))
            
        except Exception:
            return 50.0
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """Calculate RSI."""
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
    
    def _save_cache(self, tier: str, results: List[ScanResult]) -> None:
        """Save scan results to disk."""
        cache_file = CACHE_DIR / f"{tier}.json"
        
        try:
            data = {
                "tier": tier,
                "timestamp": datetime.now().isoformat(),
                "count": len(results),
                "results": [r.to_dict() for r in results],
            }
            
            with open(cache_file, "w") as f:
                json.dump(data, f)
            
            logger.debug(f"Saved {len(results)} results to {cache_file}")
            
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def _load_cache(self) -> None:
        """Load cached results from disk."""
        for tier in [ScanTier.HOT_100, ScanTier.ACTIVE_1000, ScanTier.FULL_UNIVERSE]:
            cache_file = CACHE_DIR / f"{tier.value}.json"
            
            if not cache_file.exists():
                continue
            
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                
                results = [
                    ScanResult(
                        symbol=r["symbol"],
                        tier=r["tier"],
                        current_price=r.get("current_price", 0),
                        previous_close=r.get("previous_close", 0),
                        price_change=r.get("price_change", 0),
                        price_change_pct=r.get("price_change_pct", 0),
                        volume=r.get("volume", 0),
                        avg_volume=r.get("avg_volume", 0),
                        volume_ratio=r.get("volume_ratio", 0),
                        momentum_score=r.get("momentum_score", 0),
                        rsi=r.get("rsi"),
                        sector=r.get("sector", ""),
                        timestamp=r.get("timestamp"),
                    )
                    for r in data.get("results", [])
                ]
                
                if tier == ScanTier.HOT_100:
                    self._hot_100 = results
                elif tier == ScanTier.ACTIVE_1000:
                    self._active_1000 = results
                elif tier == ScanTier.FULL_UNIVERSE:
                    self._full_universe = results
                
                # Update status
                self._status[tier.value].last_scan = datetime.fromisoformat(data["timestamp"])
                self._status[tier.value].symbols_scanned = len(results)
                
                logger.info(f"Loaded {len(results)} cached results for {tier.value}")
                
            except Exception as e:
                logger.error(f"Error loading cache for {tier.value}: {e}")


# Global instance
_scanner: Optional[UniverseScanner] = None
_scanner_lock = threading.Lock()


def get_universe_scanner() -> UniverseScanner:
    """Get the global universe scanner instance."""
    global _scanner
    
    with _scanner_lock:
        if _scanner is None:
            _scanner = UniverseScanner()
        return _scanner

