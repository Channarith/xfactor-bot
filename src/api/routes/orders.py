"""
Orders API routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class OrderRequest(BaseModel):
    """Order request model."""
    symbol: str
    side: str  # BUY or SELL
    quantity: float
    order_type: str = "MKT"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    strategy: str = "manual"


@router.get("/")
async def get_orders():
    """Get all orders."""
    return {
        "open": [],
        "filled": [],
        "cancelled": [],
    }


@router.get("/open")
async def get_open_orders():
    """Get open orders."""
    return {"orders": []}


@router.post("/")
async def submit_order(order: OrderRequest):
    """Submit a new order."""
    # TODO: Submit through order manager
    return {
        "status": "submitted",
        "order_id": "pending",
        "symbol": order.symbol,
        "side": order.side,
        "quantity": order.quantity,
    }


@router.delete("/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an order."""
    return {
        "status": "cancelled",
        "order_id": order_id,
    }


@router.delete("/")
async def cancel_all_orders():
    """Cancel all open orders."""
    return {
        "status": "cancelled",
        "count": 0,
    }

