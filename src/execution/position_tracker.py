"""
Position Tracker for portfolio management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from loguru import logger

from src.connectors.ibkr_connector import IBKRConnector
from src.data.redis_cache import RedisCache
from src.data.timescale_client import TimescaleClient


@dataclass
class Position:
    """Represents a portfolio position."""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float = 0
    market_value: float = 0
    unrealized_pnl: float = 0
    unrealized_pnl_pct: float = 0
    realized_pnl: float = 0
    sector: str = ""
    strategy: str = ""
    entry_time: datetime = field(default_factory=datetime.utcnow)
    
    def update_price(self, price: float) -> None:
        """Update position with new price."""
        self.current_price = price
        self.market_value = self.quantity * price
        cost_basis = self.quantity * self.avg_cost
        self.unrealized_pnl = self.market_value - cost_basis
        if cost_basis != 0:
            self.unrealized_pnl_pct = self.unrealized_pnl / cost_basis * 100


@dataclass
class PortfolioSummary:
    """Portfolio summary statistics."""
    total_value: float
    cash: float
    positions_value: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    daily_pnl: float
    position_count: int
    
    @property
    def total_pnl(self) -> float:
        return self.total_unrealized_pnl + self.total_realized_pnl


class PositionTracker:
    """
    Track and manage portfolio positions.
    
    Features:
    - Real-time position updates
    - P&L calculation
    - Position history
    - Sector exposure tracking
    """
    
    def __init__(
        self,
        ibkr: IBKRConnector,
        cache: RedisCache,
        db: TimescaleClient,
    ):
        """Initialize position tracker."""
        self.ibkr = ibkr
        self.cache = cache
        self.db = db
        
        self._positions: dict[str, Position] = {}
        self._realized_pnl: float = 0
        self._daily_realized_pnl: float = 0
        self._initial_portfolio_value: float = 0
    
    async def sync_positions(self) -> None:
        """Sync positions from IBKR."""
        ibkr_positions = await self.ibkr.get_positions()
        
        for pos in ibkr_positions:
            if pos.symbol in self._positions:
                # Update existing
                self._positions[pos.symbol].quantity = pos.quantity
                self._positions[pos.symbol].avg_cost = pos.avg_cost
            else:
                # Add new
                self._positions[pos.symbol] = Position(
                    symbol=pos.symbol,
                    quantity=pos.quantity,
                    avg_cost=pos.avg_cost,
                )
        
        # Remove positions no longer held
        ibkr_symbols = {p.symbol for p in ibkr_positions}
        for symbol in list(self._positions.keys()):
            if symbol not in ibkr_symbols:
                del self._positions[symbol]
        
        logger.info(f"Synced {len(self._positions)} positions from IBKR")
    
    async def update_prices(self) -> None:
        """Update all position prices."""
        for symbol, position in self._positions.items():
            cached = await self.cache.get_market_price(symbol)
            if cached and cached.get("price"):
                position.update_price(cached["price"])
    
    def add_position(
        self,
        symbol: str,
        quantity: float,
        price: float,
        sector: str = "",
        strategy: str = "",
    ) -> Position:
        """Add or update a position."""
        if symbol in self._positions:
            pos = self._positions[symbol]
            # Calculate new average cost
            total_cost = (pos.quantity * pos.avg_cost) + (quantity * price)
            total_qty = pos.quantity + quantity
            
            if total_qty != 0:
                pos.avg_cost = total_cost / total_qty
            pos.quantity = total_qty
        else:
            pos = Position(
                symbol=symbol,
                quantity=quantity,
                avg_cost=price,
                current_price=price,
                market_value=quantity * price,
                sector=sector,
                strategy=strategy,
            )
            self._positions[symbol] = pos
        
        logger.info(f"Position updated: {symbol} {quantity} @ {price}")
        return pos
    
    def reduce_position(
        self,
        symbol: str,
        quantity: float,
        price: float,
    ) -> float:
        """
        Reduce a position and calculate realized P&L.
        
        Returns:
            Realized P&L from the trade
        """
        if symbol not in self._positions:
            return 0.0
        
        pos = self._positions[symbol]
        
        # Calculate realized P&L
        cost_basis = quantity * pos.avg_cost
        sale_proceeds = quantity * price
        realized = sale_proceeds - cost_basis
        
        self._realized_pnl += realized
        self._daily_realized_pnl += realized
        
        # Update position
        pos.quantity -= quantity
        pos.realized_pnl += realized
        
        if pos.quantity <= 0:
            del self._positions[symbol]
            logger.info(f"Position closed: {symbol} P&L: ${realized:.2f}")
        else:
            logger.info(f"Position reduced: {symbol} -{quantity} P&L: ${realized:.2f}")
        
        return realized
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a position by symbol."""
        return self._positions.get(symbol)
    
    def get_all_positions(self) -> list[Position]:
        """Get all positions."""
        return list(self._positions.values())
    
    def get_sector_exposure(self) -> dict[str, float]:
        """Get exposure by sector."""
        exposure = {}
        for pos in self._positions.values():
            sector = pos.sector or "Unknown"
            exposure[sector] = exposure.get(sector, 0) + pos.market_value
        return exposure
    
    def get_strategy_exposure(self) -> dict[str, float]:
        """Get exposure by strategy."""
        exposure = {}
        for pos in self._positions.values():
            strategy = pos.strategy or "Unknown"
            exposure[strategy] = exposure.get(strategy, 0) + pos.market_value
        return exposure
    
    async def get_summary(self) -> PortfolioSummary:
        """Get portfolio summary."""
        # Update prices first
        await self.update_prices()
        
        positions_value = sum(p.market_value for p in self._positions.values())
        total_unrealized = sum(p.unrealized_pnl for p in self._positions.values())
        
        # Get account summary from IBKR
        account = await self.ibkr.get_account_summary()
        total_value = float(account.get("NetLiquidation", {}).get("value", 0))
        cash = float(account.get("TotalCashValue", {}).get("value", 0))
        
        if self._initial_portfolio_value == 0:
            self._initial_portfolio_value = total_value
        
        daily_pnl = total_value - self._initial_portfolio_value + self._daily_realized_pnl
        
        return PortfolioSummary(
            total_value=total_value,
            cash=cash,
            positions_value=positions_value,
            total_unrealized_pnl=total_unrealized,
            total_realized_pnl=self._realized_pnl,
            daily_pnl=daily_pnl,
            position_count=len(self._positions),
        )
    
    async def save_snapshot(self) -> None:
        """Save portfolio snapshot to database."""
        summary = await self.get_summary()
        
        await self.db.insert_portfolio_snapshot(
            total_value=summary.total_value,
            cash=summary.cash,
            positions_value=summary.positions_value,
            daily_pnl=summary.daily_pnl,
            total_pnl=summary.total_pnl,
            position_count=summary.position_count,
        )
    
    def reset_daily(self) -> None:
        """Reset daily P&L tracking."""
        self._daily_realized_pnl = 0
        self._initial_portfolio_value = 0
        logger.info("Daily P&L tracking reset")

