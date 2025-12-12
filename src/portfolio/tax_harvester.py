"""
Tax-Loss Harvesting System for XFactor Bot

Automatically identifies and executes tax-loss harvesting opportunities
while respecting wash sale rules and maintaining portfolio exposure.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HarvestStrategy(str, Enum):
    """Tax harvesting strategies."""
    AGGRESSIVE = "aggressive"  # Harvest all losses > threshold
    CONSERVATIVE = "conservative"  # Only harvest large losses
    TAX_BRACKET = "tax_bracket"  # Based on tax bracket optimization
    OFFSET_GAINS = "offset_gains"  # Harvest to offset realized gains


@dataclass
class TaxHarvestConfig:
    """Configuration for tax-loss harvesting."""
    # Strategy
    strategy: HarvestStrategy = HarvestStrategy.AGGRESSIVE
    
    # Thresholds
    min_loss_amount: float = 100.0  # Minimum loss to harvest
    min_loss_percent: float = 0.05  # 5% minimum loss
    
    # Tax rates
    short_term_rate: float = 0.37  # Short-term capital gains rate
    long_term_rate: float = 0.20  # Long-term capital gains rate
    state_rate: float = 0.05  # State tax rate
    
    # Wash sale prevention
    wash_sale_window: int = 30  # Days before/after to avoid wash sale
    use_substantially_identical: bool = True  # Check for similar securities
    
    # Replacement securities
    use_replacement: bool = True  # Replace harvested securities
    replacement_holding_period: int = 31  # Days to hold replacement
    
    # Annual limits
    max_annual_harvest: float = 3000.0  # IRS limit for excess losses
    carryover_losses: float = 0.0  # Losses carried from prior years
    
    # Constraints
    max_trades_per_day: int = 5
    maintain_exposure: bool = True  # Keep similar market exposure
    
    # Realized gains this year
    realized_short_term_gains: float = 0.0
    realized_long_term_gains: float = 0.0


@dataclass
class HarvestOpportunity:
    """A tax-loss harvesting opportunity."""
    symbol: str
    quantity: int
    purchase_date: datetime
    purchase_price: float
    current_price: float
    unrealized_loss: float
    loss_percent: float
    is_short_term: bool
    tax_savings: float
    replacement_symbol: Optional[str] = None
    wash_sale_risk: bool = False
    priority: int = 0


@dataclass
class HarvestResult:
    """Result of tax-loss harvesting analysis/execution."""
    # Opportunities
    opportunities: list[HarvestOpportunity] = field(default_factory=list)
    executed: list[HarvestOpportunity] = field(default_factory=list)
    
    # Totals
    total_harvestable_loss: float = 0.0
    total_tax_savings: float = 0.0
    
    # This year
    ytd_harvested: float = 0.0
    remaining_harvest_capacity: float = 0.0
    
    # Wash sales avoided
    wash_sales_prevented: int = 0
    
    # Timing
    analysis_time: datetime = field(default_factory=datetime.now)


# Mapping of securities to their substantially identical replacements
REPLACEMENT_SECURITIES = {
    # S&P 500 ETFs
    'SPY': 'VOO',
    'VOO': 'IVV',
    'IVV': 'SPY',
    
    # Total Market ETFs
    'VTI': 'ITOT',
    'ITOT': 'VTI',
    
    # Tech ETFs
    'QQQ': 'QQQM',
    'QQQM': 'QQQ',
    
    # Bond ETFs
    'BND': 'AGG',
    'AGG': 'BND',
    
    # International ETFs
    'VXUS': 'IXUS',
    'IXUS': 'VXUS',
    
    # Sector ETFs
    'XLK': 'VGT',
    'VGT': 'XLK',
    'XLF': 'VFH',
    'VFH': 'XLF',
    'XLE': 'VDE',
    'VDE': 'XLE',
    
    # Individual stocks - use sector ETFs
    'AAPL': 'XLK',
    'MSFT': 'XLK',
    'GOOGL': 'XLC',
    'AMZN': 'XLY',
    'NVDA': 'SMH',
    'META': 'XLC',
    'TSLA': 'XLY',
}


class TaxLossHarvester:
    """
    Automated tax-loss harvesting system.
    
    Features:
    - Automatic loss identification
    - Wash sale rule compliance
    - Replacement security selection
    - Tax bracket optimization
    - Gain/loss offsetting
    """
    
    def __init__(self, broker=None):
        self.broker = broker
        self.config: Optional[TaxHarvestConfig] = None
        self.harvest_history: list[dict] = []
        self.wash_sale_tracker: dict[str, datetime] = {}  # symbol -> last sale date
        
    def configure(self, config: TaxHarvestConfig) -> None:
        """Set harvesting configuration."""
        self.config = config
        logger.info(f"Configured tax harvester: strategy={config.strategy.value}")
    
    def analyze(self,
                positions: dict[str, dict],
                market_prices: dict[str, float],
                trade_history: Optional[list[dict]] = None) -> HarvestResult:
        """
        Analyze portfolio for tax-loss harvesting opportunities.
        
        Args:
            positions: Current positions with cost basis
            market_prices: Current market prices
            trade_history: Recent trade history for wash sale detection
            
        Returns:
            HarvestResult with opportunities
        """
        if not self.config:
            raise ValueError("Tax harvester not configured")
        
        result = HarvestResult()
        opportunities = []
        
        now = datetime.now()
        one_year_ago = now - timedelta(days=365)
        
        # Update wash sale tracker from trade history
        if trade_history:
            self._update_wash_sale_tracker(trade_history)
        
        for symbol, pos in positions.items():
            quantity = pos.get('quantity', 0)
            if quantity <= 0:
                continue
            
            avg_cost = pos.get('avg_cost', 0)
            purchase_date = pos.get('purchase_date', now - timedelta(days=400))
            if isinstance(purchase_date, str):
                purchase_date = datetime.fromisoformat(purchase_date)
            
            current_price = market_prices.get(symbol, avg_cost)
            
            # Calculate unrealized loss
            unrealized_loss = (avg_cost - current_price) * quantity
            
            if unrealized_loss <= 0:
                continue  # No loss to harvest
            
            loss_percent = (avg_cost - current_price) / avg_cost if avg_cost > 0 else 0
            
            # Check minimum thresholds
            if unrealized_loss < self.config.min_loss_amount:
                continue
            if loss_percent < self.config.min_loss_percent:
                continue
            
            # Check for wash sale risk
            wash_sale_risk = self._check_wash_sale_risk(symbol)
            
            # Determine if short-term or long-term
            is_short_term = purchase_date > one_year_ago
            
            # Calculate tax savings
            tax_rate = self._get_effective_rate(is_short_term)
            tax_savings = unrealized_loss * tax_rate
            
            # Find replacement security
            replacement = self._find_replacement(symbol) if self.config.use_replacement else None
            
            # Priority based on tax savings and loss percent
            priority = int(tax_savings / 10) + int(loss_percent * 100)
            
            opportunity = HarvestOpportunity(
                symbol=symbol,
                quantity=quantity,
                purchase_date=purchase_date,
                purchase_price=avg_cost,
                current_price=current_price,
                unrealized_loss=unrealized_loss,
                loss_percent=loss_percent,
                is_short_term=is_short_term,
                tax_savings=tax_savings,
                replacement_symbol=replacement,
                wash_sale_risk=wash_sale_risk,
                priority=priority,
            )
            
            opportunities.append(opportunity)
        
        # Sort by priority (highest first)
        opportunities.sort(key=lambda x: x.priority, reverse=True)
        
        # Apply strategy filtering
        opportunities = self._filter_by_strategy(opportunities)
        
        # Calculate totals
        result.opportunities = opportunities
        result.total_harvestable_loss = sum(o.unrealized_loss for o in opportunities)
        result.total_tax_savings = sum(o.tax_savings for o in opportunities)
        result.wash_sales_prevented = sum(1 for o in opportunities if o.wash_sale_risk)
        
        # Calculate remaining capacity
        total_gains = self.config.realized_short_term_gains + self.config.realized_long_term_gains
        result.remaining_harvest_capacity = max(
            0, 
            total_gains + self.config.max_annual_harvest - self.config.carryover_losses
        )
        
        logger.info(f"Found {len(opportunities)} harvest opportunities, "
                   f"total savings: ${result.total_tax_savings:,.2f}")
        
        return result
    
    def execute(self, result: HarvestResult,
                max_opportunities: Optional[int] = None) -> HarvestResult:
        """
        Execute tax-loss harvesting trades.
        
        Args:
            result: HarvestResult from analyze()
            max_opportunities: Maximum opportunities to execute
            
        Returns:
            Updated HarvestResult with execution details
        """
        if not self.broker:
            logger.warning("No broker configured, cannot execute harvesting trades")
            return result
        
        opportunities = result.opportunities
        
        # Filter out wash sale risks if configured
        if self.config.use_substantially_identical:
            opportunities = [o for o in opportunities if not o.wash_sale_risk]
        
        # Limit number of trades
        max_trades = max_opportunities or self.config.max_trades_per_day
        opportunities = opportunities[:max_trades]
        
        executed = []
        
        for opp in opportunities:
            try:
                # Sell the losing position
                sell_order = self.broker.place_order(
                    symbol=opp.symbol,
                    side='sell',
                    quantity=opp.quantity,
                    order_type='market',
                )
                
                if sell_order and sell_order.status in ('filled', 'submitted'):
                    # Track for wash sale prevention
                    self.wash_sale_tracker[opp.symbol] = datetime.now()
                    
                    # Buy replacement if configured
                    if opp.replacement_symbol and self.config.maintain_exposure:
                        buy_order = self.broker.place_order(
                            symbol=opp.replacement_symbol,
                            side='buy',
                            quantity=opp.quantity,
                            order_type='market',
                        )
                    
                    executed.append(opp)
                    
                    # Record in history
                    self.harvest_history.append({
                        'date': datetime.now().isoformat(),
                        'symbol': opp.symbol,
                        'quantity': opp.quantity,
                        'loss': opp.unrealized_loss,
                        'tax_savings': opp.tax_savings,
                        'replacement': opp.replacement_symbol,
                    })
                    
            except Exception as e:
                logger.error(f"Failed to harvest {opp.symbol}: {e}")
        
        result.executed = executed
        result.ytd_harvested = sum(o.unrealized_loss for o in executed)
        
        logger.info(f"Executed {len(executed)} harvest trades, "
                   f"realized ${result.ytd_harvested:,.2f} in losses")
        
        return result
    
    def get_wash_sale_report(self) -> dict:
        """Get report of securities in wash sale window."""
        now = datetime.now()
        report = {
            'timestamp': now.isoformat(),
            'wash_sale_window_days': self.config.wash_sale_window if self.config else 30,
            'restricted_securities': [],
        }
        
        window_days = self.config.wash_sale_window if self.config else 30
        
        for symbol, sale_date in self.wash_sale_tracker.items():
            days_since = (now - sale_date).days
            days_remaining = window_days - days_since
            
            if days_remaining > 0:
                report['restricted_securities'].append({
                    'symbol': symbol,
                    'sale_date': sale_date.isoformat(),
                    'days_remaining': days_remaining,
                    'can_repurchase_date': (sale_date + timedelta(days=window_days + 1)).isoformat(),
                })
        
        return report
    
    def estimate_year_end_impact(self,
                                 opportunities: list[HarvestOpportunity]) -> dict:
        """Estimate year-end tax impact if opportunities are harvested."""
        if not self.config:
            return {}
        
        total_short_term_loss = sum(
            o.unrealized_loss for o in opportunities if o.is_short_term
        )
        total_long_term_loss = sum(
            o.unrealized_loss for o in opportunities if not o.is_short_term
        )
        
        # Net against gains
        net_short_term = self.config.realized_short_term_gains - total_short_term_loss
        net_long_term = self.config.realized_long_term_gains - total_long_term_loss
        
        # Calculate tax impact
        if net_short_term < 0 and net_long_term > 0:
            # Short-term losses offset long-term gains
            net_long_term += net_short_term
            net_short_term = 0
        elif net_long_term < 0 and net_short_term > 0:
            # Long-term losses offset short-term gains
            net_short_term += net_long_term
            net_long_term = 0
        
        # Calculate taxes
        short_term_tax = max(0, net_short_term) * self.config.short_term_rate
        long_term_tax = max(0, net_long_term) * self.config.long_term_rate
        
        # Deductible losses (max $3000)
        total_loss = abs(min(0, net_short_term)) + abs(min(0, net_long_term))
        deductible = min(total_loss, 3000)
        deduction_savings = deductible * self.config.short_term_rate
        
        carryover = max(0, total_loss - 3000)
        
        return {
            'net_short_term_gain': net_short_term,
            'net_long_term_gain': net_long_term,
            'short_term_tax': short_term_tax,
            'long_term_tax': long_term_tax,
            'total_tax': short_term_tax + long_term_tax,
            'deductible_loss': deductible,
            'deduction_savings': deduction_savings,
            'loss_carryover': carryover,
            'total_tax_savings': sum(o.tax_savings for o in opportunities),
        }
    
    def _get_effective_rate(self, is_short_term: bool) -> float:
        """Get effective tax rate including state taxes."""
        federal_rate = self.config.short_term_rate if is_short_term else self.config.long_term_rate
        return federal_rate + self.config.state_rate
    
    def _check_wash_sale_risk(self, symbol: str) -> bool:
        """Check if symbol is in wash sale window."""
        if symbol not in self.wash_sale_tracker:
            return False
        
        last_sale = self.wash_sale_tracker[symbol]
        days_since = (datetime.now() - last_sale).days
        
        return days_since < self.config.wash_sale_window
    
    def _find_replacement(self, symbol: str) -> Optional[str]:
        """Find a replacement security that is not substantially identical."""
        # Check predefined replacements
        if symbol in REPLACEMENT_SECURITIES:
            replacement = REPLACEMENT_SECURITIES[symbol]
            # Make sure replacement isn't in wash sale window
            if not self._check_wash_sale_risk(replacement):
                return replacement
        
        # For stocks, use sector ETF
        # This would require sector mapping in production
        return None
    
    def _update_wash_sale_tracker(self, trade_history: list[dict]) -> None:
        """Update wash sale tracker from trade history."""
        for trade in trade_history:
            if trade.get('side') == 'sell':
                symbol = trade.get('symbol')
                date_str = trade.get('date', trade.get('timestamp'))
                if symbol and date_str:
                    try:
                        trade_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        if symbol not in self.wash_sale_tracker or \
                           trade_date > self.wash_sale_tracker[symbol]:
                            self.wash_sale_tracker[symbol] = trade_date
                    except (ValueError, TypeError):
                        pass
    
    def _filter_by_strategy(self, 
                            opportunities: list[HarvestOpportunity]) -> list[HarvestOpportunity]:
        """Filter opportunities based on strategy."""
        if self.config.strategy == HarvestStrategy.AGGRESSIVE:
            # Take all opportunities above threshold
            return opportunities
        
        elif self.config.strategy == HarvestStrategy.CONSERVATIVE:
            # Only large losses (>10%)
            return [o for o in opportunities if o.loss_percent > 0.10]
        
        elif self.config.strategy == HarvestStrategy.OFFSET_GAINS:
            # Only harvest enough to offset gains
            total_gains = self.config.realized_short_term_gains + self.config.realized_long_term_gains
            if total_gains <= 0:
                return []
            
            filtered = []
            cumulative_loss = 0
            for opp in opportunities:
                if cumulative_loss >= total_gains:
                    break
                filtered.append(opp)
                cumulative_loss += opp.unrealized_loss
            return filtered
        
        return opportunities

