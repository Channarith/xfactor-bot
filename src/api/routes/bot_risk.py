"""
Bot Risk Management API Routes

Endpoints for bot risk assessment and monitoring:
- Risk score calculation
- Risk-adjusted metrics
- Risk alerts
- Portfolio risk overview
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from loguru import logger


router = APIRouter(prefix="/api/bots/risk", tags=["Bot Risk Management"])


# =============================================================================
# Risk Score Endpoints
# =============================================================================

@router.get("/{bot_id}/score")
async def get_bot_risk_score(bot_id: str):
    """Get comprehensive risk score for a bot."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    
    # Check for cached score
    score = manager.get_risk_score(bot_id)
    if score:
        return score.to_dict()
    
    # Need to calculate - get bot data
    # In production, this would fetch from database
    # For demo, return sample calculation
    sample_bot_data = {
        "name": f"Bot {bot_id}",
        "account_value": 100000,
        "current_drawdown_pct": 8.5,
        "max_drawdown_pct": 15.2,
        "daily_volatility_pct": 1.2,
        "win_rate_pct": 58,
        "total_trades": 145,
        "leverage": 1.0,
        "current_exposure_pct": 45,
        "total_return_pct": 12.5,
        "sharpe_ratio": 1.2,
        "profit_factor": 1.8,
        "avg_win_pct": 2.1,
        "avg_loss_pct": 1.4,
        "positions": [
            {"symbol": "NVDA", "value": 15000},
            {"symbol": "AAPL", "value": 12000},
            {"symbol": "MSFT", "value": 10000},
            {"symbol": "GOOGL", "value": 8000},
        ],
    }
    
    score = manager.calculate_risk_score(bot_id, sample_bot_data)
    return score.to_dict()


class BotDataInput(BaseModel):
    """Input data for risk calculation."""
    name: str = "Trading Bot"
    account_value: float = 100000
    current_drawdown_pct: float = 0
    max_drawdown_pct: float = 0
    daily_volatility_pct: float = 1.0
    win_rate_pct: float = 50
    total_trades: int = 0
    leverage: float = 1.0
    current_exposure_pct: float = 0
    total_return_pct: float = 0
    sharpe_ratio: float = 0
    profit_factor: float = 1.0
    avg_win_pct: float = 0
    avg_loss_pct: float = 0
    largest_win_pct: float = 0
    largest_loss_pct: float = 0
    positions: List[Dict[str, Any]] = Field(default_factory=list)
    position_correlations: Dict[str, float] = Field(default_factory=dict)


@router.post("/{bot_id}/calculate")
async def calculate_bot_risk_score(bot_id: str, data: BotDataInput):
    """Calculate risk score with provided bot data."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    
    bot_data = data.model_dump()
    score = manager.calculate_risk_score(bot_id, bot_data)
    
    return score.to_dict()


@router.get("/all")
async def get_all_risk_scores():
    """Get risk scores for all monitored bots."""
    from src.bot.risk_manager import get_bot_risk_manager
    from src.bot.bot_manager import get_bot_manager
    
    risk_manager = get_bot_risk_manager()
    bot_manager = get_bot_manager()
    
    # Auto-score all active bots if not already scored
    all_bots = bot_manager.get_all_bots()
    for bot in all_bots:
        status = bot.get_status()
        bot_data = {
            "name": bot.config.name,
            "account_value": 100000,  # Default for now
            "current_drawdown_pct": 0,
            "max_drawdown_pct": status.get("stats", {}).get("max_drawdown_pct", 0),
            "daily_volatility_pct": 1.0,
            "win_rate_pct": status.get("stats", {}).get("win_rate_pct", 50),
            "total_trades": status.get("stats", {}).get("trades", 0),
            "leverage": 1.0,
            "current_exposure_pct": 0,
            "total_return_pct": status.get("stats", {}).get("total_pnl_pct", 0),
            "sharpe_ratio": 0,
            "profit_factor": status.get("stats", {}).get("profit_factor", 1.0),
            "avg_win_pct": 0,
            "avg_loss_pct": 0,
            "positions": [],
        }
        risk_manager.calculate_risk_score(bot.id, bot_data)
    
    scores = risk_manager.get_all_risk_scores()
    
    # Sort by risk score (highest risk first)
    scores.sort(key=lambda x: x["overall_risk_score"], reverse=True)
    
    return {
        "bot_count": len(scores),
        "scores": scores,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/high-risk")
async def get_high_risk_bots(threshold: float = Query(60, ge=0, le=100)):
    """Get bots with risk score above threshold."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    scores = manager.get_all_risk_scores()
    
    high_risk = [s for s in scores if s["overall_risk_score"] >= threshold]
    high_risk.sort(key=lambda x: x["overall_risk_score"], reverse=True)
    
    return {
        "threshold": threshold,
        "count": len(high_risk),
        "high_risk_bots": high_risk,
    }


