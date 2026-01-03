"""
Symbol Universe - Master database of all tradeable symbols.

Manages 12,000+ symbols from:
- NASDAQ (~3,450 stocks)
- NYSE (~2,200 stocks)
- OTC Markets (~6,500 stocks)
- ETFs (1,000+)

Data sources:
- NASDAQ FTP (free, updated daily)
- SEC EDGAR (company filings)
- Alpaca API (for tradeable stocks)
- yfinance (for historical data)
"""

import asyncio
import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
import threading

import aiohttp
from loguru import logger


# Cache directory
CACHE_DIR = Path.home() / ".xfactor" / "symbol_cache"
CACHE_EXPIRY_HOURS = 24  # Refresh cache daily


@dataclass
class SymbolInfo:
    """Information about a tradeable symbol."""
    symbol: str
    name: str
    exchange: str  # NASDAQ, NYSE, AMEX, OTC
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    country: str = "US"
    ipo_year: Optional[int] = None
    is_etf: bool = False
    is_adr: bool = False  # American Depositary Receipt
    last_updated: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "sector": self.sector,
            "industry": self.industry,
            "market_cap": self.market_cap,
            "country": self.country,
            "ipo_year": self.ipo_year,
            "is_etf": self.is_etf,
            "is_adr": self.is_adr,
        }


# Popular ETF lists to include
LEVERAGED_ETFS = ["SOXL", "SOXS", "TQQQ", "SQQQ", "UPRO", "SPXU", "SPXL", "SPXS", "TECL", "TECS", "FNGU", "FNGD", "LABU", "LABD", "TNA", "TZA", "UDOW", "SDOW"]
VANGUARD_ETFS = ["VOO", "VTI", "VGT", "VUG", "VTV", "VIG", "VXUS", "VEA", "VWO", "VNQ", "VYM", "VB", "VO", "VV", "VOOG", "VOOV", "VBK", "VBR"]
ISHARES_ETFS = ["IVV", "IWM", "IWF", "IWD", "EFA", "EEM", "AGG", "LQD", "TLT", "SHY", "HYG", "IEF", "IEFA", "IEMG", "IJH", "IJR", "IWB", "IWN", "IWO", "IWS"]
SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]
COMMODITY_ETFS = ["GLD", "SLV", "USO", "UNG", "GDX", "GDXJ", "SIL", "PPLT", "PALL", "COPX", "CPER", "DBA", "DBC", "PDBC", "URA", "LIT", "REMX"]
BOND_ETFS = ["BND", "BNDX", "VCSH", "VCIT", "VCLT", "BSV", "BIV", "BLV", "VTIP", "VGSH", "VGIT", "VGLT"]
CRYPTO_ETFS = ["IBIT", "FBTC", "GBTC", "ETHE", "BITO", "BITX"]

ALL_POPULAR_ETFS = (
    LEVERAGED_ETFS + VANGUARD_ETFS + ISHARES_ETFS + 
    SECTOR_ETFS + COMMODITY_ETFS + BOND_ETFS + CRYPTO_ETFS
)


