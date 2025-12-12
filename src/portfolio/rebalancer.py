"""
Portfolio Rebalancer for XFactor Bot

Automatically rebalances portfolio to maintain target allocations
with support for multiple rebalancing strategies.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RebalanceMethod(str, Enum):
    """Rebalancing methods."""
    THRESHOLD = "threshold"  # Rebalance when drift exceeds threshold
    CALENDAR = "calendar"    # Rebalance on schedule
    TACTICAL = "tactical"    # Dynamic based on market conditions
    HYBRID = "hybrid"        # Combination of methods


class AllocationStrategy(str, Enum):
    """Portfolio allocation strategies."""
    EQUAL_WEIGHT = "equal_weight"
    MARKET_CAP = "market_cap"
    RISK_PARITY = "risk_parity"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_SHARPE = "maximum_sharpe"
    CUSTOM = "custom"


@dataclass
class TargetAllocation:
    """Target allocation for a single asset."""
    symbol: str
    target_weight: float  # 0.0 to 1.0
    min_weight: float = 0.0
    max_weight: float = 1.0
    asset_class: str = "equity"
    sector: Optional[str] = None


@dataclass
class RebalanceConfig:
    """Configuration for portfolio rebalancing."""
    # Method
    method: RebalanceMethod = RebalanceMethod.THRESHOLD
    allocation_strategy: AllocationStrategy = AllocationStrategy.EQUAL_WEIGHT
    
    # Thresholds
    drift_threshold: float = 0.05  # 5% drift triggers rebalance
    min_trade_value: float = 100.0  # Don't trade less than $100
    
    # Calendar settings
    rebalance_frequency: str = "quarterly"  # daily, weekly, monthly, quarterly
    rebalance_day: int = 1  # Day of period (1=first)
    
    # Tax efficiency
    tax_aware: bool = True
    avoid_wash_sales: bool = True
    prefer_long_term_gains: bool = True
    
    # Constraints
    max_turnover: float = 0.25  # Max 25% portfolio turnover per rebalance
    max_trades_per_day: int = 10
    
    # Costs
    estimated_commission: float = 1.0
    estimated_slippage_bps: float = 5.0
    
    # Target allocations
    target_allocations: list[TargetAllocation] = field(default_factory=list)


@dataclass
class RebalanceTrade:
    """A trade required for rebalancing."""
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: int
    current_weight: float
    target_weight: float
    drift: float
    estimated_value: float
    priority: int = 0  # Higher = execute first


@dataclass
class RebalanceResult:
    """Result of a rebalancing operation."""
    # Status
    rebalance_needed: bool = False
    trades_proposed: list[RebalanceTrade] = field(default_factory=list)
    trades_executed: list[RebalanceTrade] = field(default_factory=list)
    
    # Metrics
    pre_drift: float = 0.0  # Weighted average drift before
    post_drift: float = 0.0  # Weighted average drift after
    turnover: float = 0.0  # Portfolio turnover
    
    # Costs
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    
    # Tax impact
    short_term_gains: float = 0.0
    long_term_gains: float = 0.0
    tax_liability_estimate: float = 0.0
    
    # Timing
    analysis_time: datetime = field(default_factory=datetime.now)
    execution_time: Optional[datetime] = None


class PortfolioRebalancer:
    """
    Automated portfolio rebalancing system.
    
    Features:
    - Multiple rebalancing strategies
    - Tax-efficient trading
    - Drift monitoring and alerts
    - Transaction cost optimization
    - Multi-asset class support
    """
    
    def __init__(self, broker=None):
        self.broker = broker
        self.config: Optional[RebalanceConfig] = None
        self.last_rebalance: Optional[datetime] = None
        
    def configure(self, config: RebalanceConfig) -> None:
        """Set rebalancing configuration."""
        self.config = config
        logger.info(f"Configured rebalancer: method={config.method.value}, "
                   f"strategy={config.allocation_strategy.value}")
    
    def analyze(self, 
                positions: dict[str, dict],
                portfolio_value: float,
                market_prices: dict[str, float]) -> RebalanceResult:
        """
        Analyze current portfolio and determine if rebalancing is needed.
        
        Args:
            positions: Current positions {symbol: {quantity, avg_cost, ...}}
            portfolio_value: Total portfolio value
            market_prices: Current market prices {symbol: price}
            
        Returns:
            RebalanceResult with proposed trades
        """
        if not self.config:
            raise ValueError("Rebalancer not configured")
        
        result = RebalanceResult()
        
        # Calculate current weights
        current_weights = self._calculate_current_weights(
            positions, portfolio_value, market_prices
        )
        
        # Get target weights
        target_weights = self._get_target_weights()
        
        # Calculate drift for each position
        drifts = {}
        for symbol in set(list(current_weights.keys()) + list(target_weights.keys())):
            current = current_weights.get(symbol, 0.0)
            target = target_weights.get(symbol, 0.0)
            drifts[symbol] = current - target
        
        # Calculate weighted average absolute drift
        result.pre_drift = sum(abs(d) for d in drifts.values()) / 2
        
        # Check if rebalancing is needed
        result.rebalance_needed = self._should_rebalance(drifts, result.pre_drift)
        
        if not result.rebalance_needed:
            logger.info(f"No rebalancing needed. Drift: {result.pre_drift:.2%}")
            return result
        
        # Generate trades to rebalance
        trades = self._generate_trades(
            drifts, current_weights, target_weights,
            positions, portfolio_value, market_prices
        )
        
        # Sort by priority (sells first to generate cash)
        trades.sort(key=lambda t: (t.side != 'sell', -t.priority))
        
        # Apply constraints
        trades = self._apply_constraints(trades, portfolio_value)
        
        result.trades_proposed = trades
        result.turnover = sum(t.estimated_value for t in trades) / portfolio_value
        result.estimated_cost = self._estimate_costs(trades)
        
        # Estimate tax impact if tax-aware
        if self.config.tax_aware:
            self._estimate_tax_impact(trades, positions, result)
        
        logger.info(f"Rebalancing analysis complete. "
                   f"Drift: {result.pre_drift:.2%}, "
                   f"Trades: {len(trades)}, "
                   f"Turnover: {result.turnover:.2%}")
        
        return result
    
    def execute(self, result: RebalanceResult) -> RebalanceResult:
        """
        Execute the proposed rebalancing trades.
        
        Args:
            result: RebalanceResult from analyze()
            
        Returns:
            Updated RebalanceResult with execution details
        """
        if not result.rebalance_needed or not result.trades_proposed:
            return result
        
        if not self.broker:
            logger.warning("No broker configured, cannot execute trades")
            return result
        
        executed = []
        actual_cost = 0.0
        
        for trade in result.trades_proposed:
            try:
                # Place order through broker
                order = self.broker.place_order(
                    symbol=trade.symbol,
                    side=trade.side,
                    quantity=trade.quantity,
                    order_type='market',
                )
                
                if order and order.status in ('filled', 'submitted'):
                    executed.append(trade)
                    actual_cost += self.config.estimated_commission
                    
            except Exception as e:
                logger.error(f"Failed to execute rebalance trade for {trade.symbol}: {e}")
        
        result.trades_executed = executed
        result.actual_cost = actual_cost
        result.execution_time = datetime.now()
        self.last_rebalance = result.execution_time
        
        logger.info(f"Rebalancing executed. {len(executed)}/{len(result.trades_proposed)} trades completed")
        
        return result
    
    def get_drift_report(self,
                         positions: dict[str, dict],
                         portfolio_value: float,
                         market_prices: dict[str, float]) -> dict:
        """Get detailed drift report for monitoring."""
        if not self.config:
            return {}
        
        current_weights = self._calculate_current_weights(
            positions, portfolio_value, market_prices
        )
        target_weights = self._get_target_weights()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'portfolio_value': portfolio_value,
            'positions': [],
            'total_drift': 0.0,
            'rebalance_needed': False,
        }
        
        all_symbols = set(list(current_weights.keys()) + list(target_weights.keys()))
        
        for symbol in sorted(all_symbols):
            current = current_weights.get(symbol, 0.0)
            target = target_weights.get(symbol, 0.0)
            drift = current - target
            
            report['positions'].append({
                'symbol': symbol,
                'current_weight': current,
                'target_weight': target,
                'drift': drift,
                'abs_drift': abs(drift),
                'over_threshold': abs(drift) > self.config.drift_threshold,
            })
        
        report['total_drift'] = sum(abs(p['drift']) for p in report['positions']) / 2
        report['rebalance_needed'] = report['total_drift'] > self.config.drift_threshold
        
        return report
    
    def _calculate_current_weights(self,
                                   positions: dict[str, dict],
                                   portfolio_value: float,
                                   market_prices: dict[str, float]) -> dict[str, float]:
        """Calculate current portfolio weights."""
        weights = {}
        
        if portfolio_value <= 0:
            return weights
        
        for symbol, pos in positions.items():
            quantity = pos.get('quantity', 0)
            price = market_prices.get(symbol, pos.get('current_price', 0))
            position_value = quantity * price
            weights[symbol] = position_value / portfolio_value
        
        return weights
    
    def _get_target_weights(self) -> dict[str, float]:
        """Get target weights from configuration."""
        weights = {}
        
        if self.config.allocation_strategy == AllocationStrategy.EQUAL_WEIGHT:
            # Equal weight all positions
            n = len(self.config.target_allocations)
            if n > 0:
                weight = 1.0 / n
                for alloc in self.config.target_allocations:
                    weights[alloc.symbol] = weight
        else:
            # Use configured target weights
            for alloc in self.config.target_allocations:
                weights[alloc.symbol] = alloc.target_weight
        
        return weights
    
    def _should_rebalance(self, drifts: dict[str, float], total_drift: float) -> bool:
        """Determine if rebalancing should occur."""
        if self.config.method == RebalanceMethod.THRESHOLD:
            # Any single position exceeds threshold
            max_drift = max(abs(d) for d in drifts.values()) if drifts else 0
            return max_drift > self.config.drift_threshold
            
        elif self.config.method == RebalanceMethod.CALENDAR:
            # Check if we're on the rebalancing schedule
            now = datetime.now()
            if self.config.rebalance_frequency == 'daily':
                return True
            elif self.config.rebalance_frequency == 'weekly':
                return now.weekday() == 0  # Monday
            elif self.config.rebalance_frequency == 'monthly':
                return now.day == self.config.rebalance_day
            elif self.config.rebalance_frequency == 'quarterly':
                return now.month in [1, 4, 7, 10] and now.day == self.config.rebalance_day
        
        elif self.config.method == RebalanceMethod.HYBRID:
            # Calendar OR threshold exceeded significantly
            threshold_triggered = total_drift > self.config.drift_threshold * 1.5
            return threshold_triggered or self._should_rebalance_calendar()
        
        return total_drift > self.config.drift_threshold
    
    def _should_rebalance_calendar(self) -> bool:
        """Check calendar-based rebalancing."""
        if not self.last_rebalance:
            return True
        
        now = datetime.now()
        days_since = (now - self.last_rebalance).days
        
        if self.config.rebalance_frequency == 'daily':
            return days_since >= 1
        elif self.config.rebalance_frequency == 'weekly':
            return days_since >= 7
        elif self.config.rebalance_frequency == 'monthly':
            return days_since >= 30
        elif self.config.rebalance_frequency == 'quarterly':
            return days_since >= 90
        
        return False
    
    def _generate_trades(self,
                         drifts: dict[str, float],
                         current_weights: dict[str, float],
                         target_weights: dict[str, float],
                         positions: dict[str, dict],
                         portfolio_value: float,
                         market_prices: dict[str, float]) -> list[RebalanceTrade]:
        """Generate trades to close drift."""
        trades = []
        
        for symbol, drift in drifts.items():
            if abs(drift) < 0.001:  # Ignore tiny drifts
                continue
            
            price = market_prices.get(symbol, 0)
            if price <= 0:
                continue
            
            current_weight = current_weights.get(symbol, 0)
            target_weight = target_weights.get(symbol, 0)
            
            # Calculate trade value and quantity
            trade_value = abs(drift) * portfolio_value
            
            if trade_value < self.config.min_trade_value:
                continue
            
            quantity = int(trade_value / price)
            if quantity <= 0:
                continue
            
            side = 'sell' if drift > 0 else 'buy'
            
            # Priority based on drift magnitude
            priority = int(abs(drift) * 100)
            
            trades.append(RebalanceTrade(
                symbol=symbol,
                side=side,
                quantity=quantity,
                current_weight=current_weight,
                target_weight=target_weight,
                drift=drift,
                estimated_value=quantity * price,
                priority=priority,
            ))
        
        return trades
    
    def _apply_constraints(self, trades: list[RebalanceTrade],
                           portfolio_value: float) -> list[RebalanceTrade]:
        """Apply constraints to proposed trades."""
        # Limit number of trades
        if len(trades) > self.config.max_trades_per_day:
            trades = trades[:self.config.max_trades_per_day]
        
        # Limit turnover
        total_value = sum(t.estimated_value for t in trades)
        max_value = portfolio_value * self.config.max_turnover
        
        if total_value > max_value:
            # Scale down proportionally
            scale = max_value / total_value
            for trade in trades:
                trade.quantity = int(trade.quantity * scale)
                trade.estimated_value *= scale
            
            # Remove trades with 0 quantity
            trades = [t for t in trades if t.quantity > 0]
        
        return trades
    
    def _estimate_costs(self, trades: list[RebalanceTrade]) -> float:
        """Estimate transaction costs."""
        total_value = sum(t.estimated_value for t in trades)
        
        commission_cost = len(trades) * self.config.estimated_commission
        slippage_cost = total_value * (self.config.estimated_slippage_bps / 10000)
        
        return commission_cost + slippage_cost
    
    def _estimate_tax_impact(self, trades: list[RebalanceTrade],
                             positions: dict[str, dict],
                             result: RebalanceResult) -> None:
        """Estimate tax impact of proposed trades."""
        short_term = 0.0
        long_term = 0.0
        
        now = datetime.now()
        one_year_ago = now - timedelta(days=365)
        
        for trade in trades:
            if trade.side != 'sell':
                continue
            
            pos = positions.get(trade.symbol, {})
            avg_cost = pos.get('avg_cost', 0)
            purchase_date = pos.get('purchase_date')
            
            if avg_cost <= 0:
                continue
            
            price = trade.estimated_value / trade.quantity if trade.quantity > 0 else 0
            gain = (price - avg_cost) * trade.quantity
            
            if gain > 0:
                if purchase_date and purchase_date > one_year_ago:
                    short_term += gain
                else:
                    long_term += gain
        
        result.short_term_gains = short_term
        result.long_term_gains = long_term
        
        # Rough tax estimate (37% short-term, 20% long-term)
        result.tax_liability_estimate = short_term * 0.37 + long_term * 0.20

