"""
Interactive Brokers (IBKR) Broker Integration.

Connects to TWS (Trader Workstation) or IB Gateway using ib_insync.

Requirements:
- TWS or IB Gateway running
- API enabled in TWS: Configure → API → Settings
- Socket port: 7497 (TWS paper), 7496 (TWS live), 4002 (Gateway paper), 4001 (Gateway live)

IMPORTANT: TWS/Gateway Daily Restart
- TWS disconnects daily around 11:45 PM ET and restarts
- Configure TWS: Configure → Settings → Lock and Exit → Auto restart
- Set "Auto restart time" to a time that works for you (e.g., 11:45 PM)
- The BrokerRegistry has auto-reconnection that will reconnect when TWS comes back
- IB Gateway is recommended for 24/7 operation as it's more stable
"""

import asyncio
import os
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, List, Dict, Any

from loguru import logger

from src.brokers.base import (
    BaseBroker, BrokerType, Position, Order, AccountInfo,
    OrderStatus, OrderType, OrderSide
)

# Thread pool for blocking IB operations - use single worker to prevent concurrent access
_ib_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ibkr")

# Global lock for IBKR operations to prevent concurrent API calls
_ibkr_lock = threading.Lock()


def _resolve_host(host: str) -> str:
    """
    Resolve host for Docker environment.
    If running in Docker and host is 127.0.0.1/localhost, use host.docker.internal
    """
    in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', '') == 'true'
    
    if in_docker and host in ('127.0.0.1', 'localhost'):
        resolved = 'host.docker.internal'
        logger.info(f"Running in Docker, resolving {host} to {resolved}")
        return resolved
    
    return host


