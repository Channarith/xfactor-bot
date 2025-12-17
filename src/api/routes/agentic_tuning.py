"""
API routes for Agentic Tuning & Removing Wasted Agent Cycles (ATRWAC).

Provides endpoints to configure, monitor, and control the agentic tuning
process that optimizes bot portfolios by pruning underperformers.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

from loguru import logger

from src.bot.agentic_tuner import (
    get_agentic_tuner,
    initialize_agentic_tuner,
    AgenticTuningConfig,
    OptimizationTarget,
    ScoringWeights,
    PruningConfig,
)
from src.bot.bot_manager import bot_manager


router = APIRouter(prefix="/api/agentic-tuning", tags=["Agentic Tuning"])


# Pydantic models for API
class OptimizationTargetEnum(str, Enum):
    max_profit = "max_profit"
    max_growth_pct = "max_growth_pct"
    fastest_speed = "fastest_speed"
    max_win_rate = "max_win_rate"
    min_drawdown = "min_drawdown"
    best_sharpe = "best_sharpe"
    sentiment_aligned = "sentiment_aligned"
    custom = "custom"


class ScoringWeightsModel(BaseModel):
    profit_weight: float = 0.40
    win_rate_weight: float = 0.30
    efficiency_weight: float = 0.20
    resource_penalty: float = 0.10
    speed_weight: float = 0.0
    sentiment_weight: float = 0.0
    drawdown_weight: float = 0.0


class PruningConfigModel(BaseModel):
    first_pruning_days: int = 30
    deep_pruning_days: int = 60
    optimal_state_days: int = 90
    first_pruning_keep_pct: float = 0.50
    deep_pruning_keep_pct: float = 0.25
    optimal_keep_count: int = 3


class AgenticTuningConfigModel(BaseModel):
    enabled: bool = False
    target: OptimizationTargetEnum = OptimizationTargetEnum.max_profit
    pruning: Optional[PruningConfigModel] = None
    weights: Optional[ScoringWeightsModel] = None
    evaluation_interval_hours: int = 24
    auto_prune: bool = True


class StartTuningRequest(BaseModel):
    target: OptimizationTargetEnum = OptimizationTargetEnum.max_profit
    auto_prune: bool = True
    custom_weights: Optional[ScoringWeightsModel] = None


# Initialize tuner with bot manager callbacks
def _ensure_tuner_initialized():
    """Ensure the agentic tuner is initialized with bot manager."""
    tuner = get_agentic_tuner()
    
    if tuner._get_all_bots is None:
        # Initialize with bot manager callbacks
        async def stop_bot(bot_id: str):
            return await bot_manager.stop_bot(bot_id)
        
        initialize_agentic_tuner(
            get_all_bots=bot_manager.get_all_bots,
            stop_bot=stop_bot,
            delete_bot=bot_manager.delete_bot,
        )
    
    return get_agentic_tuner()


@router.get("/status")
async def get_tuning_status():
    """
    Get current agentic tuning status.
    
    Returns phase, bot counts, champions, and resource usage.
    """
    tuner = _ensure_tuner_initialized()
    return tuner.get_status()


@router.get("/config")
async def get_tuning_config():
    """Get current agentic tuning configuration."""
    tuner = _ensure_tuner_initialized()
    return tuner.config.to_dict()


@router.put("/config")
async def update_tuning_config(config: AgenticTuningConfigModel):
    """
    Update agentic tuning configuration.
    
    Changes take effect on next evaluation cycle.
    """
    tuner = _ensure_tuner_initialized()
    
    config_dict = {
        "enabled": config.enabled,
        "target": config.target.value,
        "evaluation_interval_hours": config.evaluation_interval_hours,
        "auto_prune": config.auto_prune,
    }
    
    if config.pruning:
        config_dict["pruning"] = config.pruning.dict()
    
    if config.weights:
        config_dict["weights"] = config.weights.dict()
    
    tuner.update_config(config_dict)
    
    return {"status": "ok", "config": tuner.config.to_dict()}


@router.post("/start")
async def start_tuning(request: StartTuningRequest):
    """
    Start the agentic tuning process.
    
    This will begin evaluating all bots and progressively pruning
    underperformers according to the configured schedule.
    """
    tuner = _ensure_tuner_initialized()
    
    if tuner._running:
        return {"status": "already_running", "message": "Agentic tuning is already active"}
    
    # Configure based on target
    config = AgenticTuningConfig.for_target(
        OptimizationTarget(request.target.value)
    )
    config.auto_prune = request.auto_prune
    
    # Apply custom weights if provided
    if request.custom_weights:
        config.weights = ScoringWeights(
            profit_weight=request.custom_weights.profit_weight,
            win_rate_weight=request.custom_weights.win_rate_weight,
            efficiency_weight=request.custom_weights.efficiency_weight,
            resource_penalty=request.custom_weights.resource_penalty,
            speed_weight=request.custom_weights.speed_weight,
            sentiment_weight=request.custom_weights.sentiment_weight,
            drawdown_weight=request.custom_weights.drawdown_weight,
        )
    
    tuner.config = config
    tuner.start()
    
    logger.info(f"Agentic tuning started with target: {request.target.value}")
    
    return {
        "status": "started",
        "target": request.target.value,
        "active_bots": tuner.active_bot_count,
        "message": f"Agentic tuning started. {tuner.active_bot_count} bots in initial blast phase.",
    }


@router.post("/stop")
async def stop_tuning():
    """
    Stop the agentic tuning process.
    
    Bots will remain in their current state (not unpaused).
    """
    tuner = _ensure_tuner_initialized()
    
    if not tuner._running:
        return {"status": "not_running", "message": "Agentic tuning is not active"}
    
    tuner.stop()
    
    return {
        "status": "stopped",
        "active_bots": tuner.active_bot_count,
        "pruned_bots": len(tuner._pruning_history),
    }


@router.get("/rankings")
async def get_bot_rankings():
    """
    Get current bot rankings by score.
    
    Returns all active bots sorted by their calculated score.
    """
    tuner = _ensure_tuner_initialized()
    return {
        "phase": tuner._current_phase.value,
        "target": tuner.config.target.value,
        "rankings": tuner.get_rankings(),
    }


@router.get("/champions")
async def get_champions():
    """
    Get info about current champion bots.
    
    Champions are the top-performing bots that will be kept
    when reaching the optimal state.
    """
    tuner = _ensure_tuner_initialized()
    return {
        "count": tuner.champion_count,
        "champions": tuner.get_champion_info(),
    }


@router.get("/pruning-history")
async def get_pruning_history():
    """
    Get history of pruned bots.
    
    Shows when each bot was pruned and why.
    """
    tuner = _ensure_tuner_initialized()
    return {
        "total_pruned": len(tuner._pruning_history),
        "history": tuner.get_pruning_history(),
    }


@router.get("/targets")
async def get_available_targets():
    """
    Get list of available optimization targets.
    
    Each target optimizes for different metrics.
    """
    return {
        "targets": [
            {
                "id": "max_profit",
                "name": "Maximum Profit",
                "description": "Maximize total profit across all trades",
                "primary_weight": "profit_weight (40%)",
            },
            {
                "id": "max_growth_pct",
                "name": "Maximum % Growth",
                "description": "Maximize percentage return on investment",
                "primary_weight": "profit_weight (60%)",
            },
            {
                "id": "fastest_speed",
                "name": "Fastest Speed",
                "description": "Optimize for quick, profitable trades",
                "primary_weight": "speed_weight (30%)",
            },
            {
                "id": "max_win_rate",
                "name": "Highest Win Rate",
                "description": "Maximize the percentage of winning trades",
                "primary_weight": "win_rate_weight (50%)",
            },
            {
                "id": "min_drawdown",
                "name": "Minimum Drawdown",
                "description": "Minimize maximum drawdown for stability",
                "primary_weight": "drawdown_weight (30%)",
            },
            {
                "id": "best_sharpe",
                "name": "Best Risk-Adjusted Returns",
                "description": "Optimize Sharpe ratio for risk/reward balance",
                "primary_weight": "efficiency_weight (30%)",
            },
            {
                "id": "sentiment_aligned",
                "name": "Sentiment Prediction",
                "description": "Best accuracy in sentiment-based predictions",
                "primary_weight": "sentiment_weight (35%)",
            },
            {
                "id": "custom",
                "name": "Custom Weights",
                "description": "Define your own scoring weights",
                "primary_weight": "user-defined",
            },
        ]
    }


@router.post("/force-evaluation")
async def force_evaluation():
    """
    Force an immediate evaluation and ranking of all bots.
    
    Useful for testing or when you want immediate results.
    """
    tuner = _ensure_tuner_initialized()
    
    await tuner._calculate_all_scores()
    tuner._rank_bots()
    
    return {
        "status": "ok",
        "active_bots": tuner.active_bot_count,
        "champions": tuner._champions,
        "rankings": tuner.get_rankings()[:5],  # Top 5
    }


@router.post("/prune/{bot_id}")
async def manually_prune_bot(bot_id: str, reason: str = "Manually pruned"):
    """
    Manually prune a specific bot.
    
    This stops the bot and marks it as pruned.
    """
    tuner = _ensure_tuner_initialized()
    
    if bot_id not in tuner._bot_scores:
        raise HTTPException(status_code=404, detail=f"Bot {bot_id} not found")
    
    score = tuner._bot_scores[bot_id]
    if not score.is_active:
        raise HTTPException(status_code=400, detail=f"Bot {bot_id} is already pruned")
    
    await tuner._prune_bot(bot_id, reason)
    
    return {
        "status": "pruned",
        "bot_id": bot_id,
        "reason": reason,
        "active_bots": tuner.active_bot_count,
    }


@router.get("/resource-usage")
async def get_resource_usage():
    """
    Get GPU and lane resource usage.
    
    Shows which GPUs and lanes are in use by active bots.
    """
    tuner = _ensure_tuner_initialized()
    
    return {
        "gpu_allocation": {
            str(gpu_id): {
                "bots": bots,
                "count": len(bots),
            }
            for gpu_id, bots in tuner._gpu_allocation.items()
        },
        "lane_allocation": tuner._lane_allocation,
        "active_gpus": sum(1 for bots in tuner._gpu_allocation.values() if bots),
        "total_gpus": len(tuner._gpu_allocation),
        "active_lanes": len(tuner._lane_allocation),
        "compute_savings_pct": 100 - (tuner.active_bot_count / len(tuner._bot_scores) * 100) if tuner._bot_scores else 0,
    }

