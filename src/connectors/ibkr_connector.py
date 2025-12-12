"""
Interactive Brokers (IBKR) connector using ib_insync.
Handles connection, market data, and order execution.
"""

import asyncio
from datetime import datetime
from typing import Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from ib_insync import IB, Contract, Stock, Option, Future, Forex, Order, Trade, MarketOrder, LimitOrder, StopOrder
from ib_insync import util
from loguru import logger

from src.config.settings import get_settings


class ConnectionStatus(str, Enum):
    """IBKR connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class OrderSide(str, Enum):
    """Order side."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order types."""
    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP LMT"


@dataclass
class Position:
    """Represents a position in the portfolio."""
    symbol: str
    quantity: float
    avg_cost: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    account: str


@dataclass
class OrderResult:
    """Result of an order submission."""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    status: str
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    error_message: str = ""


class IBKRConnector:
    """
    Interactive Brokers connector for trading operations.
    
    Uses ib_insync for async operations with TWS/IB Gateway.
    """
    
    def __init__(self):
        """Initialize the IBKR connector."""
        self.settings = get_settings()
        self.ib = IB()
        self._status = ConnectionStatus.DISCONNECTED
        self._account = ""
        self._callbacks: dict[str, list[Callable]] = {
            "on_connected": [],
            "on_disconnected": [],
            "on_error": [],
            "on_order_update": [],
            "on_position_update": [],
            "on_bar_update": [],
        }
        
        # Setup event handlers
        self.ib.connectedEvent += self._on_connected
        self.ib.disconnectedEvent += self._on_disconnected
        self.ib.errorEvent += self._on_error
        self.ib.orderStatusEvent += self._on_order_status
        self.ib.newOrderEvent += self._on_new_order
        
    @property
    def status(self) -> ConnectionStatus:
        """Get current connection status."""
        return self._status
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to IBKR."""
        return self.ib.isConnected()
    
    @property
    def account(self) -> str:
        """Get the current account ID."""
        return self._account
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a callback for an event."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event to all registered callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in callback for {event}: {e}")
    
    async def connect(self) -> bool:
        """
        Connect to IBKR TWS or IB Gateway.
        
        Returns:
            True if connection successful, False otherwise.
        """
        if self.is_connected:
            logger.info("Already connected to IBKR")
            return True
        
        self._status = ConnectionStatus.CONNECTING
        logger.info(
            f"Connecting to IBKR at {self.settings.ibkr_host}:{self.settings.ibkr_port} "
            f"(client_id={self.settings.ibkr_client_id})"
        )
        
        try:
            await self.ib.connectAsync(
                host=self.settings.ibkr_host,
                port=self.settings.ibkr_port,
                clientId=self.settings.ibkr_client_id,
                readonly=False,
            )
            
            # Get account info
            accounts = self.ib.managedAccounts()
            if accounts:
                self._account = self.settings.ibkr_account or accounts[0]
                logger.info(f"Connected to account: {self._account}")
            
            self._status = ConnectionStatus.CONNECTED
            logger.info("Successfully connected to IBKR")
            return True
            
        except Exception as e:
            self._status = ConnectionStatus.ERROR
            logger.error(f"Failed to connect to IBKR: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from IBKR."""
        if self.is_connected:
            logger.info("Disconnecting from IBKR...")
            self.ib.disconnect()
            self._status = ConnectionStatus.DISCONNECTED
            logger.info("Disconnected from IBKR")
    
    def _on_connected(self) -> None:
        """Handle connection event."""
        self._status = ConnectionStatus.CONNECTED
        logger.info("IBKR connection established")
        self._emit("on_connected")
    
    def _on_disconnected(self) -> None:
        """Handle disconnection event."""
        self._status = ConnectionStatus.DISCONNECTED
        logger.warning("IBKR connection lost")
        self._emit("on_disconnected")
    
    def _on_error(self, reqId: int, errorCode: int, errorString: str, contract: Contract = None) -> None:
        """Handle error event."""
        # Filter out non-critical messages
        if errorCode in [2104, 2106, 2158]:  # Market data farm connection messages
            logger.debug(f"IBKR info: {errorString}")
            return
        
        logger.error(f"IBKR error {errorCode}: {errorString}")
        self._emit("on_error", errorCode, errorString, contract)
    
    def _on_order_status(self, trade: Trade) -> None:
        """Handle order status update."""
        logger.info(
            f"Order {trade.order.orderId} status: {trade.orderStatus.status} "
            f"(filled: {trade.orderStatus.filled}/{trade.order.totalQuantity})"
        )
        self._emit("on_order_update", trade)
    
    def _on_new_order(self, trade: Trade) -> None:
        """Handle new order event."""
        logger.info(f"New order submitted: {trade.order.orderId}")
    
    # =========================================================================
    # Contract Creation
    # =========================================================================
    
    def create_stock_contract(
        self,
        symbol: str,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> Stock:
        """Create a stock contract."""
        return Stock(symbol, exchange, currency)
    
    def create_option_contract(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        right: str,  # 'C' or 'P'
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> Option:
        """Create an option contract."""
        return Option(symbol, expiry, strike, right, exchange, currency=currency)
    
    def create_future_contract(
        self,
        symbol: str,
        expiry: str,
        exchange: str,
        currency: str = "USD",
    ) -> Future:
        """Create a futures contract."""
        return Future(symbol, expiry, exchange, currency=currency)
    
    def create_forex_contract(
        self,
        pair: str,
        exchange: str = "IDEALPRO",
    ) -> Forex:
        """Create a forex contract."""
        return Forex(pair, exchange)
    
    async def qualify_contract(self, contract: Contract) -> Optional[Contract]:
        """Qualify a contract with IBKR to get full details."""
        try:
            qualified = await self.ib.qualifyContractsAsync(contract)
            if qualified:
                return qualified[0]
            return None
        except Exception as e:
            logger.error(f"Failed to qualify contract {contract.symbol}: {e}")
            return None
    
    # =========================================================================
    # Market Data
    # =========================================================================
    
    async def get_market_price(self, contract: Contract) -> Optional[float]:
        """Get the current market price for a contract."""
        try:
            ticker = self.ib.reqMktData(contract, '', False, False)
            await asyncio.sleep(2)  # Wait for data
            
            price = ticker.marketPrice()
            self.ib.cancelMktData(contract)
            
            if price and price > 0:
                return price
            return None
        except Exception as e:
            logger.error(f"Failed to get market price for {contract.symbol}: {e}")
            return None
    
    async def get_historical_data(
        self,
        contract: Contract,
        duration: str = "1 D",
        bar_size: str = "1 min",
        what_to_show: str = "TRADES",
    ) -> list:
        """
        Get historical bar data.
        
        Args:
            contract: The contract to get data for
            duration: Duration string (e.g., "1 D", "1 W", "1 M")
            bar_size: Bar size (e.g., "1 min", "5 mins", "1 hour", "1 day")
            what_to_show: Data type (TRADES, MIDPOINT, BID, ASK)
            
        Returns:
            List of bar data
        """
        try:
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=True,
                formatDate=1,
            )
            return bars
        except Exception as e:
            logger.error(f"Failed to get historical data for {contract.symbol}: {e}")
            return []
    
    def subscribe_market_data(
        self,
        contract: Contract,
        callback: Callable,
    ) -> None:
        """Subscribe to real-time market data updates."""
        ticker = self.ib.reqMktData(contract, '', False, False)
        ticker.updateEvent += callback
    
    def unsubscribe_market_data(self, contract: Contract) -> None:
        """Unsubscribe from market data."""
        self.ib.cancelMktData(contract)
    
    # =========================================================================
    # Order Execution
    # =========================================================================
    
    async def submit_market_order(
        self,
        contract: Contract,
        side: OrderSide,
        quantity: float,
    ) -> OrderResult:
        """Submit a market order."""
        order = MarketOrder(
            action=side.value,
            totalQuantity=quantity,
        )
        return await self._submit_order(contract, order)
    
    async def submit_limit_order(
        self,
        contract: Contract,
        side: OrderSide,
        quantity: float,
        limit_price: float,
    ) -> OrderResult:
        """Submit a limit order."""
        order = LimitOrder(
            action=side.value,
            totalQuantity=quantity,
            lmtPrice=limit_price,
        )
        return await self._submit_order(contract, order)
    
    async def submit_stop_order(
        self,
        contract: Contract,
        side: OrderSide,
        quantity: float,
        stop_price: float,
    ) -> OrderResult:
        """Submit a stop order."""
        order = StopOrder(
            action=side.value,
            totalQuantity=quantity,
            stopPrice=stop_price,
        )
        return await self._submit_order(contract, order)
    
    async def _submit_order(self, contract: Contract, order: Order) -> OrderResult:
        """Internal method to submit an order."""
        try:
            trade = self.ib.placeOrder(contract, order)
            
            # Wait briefly for initial status
            await asyncio.sleep(0.5)
            
            return OrderResult(
                order_id=str(trade.order.orderId),
                symbol=contract.symbol,
                side=OrderSide(order.action),
                quantity=order.totalQuantity,
                order_type=OrderType(order.orderType),
                status=trade.orderStatus.status,
                filled_qty=trade.orderStatus.filled,
                avg_fill_price=trade.orderStatus.avgFillPrice,
            )
        except Exception as e:
            logger.error(f"Failed to submit order for {contract.symbol}: {e}")
            return OrderResult(
                order_id="",
                symbol=contract.symbol,
                side=OrderSide(order.action),
                quantity=order.totalQuantity,
                order_type=OrderType(order.orderType),
                status="Error",
                error_message=str(e),
            )
    
    async def cancel_order(self, order_id: int) -> bool:
        """Cancel an open order."""
        try:
            for trade in self.ib.openTrades():
                if trade.order.orderId == order_id:
                    self.ib.cancelOrder(trade.order)
                    logger.info(f"Cancelled order {order_id}")
                    return True
            logger.warning(f"Order {order_id} not found in open orders")
            return False
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def cancel_all_orders(self) -> int:
        """Cancel all open orders."""
        count = 0
        for trade in self.ib.openTrades():
            try:
                self.ib.cancelOrder(trade.order)
                count += 1
            except Exception as e:
                logger.error(f"Failed to cancel order {trade.order.orderId}: {e}")
        logger.info(f"Cancelled {count} orders")
        return count
    
    # =========================================================================
    # Portfolio & Account
    # =========================================================================
    
    async def get_positions(self) -> list[Position]:
        """Get all current positions."""
        positions = []
        for pos in self.ib.positions():
            if pos.position != 0:
                positions.append(Position(
                    symbol=pos.contract.symbol,
                    quantity=pos.position,
                    avg_cost=pos.avgCost,
                    market_price=0.0,  # Would need market data subscription
                    market_value=pos.position * pos.avgCost,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    account=pos.account,
                ))
        return positions
    
    async def get_account_summary(self) -> dict[str, Any]:
        """Get account summary."""
        summary = {}
        for item in self.ib.accountSummary():
            if item.account == self._account:
                summary[item.tag] = {
                    "value": item.value,
                    "currency": item.currency,
                }
        return summary
    
    async def get_portfolio_value(self) -> float:
        """Get total portfolio value."""
        summary = await self.get_account_summary()
        if "NetLiquidation" in summary:
            return float(summary["NetLiquidation"]["value"])
        return 0.0
    
    async def get_buying_power(self) -> float:
        """Get available buying power."""
        summary = await self.get_account_summary()
        if "BuyingPower" in summary:
            return float(summary["BuyingPower"]["value"])
        return 0.0
    
    async def close_all_positions(self) -> list[OrderResult]:
        """Close all open positions with market orders."""
        results = []
        positions = await self.get_positions()
        
        for pos in positions:
            contract = self.create_stock_contract(pos.symbol)
            side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY
            quantity = abs(pos.quantity)
            
            result = await self.submit_market_order(contract, side, quantity)
            results.append(result)
            logger.info(f"Closing position: {pos.symbol} {quantity} shares")
        
        return results