class IBKRBroker(BaseBroker):
    """
    Interactive Brokers broker implementation using ib_insync.
    
    TWS/Gateway must be running with API enabled.
    
    Ports:
    - 7497: TWS Paper Trading
    - 7496: TWS Live Trading
    - 4002: IB Gateway Paper Trading
    - 4001: IB Gateway Live Trading
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        account_id: str = "",
        timeout: int = 60,  # Increased from 30 to 60 seconds
        readonly: bool = False,
        max_retries: int = 3,
        **kwargs
    ):
        super().__init__(BrokerType.IBKR)
        # Resolve host for Docker environment
        self.host = _resolve_host(host)
        self.port = port
        self.client_id = client_id
        self.account_id = account_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.readonly = readonly
        self._ib = None
        self._error_message = None
        
        # Caching to prevent excessive API calls
        self._account_cache: Optional[List[AccountInfo]] = None
        self._account_cache_time: Optional[datetime] = None
        self._account_cache_ttl = 10  # Cache for 10 seconds
        
        self._positions_cache: Optional[List[Position]] = None
        self._positions_cache_time: Optional[datetime] = None
        self._positions_cache_ttl = 5  # Cache for 5 seconds
        
        # Async lock for coordinating calls - store both lock and its event loop
        self._async_lock: Optional[asyncio.Lock] = None
        self._async_lock_loop: Optional[asyncio.AbstractEventLoop] = None
    
    def _connect_sync(self) -> bool:
        """
        Synchronous connect method to be run in executor.
        ib_insync requires its own event loop management.
        Includes retry logic for robustness.
        """
        import time
        
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                from ib_insync import IB, util
                
                # Enable nested event loops for ib_insync
                util.startLoop()
                
                # Clean up any existing connection
                if self._ib:
                    try:
                        self._ib.disconnect()
                    except:
                        pass
                
                self._ib = IB()
                
                logger.info(f"Attempting IBKR connection to {self.host}:{self.port} (attempt {attempt}/{self.max_retries})")
                
                # ib_insync connect is synchronous when called directly
                self._ib.connect(
                    self.host,
                    self.port,
                    clientId=self.client_id,
                    timeout=self.timeout,
                    readonly=self.readonly
                )
                
                if self._ib.isConnected():
                    # Get account ID if not provided
                    if not self.account_id:
                        accounts = self._ib.managedAccounts()
                        if accounts:
                            self.account_id = accounts[0]
                    
                    logger.info(f"Connected to IBKR - Account: {self.account_id}")
                    return True
                else:
                    logger.warning(f"IBKR connect attempt {attempt} returned but isConnected() is False")
                    last_error = "Connection returned but not connected"
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"IBKR connection attempt {attempt} failed: {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                wait_time = min(2 ** attempt, 10)  # 2s, 4s, 8s max 10s
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        logger.error(f"All {self.max_retries} IBKR connection attempts failed. Last error: {last_error}")
        raise Exception(f"Failed to connect after {self.max_retries} attempts: {last_error}")
    
    async def connect(self) -> bool:
        """
        Connect to TWS or IB Gateway.
        
        Returns True if connected successfully.
        """
        try:
            from ib_insync import IB
            
            logger.info(f"Connecting to IBKR at {self.host}:{self.port} (client_id={self.client_id})")
            
            # First, test if the port is reachable (with retry)
            port_reachable = False
            for socket_attempt in range(3):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)  # Increased from 5 to 10 seconds
                    result = sock.connect_ex((self.host, self.port))
                    sock.close()
                    
                    if result == 0:
                        port_reachable = True
                        logger.info(f"Port {self.port} is reachable on {self.host}")
                        break
                    else:
                        logger.warning(f"Socket test attempt {socket_attempt + 1}: port not reachable (code {result})")
                except Exception as e:
                    logger.warning(f"Socket test attempt {socket_attempt + 1} failed: {e}")
                
                if socket_attempt < 2:
                    import time
                    time.sleep(2)
            
            if not port_reachable:
                self._error_message = f"Cannot reach {self.host}:{self.port}. Make sure TWS/Gateway is running and API is enabled on this port."
                logger.error(self._error_message)
                return False
            
            # Run the synchronous connect in a thread pool with timeout
            loop = asyncio.get_running_loop()
            try:
                # Total timeout: timeout * max_retries + buffer for retries
                total_timeout = self.timeout * self.max_retries + 30
                
                connected = await asyncio.wait_for(
                    loop.run_in_executor(_ib_executor, self._connect_sync),
                    timeout=total_timeout
                )
                
                if connected:
                    self._connected = True
                    return True
                else:
                    self._error_message = "Failed to connect to TWS/Gateway. Check that it's running and API is enabled."
                    return False
                    
            except asyncio.TimeoutError:
                self._error_message = f"Connection timed out after {total_timeout}s. TWS/Gateway may be slow to respond."
                logger.error(self._error_message)
                return False
            except Exception as e:
                self._error_message = f"Connection failed: {str(e)}"
                logger.error(f"IBKR connect executor error: {e}")
                return False
                
        except ImportError:
            self._error_message = "ib_insync not installed. Run: pip install ib_insync"
            logger.error(self._error_message)
            return False
        except ConnectionRefusedError:
            self._error_message = f"Connection refused at {self.host}:{self.port}. Make sure TWS/Gateway is running and API is enabled."
            logger.error(self._error_message)
            return False
        except Exception as e:
            self._error_message = f"Connection failed: {str(e)}"
            logger.error(f"Failed to connect to IBKR: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from IBKR."""
        if self._ib and self._ib.isConnected():
            self._ib.disconnect()
        self._ib = None
        self._connected = False
        logger.info("Disconnected from IBKR")
    
    async def health_check(self) -> bool:
        """Check IBKR connection health."""
        if not self._ib:
            return False
        return self._ib.isConnected()
    
    def _get_async_lock(self) -> asyncio.Lock:
        """Get or create async lock for the current event loop.
        
        asyncio.Lock is bound to the event loop where it was created.
        If the event loop changes (e.g., different request context), we need
        to create a new lock for the current event loop.
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create one for when we need it
            current_loop = None
        
        # Check if we need to create a new lock for the current event loop
        if self._async_lock is None or self._async_lock_loop is not current_loop:
            self._async_lock = asyncio.Lock()
            self._async_lock_loop = current_loop
        
        return self._async_lock
    
    async def get_accounts(self) -> List[AccountInfo]:
        """Get IBKR accounts with caching to prevent excessive API calls."""
        if not self._ib or not self._ib.isConnected():
            logger.warning("IBKR get_accounts called but not connected")
            return []
        
        # Check cache first
        now = datetime.now()
        if self._account_cache and self._account_cache_time:
            age = (now - self._account_cache_time).total_seconds()
            if age < self._account_cache_ttl:
                logger.debug(f"Using cached account data (age: {age:.1f}s)")
                return self._account_cache
        
        # Use async lock to prevent concurrent API calls
        lock = self._get_async_lock()
        
        # Try to acquire lock without blocking - if can't, return cached data
        if lock.locked():
            logger.debug("IBKR API call in progress, returning cached data")
            return self._account_cache or []
        
        async with lock:
            # Double-check cache after acquiring lock
            if self._account_cache and self._account_cache_time:
                age = (datetime.now() - self._account_cache_time).total_seconds()
                if age < self._account_cache_ttl:
                    return self._account_cache
            
            try:
                logger.debug(f"Fetching account summary for {self.account_id}")
                
                # Get account summary - run in executor with global lock
                def fetch_account_data():
                    with _ibkr_lock:  # Prevent concurrent IBKR API access
                        # First try accountSummary
                        summary = self._ib.accountSummary(self.account_id)
                        if summary:
                            return summary, 'summary'
                        
                        # Fall back to accountValues
                        values = self._ib.accountValues(self.account_id)
                        return values, 'values'
                
                loop = asyncio.get_event_loop()
                
                # Use the dedicated IBKR executor
                data, data_type = await asyncio.wait_for(
                    loop.run_in_executor(_ib_executor, fetch_account_data),
                    timeout=15  # 15 second timeout for account fetch
                )
                
                # Parse data into dict
                summary_dict = {}
                for item in data:
                    # Handle both AccountValue and AccountSummary objects
                    tag = getattr(item, 'tag', None)
                    value = getattr(item, 'value', None)
                    if tag and value:
                        summary_dict[tag] = value
                
                logger.debug(f"IBKR account data ({data_type}): {len(summary_dict)} fields")
                
                # Log key values for debugging
                net_liq = summary_dict.get("NetLiquidation", summary_dict.get("NetLiquidationByCurrency", "0"))
                cash = summary_dict.get("TotalCashValue", summary_dict.get("CashBalance", "0"))
                buying_power = summary_dict.get("BuyingPower", summary_dict.get("AvailableFunds", "0"))
                
                logger.info(f"IBKR Account {self.account_id}: NetLiq={net_liq}, Cash={cash}, BuyingPower={buying_power}")
                
                # Parse values safely
                def parse_float(val, default=0.0):
                    if val is None:
                        return default
                    try:
                        return float(str(val).replace(',', ''))
                    except (ValueError, TypeError):
                        return default
                
                equity = parse_float(summary_dict.get("NetLiquidation") or summary_dict.get("NetLiquidationByCurrency"))
                cash_val = parse_float(summary_dict.get("TotalCashValue") or summary_dict.get("CashBalance"))
                bp = parse_float(summary_dict.get("BuyingPower") or summary_dict.get("AvailableFunds"))
                portfolio = parse_float(summary_dict.get("GrossPositionValue") or summary_dict.get("StockMarketValue"))
                
                result = [AccountInfo(
                    account_id=self.account_id,
                    broker=BrokerType.IBKR,
                    account_type=summary_dict.get("AccountType", "Paper" if "D" in self.account_id else "Live"),
                    buying_power=bp,
                    cash=cash_val,
                    portfolio_value=portfolio,
                    equity=equity,
                    margin_used=parse_float(summary_dict.get("MaintMarginReq")),
                    margin_available=parse_float(summary_dict.get("AvailableFunds")),
                    day_trades_remaining=int(parse_float(summary_dict.get("DayTradesRemaining", 3))),
                    is_pattern_day_trader=summary_dict.get("DayTradesRemaining", "3") == "0",
                    currency="USD",
                    last_updated=datetime.now()
                )]
                
                # Update cache
                self._account_cache = result
                self._account_cache_time = datetime.now()
                
                return result
                
            except asyncio.TimeoutError:
                logger.warning("IBKR get_accounts timed out, returning cached data")
                return self._account_cache or []
            except Exception as e:
                logger.error(f"Error getting IBKR account: {e}")
                # Return cached data on error
                if self._account_cache:
                    logger.info("Returning cached account data due to error")
                    return self._account_cache
                return []
    
    async def get_account_info(self, account_id: str) -> AccountInfo:
        """Get IBKR account info."""
        accounts = await self.get_accounts()
        if accounts:
            return accounts[0]
        raise ValueError("No account found")
    
    async def get_buying_power(self, account_id: str) -> float:
        """Get available buying power."""
        accounts = await self.get_accounts()
        if accounts:
            return accounts[0].buying_power
        return 0.0
    
    async def get_positions(self, account_id: str) -> List[Position]:
        """Get all open positions with caching."""
        if not self._ib or not self._ib.isConnected():
            return []
        
        # Check cache first
        now = datetime.now()
        if self._positions_cache and self._positions_cache_time:
            age = (now - self._positions_cache_time).total_seconds()
            if age < self._positions_cache_ttl:
                logger.debug(f"Using cached positions data (age: {age:.1f}s)")
                return self._positions_cache
        
        # Use async lock to prevent concurrent API calls
        lock = self._get_async_lock()
        
        if lock.locked():
            logger.debug("IBKR API call in progress, returning cached positions")
            return self._positions_cache or []
        
        async with lock:
            try:
                loop = asyncio.get_event_loop()
                
                def fetch_portfolio():
                    with _ibkr_lock:
                        return self._ib.portfolio(self.account_id)
                
                portfolio_items = await asyncio.wait_for(
                    loop.run_in_executor(_ib_executor, fetch_portfolio),
                    timeout=15
                )
                
                positions = []
                for item in portfolio_items:
                    quantity = float(item.position)
                    avg_cost = float(item.averageCost)
                    current_price = float(item.marketPrice)
                    market_value = float(item.marketValue)
                    unrealized_pnl = float(item.unrealizedPNL)
                    
                    positions.append(Position(
                        symbol=item.contract.symbol,
                        quantity=quantity,
                        avg_cost=avg_cost,
                        current_price=current_price,
                        market_value=market_value,
                        unrealized_pnl=unrealized_pnl,
                        unrealized_pnl_pct=(unrealized_pnl / (quantity * avg_cost) * 100) if quantity * avg_cost != 0 else 0,
                        side="long" if quantity > 0 else "short",
                        broker=BrokerType.IBKR,
                        account_id=account_id,
                        last_updated=datetime.now()
                    ))
                
                # Update cache
                self._positions_cache = positions
                self._positions_cache_time = datetime.now()
                
                return positions
                
            except asyncio.TimeoutError:
                logger.warning("IBKR get_positions timed out, returning cached data")
                return self._positions_cache or []
            except Exception as e:
                logger.error(f"Error getting IBKR positions: {e}")
                if self._positions_cache:
                    return self._positions_cache
                return []
    
    async def get_position(self, account_id: str, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        positions = await self.get_positions(account_id)
        for p in positions:
            if p.symbol.upper() == symbol.upper():
                return p
        return None
    
    async def submit_order(
        self,
        account_id: str,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "DAY",
        **kwargs
    ) -> Order:
        """Submit an order to IBKR."""
        if not self._ib or not self._ib.isConnected():
            raise ConnectionError("Not connected to IBKR")
        
        lock = self._get_async_lock()
        async with lock:
            try:
                from ib_insync import Stock, MarketOrder, LimitOrder, StopOrder, StopLimitOrder
                
                loop = asyncio.get_event_loop()
                
                # Create contract
                contract = Stock(symbol.upper(), "SMART", "USD")
                
                # Create order based on type
                action = "BUY" if side == OrderSide.BUY else "SELL"
                
                if order_type == OrderType.MARKET:
                    ib_order = MarketOrder(action, quantity)
                elif order_type == OrderType.LIMIT:
                    ib_order = LimitOrder(action, quantity, limit_price)
                elif order_type == OrderType.STOP:
                    ib_order = StopOrder(action, quantity, stop_price)
                elif order_type == OrderType.STOP_LIMIT:
                    ib_order = StopLimitOrder(action, quantity, limit_price, stop_price)
                else:
                    raise ValueError(f"Unsupported order type: {order_type}")
                
                ib_order.tif = time_in_force.upper()
                
                # Place order with lock
                def place_order():
                    with _ibkr_lock:
                        return self._ib.placeOrder(contract, ib_order)
                
                trade = await asyncio.wait_for(
                    loop.run_in_executor(_ib_executor, place_order),
                    timeout=30
                )
                
                logger.info(f"IBKR order submitted: {trade.order.orderId} - {action} {quantity} {symbol}")
                
                # Invalidate caches after order
                self._account_cache = None
                self._positions_cache = None
                
                return Order(
                    order_id=str(trade.order.orderId),
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    limit_price=limit_price,
                    stop_price=stop_price,
                    status=OrderStatus.SUBMITTED,
                    filled_quantity=0,
                    avg_fill_price=None,
                    broker=BrokerType.IBKR,
                    account_id=account_id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
            except Exception as e:
                logger.error(f"Error submitting IBKR order: {e}")
                raise
    
    async def cancel_order(self, account_id: str, order_id: str) -> bool:
        """Cancel an open order."""
        if not self._ib or not self._ib.isConnected():
            return False
        
        try:
            loop = asyncio.get_event_loop()
            
            # Find the order
            orders = self._ib.openOrders()
            for order in orders:
                if str(order.orderId) == order_id:
                    await loop.run_in_executor(
                        None,
                        lambda: self._ib.cancelOrder(order)
                    )
                    logger.info(f"IBKR order cancelled: {order_id}")
                    return True
            
            logger.warning(f"Order not found: {order_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling IBKR order: {e}")
            return False
    
    async def get_order(self, account_id: str, order_id: str) -> Optional[Order]:
        """Get order details."""
        orders = await self.get_open_orders(account_id)
        for o in orders:
            if o.order_id == order_id:
                return o
        return None
    
    async def get_open_orders(self, account_id: str) -> List[Order]:
        """Get all open orders."""
        if not self._ib or not self._ib.isConnected():
            return []
        
        try:
            loop = asyncio.get_event_loop()
            
            trades = await loop.run_in_executor(
                None,
                self._ib.openTrades
            )
            
            orders = []
            for trade in trades:
                orders.append(self._convert_trade(trade, account_id))
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting IBKR open orders: {e}")
            return []
    
    async def get_order_history(
        self,
        account_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Order]:
        """Get order history."""
        if not self._ib or not self._ib.isConnected():
            return []
        
        try:
            loop = asyncio.get_event_loop()
            
            trades = await loop.run_in_executor(
                None,
                self._ib.trades
            )
            
            orders = []
            for trade in trades[:limit]:
                orders.append(self._convert_trade(trade, account_id))
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting IBKR order history: {e}")
            return []
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote from IBKR."""
        if not self._ib or not self._ib.isConnected():
            return None
        
        try:
            from ib_insync import Stock
            
            loop = asyncio.get_event_loop()
            
            contract = Stock(symbol.upper(), "SMART", "USD")
            
            # Qualify the contract
            await loop.run_in_executor(
                None,
                lambda: self._ib.qualifyContracts(contract)
            )
            
            # Get ticker
            ticker = self._ib.reqMktData(contract, snapshot=True)
            await loop.run_in_executor(None, lambda: self._ib.sleep(1))
            
            return {
                "symbol": symbol.upper(),
                "bid": float(ticker.bid) if ticker.bid else 0,
                "ask": float(ticker.ask) if ticker.ask else 0,
                "last": float(ticker.last) if ticker.last else 0,
                "volume": int(ticker.volume) if ticker.volume else 0,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting IBKR quote: {e}")
            return None
    
    def _convert_trade(self, trade, account_id: str) -> Order:
        """Convert IB Trade to our Order type."""
        order = trade.order
        contract = trade.contract
        
        # Map order status
        status_map = {
            "PendingSubmit": OrderStatus.PENDING,
            "PendingCancel": OrderStatus.PENDING,
            "PreSubmitted": OrderStatus.PENDING,
            "Submitted": OrderStatus.SUBMITTED,
            "Cancelled": OrderStatus.CANCELLED,
            "Filled": OrderStatus.FILLED,
            "Inactive": OrderStatus.REJECTED,
        }
        
        # Map order type
        type_map = {
            "MKT": OrderType.MARKET,
            "LMT": OrderType.LIMIT,
            "STP": OrderType.STOP,
            "STP LMT": OrderType.STOP_LIMIT,
        }
        
        return Order(
            order_id=str(order.orderId),
            symbol=contract.symbol,
            side=OrderSide.BUY if order.action == "BUY" else OrderSide.SELL,
            order_type=type_map.get(order.orderType, OrderType.MARKET),
            quantity=float(order.totalQuantity),
            limit_price=float(order.lmtPrice) if order.lmtPrice else None,
            stop_price=float(order.auxPrice) if order.auxPrice else None,
            status=status_map.get(trade.orderStatus.status, OrderStatus.PENDING),
            filled_quantity=float(trade.orderStatus.filled),
            avg_fill_price=float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None,
            broker=BrokerType.IBKR,
            account_id=account_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

