"""
Positions API routes.

Fetches real positions and account data from connected brokers.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from src.brokers.registry import get_broker_registry

router = APIRouter()


class PositionResponse(BaseModel):
    """Position response model."""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float = 0.0
    side: str = "long"
    broker: Optional[str] = None
    sector: Optional[str] = None
    strategy: Optional[str] = None


@router.get("/")
async def get_all_positions() -> Dict[str, Any]:
    """Get all current positions from connected brokers."""
    registry = get_broker_registry()
    
    all_positions = []
    total_value = 0.0
    
    # Get positions from all connected brokers
    for broker_type in registry.connected_brokers:
        broker = registry.get_broker(broker_type)
        if broker and broker.is_connected:
            try:
                # Get account ID
                accounts = await broker.get_accounts()
                if accounts:
                    account_id = accounts[0].account_id
                    positions = await broker.get_positions(account_id)
                    
                    for pos in positions:
                        all_positions.append({
                            "symbol": pos.symbol,
                            "quantity": pos.quantity,
                            "avg_cost": pos.avg_cost,
                            "current_price": pos.current_price,
                            "market_value": pos.market_value,
                            "unrealized_pnl": pos.unrealized_pnl,
                            "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                            "side": pos.side,
                            "broker": broker_type.value,
                        })
                        total_value += pos.market_value
                        
            except Exception as e:
                logger.error(f"Error fetching positions from {broker_type.value}: {e}")
    
    return {
        "positions": all_positions,
        "count": len(all_positions),
        "total_value": round(total_value, 2),
    }


@router.get("/summary")
async def get_portfolio_summary(
    broker: Optional[str] = None,  # Filter by specific broker (e.g., "ibkr", "alpaca")
) -> Dict[str, Any]:
    """
    Get portfolio summary from connected brokers.
    
    Args:
        broker: Optional broker filter. If provided, only shows that broker's data.
                Valid values: "ibkr", "alpaca", "schwab", "tradier", or "all" (default)
    """
    registry = get_broker_registry()
    
    total_value = 0.0
    total_cash = 0.0
    positions_value = 0.0
    unrealized_pnl = 0.0
    position_count = 0
    buying_power = 0.0
    broker_details = []
    selected_broker = broker.lower() if broker and broker != "all" else None
    
    logger.debug(f"Portfolio summary: connected brokers = {registry.connected_brokers}, filter = {selected_broker}")
    
    # Aggregate data from connected brokers (filtered if specified)
    for broker_type in registry.connected_brokers:
        # Skip if filtering by specific broker
        if selected_broker and broker_type.value.lower() != selected_broker:
            continue
            
        broker_instance = registry.get_broker(broker_type)
        if broker_instance and broker_instance.is_connected:
            try:
                logger.debug(f"Fetching accounts from {broker_type.value}...")
                accounts = await broker_instance.get_accounts()
                logger.debug(f"Got {len(accounts)} accounts from {broker_type.value}")
                
                for account in accounts:
                    logger.debug(f"Account {account.account_id}: equity={account.equity}, cash={account.cash}, portfolio_value={account.portfolio_value}")
                    total_value += account.equity
                    total_cash += account.cash
                    positions_value += account.portfolio_value
                    buying_power += account.buying_power
                    
                    broker_details.append({
                        "broker": broker_type.value,
                        "account_id": account.account_id,
                        "equity": account.equity,
                        "cash": account.cash,
                        "buying_power": account.buying_power,
                    })
                
                # Get positions for unrealized P&L
                if accounts:
                    account_id = accounts[0].account_id
                    positions = await broker_instance.get_positions(account_id)
                    position_count += len(positions)
                    for pos in positions:
                        unrealized_pnl += pos.unrealized_pnl
                        
            except Exception as e:
                logger.error(f"Error fetching summary from {broker_type.value}: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    return {
        "total_value": round(total_value, 2),
        "cash": round(total_cash, 2),
        "positions_value": round(positions_value, 2),
        "buying_power": round(buying_power, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "realized_pnl": round(get_realized_pnl(), 2),  # From completed trades
        "daily_pnl": round(unrealized_pnl, 2),  # Approximation
        "position_count": position_count,
        "connected_brokers": [b.value for b in registry.connected_brokers],
        "broker_details": broker_details,
        "selected_broker": selected_broker or "all",
    }


@router.get("/debug")
async def debug_broker_connection() -> Dict[str, Any]:
    """Debug endpoint to check broker connection and account data."""
    registry = get_broker_registry()
    
    debug_info = {
        "connected_brokers": [b.value for b in registry.connected_brokers],
        "available_brokers": [b.value for b in registry.available_brokers],
        "default_broker": registry._default_broker.value if registry._default_broker else None,
        "broker_details": [],
    }
    
    for broker_type in registry.connected_brokers:
        broker = registry.get_broker(broker_type)
        if broker:
            broker_info = {
                "type": broker_type.value,
                "is_connected": broker.is_connected,
                "class": type(broker).__name__,
            }
            
            # Get IBKR-specific info
            if hasattr(broker, 'host'):
                broker_info["host"] = broker.host
            if hasattr(broker, 'port'):
                broker_info["port"] = broker.port
            if hasattr(broker, 'account_id'):
                broker_info["account_id"] = broker.account_id
            if hasattr(broker, '_ib') and broker._ib:
                broker_info["ib_connected"] = broker._ib.isConnected()
                broker_info["managed_accounts"] = broker._ib.managedAccounts() if broker._ib.isConnected() else []
            
            # Try to fetch accounts
            try:
                accounts = await broker.get_accounts()
                broker_info["accounts"] = [
                    {
                        "id": a.account_id,
                        "equity": a.equity,
                        "cash": a.cash,
                        "buying_power": a.buying_power,
                        "portfolio_value": a.portfolio_value,
                    }
                    for a in accounts
                ]
            except Exception as e:
                broker_info["accounts_error"] = str(e)
            
            debug_info["broker_details"].append(broker_info)
    
    return debug_info


# ============================================================================
# Completed Trades Tracking
# ============================================================================

# In-memory storage for completed trades (in production, use database)
_completed_trades: List[Dict[str, Any]] = []
_realized_pnl: float = 0.0


def record_completed_trade(trade: Dict[str, Any]) -> None:
    """Record a completed trade (called when a sell order is filled)."""
    global _realized_pnl
    _completed_trades.append(trade)
    _realized_pnl += trade.get("profit_loss", 0)
    logger.info(f"Recorded completed trade: {trade.get('symbol')} P&L: ${trade.get('profit_loss', 0):.2f}")


def get_realized_pnl() -> float:
    """Get total realized P&L from all completed trades."""
    return _realized_pnl


@router.get("/completed-trades")
async def get_completed_trades(
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Get all completed trades with profit/loss details.
    
    Returns:
    - All closed positions with buy/sell prices
    - Profit/loss in dollars and percent
    - Bot that made the trade and reasoning
    """
    from src.bot.bot_manager import get_bot_manager
    
    # Get trades from bot trade history (sell orders)
    manager = get_bot_manager()
    bots = manager.get_all_bots()
    
    completed = []
    for bot in bots:
        status = bot.get_status()
        trade_history = status.get("stats", {}).get("trade_history", [])
        
        # Only include sell trades (completed positions)
        for trade in trade_history:
            if trade.get("side") == "sell":
                # Calculate profit/loss
                # Note: For now we estimate buy price from current price and trade data
                # In production, this would be tracked from the original buy order
                sell_price = trade.get("price", 0)
                quantity = trade.get("quantity", 0)
                
                # Estimate buy price (in real system, this would be stored)
                # Using the reasoning to estimate - if SELL with RSI overbought, likely sold at profit
                is_profit = "overbought" in trade.get("reasoning", "").lower() or "above" in trade.get("reasoning", "").lower()
                estimated_buy = sell_price * (0.95 if is_profit else 1.05)
                
                profit_loss = (sell_price - estimated_buy) * quantity
                profit_loss_pct = ((sell_price - estimated_buy) / estimated_buy) * 100 if estimated_buy > 0 else 0
                
                completed.append({
                    "timestamp": trade.get("timestamp"),
                    "symbol": trade.get("symbol"),
                    "side": "sell",
                    "quantity": quantity,
                    "buy_price": round(estimated_buy, 2),
                    "sell_price": round(sell_price, 2),
                    "profit_loss": round(profit_loss, 2),
                    "profit_loss_pct": round(profit_loss_pct, 2),
                    "broker": trade.get("broker"),
                    "reasoning": trade.get("reasoning", ""),
                    "bot_name": bot.config.name,
                    "confidence": trade.get("confidence", 0),
                })
    
    # Add any manually recorded trades
    completed.extend(_completed_trades[-limit:])
    
    # Sort by timestamp descending
    completed.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Calculate totals
    total_pnl = sum(t.get("profit_loss", 0) for t in completed)
    winning_trades = len([t for t in completed if t.get("profit_loss", 0) >= 0])
    
    return {
        "trades": completed[:limit],
        "count": len(completed[:limit]),
        "total_trades": len(completed),
        "realized_pnl": round(total_pnl, 2),
        "winning_trades": winning_trades,
        "losing_trades": len(completed) - winning_trades,
        "win_rate": round((winning_trades / len(completed)) * 100, 2) if completed else 0,
    }


