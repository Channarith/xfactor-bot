"""
Manual Trading API routes.

Provides endpoints for manual buy/sell orders with performance tracking
to compare against automated bot trading.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid
import threading

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger


router = APIRouter()


# =============================================================================
# Trade Source Tracking
# =============================================================================

class TradeSource(str, Enum):
    """Source of a trade."""
    MANUAL = "manual"
    BOT = "bot"
    TRADINGVIEW = "tradingview"
    API = "api"


class TradeRecord(BaseModel):
    """Record of a completed trade with source tracking."""
    trade_id: str
    timestamp: str
    symbol: str
    side: str  # buy or sell
    quantity: float
    price: float
    total_value: float
    order_type: str
    source: TradeSource
    source_id: Optional[str] = None  # bot_id if bot, user if manual
    source_name: Optional[str] = None  # bot name or "Manual Trade"
    broker: str
    order_id: str
    reasoning: Optional[str] = None
    pnl: Optional[float] = None  # Realized P&L for closing trades
    pnl_pct: Optional[float] = None


# In-memory trade history (in production, use database)
_trade_history: List[Dict[str, Any]] = []
_trade_lock = threading.Lock()


def record_trade(
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    order_type: str,
    source: TradeSource,
    broker: str,
    order_id: str,
    source_id: Optional[str] = None,
    source_name: Optional[str] = None,
    reasoning: Optional[str] = None,
    pnl: Optional[float] = None,
    pnl_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """Record a trade in the history."""
    trade = {
        "trade_id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol.upper(),
        "side": side.lower(),
        "quantity": quantity,
        "price": price,
        "total_value": quantity * price,
        "order_type": order_type,
        "source": source.value,
        "source_id": source_id,
        "source_name": source_name or ("Manual Trade" if source == TradeSource.MANUAL else source_id),
        "broker": broker,
        "order_id": order_id,
        "reasoning": reasoning,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
    }
    
    with _trade_lock:
        _trade_history.append(trade)
        # Keep last 1000 trades
        if len(_trade_history) > 1000:
            _trade_history.pop(0)
    
    logger.info(f"Trade recorded: {source.value} {side} {quantity} {symbol} @ {price}")
    return trade


def clear_trade_store() -> None:
    """Clear all trades from the store (for testing)."""
    global _trade_history
    with _trade_lock:
        _trade_history.clear()


def get_trade_history(
    source: Optional[TradeSource] = None,
    symbol: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get trade history with optional filters."""
    with _trade_lock:
        trades = list(_trade_history)
    
    # Filter by source
    if source:
        trades = [t for t in trades if t["source"] == source.value]
    
    # Filter by symbol
    if symbol:
        trades = [t for t in trades if t["symbol"] == symbol.upper()]
    
    # Sort by timestamp descending
    trades.sort(key=lambda t: t["timestamp"], reverse=True)
    
    return trades[:limit]


# =============================================================================
# Request/Response Models
# =============================================================================

class ManualOrderRequest(BaseModel):
    """Manual order request."""
    symbol: str = Field(..., description="Stock/crypto symbol")
    side: str = Field(..., description="'buy' or 'sell'")
    quantity: float = Field(..., gt=0, description="Number of shares/units")
    order_type: str = Field(default="market", description="'market', 'limit', or 'stop'")
    limit_price: Optional[float] = Field(None, description="Limit price (required for limit orders)")
    stop_price: Optional[float] = Field(None, description="Stop price (required for stop orders)")
    broker: Optional[str] = Field(None, description="Broker to use (default: first connected)")
    note: Optional[str] = Field(None, description="Personal note/reasoning for this trade")


class QuickTradeRequest(BaseModel):
    """Simplified quick trade request."""
    symbol: str
    action: str  # "buy" or "sell"
    amount: float  # Dollar amount OR quantity
    is_dollar_amount: bool = True  # If True, amount is dollars; if False, shares