# =============================================================================
# Risk Metrics Endpoints
# =============================================================================

@router.get("/{bot_id}/metrics")
async def get_bot_risk_metrics(bot_id: str):
    """Get detailed risk-adjusted metrics for a bot."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    score = manager.get_risk_score(bot_id)
    
    if not score:
        raise HTTPException(status_code=404, detail=f"No risk data for bot {bot_id}")
    
    return {
        "bot_id": bot_id,
        "metrics": score.metrics.to_dict(),
        "risk_level": score.risk_level.value,
    }


@router.get("/{bot_id}/components")
async def get_risk_components(bot_id: str):
    """Get breakdown of risk score components."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    score = manager.get_risk_score(bot_id)
    
    if not score:
        raise HTTPException(status_code=404, detail=f"No risk data for bot {bot_id}")
    
    return {
        "bot_id": bot_id,
        "overall_risk_score": round(score.overall_risk_score, 1),
        "risk_level": score.risk_level.value,
        "components": score.to_dict()["component_scores"],
        "weights": {
            "position_size": 0.15,
            "concentration": 0.15,
            "drawdown": 0.20,
            "volatility": 0.10,
            "leverage": 0.10,
            "correlation": 0.10,
            "win_rate": 0.10,
            "exposure": 0.10,
        },
    }


# =============================================================================
# Risk Alerts Endpoints
# =============================================================================

@router.get("/alerts")
async def get_risk_alerts(
    min_level: str = Query("elevated", description="Minimum alert level"),
):
    """Get all active risk alerts."""
    from src.bot.risk_manager import get_bot_risk_manager, RiskLevel
    
    manager = get_bot_risk_manager()
    
    try:
        level = RiskLevel(min_level.lower())
    except ValueError:
        level = RiskLevel.ELEVATED
    
    alerts = manager.get_active_alerts(level)
    
    # Group by level
    by_level = {}
    for alert in alerts:
        lvl = alert["level"]
        if lvl not in by_level:
            by_level[lvl] = []
        by_level[lvl].append(alert)
    
    return {
        "total_alerts": len(alerts),
        "by_level": by_level,
        "alerts": alerts,
    }


@router.get("/{bot_id}/alerts")
async def get_bot_alerts(bot_id: str):
    """Get risk alerts for a specific bot."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    score = manager.get_risk_score(bot_id)
    
    if not score:
        return {"bot_id": bot_id, "alerts": [], "message": "No risk data available"}
    
    return {
        "bot_id": bot_id,
        "alert_count": len(score.alerts),
        "critical_count": len([a for a in score.alerts if a.level.value == "critical"]),
        "alerts": [a.to_dict() for a in score.alerts],
    }


@router.delete("/alerts/{bot_id}")
async def clear_bot_alerts(bot_id: str):
    """Clear alerts for a specific bot."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    cleared = manager.clear_alerts(bot_id)
    
    return {"success": True, "cleared_count": cleared}


@router.delete("/alerts")
async def clear_all_alerts():
    """Clear all risk alerts."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    cleared = manager.clear_alerts()
    
    return {"success": True, "cleared_count": cleared}


# =============================================================================
# Portfolio Risk Endpoints
# =============================================================================

@router.get("/portfolio")
async def get_portfolio_risk():
    """Get aggregate risk across all bots."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    
    # Get all scored bots
    scores = manager.get_all_risk_scores()
    
    if not scores:
        return {
            "overall_risk_score": 0,
            "risk_level": "low",
            "bot_count": 0,
            "message": "No bots being monitored",
        }
    
    # Calculate portfolio metrics
    bots = [{"id": s["bot_id"], "current_exposure_pct": s["metrics"]["exposure"]["current_pct"]} for s in scores]
    portfolio_risk = manager.get_portfolio_risk(bots)
    
    return {
        **portfolio_risk,
        "bots_summary": [
            {
                "bot_id": s["bot_id"],
                "bot_name": s["bot_name"],
                "risk_score": s["overall_risk_score"],
                "risk_level": s["risk_level"],
                "alert_count": s["alert_count"],
            }
            for s in scores
        ],
    }


# =============================================================================
# Risk Thresholds & Configuration
# =============================================================================

