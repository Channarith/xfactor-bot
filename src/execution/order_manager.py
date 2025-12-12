"""
Order Manager for executing trades.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable
from enum import Enum

from loguru import logger

from src.connectors.ibkr_connector import IBKRConnector, OrderSide, OrderResult
from src.risk.risk_manager import RiskManager, RiskCheckResult
from src.data.redis_cache import RedisCache
from src.data.timescale_client import TimescaleClient
from src.utils.helpers import generate_order_id


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass
class Order:
    """Internal order representation."""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: str
    status: OrderStatus = OrderStatus.PENDING
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_qty: float = 0
    avg_fill_price: float = 0
    strategy: str = ""
    signal_strength: float = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    error_message: str = ""
    
    @property
    def is_complete(self) -> bool:
        return self.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED)
    
    @property
    def remaining_qty(self) -> float:
        return self.quantity - self.filled_qty


class OrderManager:
    """
    Manages order execution and lifecycle.
    
    Features:
    - Risk check before submission
    - Order tracking and status updates
    - Trade logging and audit trail
    - Order throttling
    """
    
    def __init__(
        self,
        ibkr: IBKRConnector,
        risk_manager: RiskManager,
        cache: RedisCache,
        db: TimescaleClient,
    ):
        """Initialize order manager."""
        self.ibkr = ibkr
        self.risk = risk_manager
        self.cache = cache
        self.db = db
        
        self._orders: dict[str, Order] = {}
        self._callbacks: list[Callable] = []
        
        # Register for IBKR order updates
        self.ibkr.register_callback("on_order_update", self._on_order_update)
    
    def register_callback(self, callback: Callable[[Order], None]) -> None:
        """Register callback for order updates."""
        self._callbacks.append(callback)
    
    async def submit_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        strategy: str = "",
        signal_strength: float = 0,
    ) -> Order:
        """
        Submit a market order.
        
        Args:
            symbol: Stock symbol
            side: BUY or SELL
            quantity: Order quantity
            strategy: Strategy name
            signal_strength: Signal strength (0-1)
            
        Returns:
            Order object
        """
        order = Order(
            order_id=generate_order_id(),
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="MKT",
            strategy=strategy,
            signal_strength=signal_strength,
        )
        
        return await self._execute_order(order)
    
    async def submit_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        limit_price: float,
        strategy: str = "",
        signal_strength: float = 0,
    ) -> Order:
        """Submit a limit order."""
        order = Order(
            order_id=generate_order_id(),
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="LMT",
            limit_price=limit_price,
            strategy=strategy,
            signal_strength=signal_strength,
        )
        
        return await self._execute_order(order)
    
    async def submit_stop_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        stop_price: float,
        strategy: str = "",
    ) -> Order:
        """Submit a stop order."""
        order = Order(
            order_id=generate_order_id(),
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="STP",
            stop_price=stop_price,
            strategy=strategy,
        )
        
        return await self._execute_order(order)
    
    async def _execute_order(self, order: Order) -> Order:
        """Execute an order after risk checks."""
        self._orders[order.order_id] = order
        
        try:
            # Check order throttle
            order_count = await self.cache.increment_order_count()
            if order_count > 500:  # Max 500 orders per day
                order.status = OrderStatus.REJECTED
                order.error_message = "Daily order limit exceeded"
                return order
            
            # Get estimated price for risk check
            price = order.limit_price or order.stop_price
            if not price:
                # Get market price
                cached = await self.cache.get_market_price(order.symbol)
                price = cached.get("price", 100) if cached else 100
            
            # Risk check
            decision = self.risk.check_order(
                symbol=order.symbol,
                quantity=order.quantity,
                price=price,
                side=order.side.value,
            )
            
            if decision.result == RiskCheckResult.REJECTED:
                order.status = OrderStatus.REJECTED
                order.error_message = decision.reason
                logger.warning(f"Order rejected: {order.symbol} - {decision.reason}")
                return order
            
            if decision.result == RiskCheckResult.REDUCED:
                order.quantity = decision.approved_quantity
                logger.info(f"Order reduced: {order.symbol} {decision.original_quantity} -> {decision.approved_quantity}")
            
            # Submit to IBKR
            contract = self.ibkr.create_stock_contract(order.symbol)
            
            if order.order_type == "MKT":
                result = await self.ibkr.submit_market_order(contract, order.side, order.quantity)
            elif order.order_type == "LMT":
                result = await self.ibkr.submit_limit_order(contract, order.side, order.quantity, order.limit_price)
            elif order.order_type == "STP":
                result = await self.ibkr.submit_stop_order(contract, order.side, order.quantity, order.stop_price)
            else:
                order.status = OrderStatus.ERROR
                order.error_message = f"Unknown order type: {order.order_type}"
                return order
            
            # Update order with result
            order.submitted_at = datetime.utcnow()
            order.status = OrderStatus.SUBMITTED
            order.filled_qty = result.filled_qty
            order.avg_fill_price = result.avg_fill_price
            
            if result.status == "Filled":
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.utcnow()
            elif result.error_message:
                order.status = OrderStatus.ERROR
                order.error_message = result.error_message
            
            logger.info(f"Order submitted: {order.order_id} {order.symbol} {order.side.value} {order.quantity}")
            
            # Log to database
            await self._log_order(order)
            
            return order
            
        except Exception as e:
            order.status = OrderStatus.ERROR
            order.error_message = str(e)
            logger.error(f"Order execution failed: {e}")
            return order
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        order = self._orders.get(order_id)
        if not order:
            return False
        
        if order.is_complete:
            return False
        
        # Cancel in IBKR
        ibkr_id = int(order_id.split("-")[-1]) if "-" in order_id else 0
        success = await self.ibkr.cancel_order(ibkr_id)
        
        if success:
            order.status = OrderStatus.CANCELLED
            logger.info(f"Order cancelled: {order_id}")
        
        return success
    
    async def cancel_all_orders(self) -> int:
        """Cancel all open orders."""
        count = await self.ibkr.cancel_all_orders()
        
        for order in self._orders.values():
            if not order.is_complete:
                order.status = OrderStatus.CANCELLED
        
        return count
    
    def _on_order_update(self, trade) -> None:
        """Handle order update from IBKR."""
        # Find matching order
        for order in self._orders.values():
            if order.symbol == trade.contract.symbol and order.status == OrderStatus.SUBMITTED:
                order.filled_qty = trade.orderStatus.filled
                order.avg_fill_price = trade.orderStatus.avgFillPrice
                
                if trade.orderStatus.status == "Filled":
                    order.status = OrderStatus.FILLED
                    order.filled_at = datetime.utcnow()
                elif trade.orderStatus.status == "Cancelled":
                    order.status = OrderStatus.CANCELLED
                
                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(order)
                    except Exception as e:
                        logger.error(f"Error in order callback: {e}")
                
                break
    
    async def _log_order(self, order: Order) -> None:
        """Log order to database."""
        await self.db.insert_trade(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            price=order.avg_fill_price or order.limit_price or 0,
            strategy=order.strategy,
            signal_strength=order.signal_strength,
        )
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self._orders.get(order_id)
    
    def get_open_orders(self) -> list[Order]:
        """Get all open orders."""
        return [o for o in self._orders.values() if not o.is_complete]
    
    def get_orders_by_symbol(self, symbol: str) -> list[Order]:
        """Get all orders for a symbol."""
        return [o for o in self._orders.values() if o.symbol == symbol]

