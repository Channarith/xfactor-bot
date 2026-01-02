"""
Bot management API routes.

IMPORTANT: Static routes (like /start-all, /templates) MUST be defined BEFORE
parameterized routes (like /{bot_id}) to prevent path parameter from capturing
the static path segments.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional

from loguru import logger
from src.api.auth import AdminUser, get_admin_user
from src.bot.bot_manager import get_bot_manager
from src.bot.bot_instance import BotConfig, get_bot_activity_log, clear_bot_activity_log

router = APIRouter()


class CreateBotRequest(BaseModel):
    """Request to create a new bot."""
    name: str = Field(..., min_length=1, max_length=50)
    description: str = ""
    bot_id: Optional[str] = None
    symbols: list[str] = Field(default_factory=lambda: ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"])
    
    # All available strategies with defaults
    strategies: list[str] = Field(default_factory=lambda: [
        "Technical", "Momentum", "MeanReversion", "NewsSentiment",
        "Breakout", "TrendFollowing", "Scalping", "SwingTrading",
        "VWAP", "RSI", "MACD", "BollingerBands", "MovingAverageCrossover",
        "InsiderFollowing", "SocialSentiment", "AIAnalysis"
    ])
    strategy_weights: dict[str, float] = Field(default_factory=lambda: {
        "Technical": 0.6,
        "Momentum": 0.5,
        "MeanReversion": 0.4,
        "NewsSentiment": 0.4,
        "Breakout": 0.5,
        "TrendFollowing": 0.5,
        "Scalping": 0.3,
        "SwingTrading": 0.5,
        "VWAP": 0.4,
        "RSI": 0.5,
        "MACD": 0.5,
        "BollingerBands": 0.4,
        "MovingAverageCrossover": 0.5,
        "InsiderFollowing": 0.3,
        "SocialSentiment": 0.3,
        "AIAnalysis": 0.6,
    })
    
    # AI Strategy Prompt - describe strategy in natural language
    ai_strategy_prompt: str = Field(
        default="",
        description="Natural language description of your trading strategy. The AI will interpret this to configure the bot."
    )
    
    # Risk parameters
    max_position_size: float = 25000.0
    max_positions: int = 10
    max_daily_loss_pct: float = 2.0
    trade_frequency_seconds: int = 60
    enable_news_trading: bool = True
    
    # Instrument type
    instrument_type: str = "stock"  # stock, options, futures, crypto
    
    # Options settings (if instrument_type is options)
    options_type: str = "call"
    options_dte_min: int = 7
    options_dte_max: int = 45
    
    # Futures settings (if instrument_type is futures)
    futures_contracts: list[str] = Field(default_factory=list)
    futures_use_micro: bool = True


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


@router.get("/debug")
async def get_bot_debug_info():
    """
    Get debug information for all bots including activity logs.
    Useful for troubleshooting why bots are not trading.
    """
    manager = get_bot_manager()
    bots = manager.get_all_bots()
    
    from src.brokers.registry import get_broker_registry
    registry = get_broker_registry()
    
    debug_info = {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total_bots": manager.bot_count,
            "running_bots": manager.running_count,
            "max_bots": manager.MAX_BOTS,
        },
        "broker_status": {
            "connected_brokers": list(registry.connected_brokers.keys()) if registry.connected_brokers else [],
            "default_broker": registry.get_default_broker().name if registry.get_default_broker() else None,
        },
        "bots": [],
        "recent_activity": get_bot_activity_log(limit=50),
    }
    
    for bot in bots:
        status = bot.get_status()
        bot_debug = {
            "id": bot.id,
            "name": bot.config.name,
            "status": bot.status.value,
            "paper_trading": bot.config.use_paper_trading,
            "symbols": bot.config.symbols,
            "trade_frequency_seconds": bot.config.trade_frequency_seconds,
            "stats": status.get("stats", {}),
            "issues": [],
        }
        
        # Identify potential issues
        if bot.status.value == "running":
            if bot.stats.cycles_completed == 0:
                bot_debug["issues"].append("Bot is running but has not completed any trading cycles")
            if bot.stats.signals_generated == 0 and bot.stats.cycles_completed > 5:
                bot_debug["issues"].append("Bot has run multiple cycles but generated no signals")
            if bot.stats.orders_submitted == 0 and bot.stats.signals_generated > 0:
                bot_debug["issues"].append("Signals generated but no orders submitted")
            if bot.stats.orders_rejected > 0:
                bot_debug["issues"].append(f"{bot.stats.orders_rejected} orders rejected")
            if not registry.connected_brokers:
                bot_debug["issues"].append("No broker connected - trades cannot be executed")
        
        debug_info["bots"].append(bot_debug)
    
    return debug_info


@router.get("/activity")
async def get_activity_log(
    bot_id: Optional[str] = None,
    limit: int = 100,
):
    """
    Get bot activity log entries.
    
    Args:
        bot_id: Optional bot ID to filter by
        limit: Maximum number of entries (default 100, max 500)
    """
    from datetime import datetime
    
    limit = min(limit, 500)
    entries = get_bot_activity_log(bot_id, limit)
    
    return {
        "entries": entries,
        "count": len(entries),
        "filter": {"bot_id": bot_id} if bot_id else None,
    }


@router.delete("/activity")
async def clear_activity_log(admin: AdminUser = Depends(get_admin_user)):
    """Clear the activity log (requires admin)."""
    clear_bot_activity_log()
    return {"success": True, "message": "Activity log cleared"}


@router.get("/strategies")
async def get_available_strategies():
    """Get all available trading strategies."""
    from src.bot.bot_instance import ALL_STRATEGIES, DEFAULT_STRATEGY_WEIGHTS
    
    strategies = []
    for strat in ALL_STRATEGIES:
        strategies.append({
            "name": strat,
            "default_weight": DEFAULT_STRATEGY_WEIGHTS.get(strat, 0.5),
            "description": get_strategy_description(strat),
            "category": get_strategy_category(strat),
        })
    
    return {
        "strategies": strategies,
        "count": len(strategies),
        "categories": list(set(s["category"] for s in strategies)),
    }


def get_strategy_description(name: str) -> str:
    """Get description for a strategy."""
    descriptions = {
        "Technical": "Traditional technical analysis with RSI, MACD, and chart patterns",
        "Momentum": "Trade in direction of strong price and volume momentum",
        "MeanReversion": "Fade extreme moves expecting price to revert to mean",
        "NewsSentiment": "Trade based on news headlines and sentiment analysis",
        "Breakout": "Enter on price breakouts from consolidation patterns",
        "TrendFollowing": "Follow established trends with trend-continuation signals",
        "Scalping": "Ultra short-term trades capturing small price movements",
        "SwingTrading": "Multi-day positions capturing swing highs and lows",
        "VWAP": "Trade relative to volume-weighted average price",
        "RSI": "Overbought/oversold signals using Relative Strength Index",
        "MACD": "Moving Average Convergence Divergence crossover signals",
        "BollingerBands": "Trade Bollinger Band breakouts and mean reversions",
        "MovingAverageCrossover": "SMA/EMA crossover buy and sell signals",
        "InsiderFollowing": "Follow insider buying/selling activity",
        "SocialSentiment": "Trade based on social media buzz and sentiment",
        "AIAnalysis": "AI-powered pattern recognition and prediction",
    }
    return descriptions.get(name, "")


def get_strategy_category(name: str) -> str:
    """Get category for a strategy."""
    categories = {
        "Technical": "Technical Analysis",
        "Momentum": "Momentum",
        "MeanReversion": "Mean Reversion",
        "NewsSentiment": "Sentiment",
        "Breakout": "Technical Analysis",
        "TrendFollowing": "Momentum",
        "Scalping": "Short-Term",
        "SwingTrading": "Medium-Term",
        "VWAP": "Technical Analysis",
        "RSI": "Technical Analysis",
        "MACD": "Technical Analysis",
        "BollingerBands": "Technical Analysis",
        "MovingAverageCrossover": "Technical Analysis",
        "InsiderFollowing": "Sentiment",
        "SocialSentiment": "Sentiment",
        "AIAnalysis": "AI/ML",
    }
    return categories.get(name, "Other")


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
    
    # If AI strategy prompt is provided, interpret it
    ai_interpreted_config = {}
    if request.ai_strategy_prompt:
        ai_interpreted_config = await interpret_strategy_prompt(request.ai_strategy_prompt)
    
    # Determine instrument type
    from src.bot.bot_instance import InstrumentType
    instrument_type = InstrumentType.STOCK
    if request.instrument_type == "options":
        instrument_type = InstrumentType.OPTIONS
    elif request.instrument_type == "futures":
        instrument_type = InstrumentType.FUTURES
    elif request.instrument_type == "crypto":
        instrument_type = InstrumentType.CRYPTO
    
    config = BotConfig(
        name=request.name,
        description=request.description,
        ai_strategy_prompt=request.ai_strategy_prompt,
        ai_interpreted_config=ai_interpreted_config,
        instrument_type=instrument_type,
        symbols=request.symbols,
        strategies=request.strategies,
        strategy_weights=request.strategy_weights,
        max_position_size=request.max_position_size,
        max_positions=request.max_positions,
        max_daily_loss_pct=request.max_daily_loss_pct,
        trade_frequency_seconds=request.trade_frequency_seconds,
        enable_news_trading=request.enable_news_trading,
        options_type=request.options_type,
        options_dte_min=request.options_dte_min,
        options_dte_max=request.options_dte_max,
        futures_contracts=request.futures_contracts,
        futures_use_micro=request.futures_use_micro,
    )
    
    bot = manager.create_bot(config, request.bot_id)
    
    if not bot:
        raise HTTPException(status_code=400, detail="Failed to create bot")
    
    return {
        "success": True,
        "bot": bot.get_status(),
        "ai_interpretation": ai_interpreted_config if request.ai_strategy_prompt else None,
    }


async def interpret_strategy_prompt(prompt: str) -> dict:
    """
    Use AI to interpret a natural language strategy description
    and convert it to bot configuration parameters.
    """
    try:
        from src.ai.assistant import get_ai_assistant
        
        assistant = get_ai_assistant()
        
        interpretation_prompt = f"""Analyze this trading strategy description and extract configuration parameters.
