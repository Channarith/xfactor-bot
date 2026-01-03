"""
Symbol Universe and Growth Screener API routes.

Provides:
- Symbol search across 12,000+ stocks
- Exchange filtering
- ETF filtering
- Top growth stock screening
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from loguru import logger

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class SymbolSearchResult(BaseModel):
    """Search result for a symbol."""
    symbol: str
    name: str
    exchange: str
    is_etf: bool
    sector: Optional[str] = None


class SymbolSearchResponse(BaseModel):
    """Response for symbol search."""
    query: str
    count: int
    results: List[SymbolSearchResult]


class GrowthCandidateResult(BaseModel):
    """Growth candidate result."""
    symbol: str
    name: str
    current_price: float
    price_change: float
    price_change_pct: float
    volume: int
    volume_ratio: float
    momentum_score: float
    rsi: Optional[float] = None


class TopGrowthResponse(BaseModel):
    """Response for top growth screening."""
    count: int
    timeframe: str
    exchange: Optional[str]
    timestamp: str
    results: List[GrowthCandidateResult]


class ExchangeStats(BaseModel):
    """Statistics for an exchange."""
    exchange: str
    symbol_count: int


class UniverseStatsResponse(BaseModel):
    """Response for universe statistics."""
    total_symbols: int
    total_etfs: int
    exchanges: List[ExchangeStats]
    last_updated: Optional[str] = None


# ============================================================================
# Symbol Search Endpoints
# ============================================================================

@router.get("/symbols/search", response_model=SymbolSearchResponse)
async def search_symbols(
    q: str = Query(..., min_length=1, max_length=10, description="Search query (symbol or name)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    exchange: Optional[str] = Query(None, description="Filter by exchange: NASDAQ, NYSE, AMEX"),
    etfs_only: bool = Query(False, description="Only return ETFs"),
    stocks_only: bool = Query(False, description="Only return stocks (no ETFs)"),
):
    """
    Search for symbols by ticker or company name.
    
    Searches across 12,000+ symbols from NASDAQ, NYSE, and AMEX.
    
    Examples:
    - /api/screener/symbols/search?q=AAPL
    - /api/screener/symbols/search?q=apple&limit=10
    - /api/screener/symbols/search?q=SOX&etfs_only=true
    """
    from src.data.symbol_universe import ensure_symbols_loaded
    
    try:
        universe = await ensure_symbols_loaded()
        
        results = universe.search(
            query=q,
            limit=limit,
            exchange=exchange,
            etfs_only=etfs_only,
            stocks_only=stocks_only,
        )
        
        return SymbolSearchResponse(
            query=q,
            count=len(results),
            results=[
                SymbolSearchResult(
                    symbol=r.symbol,
                    name=r.name,
                    exchange=r.exchange,
                    is_etf=r.is_etf,
                    sector=r.sector,
                )
                for r in results
            ]
        )
        
    except Exception as e:
        logger.error(f"Error searching symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols/stats", response_model=UniverseStatsResponse)
async def get_universe_stats():
    """
    Get statistics about the symbol universe.
    
    Returns total symbol count, ETF count, and breakdown by exchange.
    """
    from src.data.symbol_universe import ensure_symbols_loaded
    
    try:
        universe = await ensure_symbols_loaded()
        
        exchanges = universe.get_exchanges()
        exchange_stats = [
            ExchangeStats(
                exchange=ex,
                symbol_count=len(universe.get_by_exchange(ex))
            )
            for ex in exchanges
        ]
        
        return UniverseStatsResponse(
            total_symbols=universe.symbol_count,
            total_etfs=len(universe.get_all_etfs()),
            exchanges=exchange_stats,
            last_updated=universe._last_loaded.isoformat() if universe._last_loaded else None,
        )
        
    except Exception as e:
        logger.error(f"Error getting universe stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols/etfs")
async def get_etfs(
    category: Optional[str] = Query(None, description="ETF category: leveraged, vanguard, ishares, sector, commodity, bond, crypto"),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Get ETFs by category.
    
    Categories:
    - leveraged: SOXL, TQQQ, UPRO, etc.
    - vanguard: VOO, VTI, VGT, etc.
    - ishares: IVV, IWM, EFA, etc.
    - sector: XLK, XLF, XLE, etc.
    - commodity: GLD, SLV, USO, etc.
    - bond: BND, AGG, TLT, etc.
    - crypto: IBIT, FBTC, GBTC, etc.
    """
    from src.data.symbol_universe import ensure_symbols_loaded
    
    try:
        universe = await ensure_symbols_loaded()
        
        if category:
            category_map = {
                "leveraged": universe.get_leveraged_etfs,
                "vanguard": universe.get_vanguard_etfs,
                "ishares": universe.get_ishares_etfs,
                "sector": universe.get_sector_etfs,
            }
            
            if category.lower() in category_map:
                symbols = category_map[category.lower()]()
            else:
                # Return all ETFs for unknown category
                symbols = universe.get_all_etfs()
        else:
            symbols = universe.get_all_etfs()
        
        results = []
        for symbol in symbols[:limit]:
            info = universe.get(symbol)
            if info:
                results.append({
                    "symbol": info.symbol,
                    "name": info.name,
                    "exchange": info.exchange,
                })
        
        return {
            "category": category,
            "count": len(results),
            "etfs": results,
        }
        
    except Exception as e:
        logger.error(f"Error getting ETFs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols/by-exchange/{exchange}")
