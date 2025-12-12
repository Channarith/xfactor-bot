"""
Bot management API routes.

IMPORTANT: Static routes (like /start-all, /templates) MUST be defined BEFORE
parameterized routes (like /{bot_id}) to prevent path parameter from capturing
the static path segments.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from src.api.auth import AdminUser, get_admin_user
from src.bot.bot_manager import get_bot_manager
from src.bot.bot_instance import BotConfig

router = APIRouter()


class CreateBotRequest(BaseModel):
    """Request to create a new bot."""
    name: str = Field(..., min_length=1, max_length=50)
    description: str = ""
    bot_id: Optional[str] = None
    symbols: list[str] = Field(default_factory=lambda: ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"])
    strategies: list[str] = Field(default_factory=lambda: ["Technical", "Momentum"])
    strategy_weights: dict[str, float] = Field(default_factory=lambda: {
        "Technical": 0.6,
        "Momentum": 0.5,
        "MeanReversion": 0.4,
        "NewsSentiment": 0.4,
    })
    max_position_size: float = 25000.0
    max_positions: int = 10
    max_daily_loss_pct: float = 2.0
    trade_frequency_seconds: int = 60
    enable_news_trading: bool = True


class UpdateBotRequest(BaseModel):
    """Request to update bot configuration."""
    name: Optional[str] = None
    description: Optional[str] = None
    symbols: Optional[list[str]] = None
    strategies: Optional[list[str]] = None
    strategy_weights: Optional[dict[str, float]] = None
    max_position_size: Optional[float] = None
    max_positions: Optional[int] = None
    max_daily_loss_pct: Optional[float] = None
    trade_frequency_seconds: Optional[int] = None
    enable_news_trading: Optional[bool] = None


# =========================================================================
# STATIC ROUTES - Must be defined BEFORE parameterized routes!
# =========================================================================

@router.get("/")
async def list_bots():
    """Get list of all bots."""
    manager = get_bot_manager()
    return manager.get_status()


@router.get("/summary")
async def get_bots_summary():
    """Get lightweight summary of all bots."""
    manager = get_bot_manager()
    return {
        "bots": manager.get_bot_summary(),
        "total": manager.bot_count,
        "running": manager.running_count,
        "max": manager.MAX_BOTS,
    }


@router.get("/templates")
async def get_bot_templates():
    """Get pre-configured bot templates."""
    return {
        "templates": [
            {
                "id": "aggressive_tech",
                "name": "Aggressive Tech Trader",
                "description": "High-frequency trading on tech stocks",
                "config": {
                    "symbols": ["NVDA", "AMD", "TSLA", "META", "GOOGL"],
                    "strategies": ["Technical", "Momentum", "NewsSentiment"],
                    "max_position_size": 50000,
                    "max_daily_loss_pct": 5.0,
                    "trade_frequency_seconds": 30,
                },
            },
            {
                "id": "conservative_etf",
                "name": "Conservative ETF Trader",
                "description": "Low-frequency ETF trading",
                "config": {
                    "symbols": ["SPY", "QQQ", "IWM", "DIA", "VTI"],
                    "strategies": ["Technical", "MeanReversion"],
                    "max_position_size": 25000,
                    "max_daily_loss_pct": 1.0,
                    "trade_frequency_seconds": 300,
                },
            },
            {
                "id": "news_momentum",
                "name": "News Momentum Trader",
                "description": "React to breaking news",
                "config": {
                    "symbols": ["AAPL", "MSFT", "AMZN", "NVDA", "TSLA"],
                    "strategies": ["NewsSentiment", "Momentum"],
                    "max_position_size": 30000,
                    "max_daily_loss_pct": 3.0,
                    "trade_frequency_seconds": 60,
                    "enable_news_trading": True,
                    "news_sentiment_threshold": 0.6,
                },
            },
            {
                "id": "mean_reversion",
                "name": "Mean Reversion Trader",
                "description": "Fade extreme moves",
                "config": {
                    "symbols": ["SPY", "QQQ", "IWM", "XLF", "XLE"],
                    "strategies": ["MeanReversion", "Technical"],
                    "max_position_size": 20000,
                    "max_daily_loss_pct": 2.0,
                    "trade_frequency_seconds": 120,
                },
            },
            {
                "id": "international_adr",
                "name": "International ADR Trader",
                "description": "Trade international stocks",
                "config": {
                    "symbols": ["BABA", "TSM", "NVO", "ASML", "SAP"],
                    "strategies": ["Technical", "NewsSentiment"],
                    "max_position_size": 25000,
                    "max_daily_loss_pct": 2.5,
                    "trade_frequency_seconds": 180,
                },
            },
        ]
    }


@router.post("/", status_code=201)
async def create_bot(
    request: CreateBotRequest,
    admin: AdminUser = Depends(get_admin_user),
):
    """Create a new trading bot (requires admin)."""
    manager = get_bot_manager()
    
    if not manager.can_create_bot:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {manager.MAX_BOTS} bots reached",
        )
    
    config = BotConfig(
        name=request.name,
        description=request.description,
        symbols=request.symbols,
        strategies=request.strategies,
        strategy_weights=request.strategy_weights,
        max_position_size=request.max_position_size,
        max_positions=request.max_positions,
        max_daily_loss_pct=request.max_daily_loss_pct,
        trade_frequency_seconds=request.trade_frequency_seconds,
        enable_news_trading=request.enable_news_trading,
    )
    
    bot = manager.create_bot(config, request.bot_id)
    
    if not bot:
        raise HTTPException(status_code=400, detail="Failed to create bot")
    
    return {
        "success": True,
        "bot": bot.get_status(),
    }


# =========================================================================
# Bulk Operations - MUST be before /{bot_id} routes!
# =========================================================================

@router.post("/start-all")
async def start_all_bots(admin: AdminUser = Depends(get_admin_user)):
    """Start all stopped bots (requires admin)."""
    manager = get_bot_manager()
    results = manager.start_all()
    
    return {
        "results": results,
        "started": sum(1 for v in results.values() if v),
    }


@router.post("/stop-all")
async def stop_all_bots(admin: AdminUser = Depends(get_admin_user)):
    """Stop all running bots (requires admin)."""
    manager = get_bot_manager()
    results = manager.stop_all()
    
    return {
        "results": results,
        "stopped": sum(1 for v in results.values() if v),
    }


@router.post("/pause-all")
async def pause_all_bots(admin: AdminUser = Depends(get_admin_user)):
    """Pause all running bots (requires admin)."""
    manager = get_bot_manager()
    results = manager.pause_all()
    
    return {
        "results": results,
        "paused": sum(1 for v in results.values() if v),
    }


@router.post("/resume-all")
async def resume_all_bots(admin: AdminUser = Depends(get_admin_user)):
    """Resume all paused bots (requires admin)."""
    manager = get_bot_manager()
    results = manager.resume_all()
    
    return {
        "results": results,
        "resumed": sum(1 for v in results.values() if v),
    }


# =========================================================================
# Parameterized Routes - MUST be AFTER static routes!
# =========================================================================

@router.get("/{bot_id}")
async def get_bot(bot_id: str):
    """Get a specific bot's status."""
    manager = get_bot_manager()
    bot = manager.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return bot.get_status()


