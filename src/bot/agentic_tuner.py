"""
Agentic Tuning & Removing Wasted Agent Cycles (ATRWAC)

This module implements the Agentic Tuning algorithm that:
1. Starts with all bots (agents) running
2. Evaluates performance over configurable time periods
3. Progressively prunes underperforming bots
4. Keeps only the top N performers to maximize efficiency

Supports both XFactor-botMax and XFactor-botMin editions.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, Any
import statistics
import json

from loguru import logger


class OptimizationTarget(Enum):
    """Configurable optimization targets for the Agentic Tuner."""
    MAX_PROFIT = "max_profit"              # Maximize total profit (default)
    MAX_GROWTH_PCT = "max_growth_pct"      # Maximize percentage growth
    FASTEST_SPEED = "fastest_speed"        # Fastest profitable trades
    MAX_WIN_RATE = "max_win_rate"          # Highest win rate
    MIN_DRAWDOWN = "min_drawdown"          # Minimize drawdown
    BEST_SHARPE = "best_sharpe"            # Best risk-adjusted returns
    SENTIMENT_ALIGNED = "sentiment_aligned" # Best sentiment prediction accuracy
    CUSTOM = "custom"                       # Custom weighted scoring


class TuningPhase(Enum):
    """Phases of the agentic tuning process."""
    INITIAL_BLAST = "initial_blast"        # Day 0 - All agents active
    FIRST_PRUNING = "first_pruning"        # Day 30 - Remove bottom 50%
    DEEP_PRUNING = "deep_pruning"          # Day 60 - Keep top 25%
    OPTIMAL_STATE = "optimal_state"        # Day 90+ - Top 3 champions only
    MAINTENANCE = "maintenance"            # Ongoing monitoring


@dataclass
class PruningConfig:
    """Configuration for pruning thresholds."""
    # Time-based phases (in days)
    first_pruning_days: int = 30
    deep_pruning_days: int = 60
    optimal_state_days: int = 90
    
    # Pruning percentages
    first_pruning_keep_pct: float = 0.50   # Keep top 50%
    deep_pruning_keep_pct: float = 0.25    # Keep top 25%
    optimal_keep_count: int = 3             # Keep top 3 bots
    
    # Minimum requirements
    min_trades_for_evaluation: int = 10
    min_days_for_evaluation: int = 7
    
    # Score thresholds (auto-adjusted based on population)
    auto_adjust_thresholds: bool = True


@dataclass
class ScoringWeights:
    """Configurable weights for scoring bots."""
    profit_weight: float = 0.40            # α - Primary objective
    win_rate_weight: float = 0.30          # β - Consistency measure
    efficiency_weight: float = 0.20        # γ - Output per cycle
    resource_penalty: float = 0.10         # δ - Punish resource hogs
    
    # Optional weights for specific targets
    speed_weight: float = 0.0              # For FASTEST_SPEED
    sentiment_weight: float = 0.0          # For SENTIMENT_ALIGNED
    drawdown_weight: float = 0.0           # For MIN_DRAWDOWN
    
    def to_dict(self) -> dict:
        return {
            "profit_weight": self.profit_weight,
            "win_rate_weight": self.win_rate_weight,
            "efficiency_weight": self.efficiency_weight,
            "resource_penalty": self.resource_penalty,
            "speed_weight": self.speed_weight,
            "sentiment_weight": self.sentiment_weight,
            "drawdown_weight": self.drawdown_weight,
        }


@dataclass
class BotScore:
    """Score and ranking for a single bot."""
    bot_id: str
    bot_name: str
    
    # Raw metrics
    total_profit: float = 0.0
    profit_pct: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    avg_trade_duration_minutes: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sentiment_accuracy: float = 0.0
    
    # Resource usage
    gpu_id: int = 0
    lane_id: int = 0
    compute_usage_pct: float = 0.0
    
    # Calculated score
    final_score: float = 0.0
    rank: int = 0
    
    # Status
    is_active: bool = True
    is_champion: bool = False
    pruned_at: Optional[datetime] = None
    pruned_reason: str = ""
    
    # History
    score_history: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "bot_id": self.bot_id,
            "bot_name": self.bot_name,
            "total_profit": self.total_profit,
            "profit_pct": self.profit_pct,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "avg_trade_duration_minutes": self.avg_trade_duration_minutes,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "sentiment_accuracy": self.sentiment_accuracy,
            "gpu_id": self.gpu_id,
            "lane_id": self.lane_id,
            "compute_usage_pct": self.compute_usage_pct,
            "final_score": self.final_score,
            "rank": self.rank,
            "is_active": self.is_active,
            "is_champion": self.is_champion,
            "pruned_at": self.pruned_at.isoformat() if self.pruned_at else None,
            "pruned_reason": self.pruned_reason,
        }


@dataclass 
class AgenticTuningConfig:
    """Main configuration for Agentic Tuning."""
    enabled: bool = False
    target: OptimizationTarget = OptimizationTarget.MAX_PROFIT
    pruning: PruningConfig = field(default_factory=PruningConfig)
    weights: ScoringWeights = field(default_factory=ScoringWeights)
    
    # Evaluation settings
    evaluation_interval_hours: int = 24    # How often to evaluate
    auto_prune: bool = True                # Automatically prune or just recommend
    
    # Notifications
    notify_on_prune: bool = True
    notify_on_champion: bool = True
    
    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "target": self.target.value,
            "pruning": {
                "first_pruning_days": self.pruning.first_pruning_days,
                "deep_pruning_days": self.pruning.deep_pruning_days,
                "optimal_state_days": self.pruning.optimal_state_days,
                "first_pruning_keep_pct": self.pruning.first_pruning_keep_pct,
                "deep_pruning_keep_pct": self.pruning.deep_pruning_keep_pct,
                "optimal_keep_count": self.pruning.optimal_keep_count,
            },
            "weights": self.weights.to_dict(),
            "evaluation_interval_hours": self.evaluation_interval_hours,
            "auto_prune": self.auto_prune,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgenticTuningConfig":
        """Create config from dictionary."""
        config = cls()
        
        if "enabled" in data:
            config.enabled = data["enabled"]
        
        if "target" in data:
            config.target = OptimizationTarget(data["target"])
        
        if "pruning" in data:
            p = data["pruning"]
            config.pruning = PruningConfig(
                first_pruning_days=p.get("first_pruning_days", 30),
                deep_pruning_days=p.get("deep_pruning_days", 60),
                optimal_state_days=p.get("optimal_state_days", 90),
                first_pruning_keep_pct=p.get("first_pruning_keep_pct", 0.50),
                deep_pruning_keep_pct=p.get("deep_pruning_keep_pct", 0.25),
                optimal_keep_count=p.get("optimal_keep_count", 3),
            )
        
        if "weights" in data:
            w = data["weights"]
            config.weights = ScoringWeights(
                profit_weight=w.get("profit_weight", 0.40),
                win_rate_weight=w.get("win_rate_weight", 0.30),
                efficiency_weight=w.get("efficiency_weight", 0.20),
                resource_penalty=w.get("resource_penalty", 0.10),
            )
        
        if "evaluation_interval_hours" in data:
            config.evaluation_interval_hours = data["evaluation_interval_hours"]
        
        if "auto_prune" in data:
            config.auto_prune = data["auto_prune"]
        
        return config
    
    @classmethod
    def for_target(cls, target: OptimizationTarget) -> "AgenticTuningConfig":
        """Create optimized config for a specific target."""
        config = cls(enabled=True, target=target)
        
        if target == OptimizationTarget.MAX_PROFIT:
            config.weights = ScoringWeights(
                profit_weight=0.50,
                win_rate_weight=0.25,
                efficiency_weight=0.15,
                resource_penalty=0.10,
            )
        
        elif target == OptimizationTarget.MAX_GROWTH_PCT:
            config.weights = ScoringWeights(
                profit_weight=0.60,  # Higher weight on profit
                win_rate_weight=0.20,
                efficiency_weight=0.10,
                resource_penalty=0.10,
            )
        
        elif target == OptimizationTarget.FASTEST_SPEED:
            config.weights = ScoringWeights(
                profit_weight=0.25,
                win_rate_weight=0.20,
                efficiency_weight=0.15,
                resource_penalty=0.10,
                speed_weight=0.30,  # High weight on speed
            )
        
        elif target == OptimizationTarget.MAX_WIN_RATE:
            config.weights = ScoringWeights(
                profit_weight=0.20,
                win_rate_weight=0.50,  # High weight on win rate
                efficiency_weight=0.20,
                resource_penalty=0.10,
            )
        
        elif target == OptimizationTarget.MIN_DRAWDOWN:
            config.weights = ScoringWeights(
                profit_weight=0.30,
                win_rate_weight=0.20,
                efficiency_weight=0.10,
                resource_penalty=0.10,
                drawdown_weight=0.30,  # High weight on low drawdown
            )
        
        elif target == OptimizationTarget.BEST_SHARPE:
            config.weights = ScoringWeights(
                profit_weight=0.30,
                win_rate_weight=0.20,
                efficiency_weight=0.30,  # Sharpe is about efficiency
                resource_penalty=0.10,
                drawdown_weight=0.10,
            )
        
        elif target == OptimizationTarget.SENTIMENT_ALIGNED:
            config.weights = ScoringWeights(
                profit_weight=0.25,
                win_rate_weight=0.20,
                efficiency_weight=0.10,
                resource_penalty=0.10,
                sentiment_weight=0.35,  # High weight on sentiment
            )
        
        return config


class AgenticTuner:
    """
    Agentic Tuning & Removing Wasted Agent Cycles (ATRWAC)
    
    Manages the lifecycle of multiple trading bots, automatically
    pruning underperformers to optimize resource usage and maximize
    the configured target (profit, speed, growth, etc.).
    """
    
    def __init__(
        self,
        config: Optional[AgenticTuningConfig] = None,
        get_all_bots: Optional[Callable] = None,
        stop_bot: Optional[Callable] = None,
        delete_bot: Optional[Callable] = None,
    ):
        """
        Initialize the Agentic Tuner.
        
        Args:
            config: Tuning configuration
            get_all_bots: Callback to get all bot instances
            stop_bot: Callback to stop a bot
            delete_bot: Callback to delete a bot
        """
        self.config = config or AgenticTuningConfig()
        self._get_all_bots = get_all_bots
        self._stop_bot = stop_bot
        self._delete_bot = delete_bot
        
        # State
        self._started_at: Optional[datetime] = None
        self._current_phase = TuningPhase.INITIAL_BLAST
        self._bot_scores: dict[str, BotScore] = {}
        self._pruning_history: list[dict] = []
        self._champions: list[str] = []
        
        # GPU/Lane tracking (for resource optimization)
        self._gpu_allocation: dict[int, list[str]] = {}  # GPU ID -> bot IDs
        self._lane_allocation: dict[int, str] = {}       # Lane ID -> bot ID
        
        # Background task
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info(f"AgenticTuner initialized with target: {self.config.target.value}")
    
    @property
    def days_running(self) -> int:
        """Get number of days since tuning started."""
        if not self._started_at:
            return 0
        return (datetime.now() - self._started_at).days
    
    @property
    def active_bot_count(self) -> int:
        """Get count of active (non-pruned) bots."""
        return sum(1 for s in self._bot_scores.values() if s.is_active)
    
    @property
    def champion_count(self) -> int:
        """Get count of champion bots."""
        return len(self._champions)
    
    def start(self) -> None:
        """Start the agentic tuning process."""
        if self._running:
            logger.warning("AgenticTuner already running")
            return
        
        self._started_at = datetime.now()
        self._running = True
        self._current_phase = TuningPhase.INITIAL_BLAST
        
        # Initialize bot scores
        self._initialize_scores()
        
        # Start background evaluation task
        self._task = asyncio.create_task(self._evaluation_loop())
        
        logger.info(f"AgenticTuner started - {self.active_bot_count} bots in initial blast phase")
    
    def stop(self) -> None:
        """Stop the agentic tuning process."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        
        logger.info("AgenticTuner stopped")
    
    def _initialize_scores(self) -> None:
        """Initialize scores for all bots."""
        if not self._get_all_bots:
            return
        
        bots = self._get_all_bots()
        for i, bot in enumerate(bots):
            bot_id = getattr(bot, 'id', str(i))
            bot_name = getattr(bot, 'name', f'Bot_{i}')
            
            # Assign GPU and lane
            gpu_id = i // 5  # 5 bots per GPU
            lane_id = i
            
            self._bot_scores[bot_id] = BotScore(
                bot_id=bot_id,
                bot_name=bot_name,
                gpu_id=gpu_id,
                lane_id=lane_id,
                is_active=True,
            )
            
            # Track allocations
            if gpu_id not in self._gpu_allocation:
                self._gpu_allocation[gpu_id] = []
            self._gpu_allocation[gpu_id].append(bot_id)
            self._lane_allocation[lane_id] = bot_id
        
        logger.info(f"Initialized {len(self._bot_scores)} bot scores")
    
    async def _evaluation_loop(self) -> None:
        """Background loop for periodic evaluation."""
        while self._running:
            try:
                await asyncio.sleep(self.config.evaluation_interval_hours * 3600)
                
                if not self._running:
                    break
                
                # Update phase based on days running
                self._update_phase()
                
                # Calculate scores
                await self._calculate_all_scores()
                
                # Rank bots
                self._rank_bots()
                
                # Prune if auto-prune is enabled
                if self.config.auto_prune:
                    await self._execute_pruning()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in evaluation loop: {e}")
                await asyncio.sleep(60)
    
    def _update_phase(self) -> None:
        """Update the current tuning phase based on days running."""
        days = self.days_running
        
        if days < self.config.pruning.first_pruning_days:
            new_phase = TuningPhase.INITIAL_BLAST
        elif days < self.config.pruning.deep_pruning_days:
            new_phase = TuningPhase.FIRST_PRUNING
        elif days < self.config.pruning.optimal_state_days:
            new_phase = TuningPhase.DEEP_PRUNING
        else:
            new_phase = TuningPhase.OPTIMAL_STATE
        
        if new_phase != self._current_phase:
            logger.info(f"Phase transition: {self._current_phase.value} -> {new_phase.value}")
            self._current_phase = new_phase
    
    async def _calculate_all_scores(self) -> None:
        """Calculate scores for all active bots."""
        if not self._get_all_bots:
            return
        
        bots = self._get_all_bots()
        
        for bot in bots:
            bot_id = getattr(bot, 'id', None)
            if not bot_id or bot_id not in self._bot_scores:
                continue
            
            score = self._bot_scores[bot_id]
            if not score.is_active:
                continue
            
            # Get metrics from bot
            metrics = await self._get_bot_metrics(bot)
            
            # Update score with metrics
            score.total_profit = metrics.get('total_profit', 0)
            score.profit_pct = metrics.get('profit_pct', 0)
            score.win_rate = metrics.get('win_rate', 0)
            score.total_trades = metrics.get('total_trades', 0)
            score.avg_trade_duration_minutes = metrics.get('avg_trade_duration', 0)
            score.max_drawdown = metrics.get('max_drawdown', 0)
            score.sharpe_ratio = metrics.get('sharpe_ratio', 0)
            score.sentiment_accuracy = metrics.get('sentiment_accuracy', 0)
            
            # Calculate final score
            score.final_score = self._calculate_score(score)
            score.score_history.append({
                'timestamp': datetime.now().isoformat(),
                'score': score.final_score,
            })
    
    async def _get_bot_metrics(self, bot: Any) -> dict:
        """Get performance metrics from a bot."""
        try:
            # Try to get stats from bot
            stats = getattr(bot, 'stats', None)
            if stats:
                return {
                    'total_profit': getattr(stats, 'total_pnl', 0),
                    'profit_pct': getattr(stats, 'return_pct', 0),
                    'win_rate': getattr(stats, 'win_rate', 0),
                    'total_trades': getattr(stats, 'total_trades', 0),
                    'avg_trade_duration': getattr(stats, 'avg_trade_duration_minutes', 0),
                    'max_drawdown': getattr(stats, 'max_drawdown', 0),
                    'sharpe_ratio': getattr(stats, 'sharpe_ratio', 0),
                    'sentiment_accuracy': getattr(stats, 'sentiment_accuracy', 0),
                }
            
            # Fall back to basic info
            return {
                'total_profit': getattr(bot, 'total_pnl', 0),
                'profit_pct': 0,
                'win_rate': 0,
                'total_trades': 0,
                'avg_trade_duration': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'sentiment_accuracy': 0,
            }
            
        except Exception as e:
            logger.warning(f"Failed to get metrics for bot: {e}")
            return {}
    
    def _calculate_score(self, bot_score: BotScore) -> float:
        """
        Calculate final score for a bot using the configured weights.
        
        SCORE = (α × Profit) + (β × WinRate) + (γ × Efficiency) - (δ × ResourceUsage)
        """
        w = self.config.weights
        
        # Normalize metrics to 0-1000 scale
        # Profit: Scale based on max observed profit
        profit_score = min(bot_score.total_profit / 10000, 1.0) * 1000 if bot_score.total_profit > 0 else 0
        
        # Win rate: Already 0-1, scale to 0-1000
        win_rate_score = bot_score.win_rate * 1000
        
        # Efficiency: Based on Sharpe ratio (typically -3 to +3)
        efficiency_score = max(0, min((bot_score.sharpe_ratio + 3) / 6, 1.0)) * 1000
        
        # Resource penalty: Lower is better
        resource_score = bot_score.compute_usage_pct * 10  # Higher usage = higher penalty
        
        # Speed bonus (for FASTEST_SPEED target)
        speed_score = 0
        if w.speed_weight > 0 and bot_score.avg_trade_duration_minutes > 0:
            # Faster trades = higher score (inverse of duration)
            speed_score = min(1000, 1000 / max(bot_score.avg_trade_duration_minutes, 1))
        
        # Sentiment bonus (for SENTIMENT_ALIGNED target)
        sentiment_score = bot_score.sentiment_accuracy * 1000 if w.sentiment_weight > 0 else 0
        
        # Drawdown penalty (for MIN_DRAWDOWN target)
        drawdown_penalty = 0
        if w.drawdown_weight > 0:
            drawdown_penalty = bot_score.max_drawdown * 1000  # Lower drawdown = lower penalty
        
        # Calculate weighted score
        score = (
            (w.profit_weight * profit_score) +
            (w.win_rate_weight * win_rate_score) +
            (w.efficiency_weight * efficiency_score) +
            (w.speed_weight * speed_score) +
            (w.sentiment_weight * sentiment_score) -
            (w.resource_penalty * resource_score) -
            (w.drawdown_weight * drawdown_penalty)
        )
        
        return max(0, score)
    
    def _rank_bots(self) -> None:
        """Rank all active bots by score."""
        active_scores = [s for s in self._bot_scores.values() if s.is_active]
        active_scores.sort(key=lambda x: x.final_score, reverse=True)
        
        for rank, score in enumerate(active_scores, 1):
            score.rank = rank
        
        # Mark champions (top 3)
        self._champions = []
        for score in active_scores[:self.config.pruning.optimal_keep_count]:
            score.is_champion = True
            self._champions.append(score.bot_id)
        
        # Reset champion status for others
        for score in active_scores[self.config.pruning.optimal_keep_count:]:
            score.is_champion = False
    
    async def _execute_pruning(self) -> None:
        """Execute pruning based on current phase."""
        if self._current_phase == TuningPhase.INITIAL_BLAST:
            # No pruning in initial phase
            return
        
        active_scores = [s for s in self._bot_scores.values() if s.is_active]
        total_active = len(active_scores)
        
        if total_active <= self.config.pruning.optimal_keep_count:
            # Already at optimal count
            self._current_phase = TuningPhase.MAINTENANCE
            return
        
        # Determine how many to keep
        if self._current_phase == TuningPhase.FIRST_PRUNING:
            keep_count = max(
                self.config.pruning.optimal_keep_count,
                int(total_active * self.config.pruning.first_pruning_keep_pct)
            )
        elif self._current_phase == TuningPhase.DEEP_PRUNING:
            keep_count = max(
                self.config.pruning.optimal_keep_count,
                int(total_active * self.config.pruning.deep_pruning_keep_pct)
            )
        else:  # OPTIMAL_STATE
            keep_count = self.config.pruning.optimal_keep_count
        
        # Prune bots below the keep threshold
        active_scores.sort(key=lambda x: x.final_score, reverse=True)
        to_prune = active_scores[keep_count:]
        
        for score in to_prune:
            await self._prune_bot(
                score.bot_id,
                reason=f"Below threshold in {self._current_phase.value} phase (rank {score.rank}/{total_active})"
            )
        
        logger.info(f"Pruned {len(to_prune)} bots, {keep_count} remaining")
    
    async def _prune_bot(self, bot_id: str, reason: str) -> None:
        """Prune (stop and optionally delete) a bot."""
        score = self._bot_scores.get(bot_id)
        if not score or not score.is_active:
            return
        
        # Mark as pruned
        score.is_active = False
        score.pruned_at = datetime.now()
        score.pruned_reason = reason
        
        # Stop the bot
        if self._stop_bot:
            try:
                await self._stop_bot(bot_id)
            except Exception as e:
                logger.warning(f"Failed to stop bot {bot_id}: {e}")
        
        # Free up GPU/lane resources
        gpu_id = score.gpu_id
        if gpu_id in self._gpu_allocation:
            self._gpu_allocation[gpu_id] = [
                bid for bid in self._gpu_allocation[gpu_id] if bid != bot_id
            ]
        
        lane_id = score.lane_id
        if lane_id in self._lane_allocation:
            del self._lane_allocation[lane_id]
        
        # Record in history
        self._pruning_history.append({
            'timestamp': datetime.now().isoformat(),
            'bot_id': bot_id,
            'bot_name': score.bot_name,
            'reason': reason,
            'final_score': score.final_score,
            'rank': score.rank,
            'phase': self._current_phase.value,
        })
        
        logger.info(f"Pruned bot {bot_id} ({score.bot_name}): {reason}")
    
    def get_status(self) -> dict:
        """Get current tuning status."""
        active_scores = [s for s in self._bot_scores.values() if s.is_active]
        pruned_scores = [s for s in self._bot_scores.values() if not s.is_active]
        
        # Calculate resource usage
        total_gpus = len(self._gpu_allocation)
        active_gpus = sum(1 for bots in self._gpu_allocation.values() if bots)
        total_lanes = len(self._lane_allocation)
        
        return {
            "enabled": self.config.enabled,
            "running": self._running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "days_running": self.days_running,
            "current_phase": self._current_phase.value,
            "target": self.config.target.value,
            "weights": self.config.weights.to_dict(),
            
            # Bot counts
            "total_bots": len(self._bot_scores),
            "active_bots": len(active_scores),
            "pruned_bots": len(pruned_scores),
            "champions": self._champions,
            
            # Resource usage
            "gpu_usage": {
                "active": active_gpus,
                "total": total_gpus,
                "usage_pct": (active_gpus / total_gpus * 100) if total_gpus > 0 else 0,
            },
            "lane_usage": {
                "active": total_lanes,
                "total": len(self._bot_scores),
                "usage_pct": (total_lanes / len(self._bot_scores) * 100) if self._bot_scores else 0,
            },
            
            # Savings
            "compute_savings_pct": 100 - (len(active_scores) / len(self._bot_scores) * 100) if self._bot_scores else 0,
            
            # Next pruning
            "next_phase_in_days": self._days_until_next_phase(),
        }
    
    def _days_until_next_phase(self) -> int:
        """Calculate days until next phase transition."""
        days = self.days_running
        
        if self._current_phase == TuningPhase.INITIAL_BLAST:
            return self.config.pruning.first_pruning_days - days
        elif self._current_phase == TuningPhase.FIRST_PRUNING:
            return self.config.pruning.deep_pruning_days - days
        elif self._current_phase == TuningPhase.DEEP_PRUNING:
            return self.config.pruning.optimal_state_days - days
        else:
            return 0  # Already at optimal
    
    def get_rankings(self) -> list[dict]:
        """Get current bot rankings."""
        active_scores = [s for s in self._bot_scores.values() if s.is_active]
        active_scores.sort(key=lambda x: x.rank)
        
        return [s.to_dict() for s in active_scores]
    
    def get_pruning_history(self) -> list[dict]:
        """Get history of pruned bots."""
        return self._pruning_history
    
    def get_champion_info(self) -> list[dict]:
        """Get info about current champion bots."""
        return [
            self._bot_scores[bot_id].to_dict()
            for bot_id in self._champions
            if bot_id in self._bot_scores
        ]
    
    def update_config(self, config_dict: dict) -> None:
        """Update configuration."""
        self.config = AgenticTuningConfig.from_dict(config_dict)
        logger.info(f"AgenticTuner config updated: target={self.config.target.value}")


# Global instance
_tuner: Optional[AgenticTuner] = None


def get_agentic_tuner() -> AgenticTuner:
    """Get or create the global AgenticTuner instance."""
    global _tuner
    if _tuner is None:
        _tuner = AgenticTuner()
    return _tuner


def initialize_agentic_tuner(
    config: Optional[AgenticTuningConfig] = None,
    get_all_bots: Optional[Callable] = None,
    stop_bot: Optional[Callable] = None,
    delete_bot: Optional[Callable] = None,
) -> AgenticTuner:
    """Initialize the global AgenticTuner with callbacks."""
    global _tuner
    _tuner = AgenticTuner(
        config=config,
        get_all_bots=get_all_bots,
        stop_bot=stop_bot,
        delete_bot=delete_bot,
    )
    return _tuner

