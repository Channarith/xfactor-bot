"""
Alpaca Broker Integration.

Alpaca provides:
- Commission-free trading
- Excellent REST and WebSocket APIs
- Paper trading environment (always online, no daily restarts)
- Fractional shares
- Extended hours trading
- Crypto trading

Advantages over IBKR:
- Cloud-based API (no local software needed)
- No daily restarts
- Simpler setup (just API keys)
- Modern REST API

Get API keys: https://app.alpaca.markets/
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx

from loguru import logger

from src.brokers.base import (
    BaseBroker, BrokerType, Position, Order, AccountInfo,
    OrderStatus, OrderType, OrderSide
)


class AlpacaBroker(BaseBroker):
    """
    Alpaca Markets broker implementation.
    
    Free, commission-free trading with excellent API.
    Supports stocks, ETFs, and crypto.
    
    Environment variables needed:
    - ALPACA_API_KEY
    - ALPACA_SECRET_KEY
    - ALPACA_PAPER (true/false)
    """
    
    BASE_URL_PAPER = "https://paper-api.alpaca.markets"
    BASE_URL_LIVE = "https://api.alpaca.markets"
    DATA_URL = "https://data.alpaca.markets"
    
    # Timeouts
    CONNECT_TIMEOUT = 30  # seconds
    REQUEST_TIMEOUT = 15  # seconds
    
    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        paper: bool = True,
        **kwargs
    ):
        super().__init__(BrokerType.ALPACA)
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        self.base_url = self.BASE_URL_PAPER if paper else self.BASE_URL_LIVE
        self._client = None
        self._trading_client = None
        self._data_client = None
        self._error_message: Optional[str] = None
        
        # Caching to prevent excessive API calls
        self._account_cache: Optional[List[AccountInfo]] = None
        self._account_cache_time: Optional[datetime] = None
        self._account_cache_ttl = 15  # seconds - increased to reduce API calls
        
        self._positions_cache: Optional[List[Position]] = None
        self._positions_cache_time: Optional[datetime] = None
        self._positions_cache_ttl = 10  # seconds - increased to reduce API calls
        
        # Connection tracking
        self._last_successful_call: Optional[datetime] = None
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5
        
        # Async lock to prevent concurrent API calls (connection pool exhaustion)
        self._api_lock = asyncio.Lock()
        
        logger.debug(f"AlpacaBroker initialized: paper={paper}, base_url={self.base_url}")
    
    async def connect(self) -> bool:
        """Connect to Alpaca API with timeout handling."""
        logger.info(f"Connecting to Alpaca {'Paper' if self.paper else 'Live'} trading...")
        
        # Validate API keys
        if not self.api_key or not self.secret_key:
            self._error_message = "API key and secret key are required"
            logger.error(self._error_message)
            return False
        
        if len(self.api_key) < 10:
            self._error_message = "API key appears invalid (too short)"
            logger.error(self._error_message)
            return False
        
        try:
            # Try to import alpaca-py
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import StockHistoricalDataClient
            
            logger.debug("Creating Alpaca trading client...")
            
            self._trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=self.paper
            )
            
            self._data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.secret_key
            )
            
            # Test connection by getting account with timeout
            logger.debug("Testing connection by fetching account...")
            
            try:
                # Wrap synchronous call in executor with timeout
                loop = asyncio.get_event_loop()
                account = await asyncio.wait_for(
                    loop.run_in_executor(None, self._trading_client.get_account),
                    timeout=self.CONNECT_TIMEOUT
                )
            except asyncio.TimeoutError:
                self._error_message = f"Connection timed out after {self.CONNECT_TIMEOUT}s"
                logger.error(self._error_message)
                return False
            
            self._connected = True
            self._last_successful_call = datetime.now()
            self._consecutive_failures = 0
            
            # Log account details
            logger.info(f"✅ Connected to Alpaca {'Paper' if self.paper else 'Live'}")
            logger.info(f"   Account: {account.account_number}")
            logger.info(f"   Status: {account.status}")
            logger.info(f"   Equity: ${float(account.equity):,.2f}")
            logger.info(f"   Buying Power: ${float(account.buying_power):,.2f}")
            logger.info(f"   Cash: ${float(account.cash):,.2f}")
            logger.info(f"   PDT: {account.pattern_day_trader}")
            
            return True
            
        except ImportError as e:
            self._error_message = "alpaca-py not installed. Run: pip install alpaca-py"
            logger.error(self._error_message)
            return False
        except Exception as e:
            error_str = str(e)
            
            # Parse common errors
            if "forbidden" in error_str.lower() or "401" in error_str:
                self._error_message = "Invalid API key or secret. Check your credentials."
            elif "not found" in error_str.lower() or "404" in error_str:
                self._error_message = "Account not found. Check your API key."
            elif "rate limit" in error_str.lower() or "429" in error_str:
                self._error_message = "Rate limited. Please wait and try again."
            elif "timeout" in error_str.lower():
                self._error_message = "Connection timed out. Check your network."
            else:
                self._error_message = f"Connection failed: {error_str}"
            
            logger.error(f"Failed to connect to Alpaca: {self._error_message}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Alpaca."""
        self._trading_client = None
        self._data_client = None
        self._connected = False
        self._account_cache = None
        self._positions_cache = None
        logger.info("Disconnected from Alpaca")
    
    async def health_check(self) -> bool:
        """Check Alpaca connection health with detailed logging."""
        if not self._trading_client:
            logger.debug("Health check failed: No trading client")
            return False
        
        try:
            loop = asyncio.get_event_loop()
            account = await asyncio.wait_for(
                loop.run_in_executor(None, self._trading_client.get_account),
                timeout=self.REQUEST_TIMEOUT
            )
            
            self._last_successful_call = datetime.now()
            self._consecutive_failures = 0
            
            logger.debug(f"Alpaca health check OK - Account status: {account.status}")
            return True
            
        except asyncio.TimeoutError:
            self._consecutive_failures += 1
            logger.warning(f"Alpaca health check timed out (failures: {self._consecutive_failures})")
            return self._consecutive_failures < self._max_consecutive_failures
            
        except Exception as e:
            self._consecutive_failures += 1
            logger.warning(f"Alpaca health check failed: {e} (failures: {self._consecutive_failures})")
            return False
    
    async def get_accounts(self) -> List[AccountInfo]:
        """Get Alpaca account with caching."""
        if not self._trading_client:
            logger.warning("get_accounts called but not connected")
            return []
        
        # Check cache first (outside lock for performance)
        now = datetime.now()
        if self._account_cache and self._account_cache_time:
            age = (now - self._account_cache_time).total_seconds()
            if age < self._account_cache_ttl:
                logger.debug(f"Using cached account data (age: {age:.1f}s)")
                return self._account_cache
        
        # Use lock to prevent concurrent API calls (connection pool exhaustion)
        async with self._api_lock:
            # Double-check cache after acquiring lock
            now = datetime.now()
            if self._account_cache and self._account_cache_time:
                age = (now - self._account_cache_time).total_seconds()
                if age < self._account_cache_ttl:
                    return self._account_cache
            
            try:
                logger.debug("Fetching Alpaca account data...")
                
                loop = asyncio.get_event_loop()
                account = await asyncio.wait_for(
                    loop.run_in_executor(None, self._trading_client.get_account),
                    timeout=self.REQUEST_TIMEOUT
                )
                
                self._last_successful_call = datetime.now()
                self._consecutive_failures = 0
                
                # Alpaca returns some fields as strings - convert them
                multiplier = int(account.multiplier) if account.multiplier else 1
                
                result = [AccountInfo(
                    account_id=account.account_number,
                    broker=BrokerType.ALPACA,
                    account_type="margin" if multiplier > 1 else "cash",
                    buying_power=float(account.buying_power),
                    cash=float(account.cash),
                    portfolio_value=float(account.portfolio_value),
                    equity=float(account.equity),
                    margin_used=float(account.initial_margin or 0),
                    margin_available=float(account.regt_buying_power or 0),
                    day_trades_remaining=int(account.daytrade_count) if hasattr(account, 'daytrade_count') and account.daytrade_count else 3,
                    is_pattern_day_trader=account.pattern_day_trader,
                    currency=account.currency,
                    last_updated=datetime.now()
                )]
                
                # Update cache
                self._account_cache = result
                self._account_cache_time = datetime.now()
                
                logger.debug(f"Alpaca account: equity=${float(account.equity):,.2f}, buying_power=${float(account.buying_power):,.2f}")
                
                return result
                
            except asyncio.TimeoutError:
                logger.warning("get_accounts timed out, returning cached data")
                self._consecutive_failures += 1
                return self._account_cache or []
                
            except Exception as e:
                logger.error(f"Error getting Alpaca account: {e}")
                self._consecutive_failures += 1
                return self._account_cache or []
    
    async def get_account_info(self, account_id: str) -> AccountInfo:
        """Get Alpaca account info."""
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
        if not self._trading_client:
            return []
        
        # Check cache first (outside lock for performance)
        now = datetime.now()
        if self._positions_cache is not None and self._positions_cache_time:
            age = (now - self._positions_cache_time).total_seconds()
            if age < self._positions_cache_ttl:
                logger.debug(f"Using cached positions (age: {age:.1f}s)")
                return self._positions_cache
        
        # Use lock to prevent concurrent API calls
        async with self._api_lock:
            # Double-check cache after acquiring lock
            now = datetime.now()
            if self._positions_cache is not None and self._positions_cache_time:
                age = (now - self._positions_cache_time).total_seconds()
                if age < self._positions_cache_ttl:
                    return self._positions_cache
            
            try:
                logger.debug("Fetching Alpaca positions...")
                
                loop = asyncio.get_event_loop()
                positions = await asyncio.wait_for(
                    loop.run_in_executor(None, self._trading_client.get_all_positions),
                    timeout=self.REQUEST_TIMEOUT
                )
                
                self._last_successful_call = datetime.now()
                
                result = [
                    Position(
                        symbol=p.symbol,
                        quantity=float(p.qty),
                        avg_cost=float(p.avg_entry_price),
                        current_price=float(p.current_price),
                        market_value=float(p.market_value),
                        unrealized_pnl=float(p.unrealized_pl),
                        unrealized_pnl_pct=float(p.unrealized_plpc) * 100,
                        side="long" if float(p.qty) > 0 else "short",
                        broker=BrokerType.ALPACA,
                        account_id=account_id,
                        last_updated=datetime.now()
                    )
                    for p in positions
                ]
                
                # Update cache
                self._positions_cache = result
                self._positions_cache_time = datetime.now()
                
                logger.debug(f"Alpaca positions: {len(result)} open positions")
                for p in result:
                    logger.debug(f"  {p.symbol}: {p.quantity} @ ${p.current_price:.2f} (P&L: ${p.unrealized_pnl:.2f})")
                
                return result
                
            except asyncio.TimeoutError:
                logger.warning("get_positions timed out, returning cached data")
                return self._positions_cache or []
                
            except Exception as e:
                logger.error(f"Error getting positions: {e}")
                return self._positions_cache or []
    
    async def get_position(self, account_id: str, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        if not self._trading_client:
            return None
        
        try:
            logger.debug(f"Fetching position for {symbol}...")
            
            loop = asyncio.get_event_loop()
            p = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._trading_client.get_open_position(symbol)),
                timeout=self.REQUEST_TIMEOUT
            )
            
            position = Position(
                symbol=p.symbol,
                quantity=float(p.qty),
                avg_cost=float(p.avg_entry_price),
                current_price=float(p.current_price),
                market_value=float(p.market_value),
                unrealized_pnl=float(p.unrealized_pl),
                unrealized_pnl_pct=float(p.unrealized_plpc) * 100,
                side="long" if float(p.qty) > 0 else "short",
                broker=BrokerType.ALPACA,
                account_id=account_id,
                last_updated=datetime.now()
            )
            
            logger.debug(f"Position {symbol}: {position.quantity} shares @ ${position.current_price:.2f}")
            return position
            
        except Exception as e:
            # Position not found is expected for symbols we don't hold
            if "not found" not in str(e).lower():
                logger.debug(f"No position for {symbol}: {e}")
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
        time_in_force: str = "day",
        **kwargs
    ) -> Order:
        """Submit an order to Alpaca with detailed logging."""
        if not self._trading_client:
            raise ConnectionError("Not connected to Alpaca")
        
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest
        from alpaca.trading.enums import OrderSide as AlpacaSide, TimeInForce
        
        logger.info(f"📤 Submitting Alpaca order: {side.value.upper()} {quantity} {symbol} ({order_type.value})")
        
        try:
            # Map order side
            alpaca_side = AlpacaSide.BUY if side == OrderSide.BUY else AlpacaSide.SELL
            
            # Map time in force
            tif_map = {
                "day": TimeInForce.DAY,
                "gtc": TimeInForce.GTC,
                "ioc": TimeInForce.IOC,
                "fok": TimeInForce.FOK,
            }
            alpaca_tif = tif_map.get(time_in_force.lower(), TimeInForce.DAY)
            
            # Create order request based on type
            if order_type == OrderType.MARKET:
                request = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif
                )
                logger.debug(f"Market order: {alpaca_side.value} {quantity} {symbol}")
            elif order_type == OrderType.LIMIT:
                request = LimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    limit_price=limit_price
                )
                logger.debug(f"Limit order: {alpaca_side.value} {quantity} {symbol} @ ${limit_price}")
            elif order_type == OrderType.STOP:
                request = StopOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    stop_price=stop_price
                )
                logger.debug(f"Stop order: {alpaca_side.value} {quantity} {symbol} stop @ ${stop_price}")
            elif order_type == OrderType.STOP_LIMIT:
                request = StopLimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    limit_price=limit_price,
                    stop_price=stop_price
                )
                logger.debug(f"Stop-limit order: {alpaca_side.value} {quantity} {symbol} stop @ ${stop_price} limit @ ${limit_price}")
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            # Submit order with timeout
            loop = asyncio.get_event_loop()
            order = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._trading_client.submit_order(request)),
                timeout=self.REQUEST_TIMEOUT
            )
            
            # Invalidate caches
            self._account_cache = None
            self._positions_cache = None
            
            logger.info(f"✅ Alpaca order submitted: {order.id}")
            logger.info(f"   Symbol: {order.symbol}")
            logger.info(f"   Side: {order.side.value}")
            logger.info(f"   Quantity: {order.qty}")
            logger.info(f"   Status: {order.status.value}")
            
            return Order(
                order_id=str(order.id),
                symbol=order.symbol,
                side=side,
                order_type=order_type,
                quantity=float(order.qty),
                limit_price=float(order.limit_price) if order.limit_price else None,
                stop_price=float(order.stop_price) if order.stop_price else None,
                status=self._map_order_status(order.status.value),
                filled_quantity=float(order.filled_qty) if order.filled_qty else 0,
                avg_fill_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                broker=BrokerType.ALPACA,
                account_id=account_id,
                created_at=order.created_at,
                updated_at=order.updated_at or datetime.now()
            )
            
        except asyncio.TimeoutError:
            error_msg = f"Order submission timed out after {self.REQUEST_TIMEOUT}s"
            logger.error(f"❌ {error_msg}")
            raise ConnectionError(error_msg)
            
        except Exception as e:
            error_str = str(e)
            
            # Parse common order errors
            if "insufficient" in error_str.lower():
                logger.error(f"❌ Insufficient buying power for {quantity} {symbol}")
            elif "not tradeable" in error_str.lower():
                logger.error(f"❌ {symbol} is not tradeable")
            elif "market closed" in error_str.lower() or "market is closed" in error_str.lower():
                logger.error(f"❌ Market is closed - cannot submit order")
            else:
                logger.error(f"❌ Order failed: {error_str}")
            
            raise
    
    async def cancel_order(self, account_id: str, order_id: str) -> bool:
        """Cancel an open order."""
        if not self._trading_client:
            return False
        
        try:
            logger.info(f"Cancelling Alpaca order: {order_id}")
            
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._trading_client.cancel_order_by_id(order_id)),
                timeout=self.REQUEST_TIMEOUT
            )
            
            logger.info(f"✅ Alpaca order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cancelling Alpaca order: {e}")
            return False
    
    async def get_order(self, account_id: str, order_id: str) -> Optional[Order]:
        """Get order details."""
        if not self._trading_client:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            order = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._trading_client.get_order_by_id(order_id)),
                timeout=self.REQUEST_TIMEOUT
            )
            return self._convert_order(order, account_id)
        except Exception as e:
            logger.debug(f"Could not get order {order_id}: {e}")
            return None
    
    async def get_open_orders(self, account_id: str) -> List[Order]:
        """Get all open orders."""
        if not self._trading_client:
            return []
        
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus
            
            logger.debug("Fetching open orders...")
            
            request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
            
            loop = asyncio.get_event_loop()
            orders = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._trading_client.get_orders(request)),
                timeout=self.REQUEST_TIMEOUT
            )
            
            result = [self._convert_order(o, account_id) for o in orders]
            logger.debug(f"Found {len(result)} open orders")
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []
    
    async def get_order_history(
        self,
        account_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Order]:
        """Get order history."""
        if not self._trading_client:
            return []
        
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus
            
            request = GetOrdersRequest(
                status=QueryOrderStatus.ALL,
                limit=limit,
                after=start_date,
                until=end_date
            )
            
            loop = asyncio.get_event_loop()
            orders = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._trading_client.get_orders(request)),
                timeout=self.REQUEST_TIMEOUT
            )
            
            return [self._convert_order(o, account_id) for o in orders]
            
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return []
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote from Alpaca data."""
        if not self._data_client:
            return None
        
        try:
            from alpaca.data.requests import StockLatestQuoteRequest
            
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            
            loop = asyncio.get_event_loop()
            quotes = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._data_client.get_stock_latest_quote(request)),
                timeout=self.REQUEST_TIMEOUT
            )
            
            if symbol in quotes:
                q = quotes[symbol]
                return {
                    "symbol": symbol,
                    "bid": float(q.bid_price),
                    "ask": float(q.ask_price),
                    "bid_size": int(q.bid_size),
                    "ask_size": int(q.ask_size),
                    "timestamp": q.timestamp.isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting quote: {e}")
        return None
    
    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """Get historical bars from Alpaca."""
        if not self._data_client:
            return None
        
        try:
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            # Map timeframe
            tf_map = {
                "1m": TimeFrame.Minute,
                "5m": TimeFrame.Minute,
                "15m": TimeFrame.Minute,
                "1h": TimeFrame.Hour,
                "1d": TimeFrame.Day,
                "1w": TimeFrame.Week,
            }
            tf = tf_map.get(timeframe, TimeFrame.Day)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start,
                end=end,
                limit=limit
            )
            
            loop = asyncio.get_event_loop()
            bars = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._data_client.get_stock_bars(request)),
                timeout=self.REQUEST_TIMEOUT
            )
            
            if symbol in bars:
                return [
                    {
                        "timestamp": b.timestamp.isoformat(),
                        "open": float(b.open),
                        "high": float(b.high),
                        "low": float(b.low),
                        "close": float(b.close),
                        "volume": int(b.volume),
                        "vwap": float(b.vwap) if b.vwap else None
                    }
                    for b in bars[symbol]
                ]
        except Exception as e:
            logger.error(f"Error getting bars: {e}")
        return None
    
    def _map_order_status(self, status: str) -> OrderStatus:
        """Map Alpaca order status to our OrderStatus."""
        status_map = {
            "new": OrderStatus.SUBMITTED,
            "accepted": OrderStatus.SUBMITTED,
            "pending_new": OrderStatus.PENDING,
            "accepted_for_bidding": OrderStatus.SUBMITTED,
            "filled": OrderStatus.FILLED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "canceled": OrderStatus.CANCELLED,
            "expired": OrderStatus.EXPIRED,
            "rejected": OrderStatus.REJECTED,
            "pending_cancel": OrderStatus.SUBMITTED,
            "pending_replace": OrderStatus.SUBMITTED,
        }
        return status_map.get(status.lower(), OrderStatus.PENDING)
    
    def _convert_order(self, order, account_id: str) -> Order:
        """Convert Alpaca order to our Order type."""
        return Order(
            order_id=str(order.id),
            symbol=order.symbol,
            side=OrderSide.BUY if order.side.value == "buy" else OrderSide.SELL,
            order_type=OrderType.MARKET,  # Simplified
            quantity=float(order.qty),
            limit_price=float(order.limit_price) if order.limit_price else None,
            stop_price=float(order.stop_price) if order.stop_price else None,
            status=self._map_order_status(order.status.value),
            filled_quantity=float(order.filled_qty) if order.filled_qty else 0,
            avg_fill_price=float(order.filled_avg_price) if order.filled_avg_price else None,
            broker=BrokerType.ALPACA,
            account_id=account_id,
            created_at=order.created_at,
            updated_at=order.updated_at or datetime.now()
        )
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic information about the connection."""
        return {
            "broker": "alpaca",
            "connected": self._connected,
            "paper": self.paper,
            "base_url": self.base_url,
            "last_successful_call": self._last_successful_call.isoformat() if self._last_successful_call else None,
            "consecutive_failures": self._consecutive_failures,
            "error_message": self._error_message,
            "account_cache_age": (datetime.now() - self._account_cache_time).total_seconds() if self._account_cache_time else None,
            "positions_cache_age": (datetime.now() - self._positions_cache_time).total_seconds() if self._positions_cache_time else None,
        }