class ClosePositionRequest(BaseModel):
    """Request to close a position."""
    symbol: str
    broker: Optional[str] = None
    percentage: float = Field(default=100.0, ge=0, le=100, description="Percentage of position to close")


# =============================================================================
# Manual Trading Endpoints
# =============================================================================

@router.post("/order")
async def submit_manual_order(request: ManualOrderRequest) -> Dict[str, Any]:
    """
    Submit a manual trade order.
    
    This executes through the connected broker and tracks it as a manual trade
    for performance comparison with bot trades.
    """
    from src.brokers.registry import get_broker_registry, BrokerType
    from src.brokers.base import OrderSide, OrderType
    
    registry = get_broker_registry()
    
    # Get broker
    if request.broker:
        try:
            bt = BrokerType(request.broker.lower())
            broker = registry.get_broker(bt)
        except ValueError:
            raise HTTPException(400, f"Unknown broker: {request.broker}")
    else:
        # Use first connected broker
        broker = registry.get_default_broker()
    
    if not broker:
        raise HTTPException(404, "No broker connected. Please connect a broker first.")
    
    if not broker.is_connected:
        raise HTTPException(400, f"Broker {broker.name} is not connected")
    
    # Validate order type
    if request.order_type.lower() == "limit" and not request.limit_price:
        raise HTTPException(400, "Limit price required for limit orders")
    if request.order_type.lower() == "stop" and not request.stop_price:
        raise HTTPException(400, "Stop price required for stop orders")
    
    # Get account
    try:
        accounts = await broker.get_accounts()
        if not accounts:
            raise HTTPException(400, "No accounts available")
        account_id = accounts[0].account_id
    except Exception as e:
        raise HTTPException(500, f"Failed to get account: {e}")
    
    # Map order side and type
    try:
        side = OrderSide(request.side.upper())
    except ValueError:
        raise HTTPException(400, f"Invalid side: {request.side}. Use 'buy' or 'sell'")
    
    order_type_map = {
        "market": OrderType.MARKET,
        "limit": OrderType.LIMIT,
        "stop": OrderType.STOP,
    }
    order_type = order_type_map.get(request.order_type.lower())
    if not order_type:
        raise HTTPException(400, f"Invalid order type: {request.order_type}")
    
    # Submit order
    try:
        order = await broker.submit_order(
            account_id=account_id,
            symbol=request.symbol.upper(),
            side=side,
            quantity=request.quantity,
            order_type=order_type,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
        )
        
        # Get fill price (estimate for market orders)
        fill_price = request.limit_price or request.stop_price
        if not fill_price:
            # Get current price
            try:
                positions = await broker.get_positions(account_id)
                pos = next((p for p in positions if p.symbol == request.symbol.upper()), None)
                fill_price = pos.current_price if pos else 0
            except:
                fill_price = 0
        
        # Record the trade
        trade_record = record_trade(
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            price=fill_price,
            order_type=request.order_type,
            source=TradeSource.MANUAL,
            broker=broker.name,
            order_id=order.order_id,
            source_name="Manual Trade",
            reasoning=request.note,
        )
        
        return {
            "status": "success",
            "message": f"Manual {request.side.upper()} order submitted",
            "order": {
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": order.quantity,
                "order_type": order.order_type.value,
                "status": order.status.value,
            },
            "trade_record": trade_record,
            "broker": broker.name,
            "is_paper": getattr(broker, 'paper_trading', True),
        }
        
    except Exception as e:
        logger.error(f"Manual order failed: {e}")
        raise HTTPException(500, f"Order failed: {str(e)}")


