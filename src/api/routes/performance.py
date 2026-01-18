"""
Performance API Routes.

Provides endpoints for bot and position performance data,
including historical time series for charting.
"""

from datetime import datetime, timedelta
from typing import Optional
import random
import math

from fastapi import APIRouter, Query
from pydantic import BaseModel


router = APIRouter(prefix="/api/performance", tags=["performance"])


class PerformancePoint(BaseModel):
    """Single point in performance time series."""
    timestamp: str
    value: float
    pnl: float
    pnl_pct: float


class BotPerformanceResponse(BaseModel):
    """Bot performance response."""
    bot_id: str
    bot_name: str
    time_range: str
    data_points: list[dict]
    summary: dict


class PositionPerformanceResponse(BaseModel):
    """Position performance response."""
    symbol: str
    time_range: str
    data_points: list[dict]
    summary: dict


def _generate_performance_data(
    start_value: float,
    num_points: int,
    volatility: float = 0.02,
    trend: float = 0.0001,
    start_time: datetime = None,
    interval_minutes: int = 60,
) -> list[dict]:
    """Generate realistic performance data points."""
    data = []
    current_value = start_value
    start = start_time or datetime.now() - timedelta(hours=num_points)
    
    for i in range(num_points):
        # Random walk with drift
        change_pct = random.gauss(trend, volatility)
        current_value *= (1 + change_pct)
        
        timestamp = start + timedelta(minutes=i * interval_minutes)
        pnl = current_value - start_value
        pnl_pct = (current_value / start_value - 1) * 100
        
        data.append({
            "timestamp": timestamp.isoformat(),
            "value": round(current_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })
    
    return data


def _get_time_params(time_range: str) -> tuple[int, int, datetime]:
    """Get number of points and interval based on time range."""
    now = datetime.now()
    
    if time_range == "1D":
        # 1 day: 1 point per 5 minutes = 288 points
        return 288, 5, now - timedelta(days=1)
    elif time_range == "1W":
        # 1 week: 1 point per hour = 168 points
        return 168, 60, now - timedelta(weeks=1)
    elif time_range == "1M":
        # 1 month: 1 point per 4 hours = 180 points
        return 180, 240, now - timedelta(days=30)
    elif time_range == "3M":
        # 3 months: 1 point per day = 90 points
        return 90, 1440, now - timedelta(days=90)
    elif time_range == "6M":
        # 6 months: 1 point per day = 180 points
        return 180, 1440, now - timedelta(days=180)
    elif time_range == "1Y":
        # 1 year: 1 point per day = 365 points
        return 365, 1440, now - timedelta(days=365)
    elif time_range == "YTD":
        # Year to date: 1 point per day
        start_of_year = datetime(now.year, 1, 1)
        days = (now - start_of_year).days
        return max(days, 1), 1440, start_of_year
    elif time_range == "ALL":
        # All time: 1 point per week for 2 years
        return 104, 10080, now - timedelta(days=730)
    else:
        # Default to 1 day
        return 288, 5, now - timedelta(days=1)


@router.get("/bot/{bot_id}")
async def get_bot_performance(
    bot_id: str,
    time_range: str = Query("1D", pattern="^(1D|1W|1M|3M|6M|1Y|YTD|ALL)$"),
) -> dict:
    """
    Get performance data for a specific bot.
    
    Time ranges:
    - 1D: Last 24 hours (5-minute intervals)
    - 1W: Last week (hourly)
    - 1M: Last month (4-hour intervals)
    - 3M: Last 3 months (daily)
    - 6M: Last 6 months (daily)
    - 1Y: Last year (daily)
    - YTD: Year to date (daily)
    - ALL: All available data (weekly)
    """
    num_points, interval, start_time = _get_time_params(time_range)
    
    # Get bot info (in real implementation, fetch from bot manager)
    from src.bot.bot_manager import get_bot_manager
    manager = get_bot_manager()
    bot = manager.get_bot(bot_id)
    
    if not bot:
        return {"error": f"Bot {bot_id} not found"}
    
    # Generate performance data
    # In real implementation, this would come from trade history database
    initial_value = 10000  # Starting portfolio value
    
    # Use bot's actual P&L if available, otherwise simulate
    if hasattr(bot, 'total_pnl'):
        trend = 0.0001 if bot.total_pnl >= 0 else -0.00005
    else:
        trend = random.uniform(-0.0001, 0.0003)
    
    data = _generate_performance_data(
        start_value=initial_value,
        num_points=num_points,
        volatility=0.015,
        trend=trend,
        start_time=start_time,
        interval_minutes=interval,
    )
    
    # Calculate summary
    if data:
        start_val = data[0]["value"]
        end_val = data[-1]["value"]
        total_pnl = end_val - start_val
        total_pnl_pct = (end_val / start_val - 1) * 100
        
        # Find max drawdown
        peak = start_val
        max_dd = 0
        for point in data:
            peak = max(peak, point["value"])
            dd = (peak - point["value"]) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Calculate volatility
        returns = []
        for i in range(1, len(data)):
            ret = (data[i]["value"] / data[i-1]["value"]) - 1
            returns.append(ret)
        
        if returns:
            import statistics
            volatility = statistics.stdev(returns) * math.sqrt(252) * 100  # Annualized
        else:
            volatility = 0
        
        summary = {
            "start_value": round(start_val, 2),
            "end_value": round(end_val, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "volatility_pct": round(volatility, 2),
            "num_trades": random.randint(10, 100),
            "win_rate": round(random.uniform(0.45, 0.65), 2),
        }
    else:
        summary = {}
    
    return {
        "bot_id": bot_id,
        "bot_name": bot.config.name if bot else bot_id,
        "time_range": time_range,
        "data_points": data,
        "summary": summary,
    }


@router.get("/position/{symbol}")
async def get_position_performance(
    symbol: str,
    time_range: str = Query("1D", pattern="^(1D|1W|1M|3M|6M|1Y|YTD|ALL)$"),
) -> dict:
    """
    Get performance data for a specific position/symbol.
    
    Returns price history and P&L for the position.
    """
    num_points, interval, start_time = _get_time_params(time_range)
    
    # Get base price (in real implementation, fetch from data provider)
    # Using rough approximations for demo
    base_prices = {
        "AAPL": 175.0, "GOOGL": 140.0, "MSFT": 375.0, "AMZN": 155.0,
        "TSLA": 250.0, "NVDA": 480.0, "META": 350.0, "NFLX": 450.0,
        "SPY": 475.0, "QQQ": 400.0, "BTC": 42000.0, "ETH": 2200.0,
    }
    base_price = base_prices.get(symbol.upper(), 100.0)
    
    # Generate price data
    data = _generate_performance_data(
        start_value=base_price,
        num_points=num_points,
        volatility=0.02,
        trend=random.uniform(-0.0001, 0.0002),
        start_time=start_time,
        interval_minutes=interval,
    )
    
    # Add price-specific fields
    for point in data:
        point["price"] = point.pop("value")
        point["change"] = point["pnl"]
        point["change_pct"] = point["pnl_pct"]
    
    # Calculate summary
    if data:
        start_price = data[0]["price"]
        end_price = data[-1]["price"]
        high = max(p["price"] for p in data)
        low = min(p["price"] for p in data)
        
        summary = {
            "symbol": symbol.upper(),
            "start_price": round(start_price, 2),
            "current_price": round(end_price, 2),
            "change": round(end_price - start_price, 2),
            "change_pct": round((end_price / start_price - 1) * 100, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "range_pct": round((high - low) / low * 100, 2),
        }
    else:
        summary = {}
    
    return {
        "symbol": symbol.upper(),
        "time_range": time_range,
        "data_points": data,
        "summary": summary,
    }


@router.get("/positions/all")
async def get_all_positions_performance(
    time_range: str = Query("1D", pattern="^(1D|1W|1M|3M|6M|1Y|YTD|ALL)$"),
    sort_by: str = Query("symbol", pattern="^(symbol|last_price|change_pct|equity|today_return|total_return|total_pct)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
) -> dict:
    """
    Get performance data for all positions with sorting.
    
    Sort options:
    - symbol: Alphabetically by symbol
    - last_price: By current price
    - change_pct: By percent change
    - equity: By position value
    - today_return: By today's return
    - total_return: By total return
    - total_pct: By total percent change
    """
    # Sample positions (in real implementation, fetch from positions tracker)
    positions = [
        {"symbol": "AAPL", "quantity": 50, "avg_cost": 165.0},
        {"symbol": "GOOGL", "quantity": 30, "avg_cost": 135.0},
        {"symbol": "MSFT", "quantity": 25, "avg_cost": 360.0},
        {"symbol": "AMZN", "quantity": 40, "avg_cost": 145.0},
        {"symbol": "TSLA", "quantity": 20, "avg_cost": 240.0},
        {"symbol": "NVDA", "quantity": 15, "avg_cost": 450.0},
        {"symbol": "META", "quantity": 35, "avg_cost": 320.0},
        {"symbol": "SPY", "quantity": 100, "avg_cost": 460.0},
    ]
    
    # Generate current prices and performance
    result_positions = []
    for pos in positions:
        symbol = pos["symbol"]
        quantity = pos["quantity"]
        avg_cost = pos["avg_cost"]
        
        # Simulate current price
        price_change = random.uniform(-0.05, 0.08)
        last_price = avg_cost * (1 + price_change)
        
        # Calculate metrics
        equity = last_price * quantity
        cost_basis = avg_cost * quantity
        total_return = equity - cost_basis
        total_pct = (equity / cost_basis - 1) * 100
        today_return = equity * random.uniform(-0.03, 0.04)
        today_pct = (today_return / equity) * 100
        
        result_positions.append({
            "symbol": symbol,
            "quantity": quantity,
            "avg_cost": round(avg_cost, 2),
            "last_price": round(last_price, 2),
            "change_pct": round(price_change * 100, 2),
            "equity": round(equity, 2),
            "cost_basis": round(cost_basis, 2),
            "today_return": round(today_return, 2),
            "today_pct": round(today_pct, 2),
            "total_return": round(total_return, 2),
            "total_pct": round(total_pct, 2),
        })
    
    # Sort positions
    sort_key_map = {
        "symbol": lambda x: x["symbol"],
        "last_price": lambda x: x["last_price"],
        "change_pct": lambda x: x["change_pct"],
        "equity": lambda x: x["equity"],
        "today_return": lambda x: x["today_return"],
        "total_return": lambda x: x["total_return"],
        "total_pct": lambda x: x["total_pct"],
    }
    
    sort_key = sort_key_map.get(sort_by, lambda x: x["symbol"])
    reverse = sort_order == "desc"
    result_positions.sort(key=sort_key, reverse=reverse)
    
    # Calculate totals
    total_equity = sum(p["equity"] for p in result_positions)
    total_cost = sum(p["cost_basis"] for p in result_positions)
    total_today = sum(p["today_return"] for p in result_positions)
    total_all_time = sum(p["total_return"] for p in result_positions)
    
    return {
        "time_range": time_range,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "positions": result_positions,
        "totals": {
            "equity": round(total_equity, 2),
            "cost_basis": round(total_cost, 2),
            "today_return": round(total_today, 2),
            "today_pct": round((total_today / total_equity) * 100, 2) if total_equity else 0,
            "total_return": round(total_all_time, 2),
            "total_pct": round((total_equity / total_cost - 1) * 100, 2) if total_cost else 0,
        },
        "count": len(result_positions),
    }


@router.get("/summary")
async def get_performance_summary() -> dict:
    """
    Get overall performance summary across all bots and positions.
    """
    return {
        "portfolio_value": round(random.uniform(80000, 120000), 2),
        "day_change": round(random.uniform(-2000, 3000), 2),
        "day_change_pct": round(random.uniform(-2, 3), 2),
        "total_return": round(random.uniform(5000, 20000), 2),
        "total_return_pct": round(random.uniform(5, 20), 2),
        "best_performer": {
            "symbol": "NVDA",
            "return_pct": round(random.uniform(10, 50), 2),
        },
        "worst_performer": {
            "symbol": "TSLA",
            "return_pct": round(random.uniform(-20, -5), 2),
        },
        "active_bots": 37,
        "total_trades_today": random.randint(10, 50),
        "win_rate_today": round(random.uniform(0.45, 0.65), 2),
    }

