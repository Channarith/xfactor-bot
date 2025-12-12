"""
Configuration API routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from src.config.settings import get_settings

router = APIRouter()


class ParameterUpdate(BaseModel):
    """Parameter update request."""
    value: Any


@router.get("/parameters")
async def get_all_parameters():
    """Get all configurable parameters."""
    settings = get_settings()
    
    return {
        "trading": {
            "mode": settings.trading_mode,
            "max_position_size": settings.max_position_size,
            "max_portfolio_pct": settings.max_portfolio_pct,
            "max_open_positions": settings.max_open_positions,
        },
        "risk": {
            "daily_loss_limit_pct": settings.daily_loss_limit_pct,
            "weekly_loss_limit_pct": settings.weekly_loss_limit_pct,
            "max_drawdown_pct": settings.max_drawdown_pct,
            "vix_pause_threshold": settings.vix_pause_threshold,
        },
        "strategies": {
            "technical_weight": settings.technical_strategy_weight,
            "momentum_weight": settings.momentum_strategy_weight,
            "news_sentiment_weight": settings.news_sentiment_weight,
        },
        "technical": {
            "rsi_oversold": settings.rsi_oversold,
            "rsi_overbought": settings.rsi_overbought,
            "ma_fast_period": settings.ma_fast_period,
            "ma_slow_period": settings.ma_slow_period,
        },
        "news": {
            "min_confidence": settings.news_min_confidence,
            "min_urgency": settings.news_min_urgency,
            "sentiment_threshold": settings.news_sentiment_threshold,
            "llm_enabled": settings.llm_analysis_enabled,
        },
    }


@router.patch("/parameters/{category}/{parameter}")
async def update_parameter(category: str, parameter: str, update: ParameterUpdate):
    """Update a specific parameter."""
    # In production, this would update a mutable config store
    # For now, return the requested change
    return {
        "status": "updated",
        "category": category,
        "parameter": parameter,
        "value": update.value,
    }


@router.get("/status")
async def get_system_status():
    """Get overall system status."""
    return {
        "trading_enabled": True,
        "mode": "paper",
        "ibkr_connected": False,  # TODO: Check actual connection
        "database_connected": False,
        "redis_connected": False,
        "uptime_seconds": 0,
    }

