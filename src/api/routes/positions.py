"""
Positions API routes.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class PositionResponse(BaseModel):
    """Position response model."""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    sector: Optional[str] = None
    strategy: Optional[str] = None


@router.get("/")
async def get_all_positions():
    """Get all current positions."""
    # TODO: Get from position tracker
    return {
        "positions": [],
        "count": 0,
        "total_value": 0,
    }


@router.get("/summary")
async def get_portfolio_summary():
    """Get portfolio summary."""
    return {
        "total_value": 0,
        "cash": 0,
        "positions_value": 0,
        "unrealized_pnl": 0,
        "realized_pnl": 0,
        "daily_pnl": 0,
        "position_count": 0,
    }


@router.get("/exposure")
async def get_exposure():
    """Get portfolio exposure breakdown."""
    return {
        "by_sector": {},
        "by_strategy": {},
        "gross_exposure": 0,
        "net_exposure": 0,
    }


@router.get("/{symbol}")
async def get_position(symbol: str):
    """Get position for a specific symbol."""
    return {
        "symbol": symbol,
        "quantity": 0,
        "avg_cost": 0,
        "current_price": 0,
        "market_value": 0,
        "unrealized_pnl": 0,
    }

