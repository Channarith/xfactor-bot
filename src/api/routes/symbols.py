"""
Symbol Search API Routes

Provides endpoints for searching stocks across ALL global exchanges.
Users can search by ticker symbol, company name, or browse by exchange/sector.
"""

from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/symbols", tags=["symbols"])


class SymbolInfo(BaseModel):
    """Information about a stock symbol."""
    symbol: str = Field(..., description="Ticker symbol (e.g., AAPL, 7203.T)")
    name: str = Field(..., description="Company name")
    exchange: str = Field(..., description="Exchange code (e.g., NYSE, TSE)")
    exchange_name: str = Field("", description="Full exchange name")
    type: str = Field("stock", description="Asset type: stock, etf, adr, index")
    currency: str = Field("USD", description="Trading currency")
    country: str = Field("", description="Country of listing")
    sector: str = Field("", description="Industry sector")
    industry: str = Field("", description="Specific industry")
    market_cap: Optional[float] = Field(None, description="Market capitalization")


class SearchResponse(BaseModel):
    """Symbol search response."""
    query: str
    total_results: int
    results: List[SymbolInfo]
    exchanges_searched: List[str]


class ExchangeInfo(BaseModel):
    """Information about a stock exchange."""
    code: str
    name: str
    country: str
    region: str
    currency: str
    timezone: str
    suffix: str
    stock_count: int
    trading_hours: str
    is_open: bool = False


class ExchangesResponse(BaseModel):
    """List of all supported exchanges."""
    total_exchanges: int
    total_stocks: int
    exchanges: List[ExchangeInfo]


# ============================================================================
# Symbol Search using yfinance
# ============================================================================
async def search_symbols_yfinance(query: str, limit: int = 50) -> List[SymbolInfo]:
    """Search for symbols using yfinance."""
    try:
        import yfinance as yf
        
        # yfinance doesn't have a direct search API, but we can try to fetch info
        # For better search, we'd use a service like Yahoo Finance search API
        
        # Try the query as a direct ticker first
        results = []
        
        try:
            ticker = yf.Ticker(query.upper())
            info = ticker.info
            
            if info and info.get("symbol"):
                results.append(SymbolInfo(
                    symbol=info.get("symbol", query.upper()),
                    name=info.get("longName") or info.get("shortName", ""),
                    exchange=info.get("exchange", ""),
                    exchange_name=info.get("exchangeTimezoneName", ""),
                    type=info.get("quoteType", "stock").lower(),
                    currency=info.get("currency", "USD"),
                    country=info.get("country", ""),
                    sector=info.get("sector", ""),
                    industry=info.get("industry", ""),
                    market_cap=info.get("marketCap"),
                ))
        except Exception as e:
            logger.debug(f"Direct ticker lookup failed for {query}: {e}")
        
        return results
        
    except ImportError:
        logger.warning("yfinance not installed, using fallback search")
        return []
    except Exception as e:
        logger.error(f"Error searching symbols with yfinance: {e}")
        return []