Return a JSON object with the following structure:
{{
    "recommended_strategies": ["list of strategy names that match"],
    "strategy_weights": {{"strategy_name": weight_0_to_1}},
    "recommended_symbols": ["list of suggested symbols"],
    "risk_level": "low|medium|high|aggressive",
    "suggested_position_size": number,
    "suggested_max_positions": number,
    "trade_frequency": "scalping|intraday|swing|position",
    "interpretation": "Brief explanation of how I interpreted this strategy",
    "warnings": ["any risk warnings or concerns"]
}}

Available strategies:
- Technical: RSI, MACD, moving averages, chart patterns
- Momentum: Price momentum, volume momentum, relative strength
- MeanReversion: Oversold/overbought reversions, statistical arbitrage
- NewsSentiment: News-based trading, sentiment analysis
- Breakout: Price breakouts, volume breakouts, range expansion
- TrendFollowing: Trend identification, trend continuation
- Scalping: Ultra short-term, quick profits
- SwingTrading: Multi-day holds, swing highs/lows
- VWAP: Volume-weighted average price strategies
- RSI: RSI-based entry/exit signals
- MACD: MACD crossover strategies
- BollingerBands: Bollinger band breakouts and reversions
- MovingAverageCrossover: SMA/EMA crossover signals
- InsiderFollowing: Follow insider trading activity
- SocialSentiment: Social media sentiment, trending stocks
- AIAnalysis: AI-powered pattern recognition