@router.post("/quick-buy")
async def quick_buy(request: QuickTradeRequest) -> Dict[str, Any]:
    """
    Quick buy with dollar amount or share quantity.
    Automatically calculates shares if dollar amount is provided.
    """
    from src.brokers.registry import get_broker_registry
    
    registry = get_broker_registry()
    broker = registry.get_default_broker()
    
    if not broker or not broker.is_connected:
        raise HTTPException(404, "No broker connected")
    
    # Get current price if dollar amount
    quantity = request.amount
    if request.is_dollar_amount:
        try:
            # Get quote
            import yfinance as yf
            ticker = yf.Ticker(request.symbol)
            price = ticker.info.get('regularMarketPrice') or ticker.info.get('currentPrice', 100)
            quantity = round(request.amount / price, 6)  # Support fractional
        except Exception as e:
            raise HTTPException(400, f"Could not get price for {request.symbol}: {e}")
    
    # Submit as manual order
    order_request = ManualOrderRequest(
        symbol=request.symbol,
        side="buy",
        quantity=quantity,
        order_type="market",
        note=f"Quick buy: ${request.amount}" if request.is_dollar_amount else f"Quick buy: {request.amount} shares",
    )
    
    return await submit_manual_order(order_request)


@router.post("/quick-sell")
async def quick_sell(request: QuickTradeRequest) -> Dict[str, Any]:
    """
    Quick sell with dollar amount or share quantity.
    """
    order_request = ManualOrderRequest(
        symbol=request.symbol,
        side="sell",
        quantity=request.amount if not request.is_dollar_amount else request.amount,
        order_type="market",
        note=f"Quick sell",
    )
    
    return await submit_manual_order(order_request)


@router.post("/close-position")
async def close_position(request: ClosePositionRequest) -> Dict[str, Any]:
    """
    Close all or part of a position.
    """
    from src.brokers.registry import get_broker_registry, BrokerType
    from src.brokers.base import OrderSide, OrderType
    
    registry = get_broker_registry()
    
    # Get broker
    if request.broker:
        try:
            bt = BrokerType(request.broker.lower())
            broker = registry.get_broker(bt)
        except ValueError:
            raise HTTPException(400, f"Unknown broker: {request.broker}")
    else:
        broker = registry.get_default_broker()
    
    if not broker or not broker.is_connected:
        raise HTTPException(404, "No broker connected")
    
    # Get current position
    try:
        accounts = await broker.get_accounts()
        if not accounts:
            raise HTTPException(400, "No accounts available")
        account_id = accounts[0].account_id
        
        positions = await broker.get_positions(account_id)
        position = next((p for p in positions if p.symbol == request.symbol.upper()), None)
        
        if not position or position.quantity == 0:
            raise HTTPException(404, f"No position found for {request.symbol}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get position: {e}")
    
    # Calculate quantity to close
    close_qty = abs(position.quantity) * (request.percentage / 100.0)
    if close_qty < 0.001:
        raise HTTPException(400, "Position too small to close")
    
    # Determine side (opposite of position)
    side = OrderSide.SELL if position.quantity > 0 else OrderSide.BUY
    
    # Submit close order
    try:
        order = await broker.submit_order(
            account_id=account_id,
            symbol=request.symbol.upper(),
            side=side,
            quantity=close_qty,
            order_type=OrderType.MARKET,
        )
        
        # Calculate P&L
        pnl = (position.current_price - position.avg_cost) * close_qty
        if side == OrderSide.BUY:  # Closing a short
            pnl = -pnl
        pnl_pct = ((position.current_price / position.avg_cost) - 1) * 100 if position.avg_cost else 0
        
        # Record the trade
        trade_record = record_trade(
            symbol=request.symbol,
            side=side.value.lower(),
            quantity=close_qty,
            price=position.current_price,
            order_type="market",
            source=TradeSource.MANUAL,
            broker=broker.name,
            order_id=order.order_id,
            source_name="Manual Close",
            reasoning=f"Closed {request.percentage}% of position",
            pnl=pnl,
            pnl_pct=pnl_pct,
        )
        
        return {
            "status": "success",
            "message": f"Closed {request.percentage}% of {request.symbol} position",
            "order": {
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": close_qty,
            },
            "realized_pnl": round(pnl, 2),
            "realized_pnl_pct": round(pnl_pct, 2),
            "trade_record": trade_record,
        }
        
    except Exception as e:
        logger.error(f"Close position failed: {e}")
        raise HTTPException(500, f"Failed to close position: {str(e)}")