@router.get("/thresholds")
async def get_risk_thresholds():
    """Get current risk threshold configuration."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    
    return {
        "thresholds": manager.THRESHOLDS,
        "weights": manager.WEIGHTS,
        "risk_levels": {
            "critical": "80-100: Immediate action required",
            "high": "60-80: Reduce exposure",
            "elevated": "40-60: Monitor closely",
            "moderate": "20-40: Acceptable",
            "low": "0-20: Well controlled",
        },
    }


class ThresholdUpdate(BaseModel):
    """Update risk thresholds."""
    max_position_size_pct: Optional[float] = None
    max_concentration_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    critical_drawdown_pct: Optional[float] = None
    high_volatility_pct: Optional[float] = None
    max_leverage: Optional[float] = None
    min_win_rate_pct: Optional[float] = None
    max_exposure_pct: Optional[float] = None
    min_sharpe_ratio: Optional[float] = None
    max_correlation: Optional[float] = None


@router.put("/thresholds")
async def update_risk_thresholds(update: ThresholdUpdate):
    """Update risk threshold configuration."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    
    updates = update.model_dump(exclude_none=True)
    
    for key, value in updates.items():
        if key in manager.THRESHOLDS:
            manager.THRESHOLDS[key] = value
    
    return {
        "success": True,
        "updated": list(updates.keys()),
        "thresholds": manager.THRESHOLDS,
    }


# =============================================================================
# Risk Recommendations
# =============================================================================

@router.get("/{bot_id}/recommendations")
async def get_bot_recommendations(bot_id: str):
    """Get risk management recommendations for a bot."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    score = manager.get_risk_score(bot_id)
    
    if not score:
        return {
            "bot_id": bot_id,
            "recommendations": ["Calculate risk score first to get recommendations"],
        }
    
    return {
        "bot_id": bot_id,
        "risk_level": score.risk_level.value,
        "recommendations": score.recommendations,
        "priority_actions": [
            r for r in score.recommendations
            if r.startswith("⚠️") or r.startswith("Reduce") or r.startswith("Consider")
        ],
    }


# =============================================================================
# Risk Summary Widget Data
# =============================================================================

@router.get("/{bot_id}/widget")
async def get_risk_widget_data(bot_id: str):
    """Get compact risk data for UI widget display."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    score = manager.get_risk_score(bot_id)
    
    if not score:
        return {
            "bot_id": bot_id,
            "risk_score": None,
            "risk_level": "unknown",
            "color": "#6b7280",
            "alerts": 0,
        }
    
    return {
        "bot_id": bot_id,
        "risk_score": round(score.overall_risk_score, 0),
        "risk_level": score.risk_level.value,
        "color": score._get_level_color(),
        "alerts": len(score.alerts),
        "critical_alerts": len([a for a in score.alerts if a.level.value == "critical"]),
        "sharpe_ratio": round(score.metrics.sharpe_ratio, 2),
        "max_drawdown_pct": round(score.metrics.max_drawdown_pct, 1),
        "win_rate_pct": round(score.metrics.win_rate_pct, 1),
    }


@router.get("/dashboard")
async def get_risk_dashboard():
    """Get risk management dashboard data."""
    from src.bot.risk_manager import get_bot_risk_manager
    
    manager = get_bot_risk_manager()
    scores = manager.get_all_risk_scores()
    alerts = manager.get_active_alerts()
    
    # Risk distribution
    risk_distribution = {
        "critical": len([s for s in scores if s["risk_level"] == "critical"]),
        "high": len([s for s in scores if s["risk_level"] == "high"]),
        "elevated": len([s for s in scores if s["risk_level"] == "elevated"]),
        "moderate": len([s for s in scores if s["risk_level"] == "moderate"]),
        "low": len([s for s in scores if s["risk_level"] == "low"]),
    }
    
    # Top risks
    top_risks = sorted(scores, key=lambda x: x["overall_risk_score"], reverse=True)[:5]
    
    # Recent alerts
    recent_alerts = sorted(alerts, key=lambda x: x["triggered_at"], reverse=True)[:10]
    
    return {
        "summary": {
            "total_bots": len(scores),
            "avg_risk_score": round(sum(s["overall_risk_score"] for s in scores) / max(len(scores), 1), 1),
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a["level"] == "critical"]),
        },
        "risk_distribution": risk_distribution,
        "top_risks": [
            {
                "bot_id": s["bot_id"],
                "bot_name": s["bot_name"],
                "risk_score": s["overall_risk_score"],
                "risk_level": s["risk_level"],
            }
            for s in top_risks
        ],
        "recent_alerts": recent_alerts,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