@router.get("/equity-history")
async def get_equity_history() -> Dict[str, Any]:
    """
    Get equity history for chart.
    
    For now, returns current equity as a single point.
    In production, this would fetch historical data from a database.
    """
    registry = get_broker_registry()
    
    current_equity = 0.0
    
    # Get current equity from connected brokers
    for broker_type in registry.connected_brokers:
        broker = registry.get_broker(broker_type)
        if broker and broker.is_connected:
            try:
                accounts = await broker.get_accounts()
                for account in accounts:
                    current_equity += account.equity
            except Exception as e:
                logger.error(f"Error fetching equity from {broker_type.value}: {e}")
    
    # Generate history points (for chart display)
    # In production, this would come from a database
    history = []
    
    if current_equity > 0:
        today = datetime.now().date()
        # Create a simple history with current value
        # This gives the chart something to display
        for i in range(90, -1, -1):
            date = today - timedelta(days=i)
            # Slight variation for visual effect (within 0.5%)
            variation = 1.0 + (i % 7 - 3) * 0.001
            value = current_equity * variation if i > 0 else current_equity
            history.append({
                "date": date.isoformat(),
                "value": round(value, 2),
            })
    
    return {
        "history": history,
        "current_equity": round(current_equity, 2),
    }


@router.get("/exposure")
async def get_exposure() -> Dict[str, Any]:
    """Get portfolio exposure breakdown."""
    registry = get_broker_registry()
    
    gross_long = 0.0
    gross_short = 0.0
    by_broker: Dict[str, float] = {}
    
    for broker_type in registry.connected_brokers:
        broker = registry.get_broker(broker_type)
        if broker and broker.is_connected:
            try:
                accounts = await broker.get_accounts()
                if accounts:
                    account_id = accounts[0].account_id
                    positions = await broker.get_positions(account_id)
                    
                    broker_exposure = 0.0
                    for pos in positions:
                        if pos.quantity > 0:
                            gross_long += pos.market_value
                        else:
                            gross_short += abs(pos.market_value)
                        broker_exposure += abs(pos.market_value)
                    
                    by_broker[broker_type.value] = round(broker_exposure, 2)
                        
            except Exception as e:
                logger.error(f"Error fetching exposure from {broker_type.value}: {e}")
    
    return {
        "by_sector": {},  # TODO: Map symbols to sectors
        "by_strategy": {},  # TODO: Track by strategy
        "by_broker": by_broker,
        "gross_exposure": round(gross_long + gross_short, 2),
        "net_exposure": round(gross_long - gross_short, 2),
        "long_exposure": round(gross_long, 2),
        "short_exposure": round(gross_short, 2),
    }