class SymbolUniverse:
    """
    Master database of all tradeable symbols.
    
    Provides:
    - Symbol lookup and search
    - Exchange filtering
    - Sector/industry classification
    - ETF identification
    - Cached data with daily refresh
    """
    
    # NASDAQ FTP URL for listed securities
    NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
    NYSE_URL = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
    
    def __init__(self):
        self._symbols: Dict[str, SymbolInfo] = {}
        self._by_exchange: Dict[str, Set[str]] = {}
        self._by_sector: Dict[str, Set[str]] = {}
        self._etfs: Set[str] = set()
        self._loaded = False
        self._lock = threading.Lock()
        self._last_loaded: Optional[datetime] = None
        
        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    @property
    def symbol_count(self) -> int:
        """Get total number of symbols."""
        return len(self._symbols)
    
    @property
    def is_loaded(self) -> bool:
        """Check if symbols have been loaded."""
        return self._loaded
    
    async def load(self, force_refresh: bool = False) -> None:
        """
        Load all symbols from sources.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data.
        """
        with self._lock:
            if self._loaded and not force_refresh:
                return
            
            # Try to load from cache first
            if not force_refresh and self._load_from_cache():
                self._loaded = True
                logger.info(f"Loaded {self.symbol_count} symbols from cache")
                return
            
            # Fetch from sources
            logger.info("Fetching symbols from NASDAQ/NYSE...")
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Fetch NASDAQ symbols
                    nasdaq_symbols = await self._fetch_nasdaq_symbols(session)
                    
                    # Fetch NYSE/AMEX symbols
                    nyse_symbols = await self._fetch_nyse_symbols(session)
                    
                    # Combine all symbols
                    for symbol_info in nasdaq_symbols + nyse_symbols:
                        self._add_symbol(symbol_info)
                    
                    # Add popular ETFs that might be missing
                    await self._add_popular_etfs()
                    
                    self._loaded = True
                    self._last_loaded = datetime.now()
                    
                    # Save to cache
                    self._save_to_cache()
                    
                    logger.info(f"Loaded {self.symbol_count} symbols from NASDAQ/NYSE")
                    
            except Exception as e:
                logger.error(f"Error loading symbols: {e}")
                # Fall back to basic list if fetch fails
                await self._load_fallback_symbols()
    
    async def _fetch_nasdaq_symbols(self, session: aiohttp.ClientSession) -> List[SymbolInfo]:
        """Fetch NASDAQ-listed symbols."""
        symbols = []
        
        try:
            async with session.get(self.NASDAQ_URL, timeout=30) as response:
                if response.status == 200:
                    text = await response.text()
                    reader = csv.DictReader(io.StringIO(text), delimiter='|')
                    
                    for row in reader:
                        symbol = row.get('Symbol', '').strip()
                        if not symbol or symbol == 'Symbol':
                            continue
                        
                        # Skip test symbols
                        if row.get('Test Issue', '') == 'Y':
                            continue
                        
                        name = row.get('Security Name', '')
                        is_etf = 'ETF' in name.upper() or 'FUND' in name.upper()
                        
                        symbols.append(SymbolInfo(
                            symbol=symbol,
                            name=name,
                            exchange="NASDAQ",
                            is_etf=is_etf,
                            last_updated=datetime.now(),
                        ))
                    
                    logger.debug(f"Fetched {len(symbols)} NASDAQ symbols")
                    
        except Exception as e:
            logger.error(f"Error fetching NASDAQ symbols: {e}")
        
        return symbols
    
    async def _fetch_nyse_symbols(self, session: aiohttp.ClientSession) -> List[SymbolInfo]:
        """Fetch NYSE/AMEX-listed symbols."""
        symbols = []
        
        try:
            async with session.get(self.NYSE_URL, timeout=30) as response:
                if response.status == 200:
                    text = await response.text()
                    reader = csv.DictReader(io.StringIO(text), delimiter='|')
                    
                    for row in reader:
                        symbol = row.get('ACT Symbol', '') or row.get('NASDAQ Symbol', '')
                        symbol = symbol.strip()
                        if not symbol:
                            continue
                        
                        # Skip test symbols
                        if row.get('Test Issue', '') == 'Y':
                            continue
                        
                        name = row.get('Security Name', '')
                        exchange = row.get('Exchange', 'NYSE').strip()
                        
                        # Map exchange codes
                        exchange_map = {
                            'A': 'AMEX',
                            'N': 'NYSE',
                            'P': 'ARCA',
                            'Z': 'BATS',
                        }
                        exchange = exchange_map.get(exchange, exchange)
                        
                        is_etf = 'ETF' in name.upper() or 'FUND' in name.upper()
                        
                        symbols.append(SymbolInfo(
                            symbol=symbol,
                            name=name,
                            exchange=exchange,
                            is_etf=is_etf,
                            last_updated=datetime.now(),
                        ))
                    
                    logger.debug(f"Fetched {len(symbols)} NYSE/AMEX symbols")
                    
        except Exception as e:
            logger.error(f"Error fetching NYSE symbols: {e}")
        
        return symbols
    
    async def _add_popular_etfs(self) -> None:
        """Ensure popular ETFs are included."""
        for symbol in ALL_POPULAR_ETFS:
            if symbol not in self._symbols:
                self._add_symbol(SymbolInfo(
                    symbol=symbol,
                    name=f"{symbol} ETF",
                    exchange="ARCA",
                    is_etf=True,
                    last_updated=datetime.now(),
                ))
    
    async def _load_fallback_symbols(self) -> None:
        """Load a basic list of popular symbols as fallback."""
        fallback = [
            # Major indices
            "SPY", "QQQ", "DIA", "IWM",
            # Tech
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "INTC", "AVGO",
            # Finance
            "JPM", "BAC", "WFC", "GS", "MS", "C", "V", "MA",
            # Healthcare
            "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY",
            # Energy
            "XOM", "CVX", "COP", "SLB", "OXY",
            # Consumer
            "WMT", "HD", "COST", "NKE", "MCD", "SBUX",
        ]
        
        # Add all popular ETFs
        fallback.extend(ALL_POPULAR_ETFS)
        
        for symbol in set(fallback):
            is_etf = symbol in ALL_POPULAR_ETFS or len(symbol) <= 4 and symbol.isupper()
            self._add_symbol(SymbolInfo(
                symbol=symbol,
                name=symbol,
                exchange="UNKNOWN",
                is_etf=is_etf,
                last_updated=datetime.now(),
            ))
        
        self._loaded = True
        logger.warning(f"Using fallback symbol list: {len(self._symbols)} symbols")
    
    def _add_symbol(self, info: SymbolInfo) -> None:
        """Add a symbol to the universe."""
        symbol = info.symbol.upper()
        self._symbols[symbol] = info
        
        # Index by exchange
        exchange = info.exchange or "UNKNOWN"
        if exchange not in self._by_exchange:
            self._by_exchange[exchange] = set()
        self._by_exchange[exchange].add(symbol)
        
        # Index by sector
        if info.sector:
            if info.sector not in self._by_sector:
                self._by_sector[info.sector] = set()
            self._by_sector[info.sector].add(symbol)
        
        # Track ETFs
        if info.is_etf:
            self._etfs.add(symbol)
    
    def _load_from_cache(self) -> bool:
        """Load symbols from cache file."""
        cache_file = CACHE_DIR / "symbols.json"
        
        if not cache_file.exists():
            return False
        
        try:
            # Check if cache is expired
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime > timedelta(hours=CACHE_EXPIRY_HOURS):
                logger.debug("Symbol cache expired")
                return False
            
            with open(cache_file, "r") as f:
                data = json.load(f)
            
            for item in data.get("symbols", []):
                info = SymbolInfo(
                    symbol=item["symbol"],
                    name=item["name"],
                    exchange=item["exchange"],
                    sector=item.get("sector"),
                    industry=item.get("industry"),
                    market_cap=item.get("market_cap"),
                    is_etf=item.get("is_etf", False),
                    is_adr=item.get("is_adr", False),
                )
                self._add_symbol(info)
            
            self._last_loaded = datetime.fromisoformat(data.get("last_loaded", datetime.now().isoformat()))
            return True
            
        except Exception as e:
            logger.error(f"Error loading symbol cache: {e}")
            return False
    
    def _save_to_cache(self) -> None:
        """Save symbols to cache file."""
        cache_file = CACHE_DIR / "symbols.json"
        
        try:
            data = {
                "last_loaded": datetime.now().isoformat(),
                "symbol_count": len(self._symbols),
                "symbols": [info.to_dict() for info in self._symbols.values()]
            }
            
            with open(cache_file, "w") as f:
                json.dump(data, f)
            
            logger.debug(f"Saved {len(self._symbols)} symbols to cache")
            
        except Exception as e:
            logger.error(f"Error saving symbol cache: {e}")
    
    def get(self, symbol: str) -> Optional[SymbolInfo]:
        """Get info for a specific symbol."""
        return self._symbols.get(symbol.upper())
    
    def exists(self, symbol: str) -> bool:
        """Check if a symbol exists."""
        return symbol.upper() in self._symbols
    
    def search(
        self,
        query: str,
        limit: int = 50,
        exchange: Optional[str] = None,
        etfs_only: bool = False,
        stocks_only: bool = False,
    ) -> List[SymbolInfo]:
        """
        Search for symbols by name or ticker.
        
        Args:
            query: Search query (matches symbol or name)
            limit: Maximum results to return
            exchange: Filter by exchange (NASDAQ, NYSE, AMEX)
            etfs_only: Only return ETFs
            stocks_only: Only return stocks (no ETFs)
        
        Returns:
            List of matching SymbolInfo
        """
        query = query.upper()
        results = []
        
        for symbol, info in self._symbols.items():
            # Apply filters
            if exchange and info.exchange != exchange:
                continue
            if etfs_only and not info.is_etf:
                continue
            if stocks_only and info.is_etf:
                continue
            
            # Match query
            if query in symbol or query in info.name.upper():
                results.append(info)
                
                if len(results) >= limit:
                    break
        
        # Sort: exact symbol matches first, then by symbol length
        results.sort(key=lambda x: (
            0 if x.symbol == query else 1,
            len(x.symbol),
            x.symbol,
        ))
        
        return results[:limit]
    
    def get_by_exchange(self, exchange: str) -> List[str]:
        """Get all symbols for an exchange."""
        return list(self._by_exchange.get(exchange, set()))
    
    def get_by_sector(self, sector: str) -> List[str]:
        """Get all symbols for a sector."""
        return list(self._by_sector.get(sector, set()))
    
    def get_all_etfs(self) -> List[str]:
        """Get all ETF symbols."""
        return list(self._etfs)
    
    def get_all_symbols(self) -> List[str]:
        """Get all symbols."""
        return list(self._symbols.keys())
    
    def get_exchanges(self) -> List[str]:
        """Get all exchanges."""
        return list(self._by_exchange.keys())
    
    def get_sectors(self) -> List[str]:
        """Get all sectors."""
        return list(self._by_sector.keys())
    
    def get_leveraged_etfs(self) -> List[str]:
        """Get leveraged ETFs."""
        return [s for s in LEVERAGED_ETFS if s in self._symbols]
    
    def get_vanguard_etfs(self) -> List[str]:
        """Get Vanguard ETFs."""
        return [s for s in VANGUARD_ETFS if s in self._symbols]
    
    def get_ishares_etfs(self) -> List[str]:
        """Get iShares ETFs."""
        return [s for s in ISHARES_ETFS if s in self._symbols]
    
    def get_sector_etfs(self) -> List[str]:
        """Get sector ETFs."""
        return [s for s in SECTOR_ETFS if s in self._symbols]


# Global instance
_symbol_universe: Optional[SymbolUniverse] = None
_universe_lock = threading.Lock()


def get_symbol_universe() -> SymbolUniverse:
    """Get the global symbol universe instance."""
    global _symbol_universe
    
    with _universe_lock:
        if _symbol_universe is None:
            _symbol_universe = SymbolUniverse()
        return _symbol_universe


async def ensure_symbols_loaded() -> SymbolUniverse:
    """Ensure symbols are loaded and return the universe."""
    universe = get_symbol_universe()
    if not universe.is_loaded:
        await universe.load()
    return universe