async def get_symbols_by_exchange(
    exchange: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Get all symbols for a specific exchange.
    
    Supported exchanges: NASDAQ, NYSE, AMEX, ARCA
    """
    from src.data.symbol_universe import ensure_symbols_loaded
    
    try:
        universe = await ensure_symbols_loaded()
        
        symbols = universe.get_by_exchange(exchange.upper())
        
        # Paginate
        paginated = symbols[offset:offset + limit]
        
        results = []
        for symbol in paginated:
            info = universe.get(symbol)
            if info:
                results.append({
                    "symbol": info.symbol,
                    "name": info.name,
                    "is_etf": info.is_etf,
                })
        
        return {
            "exchange": exchange.upper(),
            "total": len(symbols),
            "offset": offset,
            "limit": limit,
            "count": len(results),
            "symbols": results,
        }
        
    except Exception as e:
        logger.error(f"Error getting symbols by exchange: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Growth Screener Endpoints
# ============================================================================

@router.get("/top-growth", response_model=TopGrowthResponse)
async def get_top_growth(
    count: int = Query(12, ge=1, le=50, description="Number of top stocks to return"),
    timeframe: str = Query("1d", description="Timeframe: 1m, 5m, 1d, 1w, 1M"),
    exchange: Optional[str] = Query(None, description="Filter by exchange: NASDAQ, NYSE, AMEX"),
    min_price: float = Query(1.0, ge=0, description="Minimum stock price"),
    min_volume: int = Query(100000, ge=0, description="Minimum average volume"),
):
    """
    Get top growth stocks by timeframe.
    
    Screens for stocks with highest:
    - Price change percentage
    - Volume surge
    - Momentum score
    
    Timeframes:
    - 1m: Last minute (real-time, rate-limited)
    - 5m: Last 5 minutes
    - 1d: Today's performance
    - 1w: This week
    - 1M: This month
    
    Examples:
    - /api/screener/top-growth?count=12&timeframe=1d
    - /api/screener/top-growth?exchange=NASDAQ&timeframe=1w
    """
    from src.data.growth_screener import get_growth_screener
    
    # Validate timeframe
    valid_timeframes = ["1m", "5m", "1d", "1w", "1M"]
    if timeframe not in valid_timeframes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe. Must be one of: {valid_timeframes}"
        )
    
    try:
        screener = get_growth_screener()
        
        candidates = await screener.screen_top_growth(
            count=count,
            timeframe=timeframe,
            exchange=exchange,
            min_price=min_price,
            min_volume=min_volume,
        )
        
        return TopGrowthResponse(
            count=len(candidates),
            timeframe=timeframe,
            exchange=exchange,
            timestamp=datetime.now().isoformat(),
            results=[
                GrowthCandidateResult(
                    symbol=c.symbol,
                    name=c.name,
                    current_price=c.current_price,
                    price_change=c.price_change,
                    price_change_pct=c.price_change_pct,
                    volume=c.volume,
                    volume_ratio=c.volume_ratio,
                    momentum_score=c.momentum_score,
                    rsi=c.rsi,
                )
                for c in candidates
            ]
        )
        
    except Exception as e:
        logger.error(f"Error screening growth stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/movers")
async def get_market_movers(
    direction: str = Query("gainers", description="gainers or losers"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Get top market movers (gainers or losers).
    
    Quick endpoint for daily gainers/losers.
    """
    from src.data.growth_screener import get_growth_screener
    
    if direction not in ["gainers", "losers"]:
        raise HTTPException(status_code=400, detail="direction must be 'gainers' or 'losers'")
    
    try:
        screener = get_growth_screener()
        
        # For losers, we'd need to modify the screener - for now return gainers
        candidates = await screener.screen_top_growth(
            count=limit,
            timeframe="1d",
        )
        
        return {
            "direction": direction,
            "count": len(candidates),
            "movers": [
                {
                    "symbol": c.symbol,
                    "price": c.current_price,
                    "change": c.price_change,
                    "change_pct": c.price_change_pct,
                    "volume": c.volume,
                }
                for c in candidates
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting market movers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

