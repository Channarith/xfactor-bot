"""
Strategy API Routes

Exposes endpoints for:
- Strategy templates library
- Visual strategy builder
- Volatility-adaptive stops
- Market regime detection
- Martingale position sizing
- Social trading
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from loguru import logger


router = APIRouter(prefix="/api/strategies", tags=["Strategies"])


# =============================================================================
# Strategy Templates
# =============================================================================

class TemplateSearchQuery(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    risk_level: Optional[str] = None


@router.get("/templates")
async def get_strategy_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    search: Optional[str] = Query(None, description="Search query"),
):
    """Get available strategy templates."""
    from src.strategies.templates import (
        get_all_templates,
        get_templates_by_category,
        get_templates_by_risk,
        search_templates,
        get_template_stats,
    )
    
    if search:
        templates = search_templates(search)
    elif category:
        templates = get_templates_by_category(category)
    elif risk_level:
        templates = get_templates_by_risk(risk_level)
    else:
        templates = get_all_templates()
    
    return {
        "templates": templates,
        "total": len(templates),
        "stats": get_template_stats(),
    }


@router.get("/templates/{template_id}")
async def get_template_details(template_id: str):
    """Get details for a specific template."""
    from src.strategies.templates import get_template
    
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template.to_dict()


# =============================================================================
# Volatility-Adaptive Stops
# =============================================================================

class AdaptiveStopsRequest(BaseModel):
    prices: List[Dict[str, float]] = Field(..., description="OHLCV price data")
    entry_price: float
    is_long: bool = True
    atr_period: int = 14
    sl_multiplier: float = 2.0
    tp_multiplier: float = 3.0


@router.post("/adaptive-stops/calculate")
async def calculate_adaptive_stops(request: AdaptiveStopsRequest):
    """Calculate volatility-adaptive stop loss and take profit levels."""
    import pandas as pd
    from src.strategies.volatility_adaptive import calculate_adaptive_stops
    
    # Convert price data to DataFrame
    df = pd.DataFrame(request.prices)
    
    if len(df) < request.atr_period + 5:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least {request.atr_period + 5} price bars"
        )
    
    stop_loss, take_profit, details = calculate_adaptive_stops(
        df=df,
        entry_price=request.entry_price,
        is_long=request.is_long,
        atr_period=request.atr_period,
        sl_multiplier=request.sl_multiplier,
        tp_multiplier=request.tp_multiplier,
    )
    
    return {
        "entry_price": request.entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "direction": "long" if request.is_long else "short",
        **details,
    }


# =============================================================================
# Market Regime Detection
# =============================================================================

class RegimeDetectionRequest(BaseModel):
    prices: List[Dict[str, float]] = Field(..., description="OHLCV price data")


@router.post("/regime/detect")
async def detect_market_regime(request: RegimeDetectionRequest):
    """Detect current market regime (trending vs ranging)."""
    import pandas as pd
    from src.strategies.market_regime import detect_regime
    
    df = pd.DataFrame(request.prices)
    
    if len(df) < 60:
        raise HTTPException(
            status_code=400,
            detail="Need at least 60 price bars for regime detection"
        )
    
    regime = detect_regime(df)
    
    return regime


@router.get("/regime/explanation")
async def get_regime_explanation():
    """Get explanation of different market regimes."""
    return {
        "regimes": {
            "strong_uptrend": {
                "description": "Strong bullish trend, high ADX (>25), +DI > -DI",
                "recommended_strategies": ["trend_following", "breakout"],
                "recommended_actions": ["buy dips", "trail stops", "add on breakouts"],
            },
            "weak_uptrend": {
                "description": "Mild bullish bias, moderate ADX (20-25)",
                "recommended_strategies": ["momentum", "trend_following"],
                "recommended_actions": ["smaller positions", "tighter stops"],
            },
            "ranging": {
                "description": "Sideways market, low ADX (<20) or BB squeeze",
                "recommended_strategies": ["mean_reversion", "range_trading"],
                "recommended_actions": ["buy support", "sell resistance"],
            },
            "weak_downtrend": {
                "description": "Mild bearish bias, moderate ADX (20-25)",
                "recommended_strategies": ["momentum", "trend_following"],
                "recommended_actions": ["smaller positions", "tighter stops"],
            },
            "strong_downtrend": {
                "description": "Strong bearish trend, high ADX (>25), -DI > +DI",
                "recommended_strategies": ["trend_following", "breakdown"],
                "recommended_actions": ["sell rallies", "trail stops", "add on breakdowns"],
            },
            "breakout": {
                "description": "Bollinger Band squeeze, potential breakout forming",
                "recommended_strategies": ["breakout", "volatility"],
                "recommended_actions": ["wait for direction", "enter on confirmation"],
            },
            "volatile": {
                "description": "High volatility, unclear direction",
                "recommended_strategies": ["reduce_exposure"],
                "recommended_actions": ["widen stops", "smaller positions", "wait for clarity"],
            },
        }
    }


# =============================================================================
# Martingale Position Sizing
# =============================================================================

class MartingaleConfigRequest(BaseModel):
    strategy_type: str = "classic"  # classic, anti, modified, fibonacci, dalembert
    base_size: float = 100.0
    multiplier: float = 2.0
    max_levels: int = 4
    max_drawdown: float = 20.0


class MartingaleTradeResult(BaseModel):
    won: bool
    pnl: float


@router.post("/martingale/create")
async def create_martingale_sizer(config: MartingaleConfigRequest):
    """Create a new Martingale position sizer."""
    from src.strategies.martingale import create_martingale_sizer
    
    sizer = create_martingale_sizer(
        strategy_type=config.strategy_type,
        base_size=config.base_size,
        multiplier=config.multiplier,
        max_levels=config.max_levels,
        max_drawdown=config.max_drawdown,
    )
    
    return {
        "status": sizer.get_status(),
        "warning": sizer.get_risk_warning(),
        "next_size": sizer.get_next_size(),
    }


@router.get("/martingale/types")
async def get_martingale_types():
    """Get available Martingale strategy types."""
    return {
        "types": [
            {
                "id": "classic",
                "name": "Classic Martingale",
                "description": "Double position after each loss. High risk, aims to recover all losses on single win.",
                "risk_level": "very_high",
            },
            {
                "id": "anti",
                "name": "Anti-Martingale (Paroli)",
                "description": "Double position after each win. Lower risk, captures winning streaks.",
                "risk_level": "moderate",
            },
            {
                "id": "modified",
                "name": "Modified Martingale",
                "description": "Custom multiplier (not 2x). Can be more conservative.",
                "risk_level": "high",
            },
            {
                "id": "fibonacci",
                "name": "Fibonacci Martingale",
                "description": "Use Fibonacci sequence (1,1,2,3,5,8...) for position sizing. Slower escalation.",
                "risk_level": "high",
            },
            {
                "id": "dalembert",
                "name": "D'Alembert",
                "description": "Add/subtract fixed amount instead of multiplying. Most conservative.",
                "risk_level": "moderate",
            },
        ],
        "warning": "⚠️ Martingale strategies carry significant risk. Use strict position limits and stop-loss levels."
    }


# =============================================================================
# Visual Strategy Builder
# =============================================================================

class VisualStrategyRequest(BaseModel):
    name: str
    description: str = ""
    nodes: List[Dict[str, Any]] = []
    connections: List[Dict[str, Any]] = []


@router.get("/visual-builder/node-templates")
async def get_node_templates():
    """Get available node templates for visual strategy builder."""
    from src.strategies.visual_builder import NODE_TEMPLATES
    return NODE_TEMPLATES


@router.post("/visual-builder/save")
async def save_visual_strategy(strategy: VisualStrategyRequest):
    """Save a visual strategy."""
    from src.strategies.visual_builder import VisualStrategy, get_visual_strategy_engine
    import uuid
    
    engine = get_visual_strategy_engine()
    
    vs = VisualStrategy(
        id=str(uuid.uuid4()),
        name=strategy.name,
        description=strategy.description,
    )
    
    engine.save_strategy(vs)
    
    return {
        "success": True,
        "strategy_id": vs.id,
        "message": f"Strategy '{strategy.name}' saved",
    }


@router.get("/visual-builder/list")
async def list_visual_strategies():
    """List all saved visual strategies."""
    from src.strategies.visual_builder import get_visual_strategy_engine
    
    engine = get_visual_strategy_engine()
    return engine.list_strategies()


@router.delete("/visual-builder/{strategy_id}")
async def delete_visual_strategy(strategy_id: str):
    """Delete a visual strategy."""
    from src.strategies.visual_builder import get_visual_strategy_engine
    
    engine = get_visual_strategy_engine()
    if engine.delete_strategy(strategy_id):
        return {"success": True, "message": "Strategy deleted"}
    raise HTTPException(status_code=404, detail="Strategy not found")


# =============================================================================
# Social Trading
# =============================================================================

@router.get("/social/leaderboard")
async def get_social_leaderboard(
    period: str = Query("30d", description="Time period (1d, 7d, 30d, 90d, 1y, all)"),
    asset_class: Optional[str] = Query(None, description="Filter by asset class"),
    limit: int = Query(10, description="Number of results"),
):
    """Get leaderboard of top performing strategies."""
    from src.social.trading import get_social_trading_platform
    
    platform = get_social_trading_platform()
    return {
        "period": period,
        "leaderboard": platform.get_leaderboard(period, asset_class, limit),
    }


@router.get("/social/strategies")
async def list_social_strategies(
    strategy_type: Optional[str] = None,
    asset_class: Optional[str] = None,
    risk_level: Optional[str] = None,
    min_return: Optional[float] = None,
    sort_by: str = "rating",
    limit: int = 50,
):
    """List and filter shared strategies."""
    from src.social.trading import get_social_trading_platform
    
    platform = get_social_trading_platform()
    return {
        "strategies": platform.list_strategies(
            strategy_type, asset_class, risk_level, min_return, sort_by, limit
        ),
    }


@router.get("/social/strategies/{strategy_id}")
async def get_social_strategy(strategy_id: str):
    """Get details of a shared strategy."""
    from src.social.trading import get_social_trading_platform
    
    platform = get_social_trading_platform()
    strategy = platform.get_strategy(strategy_id)
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return strategy.to_dict()


@router.get("/social/strategies/{strategy_id}/reviews")
async def get_strategy_reviews(strategy_id: str, limit: int = 20):
    """Get reviews for a strategy."""
    from src.social.trading import get_social_trading_platform
    
    platform = get_social_trading_platform()
    return {
        "reviews": platform.get_reviews(strategy_id, limit),
    }


@router.get("/social/search")
async def search_social_strategies(
    q: str = Query(..., description="Search query"),
    limit: int = 20,
):
    """Search shared strategies."""
    from src.social.trading import get_social_trading_platform
    
    platform = get_social_trading_platform()
    return {
        "query": q,
        "results": platform.search_strategies(q, limit),
    }


class FollowStrategyRequest(BaseModel):
    user_id: str
    strategy_id: str


@router.post("/social/follow")
async def follow_strategy(request: FollowStrategyRequest):
    """Follow a strategy."""
    from src.social.trading import get_social_trading_platform
    
    platform = get_social_trading_platform()
    if platform.follow_strategy(request.user_id, request.strategy_id):
        return {"success": True, "message": "Now following strategy"}
    raise HTTPException(status_code=400, detail="Could not follow strategy")


class CopyStrategyRequest(BaseModel):
    copier_id: str
    strategy_id: str
    copy_mode: str = "scaled"
    scale_factor: float = 1.0
    max_position_size: float = 1000.0


@router.post("/social/copy")
async def start_copying_strategy(request: CopyStrategyRequest):
    """Start copying a strategy."""
    from src.social.trading import get_social_trading_platform, CopyMode
    
    platform = get_social_trading_platform()
    
    try:
        copy_mode = CopyMode(request.copy_mode)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid copy mode")
    
    relationship = platform.start_copying(
        request.copier_id,
        request.strategy_id,
        copy_mode,
        request.scale_factor,
        request.max_position_size,
    )
    
    if relationship:
        return {
            "success": True,
            "message": "Now copying strategy",
            "relationship_id": relationship.id,
        }
    raise HTTPException(status_code=400, detail="Could not start copying")

