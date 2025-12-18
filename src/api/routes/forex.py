"""
Forex Trading API Routes

Comprehensive Forex trading endpoints:
- Currency pairs and pip calculations
- Trading sessions and overlaps
- Currency strength analysis
- Economic calendar
- Forex-specific strategies
- Broker integrations (MT5, OANDA)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd

from loguru import logger


router = APIRouter(prefix="/api/forex", tags=["Forex"])


# =============================================================================
# Currency Pairs
# =============================================================================

@router.get("/pairs")
async def get_forex_pairs(
    pair_type: Optional[str] = Query(None, description="Filter by type: major, minor, exotic, commodity"),
):
    """Get all available Forex currency pairs."""
    from src.forex.core import get_forex_pairs, PairType
    
    pairs = get_forex_pairs()
    
    if pair_type:
        try:
            filter_type = PairType(pair_type.lower())
            pairs = [p for p in pairs if p.pair_type == filter_type]
        except ValueError:
            pass
    
    return {
        "total": len(pairs),
        "pairs": [p.to_dict() for p in pairs],
    }


@router.get("/pairs/{symbol}")
async def get_pair_details(symbol: str):
    """Get details for a specific currency pair."""
    from src.forex.core import get_forex_pairs
    
    # Normalize symbol
    symbol = symbol.upper().replace("_", "/")
    if "/" not in symbol and len(symbol) == 6:
        symbol = f"{symbol[:3]}/{symbol[3:]}"
    
    pairs = get_forex_pairs()
    pair = next((p for p in pairs if p.symbol == symbol), None)
    
    if not pair:
        raise HTTPException(status_code=404, detail=f"Pair {symbol} not found")
    
    return pair.to_dict()


# =============================================================================
# Pip Calculations
# =============================================================================

class PipCalculationRequest(BaseModel):
    pair: str
    entry_price: float
    exit_price: float
    units: int = 10000
    is_long: bool = True


@router.post("/calculate-pips")
async def calculate_pips(request: PipCalculationRequest):
    """Calculate pips and profit/loss for a trade."""
    from src.forex.core import get_pip_calculator
    
    calc = get_pip_calculator()
    
    pips = calc.price_to_pips(request.pair, request.entry_price, request.exit_price)
    pip_value = calc.pip_value(request.pair, request.units)
    pnl = calc.calculate_profit_loss(
        request.pair,
        request.entry_price,
        request.exit_price,
        request.units,
        request.is_long,
    )
    
    return {
        "pair": request.pair,
        "entry_price": request.entry_price,
        "exit_price": request.exit_price,
        "pips_moved": round(pips, 1),
        "pip_value": pip_value,
        "units": request.units,
        **pnl,
    }


class LotSizeRequest(BaseModel):
    account_balance: float
    risk_percent: float = 1.0
    stop_loss_pips: float
    pair: str
    account_currency: str = "USD"


@router.post("/calculate-lot-size")
async def calculate_lot_size(request: LotSizeRequest):
    """Calculate optimal lot size based on risk management."""
    from src.forex.core import LotSizer, get_forex_pairs
    
    pairs = get_forex_pairs()
    pair = next((p for p in pairs if p.symbol.replace("/", "") == request.pair.replace("/", "").upper()), None)
    
    if not pair:
        raise HTTPException(status_code=404, detail="Pair not found")
    
    sizer = LotSizer(
        account_balance=request.account_balance,
        risk_percent=request.risk_percent,
        account_currency=request.account_currency,
    )
    
    result = sizer.calculate_lots(pair, request.stop_loss_pips)
    
    return result


# =============================================================================
# Trading Sessions
# =============================================================================

@router.get("/sessions")
async def get_trading_sessions():
    """Get current trading sessions and overlaps."""
    from src.forex.core import get_current_session
    
    return get_current_session()


@router.get("/sessions/schedule")
async def get_session_schedule():
    """Get full trading session schedule."""
    from src.forex.core import FOREX_SESSIONS
    
    return {
        "sessions": [
            {
                "name": s.name.value,
                "open_utc": s.open_time.strftime("%H:%M"),
                "close_utc": s.close_time.strftime("%H:%M"),
                "timezone": s.timezone,
                "major_pairs": s.major_pairs,
                "volatility": s.typical_volatility,
            }
            for s in FOREX_SESSIONS
        ],
        "overlaps": [
            {
                "sessions": ["london", "new_york"],
                "start_utc": "13:00",
                "end_utc": "17:00",
                "description": "Highest volatility period",
            },
            {
                "sessions": ["london", "tokyo"],
                "start_utc": "08:00",
                "end_utc": "09:00",
                "description": "EUR/JPY, GBP/JPY active",
            },
            {
                "sessions": ["sydney", "tokyo"],
                "start_utc": "00:00",
                "end_utc": "07:00",
                "description": "AUD, NZD, JPY pairs active",
            },
        ],
    }


# =============================================================================
# Currency Strength
# =============================================================================

@router.get("/currency-strength")
async def get_currency_strength():
    """Get currency strength analysis for all major currencies."""
    from src.forex.currency_strength import get_currency_strength
    
    meter = get_currency_strength()
    
    return {
        "strengths": meter.get_all_strengths(),
        "best_pair": meter.get_best_pair(),
        "divergences": meter.get_divergences(),
    }


@router.get("/currency-strength/{currency}")
async def get_single_currency_strength(currency: str):
    """Get strength analysis for a specific currency."""
    from src.forex.currency_strength import get_currency_strength, MAJOR_CURRENCIES
    
    currency = currency.upper()
    if currency not in MAJOR_CURRENCIES:
        raise HTTPException(status_code=404, detail=f"Currency {currency} not supported")
    
    meter = get_currency_strength()
    strength = meter.get_strength(currency)
    
    if not strength:
        return {"currency": currency, "strength": 50.0, "message": "Insufficient data"}
    
    return strength.to_dict()


@router.get("/correlation-matrix")
async def get_correlation_matrix():
    """Get correlation matrix for major pairs."""
    from src.forex.currency_strength import get_currency_strength
    
    meter = get_currency_strength()
    return meter.get_correlation_matrix()


# =============================================================================
# Economic Calendar
# =============================================================================

@router.get("/calendar")
async def get_economic_calendar(
    hours: int = Query(24, description="Look-ahead hours"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    impact: Optional[str] = Query(None, description="Filter by impact: high, medium, low"),
):
    """Get upcoming economic events."""
    from src.forex.economic_calendar import get_economic_calendar, EventImpact
    
    calendar = get_economic_calendar()
    
    impact_filter = None
    if impact:
        try:
            impact_filter = EventImpact(impact.lower())
        except ValueError:
            pass
    
    events = calendar.get_upcoming_events(hours, currency, impact_filter)
    
    return {
        "total": len(events),
        "events": events,
    }


@router.get("/calendar/high-impact")
async def get_high_impact_events(
    hours: int = Query(24),
    currency: Optional[str] = Query(None),
):
    """Get high-impact economic events only."""
    from src.forex.economic_calendar import get_economic_calendar
    
    calendar = get_economic_calendar()
    events = calendar.get_high_impact_events(hours, currency)
    
    return {
        "total": len(events),
        "high_impact_events": events,
    }


@router.get("/calendar/pair/{pair}")
async def get_events_for_pair(pair: str, hours: int = Query(24)):
    """Get economic events affecting a specific currency pair."""
    from src.forex.economic_calendar import get_economic_calendar
    
    calendar = get_economic_calendar()
    events = calendar.get_events_for_pair(pair, hours)
    
    return {
        "pair": pair,
        "total": len(events),
        "events": events,
    }


@router.get("/calendar/should-trade/{pair}")
async def should_trade_pair(pair: str):
    """Check if it's safe to trade a pair (no imminent high-impact news)."""
    from src.forex.economic_calendar import get_economic_calendar
    
    calendar = get_economic_calendar()
    result = calendar.should_avoid_trading(pair)
    
    return {
        "pair": pair,
        "safe_to_trade": not result.get("avoid", False),
        **result,
    }