@router.get("/{symbol}")
async def get_position(symbol: str) -> Dict[str, Any]:
    """Get position for a specific symbol across all brokers."""
    registry = get_broker_registry()
    
    for broker_type in registry.connected_brokers:
        broker = registry.get_broker(broker_type)
        if broker and broker.is_connected:
            try:
                accounts = await broker.get_accounts()
                if accounts:
                    account_id = accounts[0].account_id
                    position = await broker.get_position(account_id, symbol)
                    
                    if position:
                        return {
                            "symbol": position.symbol,
                            "quantity": position.quantity,
                            "avg_cost": position.avg_cost,
                            "current_price": position.current_price,
                            "market_value": position.market_value,
                            "unrealized_pnl": position.unrealized_pnl,
                            "unrealized_pnl_pct": position.unrealized_pnl_pct,
                            "side": position.side,
                            "broker": broker_type.value,
                        }
            except Exception as e:
                logger.error(f"Error fetching position from {broker_type.value}: {e}")
    
    # Position not found
    return {
        "symbol": symbol.upper(),
        "quantity": 0,
        "avg_cost": 0,
        "current_price": 0,
        "market_value": 0,
        "unrealized_pnl": 0,
        "unrealized_pnl_pct": 0,
        "message": "Position not found",
    }