User's strategy description:
"{prompt}"

Return ONLY the JSON object, no other text."""

        response = await assistant.chat(
            query=interpretation_prompt,
            session_id="strategy-interpreter",
            include_context=False,
        )
        
        # Try to parse the JSON response
        import json
        import re
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            config = json.loads(json_match.group())
            return config
        
        return {"interpretation": response, "error": "Could not parse structured response"}
        
    except Exception as e:
        logger.error(f"Failed to interpret strategy prompt: {e}")
        return {"error": str(e), "interpretation": "Failed to interpret strategy"}


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


@router.get("/{bot_id}/activity")
async def get_bot_activity(
    bot_id: str,
    limit: int = Query(50, ge=1, le=500),
):
    """Get activity log for a specific bot."""
    manager = get_bot_manager()
    bot = manager.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    entries = bot.get_activity_log(limit)
    
    return {
        "bot_id": bot_id,
        "bot_name": bot.config.name,
        "status": bot.status.value,
        "entries": entries,
        "count": len(entries),
    }


@router.get("/{bot_id}/debug")
async def get_single_bot_debug(bot_id: str):
    """Get detailed debug information for a specific bot."""
    manager = get_bot_manager()
    bot = manager.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    from src.brokers.registry import get_broker_registry
    registry = get_broker_registry()
    
    # Get full status
    status = bot.get_status()
    
    # Check for issues
    issues = []
    warnings = []
    
    if bot.status.value == "created":
        issues.append("Bot has not been started yet")
    elif bot.status.value == "stopped":
        issues.append("Bot is stopped")
    elif bot.status.value == "paused":
        warnings.append("Bot is paused")
    elif bot.status.value == "running":
        if not registry.connected_brokers:
            issues.append("No broker connected - trades cannot execute")
        if bot.stats.cycles_completed == 0:
            warnings.append("Bot has not completed any cycles yet")
        elif bot.stats.signals_generated == 0:
            warnings.append(f"No signals generated in {bot.stats.cycles_completed} cycles")
        if bot.stats.errors_count > 0:
            warnings.append(f"{bot.stats.errors_count} errors occurred")
    
    # Get broker info
    broker_info = None
    if registry.connected_brokers:
        broker = registry.get_default_broker()
        if broker:
            broker_info = {
                "name": broker.name,
                "connected": broker.is_connected,
                "broker_type": type(broker).__name__,
            }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "bot": status,
        "broker": broker_info,
        "issues": issues,
        "warnings": warnings,
        "recent_activity": bot.get_activity_log(20),
        "diagnostics": {
            "cycles_per_hour": round(bot.stats.cycles_completed / max(1, bot.uptime / 3600), 2) if bot.uptime > 0 else 0,
            "signal_rate": f"{bot.stats.signals_generated}/{bot.stats.symbols_analyzed} symbols" if bot.stats.symbols_analyzed > 0 else "N/A",
            "trade_success_rate": f"{bot.stats.orders_filled}/{bot.stats.orders_submitted}" if bot.stats.orders_submitted > 0 else "N/A",
            "uptime_formatted": format_duration(bot.uptime),
        }
    }


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m {int(seconds % 60)}s"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        return f"{days}d {hours}h"
