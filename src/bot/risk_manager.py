"""
Bot Risk Manager

Comprehensive risk assessment and scoring for trading bots.

Features:
- Overall Risk Score (0-100)
- Component risk breakdown
- Risk-adjusted performance metrics
- Real-time risk alerts
- Position concentration analysis
- Drawdown monitoring
- Correlation risk assessment
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
import math
from collections import defaultdict

from loguru import logger


class RiskLevel(Enum):
    """Risk classification levels."""
    CRITICAL = "critical"      # 80-100: Immediate action required
    HIGH = "high"              # 60-80: Reduce exposure
    ELEVATED = "elevated"      # 40-60: Monitor closely
    MODERATE = "moderate"      # 20-40: Acceptable
    LOW = "low"                # 0-20: Well controlled


class RiskCategory(Enum):
    """Risk categories for assessment."""
    POSITION_SIZE = "position_size"
    CONCENTRATION = "concentration"
    DRAWDOWN = "drawdown"
    VOLATILITY = "volatility"
    LEVERAGE = "leverage"
    CORRELATION = "correlation"
    WIN_RATE = "win_rate"
    EXPOSURE = "exposure"
    LIQUIDITY = "liquidity"
    TIMING = "timing"


@dataclass
class RiskAlert:
    """A risk alert/warning."""
    id: str
    category: RiskCategory
    level: RiskLevel
    title: str
    description: str
    recommendation: str
    triggered_at: datetime
    bot_id: Optional[str] = None
    symbol: Optional[str] = None
    current_value: float = 0.0
    threshold_value: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "triggered_at": self.triggered_at.isoformat(),
            "bot_id": self.bot_id,
            "symbol": self.symbol,
            "current_value": round(self.current_value, 2),
            "threshold_value": round(self.threshold_value, 2),
        }


@dataclass
class RiskMetrics:
    """Risk-adjusted performance metrics."""
    # Returns
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    
    # Volatility
    daily_volatility_pct: float = 0.0
    annualized_volatility_pct: float = 0.0
    
    # Drawdown
    current_drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_drawdown_pct: float = 0.0
    recovery_time_days: float = 0.0
    
    # Risk-Adjusted Ratios
    sharpe_ratio: float = 0.0          # (Return - RiskFree) / Volatility
    sortino_ratio: float = 0.0          # Return / Downside Volatility
    calmar_ratio: float = 0.0           # Return / Max Drawdown
    information_ratio: float = 0.0      # Alpha / Tracking Error
    
    # Win/Loss Analysis
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0          # Gross Profit / Gross Loss
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    largest_win_pct: float = 0.0
    largest_loss_pct: float = 0.0
    win_loss_ratio: float = 0.0         # Avg Win / Avg Loss
    
    # Exposure
    avg_exposure_pct: float = 0.0       # Average % of capital at risk
    max_exposure_pct: float = 0.0
    current_exposure_pct: float = 0.0
    
    # Value at Risk
    var_95_pct: float = 0.0             # 95% VaR
    var_99_pct: float = 0.0             # 99% VaR
    expected_shortfall_pct: float = 0.0  # CVaR / Expected Shortfall
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "returns": {
                "total_return_pct": round(self.total_return_pct, 2),
                "annualized_return_pct": round(self.annualized_return_pct, 2),
            },
            "volatility": {
                "daily_pct": round(self.daily_volatility_pct, 2),
                "annualized_pct": round(self.annualized_volatility_pct, 2),
            },
            "drawdown": {
                "current_pct": round(self.current_drawdown_pct, 2),
                "max_pct": round(self.max_drawdown_pct, 2),
                "avg_pct": round(self.avg_drawdown_pct, 2),
                "recovery_days": round(self.recovery_time_days, 1),
            },
            "risk_adjusted_ratios": {
                "sharpe_ratio": round(self.sharpe_ratio, 2),
                "sortino_ratio": round(self.sortino_ratio, 2),
                "calmar_ratio": round(self.calmar_ratio, 2),
                "information_ratio": round(self.information_ratio, 2),
            },
            "win_loss": {
                "win_rate_pct": round(self.win_rate_pct, 1),
                "profit_factor": round(self.profit_factor, 2),
                "avg_win_pct": round(self.avg_win_pct, 2),
                "avg_loss_pct": round(self.avg_loss_pct, 2),
                "largest_win_pct": round(self.largest_win_pct, 2),
                "largest_loss_pct": round(self.largest_loss_pct, 2),
                "win_loss_ratio": round(self.win_loss_ratio, 2),
            },
            "exposure": {
                "current_pct": round(self.current_exposure_pct, 2),
                "avg_pct": round(self.avg_exposure_pct, 2),
                "max_pct": round(self.max_exposure_pct, 2),
            },
            "value_at_risk": {
                "var_95_pct": round(self.var_95_pct, 2),
                "var_99_pct": round(self.var_99_pct, 2),
                "expected_shortfall_pct": round(self.expected_shortfall_pct, 2),
            },
        }


@dataclass
class BotRiskScore:
    """Comprehensive risk score for a bot."""
    bot_id: str
    bot_name: str
    
    # Overall Score
    overall_risk_score: float       # 0-100 (higher = more risky)
    risk_level: RiskLevel
    
    # Component Scores (0-100 each)
    position_size_score: float = 0.0
    concentration_score: float = 0.0
    drawdown_score: float = 0.0
    volatility_score: float = 0.0
    leverage_score: float = 0.0
    correlation_score: float = 0.0
    win_rate_score: float = 0.0
    exposure_score: float = 0.0
    
    # Risk Metrics
    metrics: RiskMetrics = field(default_factory=RiskMetrics)
    
    # Active Alerts
    alerts: List[RiskAlert] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bot_id": self.bot_id,
            "bot_name": self.bot_name,
            "overall_risk_score": round(self.overall_risk_score, 1),
            "risk_level": self.risk_level.value,
            "risk_level_color": self._get_level_color(),
            "component_scores": {
                "position_size": round(self.position_size_score, 1),
                "concentration": round(self.concentration_score, 1),
                "drawdown": round(self.drawdown_score, 1),
                "volatility": round(self.volatility_score, 1),
                "leverage": round(self.leverage_score, 1),
                "correlation": round(self.correlation_score, 1),
                "win_rate": round(self.win_rate_score, 1),
                "exposure": round(self.exposure_score, 1),
            },
            "metrics": self.metrics.to_dict(),
            "alerts": [a.to_dict() for a in self.alerts],
            "alert_count": len(self.alerts),
            "critical_alerts": len([a for a in self.alerts if a.level == RiskLevel.CRITICAL]),
            "recommendations": self.recommendations,
            "calculated_at": self.calculated_at.isoformat(),
        }
    
    def _get_level_color(self) -> str:
        """Get color for risk level visualization."""
        colors = {
            RiskLevel.CRITICAL: "#dc2626",   # Red
            RiskLevel.HIGH: "#ea580c",       # Orange
            RiskLevel.ELEVATED: "#eab308",   # Yellow
            RiskLevel.MODERATE: "#22c55e",   # Green
            RiskLevel.LOW: "#06b6d4",        # Cyan
        }
        return colors.get(self.risk_level, "#6b7280")


class BotRiskManager:
    """
    Manages risk assessment for trading bots.
    
    Usage:
        manager = BotRiskManager()
        
        # Calculate risk score for a bot
        score = manager.calculate_risk_score(bot_id, bot_data)
        
        # Get risk dashboard
        dashboard = manager.get_risk_dashboard()
        
        # Check for alerts
        alerts = manager.get_active_alerts()
    """
    
    # Risk thresholds
    THRESHOLDS = {
        "max_position_size_pct": 10.0,       # Max % per position
        "max_concentration_pct": 25.0,        # Max % in single asset
        "max_drawdown_pct": 20.0,             # Max drawdown before alert
        "critical_drawdown_pct": 30.0,        # Critical drawdown
        "high_volatility_pct": 30.0,          # High volatility threshold
        "max_leverage": 3.0,                  # Max leverage ratio
        "min_win_rate_pct": 40.0,             # Minimum acceptable win rate
        "max_exposure_pct": 80.0,             # Max total exposure
        "min_sharpe_ratio": 0.5,              # Minimum Sharpe ratio
        "max_correlation": 0.8,               # Max position correlation
    }
    
    # Component weights for overall score
    WEIGHTS = {
        "position_size": 0.15,
        "concentration": 0.15,
        "drawdown": 0.20,
        "volatility": 0.10,
        "leverage": 0.10,
        "correlation": 0.10,
        "win_rate": 0.10,
        "exposure": 0.10,
    }
    
    def __init__(self):
        self._bot_scores: Dict[str, BotRiskScore] = {}
        self._alerts: List[RiskAlert] = []
        self._alert_counter = 0
    
    def calculate_risk_score(
        self,
        bot_id: str,
        bot_data: Dict[str, Any],
    ) -> BotRiskScore:
        """
        Calculate comprehensive risk score for a bot.
        
        Args:
            bot_id: Bot identifier
            bot_data: Bot performance and position data
        
        Returns:
            BotRiskScore with detailed analysis
        """
        bot_name = bot_data.get("name", f"Bot {bot_id}")
        
        # Calculate component scores
        position_size_score = self._calc_position_size_score(bot_data)
        concentration_score = self._calc_concentration_score(bot_data)
        drawdown_score = self._calc_drawdown_score(bot_data)
        volatility_score = self._calc_volatility_score(bot_data)
        leverage_score = self._calc_leverage_score(bot_data)
        correlation_score = self._calc_correlation_score(bot_data)
        win_rate_score = self._calc_win_rate_score(bot_data)
        exposure_score = self._calc_exposure_score(bot_data)
        
        # Calculate weighted overall score
        overall_score = (
            position_size_score * self.WEIGHTS["position_size"] +
            concentration_score * self.WEIGHTS["concentration"] +
            drawdown_score * self.WEIGHTS["drawdown"] +
            volatility_score * self.WEIGHTS["volatility"] +
            leverage_score * self.WEIGHTS["leverage"] +
            correlation_score * self.WEIGHTS["correlation"] +
            win_rate_score * self.WEIGHTS["win_rate"] +
            exposure_score * self.WEIGHTS["exposure"]
        )
        
        # Determine risk level
        if overall_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif overall_score >= 60:
            risk_level = RiskLevel.HIGH
        elif overall_score >= 40:
            risk_level = RiskLevel.ELEVATED
        elif overall_score >= 20:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.LOW
        
        # Calculate detailed metrics
        metrics = self._calculate_metrics(bot_data)
        
        # Generate alerts
        alerts = self._generate_alerts(bot_id, bot_name, bot_data, {
            "position_size": position_size_score,
            "concentration": concentration_score,
            "drawdown": drawdown_score,
            "volatility": volatility_score,
            "leverage": leverage_score,
            "win_rate": win_rate_score,
            "exposure": exposure_score,
        })
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            overall_score, risk_level, alerts, bot_data
        )
        
        score = BotRiskScore(
            bot_id=bot_id,
            bot_name=bot_name,
            overall_risk_score=overall_score,
            risk_level=risk_level,
            position_size_score=position_size_score,
            concentration_score=concentration_score,
            drawdown_score=drawdown_score,
            volatility_score=volatility_score,
            leverage_score=leverage_score,
            correlation_score=correlation_score,
            win_rate_score=win_rate_score,
            exposure_score=exposure_score,
            metrics=metrics,
            alerts=alerts,
            recommendations=recommendations,
        )
        
        self._bot_scores[bot_id] = score
        return score
    
    def _calc_position_size_score(self, bot_data: Dict) -> float:
        """Calculate position size risk (0-100)."""
        positions = bot_data.get("positions", [])
        account_value = bot_data.get("account_value", 100000)
        
        if not positions or account_value <= 0:
            return 0
        
        max_position_pct = 0
        for pos in positions:
            pos_value = abs(pos.get("value", 0))
            pos_pct = (pos_value / account_value) * 100
            max_position_pct = max(max_position_pct, pos_pct)
        
        threshold = self.THRESHOLDS["max_position_size_pct"]
        score = min(100, (max_position_pct / threshold) * 50)
        
        return score
    
    def _calc_concentration_score(self, bot_data: Dict) -> float:
        """Calculate concentration risk (0-100)."""
        positions = bot_data.get("positions", [])
        account_value = bot_data.get("account_value", 100000)
        
        if not positions or account_value <= 0:
            return 0
        
        # Group by symbol/asset
        asset_exposure: Dict[str, float] = defaultdict(float)
        for pos in positions:
            symbol = pos.get("symbol", "UNKNOWN")
            value = abs(pos.get("value", 0))
            asset_exposure[symbol] += value
        
        # Find max concentration
        max_concentration_pct = 0
        for symbol, value in asset_exposure.items():
            pct = (value / account_value) * 100
            max_concentration_pct = max(max_concentration_pct, pct)
        
        threshold = self.THRESHOLDS["max_concentration_pct"]
        score = min(100, (max_concentration_pct / threshold) * 50)
        
        return score
    
    def _calc_drawdown_score(self, bot_data: Dict) -> float:
        """Calculate drawdown risk (0-100)."""
        current_drawdown = abs(bot_data.get("current_drawdown_pct", 0))
        max_drawdown = abs(bot_data.get("max_drawdown_pct", 0))
        
        # Weight current drawdown more heavily
        weighted_dd = (current_drawdown * 0.6) + (max_drawdown * 0.4)
        
        critical_threshold = self.THRESHOLDS["critical_drawdown_pct"]
        score = min(100, (weighted_dd / critical_threshold) * 100)
        
        return score
    
    def _calc_volatility_score(self, bot_data: Dict) -> float:
        """Calculate volatility risk (0-100)."""
        daily_vol = bot_data.get("daily_volatility_pct", 0)
        
        # Annualize
        annual_vol = daily_vol * math.sqrt(252)
        
        threshold = self.THRESHOLDS["high_volatility_pct"]
        score = min(100, (annual_vol / threshold) * 50)
        
        return score
    
    def _calc_leverage_score(self, bot_data: Dict) -> float:
        """Calculate leverage risk (0-100)."""
        leverage = bot_data.get("leverage", 1.0)
        
        if leverage <= 1:
            return 0
        
        max_leverage = self.THRESHOLDS["max_leverage"]
        score = min(100, ((leverage - 1) / (max_leverage - 1)) * 100)
        
        return score
    
    def _calc_correlation_score(self, bot_data: Dict) -> float:
        """Calculate correlation risk (0-100)."""
        positions = bot_data.get("positions", [])
        correlations = bot_data.get("position_correlations", {})
        
        if len(positions) < 2:
            return 0
        
        # Find highest correlation between positions
        max_correlation = 0
        for key, corr in correlations.items():
            max_correlation = max(max_correlation, abs(corr))
        
        threshold = self.THRESHOLDS["max_correlation"]
        score = min(100, (max_correlation / threshold) * 50)
        
        return score
    
    def _calc_win_rate_score(self, bot_data: Dict) -> float:
        """Calculate win rate risk (0-100). Low win rate = high risk."""
        win_rate = bot_data.get("win_rate_pct", 50)
        total_trades = bot_data.get("total_trades", 0)
        
        if total_trades < 10:
            return 30  # Not enough data, moderate risk
        
        min_win_rate = self.THRESHOLDS["min_win_rate_pct"]
        
        if win_rate >= min_win_rate:
            # Above threshold: low risk
            score = max(0, 50 - ((win_rate - min_win_rate) * 2))
        else:
            # Below threshold: increasing risk
            score = 50 + ((min_win_rate - win_rate) * 2.5)
        
        return min(100, score)
    
    def _calc_exposure_score(self, bot_data: Dict) -> float:
        """Calculate exposure risk (0-100)."""
        current_exposure = bot_data.get("current_exposure_pct", 0)
        
        threshold = self.THRESHOLDS["max_exposure_pct"]
        score = min(100, (current_exposure / threshold) * 60)
        
        return score
    
    def _calculate_metrics(self, bot_data: Dict) -> RiskMetrics:
        """Calculate detailed risk metrics."""
        trades = bot_data.get("trades", [])
        
        # Basic metrics from bot_data
        total_return = bot_data.get("total_return_pct", 0)
        daily_vol = bot_data.get("daily_volatility_pct", 1)
        current_dd = bot_data.get("current_drawdown_pct", 0)
        max_dd = bot_data.get("max_drawdown_pct", 0)
        win_rate = bot_data.get("win_rate_pct", 50)
        
        # Annualized metrics (assume 252 trading days)
        annual_return = total_return * 12  # Rough monthly to annual
        annual_vol = daily_vol * math.sqrt(252)
        
        # Risk-adjusted ratios
        risk_free_rate = 5.0  # Current risk-free rate
        sharpe = (annual_return - risk_free_rate) / max(annual_vol, 1)
        
        # Sortino (using downside volatility - simplified)
        downside_vol = daily_vol * 0.6 * math.sqrt(252)  # Approximate
        sortino = (annual_return - risk_free_rate) / max(downside_vol, 1)
        
        # Calmar
        calmar = annual_return / max(abs(max_dd), 1)
        
        # Win/Loss analysis
        if trades:
            wins = [t for t in trades if t.get("pnl", 0) > 0]
            losses = [t for t in trades if t.get("pnl", 0) < 0]
            
            avg_win = sum(t.get("pnl_pct", 0) for t in wins) / len(wins) if wins else 0
            avg_loss = sum(abs(t.get("pnl_pct", 0)) for t in losses) / len(losses) if losses else 0
            
            gross_profit = sum(t.get("pnl", 0) for t in wins)
            gross_loss = abs(sum(t.get("pnl", 0) for t in losses))
            profit_factor = gross_profit / max(gross_loss, 1)
            
            largest_win = max((t.get("pnl_pct", 0) for t in trades), default=0)
            largest_loss = min((t.get("pnl_pct", 0) for t in trades), default=0)
        else:
            avg_win = bot_data.get("avg_win_pct", 0)
            avg_loss = bot_data.get("avg_loss_pct", 0)
            profit_factor = bot_data.get("profit_factor", 1.0)
            largest_win = bot_data.get("largest_win_pct", 0)
            largest_loss = bot_data.get("largest_loss_pct", 0)
        
        win_loss_ratio = avg_win / max(avg_loss, 0.1)
        
        # VaR (simplified - parametric)
        var_95 = daily_vol * 1.65
        var_99 = daily_vol * 2.33
        expected_shortfall = var_99 * 1.2  # Approximate
        
        return RiskMetrics(
            total_return_pct=total_return,
            annualized_return_pct=annual_return,
            daily_volatility_pct=daily_vol,
            annualized_volatility_pct=annual_vol,
            current_drawdown_pct=current_dd,
            max_drawdown_pct=max_dd,
            avg_drawdown_pct=max_dd * 0.6,  # Approximate
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
            avg_win_pct=avg_win,
            avg_loss_pct=avg_loss,
            largest_win_pct=largest_win,
            largest_loss_pct=largest_loss,
            win_loss_ratio=win_loss_ratio,
            current_exposure_pct=bot_data.get("current_exposure_pct", 0),
            avg_exposure_pct=bot_data.get("avg_exposure_pct", 0),
            max_exposure_pct=bot_data.get("max_exposure_pct", 0),
            var_95_pct=var_95,
            var_99_pct=var_99,
            expected_shortfall_pct=expected_shortfall,
        )
    
    def _generate_alerts(
        self,
        bot_id: str,
        bot_name: str,
        bot_data: Dict,
        component_scores: Dict[str, float],
    ) -> List[RiskAlert]:
        """Generate risk alerts based on thresholds."""
        alerts = []
        now = datetime.now(timezone.utc)
        
        # Drawdown alert
        current_dd = abs(bot_data.get("current_drawdown_pct", 0))
        if current_dd >= self.THRESHOLDS["critical_drawdown_pct"]:
            self._alert_counter += 1
            alerts.append(RiskAlert(
                id=f"alert_{self._alert_counter}",
                category=RiskCategory.DRAWDOWN,
                level=RiskLevel.CRITICAL,
                title="Critical Drawdown",
                description=f"{bot_name} has reached {current_dd:.1f}% drawdown",
                recommendation="Consider stopping the bot and reviewing strategy",
                triggered_at=now,
                bot_id=bot_id,
                current_value=current_dd,
                threshold_value=self.THRESHOLDS["critical_drawdown_pct"],
            ))
        elif current_dd >= self.THRESHOLDS["max_drawdown_pct"]:
            self._alert_counter += 1
            alerts.append(RiskAlert(
                id=f"alert_{self._alert_counter}",
                category=RiskCategory.DRAWDOWN,
                level=RiskLevel.HIGH,
                title="High Drawdown Warning",
                description=f"{bot_name} drawdown at {current_dd:.1f}%",
                recommendation="Reduce position sizes or tighten stops",
                triggered_at=now,
                bot_id=bot_id,
                current_value=current_dd,
                threshold_value=self.THRESHOLDS["max_drawdown_pct"],
            ))
        
        # Exposure alert
        exposure = bot_data.get("current_exposure_pct", 0)
        if exposure >= self.THRESHOLDS["max_exposure_pct"]:
            self._alert_counter += 1
            alerts.append(RiskAlert(
                id=f"alert_{self._alert_counter}",
                category=RiskCategory.EXPOSURE,
                level=RiskLevel.HIGH,
                title="High Exposure",
                description=f"{bot_name} exposure at {exposure:.1f}% of capital",
                recommendation="Close some positions to reduce exposure",
                triggered_at=now,
                bot_id=bot_id,
                current_value=exposure,
                threshold_value=self.THRESHOLDS["max_exposure_pct"],
            ))
        
        # Concentration alert
        if component_scores.get("concentration", 0) >= 70:
            self._alert_counter += 1
            alerts.append(RiskAlert(
                id=f"alert_{self._alert_counter}",
                category=RiskCategory.CONCENTRATION,
                level=RiskLevel.ELEVATED,
                title="Position Concentration",
                description=f"{bot_name} has concentrated positions",
                recommendation="Diversify across more symbols",
                triggered_at=now,
                bot_id=bot_id,
                current_value=component_scores["concentration"],
                threshold_value=70,
            ))
        
        # Win rate alert
        win_rate = bot_data.get("win_rate_pct", 50)
        total_trades = bot_data.get("total_trades", 0)
        if total_trades >= 20 and win_rate < self.THRESHOLDS["min_win_rate_pct"]:
            self._alert_counter += 1
            alerts.append(RiskAlert(
                id=f"alert_{self._alert_counter}",
                category=RiskCategory.WIN_RATE,
                level=RiskLevel.ELEVATED,
                title="Low Win Rate",
                description=f"{bot_name} win rate at {win_rate:.1f}%",
                recommendation="Review strategy parameters and entry criteria",
                triggered_at=now,
                bot_id=bot_id,
                current_value=win_rate,
                threshold_value=self.THRESHOLDS["min_win_rate_pct"],
            ))
        
        # Leverage alert
        leverage = bot_data.get("leverage", 1.0)
        if leverage >= self.THRESHOLDS["max_leverage"]:
            self._alert_counter += 1
            alerts.append(RiskAlert(
                id=f"alert_{self._alert_counter}",
                category=RiskCategory.LEVERAGE,
                level=RiskLevel.HIGH,
                title="High Leverage",
                description=f"{bot_name} using {leverage:.1f}x leverage",
                recommendation="Reduce leverage to limit potential losses",
                triggered_at=now,
                bot_id=bot_id,
                current_value=leverage,
                threshold_value=self.THRESHOLDS["max_leverage"],
            ))
        
        # Store alerts
        self._alerts.extend(alerts)
        
        return alerts
    
    def _generate_recommendations(
        self,
        overall_score: float,
        risk_level: RiskLevel,
        alerts: List[RiskAlert],
        bot_data: Dict,
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if risk_level == RiskLevel.CRITICAL:
            recommendations.append("⚠️ URGENT: Consider pausing this bot immediately")
            recommendations.append("Review all open positions for potential exit")
        
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            recommendations.append("Reduce position sizes by 50%")
            recommendations.append("Implement tighter stop losses")
        
        # Specific recommendations based on component scores
        if bot_data.get("current_drawdown_pct", 0) > 15:
            recommendations.append("Consider waiting for recovery before new trades")
        
        if bot_data.get("win_rate_pct", 50) < 40:
            recommendations.append("Review entry signal accuracy")
            recommendations.append("Consider adding confirmation indicators")
        
        sharpe = bot_data.get("sharpe_ratio", 0)
        if sharpe < self.THRESHOLDS["min_sharpe_ratio"]:
            recommendations.append("Improve risk-adjusted returns (current Sharpe < 0.5)")
        
        if len(bot_data.get("positions", [])) == 1:
            recommendations.append("Add more positions for diversification")
        
        if not recommendations:
            recommendations.append("✅ Risk metrics within acceptable parameters")
            recommendations.append("Continue monitoring for changes")
        
        return recommendations[:5]  # Top 5 recommendations
    
    def get_risk_score(self, bot_id: str) -> Optional[BotRiskScore]:
        """Get cached risk score for a bot."""
        return self._bot_scores.get(bot_id)
    
    def get_all_risk_scores(self) -> List[Dict[str, Any]]:
        """Get all bot risk scores."""
        return [s.to_dict() for s in self._bot_scores.values()]
    
    def get_active_alerts(
        self,
        min_level: RiskLevel = RiskLevel.ELEVATED,
    ) -> List[Dict[str, Any]]:
        """Get active alerts at or above specified level."""
        level_order = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.ELEVATED, RiskLevel.MODERATE, RiskLevel.LOW]
        min_index = level_order.index(min_level)
        allowed = level_order[:min_index + 1]
        
        return [
            a.to_dict() for a in self._alerts
            if a.level in allowed
        ]
    
    def get_portfolio_risk(self, bots: List[Dict]) -> Dict[str, Any]:
        """Calculate aggregate portfolio risk across all bots."""
        if not bots:
            return {
                "overall_risk_score": 0,
                "risk_level": RiskLevel.LOW.value,
                "total_exposure_pct": 0,
                "bot_count": 0,
            }
        
        total_exposure = sum(b.get("current_exposure_pct", 0) for b in bots)
        avg_risk_score = sum(
            self._bot_scores.get(b.get("id"), BotRiskScore(
                bot_id="", bot_name="", overall_risk_score=50, risk_level=RiskLevel.MODERATE
            )).overall_risk_score
            for b in bots
        ) / len(bots)
        
        # Determine portfolio risk level
        if avg_risk_score >= 70:
            level = RiskLevel.CRITICAL
        elif avg_risk_score >= 55:
            level = RiskLevel.HIGH
        elif avg_risk_score >= 40:
            level = RiskLevel.ELEVATED
        elif avg_risk_score >= 25:
            level = RiskLevel.MODERATE
        else:
            level = RiskLevel.LOW
        
        return {
            "overall_risk_score": round(avg_risk_score, 1),
            "risk_level": level.value,
            "total_exposure_pct": round(total_exposure, 1),
            "bot_count": len(bots),
            "high_risk_bots": len([b for b in bots if self._bot_scores.get(b.get("id")) and self._bot_scores[b.get("id")].overall_risk_score >= 60]),
            "total_alerts": len(self._alerts),
            "critical_alerts": len([a for a in self._alerts if a.level == RiskLevel.CRITICAL]),
        }
    
    def clear_alerts(self, bot_id: Optional[str] = None) -> int:
        """Clear alerts, optionally for a specific bot."""
        if bot_id:
            before = len(self._alerts)
            self._alerts = [a for a in self._alerts if a.bot_id != bot_id]
            return before - len(self._alerts)
        else:
            count = len(self._alerts)
            self._alerts = []
            return count


# Singleton instance
_risk_manager: Optional[BotRiskManager] = None


def get_bot_risk_manager() -> BotRiskManager:
    """Get or create the bot risk manager singleton."""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = BotRiskManager()
    return _risk_manager