@router.patch("/{bot_id}")
async def update_bot(
    bot_id: str,
    request: UpdateBotRequest,
    admin: AdminUser = Depends(get_admin_user),
):
    """Update a bot's configuration (requires admin)."""
    manager = get_bot_manager()
    bot = manager.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    updates = request.model_dump(exclude_unset=True)
    bot.update_config(updates)
    
    return {
        "success": True,
        "bot": bot.get_status(),
    }


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: str,
    admin: AdminUser = Depends(get_admin_user),
):
    """Delete a bot (requires admin)."""
    manager = get_bot_manager()
    
    if not manager.delete_bot(bot_id):
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return {"success": True, "message": f"Bot {bot_id} deleted"}


# =========================================================================
# Bot Control Operations (Parameterized)
# =========================================================================

@router.post("/{bot_id}/start")
async def start_bot(
    bot_id: str,
    admin: AdminUser = Depends(get_admin_user),
):
    """Start a bot (requires admin)."""
    manager = get_bot_manager()
    bot = manager.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if not bot.start():
        raise HTTPException(status_code=400, detail="Failed to start bot")
    
    return {"success": True, "status": bot.status.value}


@router.post("/{bot_id}/stop")
async def stop_bot(
    bot_id: str,
    admin: AdminUser = Depends(get_admin_user),
):
    """Stop a bot (requires admin)."""
    manager = get_bot_manager()
    bot = manager.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if not bot.stop():
        raise HTTPException(status_code=400, detail="Failed to stop bot")
    
    return {"success": True, "status": bot.status.value}


@router.post("/{bot_id}/pause")
async def pause_bot(
    bot_id: str,
    admin: AdminUser = Depends(get_admin_user),
):
    """Pause a bot (requires admin)."""
    manager = get_bot_manager()
    bot = manager.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if not bot.pause():
        raise HTTPException(status_code=400, detail="Failed to pause bot")
    
    return {"success": True, "status": bot.status.value}


@router.post("/{bot_id}/resume")
async def resume_bot(
    bot_id: str,
    admin: AdminUser = Depends(get_admin_user),
):
    """Resume a paused bot (requires admin)."""
    manager = get_bot_manager()
    bot = manager.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if not bot.resume():
        raise HTTPException(status_code=400, detail="Failed to resume bot")
    
    return {"success": True, "status": bot.status.value}