async def search_symbols_yahoo_api(query: str, limit: int = 50) -> List[SymbolInfo]:
    """Search symbols using Yahoo Finance search API."""
    try:
        import aiohttp
        
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {
            "q": query,
            "quotesCount": str(limit),
            "newsCount": "0",
            "enableFuzzyQuery": "true",
            "quotesQueryId": "tss_match_phrase_query",
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    quotes = data.get("quotes", [])
                    
                    results = []
                    for q in quotes:
                        # Filter for stocks, ETFs, and indices
                        quote_type = q.get("quoteType", "").upper()
                        if quote_type in ["EQUITY", "ETF", "INDEX", "MUTUALFUND"]:
                            results.append(SymbolInfo(
                                symbol=q.get("symbol", ""),
                                name=q.get("longname") or q.get("shortname", ""),
                                exchange=q.get("exchange", ""),
                                exchange_name=q.get("exchDisp", ""),
                                type=quote_type.lower() if quote_type != "EQUITY" else "stock",
                                currency=q.get("currency", "USD"),
                                country="",  # Not provided in search results
                                sector=q.get("sector", ""),
                                industry=q.get("industry", ""),
                                market_cap=None,
                            ))
                    
                    return results
        
        return []
        
    except Exception as e:
        logger.error(f"Error searching Yahoo Finance API: {e}")
        return []


# ============================================================================
# API Endpoints
# ============================================================================
@router.get("/search", response_model=SearchResponse)
async def search_symbols(
    q: str = Query(..., min_length=1, max_length=100, description="Search query (ticker or company name)"),
    exchange: Optional[str] = Query(None, description="Filter by exchange code (e.g., NYSE, TSE)"),
    type: Optional[str] = Query(None, description="Filter by type: stock, etf, adr, index"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
) -> SearchResponse:
    """
    Search for stocks across ALL global exchanges.
    
    Search by:
    - Ticker symbol (e.g., "AAPL", "7203" for Toyota on TSE)
    - Company name (e.g., "Apple", "Toyota")
    - Partial match (e.g., "micro" finds Microsoft, Micron, etc.)
    
    Supports 40+ exchanges worldwide including NYSE, NASDAQ, LSE, TSE, 
    Shanghai, Hong Kong, Toronto, ASX, and more.
    """
    try:
        # Try Yahoo Finance API first (faster, more comprehensive)
        results = await search_symbols_yahoo_api(q, limit)
        
        # Fallback to yfinance if Yahoo API fails
        if not results:
            results = await search_symbols_yfinance(q, limit)
        
        # Filter by exchange if specified
        if exchange:
            exchange_upper = exchange.upper()
            results = [r for r in results if exchange_upper in r.exchange.upper()]
        
        # Filter by type if specified
        if type:
            type_lower = type.lower()
            results = [r for r in results if r.type == type_lower]
        
        # Get list of exchanges searched
        from src.config.exchanges import ALL_EXCHANGES
        exchanges_searched = list(ALL_EXCHANGES.keys())
        
        return SearchResponse(
            query=q,
            total_results=len(results),
            results=results[:limit],
            exchanges_searched=exchanges_searched,
        )
        
    except Exception as e:
        logger.error(f"Error in symbol search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lookup/{symbol}", response_model=SymbolInfo)
async def lookup_symbol(
    symbol: str,
) -> SymbolInfo:
    """
    Get detailed information for a specific symbol.
    
    Supports any global stock symbol with exchange suffix:
    - US: AAPL, MSFT, NVDA
    - UK: HSBA.L, BP.L, AZN.L
    - Japan: 7203.T (Toyota), 6758.T (Sony)
    - Hong Kong: 0005.HK (HSBC), 9988.HK (Alibaba)
    - Germany: SAP.DE, BMW.DE
    - China: 600519.SS (Kweichow Moutai)
    - Australia: BHP.AX, CBA.AX
    """
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        
        if not info or not info.get("symbol"):
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
        
        return SymbolInfo(
            symbol=info.get("symbol", symbol.upper()),
            name=info.get("longName") or info.get("shortName", ""),
            exchange=info.get("exchange", ""),
            exchange_name=info.get("exchangeTimezoneName", ""),
            type=info.get("quoteType", "stock").lower(),
            currency=info.get("currency", "USD"),
            country=info.get("country", ""),
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            market_cap=info.get("marketCap"),
        )
        
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=503, detail="yfinance not installed")
    except Exception as e:
        logger.error(f"Error looking up symbol {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exchanges", response_model=ExchangesResponse)
async def list_exchanges(
    region: Optional[str] = Query(None, description="Filter by region: north_america, europe, asia_pacific, latin_america, middle_east, africa"),
) -> ExchangesResponse:
    """
    List all supported global stock exchanges.
    
    Returns information about 40+ exchanges worldwide with trading hours,
    currency, and approximate number of listed stocks.
    """
    try:
        from src.config.exchanges import (
            ALL_EXCHANGES, 
            ExchangeRegion, 
            get_exchanges_by_region,
            EXCHANGE_STOCK_COUNTS,
            get_total_available_stocks,
        )
        
        if region:
            try:
                region_enum = ExchangeRegion(region.lower())
                exchanges = get_exchanges_by_region(region_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid region: {region}")
        else:
            exchanges = list(ALL_EXCHANGES.values())
        
        result = []
        for ex in exchanges:
            if not ex.is_supported:
                continue
            result.append(ExchangeInfo(
                code=ex.code,
                name=ex.name,
                country=ex.country,
                region=ex.region.value,
                currency=ex.currency.value,
                timezone=ex.timezone,
                suffix=ex.suffix,
                stock_count=EXCHANGE_STOCK_COUNTS.get(ex.code, 0),
                trading_hours=ex.trading_hours,
                is_open=False,  # TODO: Calculate based on current time
            ))
        
        return ExchangesResponse(
            total_exchanges=len(result),
            total_stocks=get_total_available_stocks(),
            exchanges=result,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing exchanges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/popular")
async def get_popular_symbols(
    exchange: Optional[str] = Query(None, description="Exchange code"),
    category: Optional[str] = Query(None, description="Category: tech, finance, healthcare, energy, consumer"),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """
    Get popular/most traded symbols by exchange or category.
    
    Useful for discovery and browsing available stocks.
    """
    # Popular stocks by category
    popular = {
        "tech": [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", 
            "INTC", "CRM", "ORCL", "ADBE", "CSCO", "AVGO", "QCOM", "IBM",
            "TSM", "ASML", "SAP", "SONY",  # International tech
        ],
        "finance": [
            "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "V",
            "MA", "PYPL", "SQ", "HSBA.L", "UBS", "DB.DE",  # International finance
        ],
        "healthcare": [
            "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "AMGN",
            "GILD", "MRNA", "BNTX", "NVO", "AZN",  # International healthcare
        ],
        "energy": [
            "XOM", "CVX", "COP", "SLB", "EOG", "OXY", "PSX", "MPC", "VLO",
            "BP.L", "SHEL.L", "TTE.PA", "EQNR.OL",  # International energy
        ],
        "consumer": [
            "AMZN", "HD", "WMT", "COST", "NKE", "MCD", "SBUX", "TGT", "LOW",
            "DIS", "NFLX", "9984.T", "JD", "BABA",  # International consumer
        ],
        "indices": [
            "^GSPC", "^DJI", "^IXIC", "^NDX", "^RUT",  # US
            "^FTSE", "^GDAXI", "^FCHI", "^STOXX50E",  # Europe
            "^N225", "^HSI", "000001.SS", "^TWII", "^KS11",  # Asia
            "^AXJO", "^GSPTSE", "^BVSP",  # Other
        ],
        "etfs": [
            "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "IVV",  # US indices
            "VEU", "VWO", "EFA", "EEM", "IEFA", "IEMG",  # International
            "XLK", "XLF", "XLE", "XLV", "XLI", "XLC",  # Sectors
            "GLD", "SLV", "USO", "UNG",  # Commodities
            "ARKK", "ARKG", "ARKW", "ARKF",  # Thematic
        ],
        "crypto_related": [
            "COIN", "MSTR", "MARA", "RIOT", "CLSK", "HUT",
            "IBIT", "FBTC", "GBTC", "ETHE", "BITO",
        ],
        "international": {
            "japan": ["7203.T", "6758.T", "9984.T", "7267.T", "6501.T"],
            "uk": ["HSBA.L", "BP.L", "SHEL.L", "AZN.L", "GSK.L"],
            "germany": ["SAP.DE", "SIE.DE", "ALV.DE", "BMW.DE", "MBG.DE"],
            "france": ["LVMH.PA", "TTE.PA", "OR.PA", "SAN.PA", "AIR.PA"],
            "china": ["9988.HK", "0700.HK", "3690.HK", "600519.SS", "000858.SZ"],
            "hong_kong": ["0005.HK", "0941.HK", "1299.HK", "0883.HK", "2318.HK"],
            "taiwan": ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2412.TW"],
            "korea": ["005930.KS", "000660.KS", "035420.KS", "005380.KS", "051910.KS"],
            "australia": ["BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX"],
            "canada": ["RY.TO", "TD.TO", "BNS.TO", "ENB.TO", "CNR.TO"],
            "brazil": ["VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "B3SA3.SA"],
            "india": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"],
        },
    }
    
    if category:
        cat_lower = category.lower()
        if cat_lower in popular:
            data = popular[cat_lower]
            if isinstance(data, dict):
                # International - flatten all
                symbols = []
                for country_symbols in data.values():
                    symbols.extend(country_symbols)
                return {"category": category, "symbols": symbols[:limit]}
            return {"category": category, "symbols": data[:limit]}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}")
    
    # Return all categories
    return {
        "categories": list(popular.keys()),
        "total_popular_symbols": sum(
            len(v) if isinstance(v, list) else sum(len(x) for x in v.values())
            for v in popular.values()
        ),
        "sample": popular.get("tech", [])[:10],
    }


@router.get("/validate")
async def validate_symbols(
    symbols: str = Query(..., description="Comma-separated list of symbols to validate"),
) -> dict:
    """
    Validate a list of symbols and check if they exist.
    
    Returns which symbols are valid and tradeable.
    """
    try:
        import yfinance as yf
        
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        results = {"valid": [], "invalid": [], "warnings": []}
        
        for symbol in symbol_list:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if info and info.get("symbol"):
                    results["valid"].append({
                        "symbol": symbol,
                        "name": info.get("longName") or info.get("shortName", ""),
                        "exchange": info.get("exchange", ""),
                        "currency": info.get("currency", "USD"),
                    })
                else:
                    results["invalid"].append(symbol)
                    
            except Exception as e:
                results["invalid"].append(symbol)
                logger.debug(f"Failed to validate {symbol}: {e}")
        
        return results
        
    except ImportError:
        raise HTTPException(status_code=503, detail="yfinance not installed")
    except Exception as e:
        logger.error(f"Error validating symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