# =============================================================================
# Trade History & Performance Comparison
# =============================================================================

@router.get("/history")
async def get_manual_trade_history(
    source: Optional[str] = Query(None, description="Filter by source: manual, bot, all"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(100, ge=1, le=500),
) -> Dict[str, Any]:
    """
    Get trade history with optional filters.
    """
    trade_source = None
    if source and source.lower() != "all":
        try:
            trade_source = TradeSource(source.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid source: {source}")
    
    trades = get_trade_history(source=trade_source, symbol=symbol, limit=limit)
    
    # Calculate summary stats
    total_pnl = sum(t.get("pnl", 0) or 0 for t in trades)
    total_volume = sum(t.get("total_value", 0) for t in trades)
    buy_count = sum(1 for t in trades if t["side"] == "buy")
    sell_count = sum(1 for t in trades if t["side"] == "sell")
    
    return {
        "trades": trades,
        "count": len(trades),
        "summary": {
            "total_pnl": round(total_pnl, 2),
            "total_volume": round(total_volume, 2),
            "buy_count": buy_count,
            "sell_count": sell_count,
        },
    }


def get_performance_comparison(days: int = 30) -> Dict[str, Any]:
    """
    Compare performance between bot trades and manual trades (sync version for testing).
    
    Answers the question: Are automatic bots better than manual user trades?
    """
    return _calculate_performance_comparison(days)


@router.get("/performance/comparison")
async def get_performance_comparison_endpoint(
    days: int = Query(30, ge=1, le=365, description="Days to analyze"),
) -> Dict[str, Any]:
    """
    Compare performance between bot trades and manual trades.
    
    Answers the question: Are automatic bots better than manual user trades?
    """
    return _calculate_performance_comparison(days)


def _calculate_performance_comparison(days: int = 30) -> Dict[str, Any]:
    """Internal function to calculate performance comparison."""
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.isoformat()
    
    with _trade_lock:
        all_trades = [t for t in _trade_history if t["timestamp"] >= cutoff_str]
    
    # Separate by source
    bot_trades = [t for t in all_trades if t["source"] == TradeSource.BOT.value]
    manual_trades = [t for t in all_trades if t["source"] == TradeSource.MANUAL.value]
    
    def analyze_trades(trades: List[Dict]) -> Dict[str, Any]:
        if not trades:
            return {
                "count": 0,
                "total_pnl": 0,
                "win_rate": 0,
                "avg_pnl": 0,
                "total_volume": 0,
                "winners": 0,
                "losers": 0,
                "best_trade": None,
                "worst_trade": None,
                "symbols_traded": [],
            }
        
        # Only count trades with P&L (closing trades)
        pnl_trades = [t for t in trades if t.get("pnl") is not None]
        
        total_pnl = sum(t.get("pnl", 0) for t in pnl_trades)
        winners = [t for t in pnl_trades if t.get("pnl", 0) > 0]
        losers = [t for t in pnl_trades if t.get("pnl", 0) < 0]
        
        win_rate = (len(winners) / len(pnl_trades) * 100) if pnl_trades else 0
        avg_pnl = total_pnl / len(pnl_trades) if pnl_trades else 0
        
        best = max(pnl_trades, key=lambda t: t.get("pnl", 0)) if pnl_trades else None
        worst = min(pnl_trades, key=lambda t: t.get("pnl", 0)) if pnl_trades else None
        
        symbols = list(set(t["symbol"] for t in trades))
        
        return {
            "count": len(trades),
            "trades_with_pnl": len(pnl_trades),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 1),
            "avg_pnl": round(avg_pnl, 2),
            "total_volume": round(sum(t.get("total_value", 0) for t in trades), 2),
            "winners": len(winners),
            "losers": len(losers),
            "best_trade": {
                "symbol": best["symbol"],
                "pnl": round(best.get("pnl", 0), 2),
                "timestamp": best["timestamp"],
            } if best else None,
            "worst_trade": {
                "symbol": worst["symbol"],
                "pnl": round(worst.get("pnl", 0), 2),
                "timestamp": worst["timestamp"],
            } if worst else None,
            "symbols_traded": symbols[:10],  # Top 10
        }
    
    bot_stats = analyze_trades(bot_trades)
    manual_stats = analyze_trades(manual_trades)
    
    # Comparison analysis
    pnl_diff = bot_stats["total_pnl"] - manual_stats["total_pnl"]
    win_rate_diff = bot_stats["win_rate"] - manual_stats["win_rate"]
    
    if bot_stats["count"] == 0 and manual_stats["count"] == 0:
        recommendation = "No trades recorded yet. Start trading to see performance comparison."
    elif bot_stats["count"] == 0:
        recommendation = "No bot trades recorded. Enable and run bots to compare performance."
    elif manual_stats["count"] == 0:
        recommendation = "No manual trades recorded. Try some manual trades to compare against bots."
    elif pnl_diff > 0:
        recommendation = f"🤖 Bots are outperforming by ${abs(pnl_diff):,.2f}. Consider increasing bot allocation."
    elif pnl_diff < 0:
        recommendation = f"👤 Manual trades are outperforming by ${abs(pnl_diff):,.2f}. Your insights are valuable!"
    else:
        recommendation = "Performance is even. Keep monitoring both strategies."
    
    return {
        "period_days": days,
        "bot_trades": bot_stats,
        "manual_trades": manual_stats,
        "comparison": {
            "pnl_difference": round(pnl_diff, 2),
            "bots_outperform_by": round(pnl_diff, 2) if pnl_diff > 0 else 0,
            "manual_outperform_by": round(-pnl_diff, 2) if pnl_diff < 0 else 0,
            "win_rate_difference": round(win_rate_diff, 1),
            "recommendation": recommendation,
        },
        "totals": {
            "all_trades": len(all_trades),
            "combined_pnl": round(bot_stats["total_pnl"] + manual_stats["total_pnl"], 2),
            "combined_volume": round(bot_stats["total_volume"] + manual_stats["total_volume"], 2),
        },
    }


@router.get("/stats")
async def get_trading_stats() -> Dict[str, Any]:
    """
    Get overall trading statistics.
    """
    with _trade_lock:
        all_trades = list(_trade_history)
    
    if not all_trades:
        return {
            "total_trades": 0,
            "by_source": {},
            "by_symbol": {},
            "message": "No trades recorded yet",
        }
    
    # Group by source
    by_source = {}
    for t in all_trades:
        src = t["source"]
        if src not in by_source:
            by_source[src] = {"count": 0, "volume": 0, "pnl": 0}
        by_source[src]["count"] += 1
        by_source[src]["volume"] += t.get("total_value", 0)
        by_source[src]["pnl"] += t.get("pnl", 0) or 0
    
    # Group by symbol
    by_symbol = {}
    for t in all_trades:
        sym = t["symbol"]
        if sym not in by_symbol:
            by_symbol[sym] = {"count": 0, "volume": 0, "pnl": 0}
        by_symbol[sym]["count"] += 1
        by_symbol[sym]["volume"] += t.get("total_value", 0)
        by_symbol[sym]["pnl"] += t.get("pnl", 0) or 0
    
    # Sort by count
    top_symbols = dict(sorted(by_symbol.items(), key=lambda x: x[1]["count"], reverse=True)[:10])
    
    return {
        "total_trades": len(all_trades),
        "by_source": by_source,
        "top_symbols": top_symbols,
        "first_trade": all_trades[0]["timestamp"] if all_trades else None,
        "last_trade": all_trades[-1]["timestamp"] if all_trades else None,
    }