@router.get("/calendar/weekly-preview")
async def get_weekly_preview():
    """Get weekly economic calendar preview."""
    from src.forex.economic_calendar import get_economic_calendar
    
    calendar = get_economic_calendar()
    return calendar.get_weekly_preview()


# =============================================================================
# Forex Strategies
# =============================================================================

@router.get("/strategies")
async def list_forex_strategies():
    """List all available Forex trading strategies."""
    from src.forex.strategies import list_forex_strategies
    
    return {"strategies": list_forex_strategies()}


@router.get("/strategies/carry-trade/best-pairs")
async def get_best_carry_trade_pairs():
    """Get best pairs for carry trading based on interest rate differentials."""
    from src.forex.strategies import CarryTradeStrategy
    
    strategy = CarryTradeStrategy()
    return {"carry_trade_pairs": strategy.get_best_carry_pairs()}


@router.get("/strategies/news-trade/upcoming")
async def get_upcoming_news_trades():
    """Get upcoming news trading opportunities."""
    from src.forex.strategies import NewsTradeStrategy
    
    strategy = NewsTradeStrategy()
    return {"tradeable_events": strategy.get_tradeable_events(hours=48)}


class StrategyAnalyzeRequest(BaseModel):
    pair: str
    strategy: str
    prices: List[Dict[str, float]] = Field(..., description="OHLCV price data")


