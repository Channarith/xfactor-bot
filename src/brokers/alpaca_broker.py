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

API & SDK docs (check for latest changes):
- API reference: https://docs.alpaca.markets/reference
- Python SDK: https://alpaca.markets/sdks/python/ | https://github.com/alpacahq/alpaca-py
- Paper trading: https://docs.alpaca.markets/docs/paper-trading

Get API keys: https://app.alpaca.markets/
"""

import asyncio
import threading
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
    
    Base URLs per Alpaca docs (unchanged as of 2025-2026):
    - Paper: https://paper-api.alpaca.markets
    - Live:  https://api.alpaca.markets
    - Data:  https://data.alpaca.markets

    We pass url_override to TradingClient so these URLs are explicit and resilient to SDK changes.
    """
    
    BASE_URL_PAPER = "https://paper-api.alpaca.markets"
    BASE_URL_LIVE = "https://api.alpaca.markets"
    DATA_URL = "https://data.alpaca.markets"
    
    # Timeouts (generous to tolerate slow networks; transient DNS blips handled by consecutive-failure logic)
    CONNECT_TIMEOUT = 30  # seconds for initial connect
    REQUEST_TIMEOUT = 20  # seconds per request (was 15)
    
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
        
        # Caching to prevent excessive API calls (increased TTLs)
        self._account_cache: Optional[List[AccountInfo]] = None
        self._account_cache_time: Optional[datetime] = None
        self._account_cache_ttl = 30  # seconds - increased to reduce API calls
        
        self._positions_cache: Optional[List[Position]] = None
        self._positions_cache_time: Optional[datetime] = None
        self._positions_cache_ttl = 20  # seconds - increased to reduce API calls
        
        # Health check throttling
        self._last_health_check: Optional[datetime] = None
        self._health_check_ttl = 30  # Only check health every 30 seconds
        self._last_health_result: bool = True
        
        # Connection tracking
        self._last_successful_call: Optional[datetime] = None
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5
        
        # Rate limiting - prevent API flooding
        self._min_api_interval = 1.0  # Minimum 1 second between API calls
        self._last_api_call: Optional[datetime] = None
        
        # Network error tracking - reduce log spam
        self._network_error_logged = False
        self._last_network_error_time: Optional[datetime] = None
        self._network_error_log_interval = 120  # Only log network errors every 2 minutes
        
        # Thread-safe lock to prevent concurrent API calls (connection pool exhaustion)
        # Using threading.Lock instead of asyncio.Lock because bots run in different event loops
        self._api_lock = threading.Lock()
        
        # Supported crypto symbols on Alpaca (as of 2024); Alpaca uses "/" format e.g. "BTC/USD"
        self._supported_crypto = {
            "BTC/USD", "ETH/USD", "LTC/USD", "BCH/USD", "AVAX/USD",
            "LINK/USD", "UNI/USD", "AAVE/USD", "DOT/USD", "DOGE/USD",
            "SHIB/USD", "SOL/USD", "MATIC/USD", "XLM/USD", "ALGO/USD",
            "ATOM/USD", "CRV/USD", "GRT/USD", "MKR/USD", "SUSHI/USD",
        }
        self._crypto_symbol_map = {
            "BTC-USD": "BTC/USD", "ETH-USD": "ETH/USD", "LTC-USD": "LTC/USD",
            "BCH-USD": "BCH/USD", "AVAX-USD": "AVAX/USD", "LINK-USD": "LINK/USD",
            "UNI-USD": "UNI/USD", "AAVE-USD": "AAVE/USD", "DOT-USD": "DOT/USD",
            "DOGE-USD": "DOGE/USD", "SHIB-USD": "SHIB/USD", "SOL-USD": "SOL/USD",
            "MATIC-USD": "MATIC/USD", "XLM-USD": "XLM/USD", "ALGO-USD": "ALGO/USD",
            "ATOM-USD": "ATOM/USD", "CRV-USD": "CRV/USD", "GRT-USD": "GRT/USD",
            "MKR-USD": "MKR/USD", "SUSHI-USD": "SUSHI/USD",
        }
        
        logger.debug(f"AlpacaBroker initialized: paper={paper}, base_url={self.base_url}")
    
    def _is_network_error(self, error: Exception) -> bool:
        """Check if an error is a network connectivity issue."""
        error_str = str(error).lower()
        network_indicators = [
            'nodename nor servname',
            'name resolution',
            'failed to resolve',
            'connection refused',
            'network is unreachable',
            'no route to host',
            'temporary failure in name resolution',
            'getaddrinfo failed',
            'max retries exceeded',
        ]
        return any(indicator in error_str for indicator in network_indicators)
    
    def _should_log_network_error(self) -> bool:
        """Check if we should log a network error (to reduce spam)."""
        now = datetime.now()
        if self._last_network_error_time is None:
            self._last_network_error_time = now
            return True
        
        elapsed = (now - self._last_network_error_time).total_seconds()
        if elapsed >= self._network_error_log_interval:
            self._last_network_error_time = now
            return True
        return False
    
    def _log_network_error(self, context: str, error: Exception) -> None:
        """Log network error with rate limiting to reduce spam."""
        from src.utils.helpers import get_network_tracker
        tracker = get_network_tracker()
        tracker.record_error(f"alpaca.{context}", error)
    
    def _reset_network_error_state(self) -> None:
        """Reset network error state after successful call."""
        self._network_error_logged = False
        self._last_network_error_time = None
        # Notify global tracker of successful connection
        from src.utils.helpers import get_network_tracker
        tracker = get_network_tracker()
        tracker.record_success("alpaca")
    
    @property
    def supports_fractional_shares(self) -> bool:
        """Alpaca supports fractional share trading for most US stocks."""
        return True
    
    @property
    def supports_extended_hours(self) -> bool:
        """Alpaca supports extended hours trading (pre-market and after-hours)."""
        return True
    
    @property
    def max_orders_per_minute(self) -> int:
        """Alpaca allows 200 API requests per minute."""
        return 200
    
    # Retry config for connect (DNS/network can be transient)
    CONNECT_RETRIES = 3
    CONNECT_RETRY_DELAYS = (2, 4, 6)  # seconds between retries

    async def connect(self) -> bool:
        """Connect to Alpaca API with timeout handling and retries for DNS/network errors."""
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
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import StockHistoricalDataClient
        except ImportError:
            self._error_message = "alpaca-py not installed. Run: pip install alpaca-py"
            logger.error(self._error_message)
            return False
        
        last_error: Optional[Exception] = None
        for attempt in range(self.CONNECT_RETRIES):
            try:
                if attempt > 0:
                    delay = self.CONNECT_RETRY_DELAYS[attempt - 1]
                    logger.info(f"Alpaca connect retry {attempt + 1}/{self.CONNECT_RETRIES} in {delay}s...")
                    await asyncio.sleep(delay)
                
                logger.debug("Creating Alpaca trading client...")
                self._trading_client = TradingClient(
                    api_key=self.api_key,
                    secret_key=self.secret_key,
                    paper=self.paper,
                    url_override=self.base_url,
                )
                self._data_client = StockHistoricalDataClient(
                    api_key=self.api_key,
                    secret_key=self.secret_key,
                )
                
                logger.debug("Testing connection by fetching account...")
                loop = asyncio.get_event_loop()
                account = await asyncio.wait_for(
                    loop.run_in_executor(None, self._trading_client.get_account),
                    timeout=self.CONNECT_TIMEOUT
                )
                
                self._connected = True
                self._last_successful_call = datetime.now()
                self._consecutive_failures = 0
                logger.info(f"✅ Connected to Alpaca {'Paper' if self.paper else 'Live'}")
                logger.info(f"   Account: {account.account_number}")
                logger.info(f"   Status: {account.status}")
                logger.info(f"   Equity: ${float(account.equity):,.2f}")
                logger.info(f"   Buying Power: ${float(account.buying_power):,.2f}")
                logger.info(f"   Cash: ${float(account.cash):,.2f}")
                logger.info(f"   PDT: {account.pattern_day_trader}")
                return True
                
            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError()
                self._error_message = f"Connection timed out after {self.CONNECT_TIMEOUT}s"
                if not self._is_network_error(Exception(self._error_message)):
                    logger.error(self._error_message)
                    return False
                logger.warning(f"Attempt {attempt + 1} timed out (will retry)")
            except Exception as e:
                last_error = e
                error_str = str(e)
                if self._is_network_error(e):
                    self._error_message = (
                        "Cannot reach Alpaca (DNS or network error). "
                        "Check your internet connection and try again."
                    )
                    logger.warning(f"Attempt {attempt + 1} network error: {error_str[:120]} (will retry)")
                else:
                    # Non-network error: don't retry
                    self._set_connect_error_message(error_str)
                    logger.error(f"Failed to connect to Alpaca: {self._error_message}")
                    return False
        
        # All retries exhausted for network error
        self._error_message = (
            "Cannot reach Alpaca after several attempts (DNS or network issue). "
            "Check your internet connection, DNS, and firewall; then try again."
        )
        logger.error(f"Failed to connect to Alpaca: {self._error_message}")
        return False
    
    def _set_connect_error_message(self, error_str: str) -> None:
        """Set user-facing error message from exception string."""
        err = error_str.lower()
        if "forbidden" in err or "401" in error_str:
            self._error_message = "Invalid API key or secret. Check your credentials."
        elif "not found" in err or "404" in error_str:
            self._error_message = "Account not found. Check your API key."
        elif "rate limit" in err or "429" in error_str:
            self._error_message = "Rate limited. Please wait and try again."
        elif "timeout" in err:
            self._error_message = "Connection timed out. Check your network."
        elif self._is_network_error(Exception(error_str)):
            self._error_message = (
                "Cannot reach Alpaca (DNS or network error). "
                "Check your internet connection and try again."
            )
        else:
            self._error_message = f"Connection failed: {error_str[:200]}"
    
    async def disconnect(self) -> None:
        """Disconnect from Alpaca."""
        self._trading_client = None
        self._data_client = None
        self._connected = False
        self._account_cache = None
        self._positions_cache = None
    
    def _normalize_symbol(self, symbol: str) -> tuple[str, bool]:
        """
        Normalize symbol for Alpaca trading.
        
        Args:
            symbol: Original symbol (e.g. "BTC-USD", "AAPL")
            
        Returns:
            Tuple of (normalized_symbol, is_crypto)
        """
        # Check if it's a crypto symbol
        if symbol in self._crypto_symbol_map:
            return self._crypto_symbol_map[symbol], True
        
        # Check if already in Alpaca format
        if "/" in symbol and symbol in self._supported_crypto:
            return symbol, True
        
        # Check for unsupported crypto formats
        if "-USD" in symbol.upper():
            # Might be an unsupported crypto
            potential_crypto = symbol.upper().replace("-", "/")
            if potential_crypto not in self._supported_crypto:
                logger.warning(f"⚠️ {symbol} is not a supported Alpaca crypto symbol. Supported: BTC, ETH, LTC, SOL, DOGE, etc.")
                return symbol, True  # Still return it, will fail at order submission with clear error
            return potential_crypto, True
        
        # Regular stock symbol
        return symbol.upper(), False
    
    def is_symbol_tradeable(self, symbol: str) -> bool:
        """Check if a symbol is tradeable on Alpaca."""
        normalized, is_crypto = self._normalize_symbol(symbol)
        if is_crypto:
            return normalized in self._supported_crypto
        # For stocks, assume tradeable (will fail at order submission if not)
        return True

    async def health_check(self) -> bool:
        """Check Alpaca connection health with throttling, caching, and tolerance for transient DNS/network errors."""
        if not self._trading_client:
            logger.debug("Health check failed: No trading client")
            return False
        
        now = datetime.now()
        if self._last_health_check:
            elapsed = (now - self._last_health_check).total_seconds()
            if elapsed < self._health_check_ttl:
                logger.debug(f"Using cached health check result (age: {elapsed:.1f}s)")
                return self._last_health_result
        
        try:
            self._last_health_check = now
            
            loop = asyncio.get_event_loop()
            account = await asyncio.wait_for(
                loop.run_in_executor(None, self._trading_client.get_account),
                timeout=self.REQUEST_TIMEOUT
            )
            
            self._last_successful_call = datetime.now()
            self._consecutive_failures = 0
            self._last_health_result = True
            
            logger.debug(f"Alpaca health check OK - Account status: {account.status}")
            return True
            
        except asyncio.TimeoutError:
            self._consecutive_failures += 1
            # Tolerate up to _max_consecutive_failures before reporting unhealthy (avoids disconnect on brief blips)
            self._last_health_result = self._consecutive_failures < self._max_consecutive_failures
            if self._should_log_network_error():
                logger.warning(f"Alpaca health check timed out (consecutive failures: {self._consecutive_failures})")
            return self._last_health_result
            
        except Exception as e:
            self._consecutive_failures += 1
            if self._is_network_error(e):
                self._log_network_error("health_check", e)
                # Treat transient DNS/network errors as "assume still connected" until we have 3 consecutive failures
                self._last_health_result = self._consecutive_failures < self._max_consecutive_failures
            else:
                # Auth/API errors: report unhealthy immediately
                self._last_health_result = False
                logger.warning(f"Alpaca health check failed: {e} (failures: {self._consecutive_failures})")
            return self._last_health_result
    
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
        
        # Use thread lock to prevent concurrent API calls (connection pool exhaustion)
        # threading.Lock works across different event loops unlike asyncio.Lock
        with self._api_lock:
            # Double-check cache after acquiring lock
            now = datetime.now()
            if self._account_cache and self._account_cache_time:
                age = (now - self._account_cache_time).total_seconds()
                if age < self._account_cache_ttl:
                    return self._account_cache
            
            try:
                logger.debug("Fetching Alpaca account data...")
                
                # Synchronous call since we're in a thread lock
                account = self._trading_client.get_account()
                
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
                
                # Reset network error state on success
                self._reset_network_error_state()
                
                return result
                
            except Exception as e:
                self._consecutive_failures += 1
                if self._is_network_error(e):
                    self._log_network_error("get_accounts", e)
                else:
                    logger.error(f"Error getting Alpaca account: {e}")
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
        
        # Use thread lock to prevent concurrent API calls
        with self._api_lock:
            # Double-check cache after acquiring lock
            now = datetime.now()
            if self._positions_cache is not None and self._positions_cache_time:
                age = (now - self._positions_cache_time).total_seconds()
                if age < self._positions_cache_ttl:
                    return self._positions_cache
            
            try:
                logger.debug("Fetching Alpaca positions...")
                
                # Synchronous call since we're in a thread lock
                positions = self._trading_client.get_all_positions()
                
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
                
                # Reset network error state on success
                self._reset_network_error_state()
                
                return result
                
            except Exception as e:
                if self._is_network_error(e):
                    self._log_network_error("get_positions", e)
                else:
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
            self._reset_network_error_state()
            return position
            
        except Exception as e:
            # Position not found is expected for symbols we don't hold
            error_str = str(e).lower()
            if "not found" in error_str:
                return None  # Normal case - no position
            elif self._is_network_error(e):
                self._log_network_error(f"get_position({symbol})", e)
            else:
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
        
        # Normalize symbol (handle crypto format conversion)
        original_symbol = symbol
        symbol, is_crypto = self._normalize_symbol(symbol)
        
        if is_crypto and symbol not in self._supported_crypto:
            raise ValueError(f"Crypto symbol '{original_symbol}' is not supported on Alpaca. Supported crypto: BTC, ETH, LTC, SOL, DOGE, SHIB, MATIC, AVAX, LINK, etc.")
        
        # =========================================================================
        # SELL ORDER VALIDATION - Verify position exists before selling
        # =========================================================================
        if side == OrderSide.SELL:
            skip_check = kwargs.get('skip_position_check', False)
            is_valid, error_msg, position = await self.validate_sell_order(
                account_id, symbol, quantity, skip_position_check=skip_check
            )
            
            if not is_valid:
                logger.error(f"❌ Alpaca SELL order rejected: {error_msg}")
                raise ValueError(f"SELL order validation failed: {error_msg}")
            
            # Adjust quantity if trying to sell more than we have
            if position and quantity > position.quantity:
                old_qty = quantity
                quantity = position.quantity  # Alpaca supports fractional, no floor needed
                logger.warning(
                    f"Alpaca SELL quantity adjusted: {old_qty} → {quantity} "
                    f"(only {position.quantity} shares available for {symbol})"
                )
                
                if quantity <= 0:
                    raise ValueError(
                        f"Cannot sell {symbol}: Position quantity is {position.quantity}"
                    )
        
        logger.info(f"📤 Submitting Alpaca order: {side.value.upper()} {quantity} {symbol} ({order_type.value})" + 
                   (f" [normalized from {original_symbol}]" if symbol != original_symbol else ""))
        
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
            if self._is_network_error(e):
                self._log_network_error(f"submit_order({symbol})", e)
            elif "insufficient" in error_str.lower():
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
