"""
Risk management API routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class KillSwitchRequest(BaseModel):
    """Kill switch request."""
    reason: str
    close_positions: bool = False


class ResumeRequest(BaseModel):
    """Resume trading request."""
    confirmation: str


@router.get("/status")
async def get_risk_status():
    """Get current risk status."""
    return {
        "trading_allowed": True,
        "paused": False,
        "killed": False,
        "daily_pnl": 0,
        "daily_pnl_pct": 0,
        "current_drawdown_pct": 0,
        "vix": 0,
        "open_positions": 0,
    }


@router.post("/pause")
async def pause_trading():
    """Pause new trading (keep positions)."""
    return {"status": "paused"}


@router.post("/resume")
async def resume_trading(request: ResumeRequest):
    """Resume trading after pause."""
    if request.confirmation != "CONFIRM":
        raise HTTPException(status_code=400, detail="Invalid confirmation")
    return {"status": "resumed"}


@router.post("/kill-switch")
async def activate_kill_switch(request: KillSwitchRequest):
    """Activate emergency kill switch."""
    return {
        "status": "activated",
        "reason": request.reason,
        "positions_closed": request.close_positions,
    }


@router.post("/kill-switch/reset")
async def reset_kill_switch(request: ResumeRequest):
    """Reset kill switch (requires CONFIRM_DEACTIVATE)."""
    if request.confirmation != "CONFIRM_DEACTIVATE":
        raise HTTPException(status_code=400, detail="Invalid confirmation")
    return {"status": "reset"}


@router.get("/limits")
async def get_risk_limits():
    """Get current risk limits."""
    return {
        "max_position_size": 50000,
        "max_portfolio_pct": 5,
        "daily_loss_limit_pct": 3,
        "weekly_loss_limit_pct": 7,
        "max_drawdown_pct": 10,
        "vix_pause_threshold": 35,
        "max_open_positions": 50,
    }