@router.post("/strategies/analyze")
async def analyze_with_strategy(request: StrategyAnalyzeRequest):
    """Analyze a pair using a specific Forex strategy."""
    from src.forex.strategies import get_forex_strategy
    
    strategy = get_forex_strategy(request.strategy)
    if not strategy:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{request.strategy}' not found. Use /api/forex/strategies for list."
        )
    
    df = pd.DataFrame(request.prices)
    
    if len(df) < 20:
        raise HTTPException(status_code=400, detail="Need at least 20 price bars")
    
    signal = strategy.analyze(request.pair, df)
    
    if signal:
        return {
            "has_signal": True,
            "signal": signal.to_dict(),
        }
    
    return {
        "has_signal": False,
        "message": "No trading signal at this time",
    }


# =============================================================================
# Broker Status
# =============================================================================

@router.get("/brokers")
async def get_supported_brokers():
    """Get list of supported Forex brokers."""
    return {
        "brokers": [
            {
                "id": "metatrader5",
                "name": "MetaTrader 5",
                "description": "Connect to MT5 terminals for Forex trading",
                "features": ["Real-time quotes", "Order execution", "Position management", "Expert Advisors"],
                "platforms": ["Windows"],
                "requirements": "pip install MetaTrader5",
            },
            {
                "id": "oanda",
                "name": "OANDA",
                "description": "OANDA REST API v20 integration",
                "features": ["Real-time pricing", "Order execution", "Streaming prices", "Historical data"],
                "platforms": ["All"],
                "requirements": "OANDA API key and account ID",
            },
            {
                "id": "ninjatrader",
                "name": "NinjaTrader 8",
                "description": "NinjaTrader ATI for futures and Forex",
                "features": ["Order execution", "Position management", "Multi-account"],
                "platforms": ["Windows"],
                "requirements": "NinjaTrader 8 with ATI enabled",
            },
        ]
    }


# =============================================================================
# Quick Reference
# =============================================================================

@router.get("/reference/pip-values")
async def get_pip_value_reference():
    """Get pip value reference for common lot sizes."""
    from src.forex.core import get_forex_pairs
    
    pairs = get_forex_pairs()
    major_pairs = [p for p in pairs if p.pair_type.value == "major"]
    
    reference = []
    for pair in major_pairs[:7]:
        reference.append({
            "pair": pair.symbol,
            "pip_value": pair.pip_value,
            "pip_value_standard_lot": f"${10 if pair.quote_currency == 'USD' else 'varies'}",
            "pip_value_mini_lot": f"${1 if pair.quote_currency == 'USD' else 'varies'}",
            "pip_value_micro_lot": f"${0.10 if pair.quote_currency == 'USD' else 'varies'}",
            "typical_spread_pips": pair.typical_spread_pips,
            "avg_daily_range_pips": pair.avg_daily_range_pips,
        })
    
    return {
        "lot_sizes": {
            "standard": "100,000 units",
            "mini": "10,000 units",
            "micro": "1,000 units",
            "nano": "100 units",
        },
        "pip_values": reference,
    }


@router.get("/reference/margin")
async def get_margin_reference():
    """Get margin requirements reference."""
    return {
        "leverage_to_margin": {
            "50:1": "2%",
            "100:1": "1%",
            "200:1": "0.5%",
            "400:1": "0.25%",
            "500:1": "0.2%",
        },
        "example_calculation": {
            "description": "To buy 1 standard lot (100,000) EUR/USD at 1.0850 with 50:1 leverage:",
            "position_value": "$108,500",
            "margin_required": "$2,170 (2%)",
        },
        "major_pair_typical_margin": "2% (50:1 leverage)",
        "exotic_pair_typical_margin": "5-10% (10:1 - 20:1 leverage)",
    }

