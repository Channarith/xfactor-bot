"""
Robinhood Broker Integration.

Uses the unofficial robin_stocks library to connect to Robinhood.

WARNING: This uses an unofficial API that may break at any time.
Robinhood does not provide an official trading API.
Use at your own risk.

Features:
- Username/password authentication
- 2FA support (SMS, TOTP)
- Stock and options trading
- Crypto trading
- Account info and positions
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio

from loguru import logger

from src.brokers.base import (
    BaseBroker, BrokerType, Position, Order, AccountInfo,
    OrderStatus, OrderType, OrderSide
)


class RobinhoodBroker(BaseBroker):
    """
    Robinhood broker implementation using robin_stocks.
    
    This is an UNOFFICIAL integration using reverse-engineered API.
    Use at your own risk - may violate Robinhood's ToS.
    
    Authentication:
    - Username (email or phone)
    - Password
    - 2FA code (SMS or TOTP authenticator)
    
    The library handles session management and token refresh.
    """
    
    def __init__(
        self,
        username: str = "",
        password: str = "",
        mfa_code: str = "",
        device_token: Optional[str] = None,
        **kwargs
    ):
        super().__init__(BrokerType.ROBINHOOD)
        self.username = username
        self.password = password
        self.mfa_code = mfa_code
        self.device_token = device_token
        self._login_response = None
        self._requires_mfa = False
        self._mfa_type = None  # 'sms' or 'totp'
        self._account_number = None
        self._account_url = None
        self._error_message = None
    
    async def connect(self) -> bool:
        """
        Connect to Robinhood using robin_stocks.
        
        Returns True if connected, False if MFA is required.
        Check self._requires_mfa to see if 2FA code is needed.
        
        Note: Robinhood almost always requires 2FA, even if the user thinks 
        it's disabled. The first login from a new device will trigger SMS/email verification.
        """
        try:
            import robin_stocks.robinhood as rh
            
            # Prepare login kwargs (based on robin_stocks 3.x API)
            login_kwargs = {
                "expiresIn": 86400,  # 24 hours
                "scope": "internal",
                "store_session": True,  # Store session for future logins
            }
            
            if self.mfa_code:
                login_kwargs["mfa_code"] = self.mfa_code
            
            logger.info(f"Attempting Robinhood login for: {self.username[:3]}***")
            
            # Attempt login
            # robin_stocks.login() is synchronous, run in executor
            loop = asyncio.get_event_loop()
            try:
                self._login_response = await loop.run_in_executor(
                    None,
                    lambda: rh.login(
                        self.username,
                        self.password,
                        **login_kwargs
                    )
                )
            except Exception as login_error:
                error_str = str(login_error).lower()
                logger.error(f"Robinhood login exception: {login_error}")
                
                # Check for common MFA/challenge patterns
                if any(x in error_str for x in ['mfa', 'challenge', 'verification', 'sms', 'code']):
                    self._requires_mfa = True
                    self._mfa_type = "sms"
                    self._error_message = "Robinhood requires verification. Check your phone for SMS code."
                    return False
                
                self._error_message = str(login_error)
                return False
            
            logger.info(f"Robinhood login response type: {type(self._login_response)}")
            logger.info(f"Robinhood login response: {self._login_response}")
            
            # Check if login was successful
            if self._login_response and isinstance(self._login_response, dict):
                if "access_token" in self._login_response:
                    self._connected = True
                    
                    # Get account info
                    account_info = await loop.run_in_executor(None, rh.load_account_profile)
                    if account_info:
                        self._account_number = account_info.get("account_number")
                        self._account_url = account_info.get("url")
                    
                    logger.info(f"Connected to Robinhood - Account: {self._account_number}")
                    return True
                    
                elif "mfa_required" in self._login_response or "challenge" in self._login_response:
                    # 2FA required
                    self._requires_mfa = True
                    self._mfa_type = self._login_response.get("mfa_type", "sms")
                    self._error_message = f"2FA required via {self._mfa_type}. Check your phone."
                    logger.info(f"Robinhood requires 2FA via {self._mfa_type}")
                    return False
                
                # Check for challenge_id (newer flow)
                elif "challenge_id" in self._login_response:
                    self._requires_mfa = True
                    self._mfa_type = self._login_response.get("challenge_type", "sms")
                    self._error_message = "Device verification required. Check your email/phone."
                    logger.info(f"Robinhood device challenge required")
                    return False
            
            # Check for errors
            if self._login_response and isinstance(self._login_response, dict) and "detail" in self._login_response:
                error_msg = self._login_response.get("detail", "Unknown error")
                self._error_message = error_msg
                logger.error(f"Robinhood login failed: {error_msg}")
                return False
            
            # If response is None or empty, it could be credentials issue or MFA
            if not self._login_response:
                self._error_message = "Login failed. Robinhood may require 2FA verification. Check your email/phone for a verification code."
                logger.error("Robinhood login failed: Empty response (likely MFA required)")
                # Assume MFA needed since Robinhood almost always requires it
                self._requires_mfa = True
                self._mfa_type = "sms"
                return False
            
            self._error_message = f"Unknown response: {self._login_response}"
            logger.error(f"Robinhood login failed: Unknown response type {type(self._login_response)}")
            return False
            
        except ImportError:
            self._error_message = "robin-stocks library not installed"
            logger.error("robin-stocks not installed. Run: pip install robin-stocks")
            return False
        except Exception as e:
            error_str = str(e)
            
            # Check for MFA challenge in exception
            if "mfa" in error_str.lower() or "challenge" in error_str.lower():
                self._requires_mfa = True
                logger.info(f"Robinhood requires 2FA: {e}")
                return False
            
            logger.error(f"Failed to connect to Robinhood: {e}")
            return False
    
    @property
    def requires_mfa(self) -> bool:
        """Check if MFA is required for login."""
        return self._requires_mfa
    
    @property
    def mfa_type(self) -> Optional[str]:
        """Get the type of MFA required (sms or totp)."""
        return self._mfa_type
    
    async def submit_mfa(self, mfa_code: str) -> bool:
        """Submit MFA code to complete login."""
        self.mfa_code = mfa_code
        return await self.connect()
    
    async def disconnect(self) -> None:
        """Disconnect from Robinhood."""
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, rh.logout)
        except Exception as e:
            logger.warning(f"Error during Robinhood logout: {e}")
        
        self._connected = False
        self._login_response = None
        self._requires_mfa = False
        logger.info("Disconnected from Robinhood")
    
    async def health_check(self) -> bool:
        """Check Robinhood connection health."""
        if not self._connected:
            return False
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            profile = await loop.run_in_executor(None, rh.load_account_profile)
            return profile is not None
        except Exception:
            return False
    
    async def get_accounts(self) -> List[AccountInfo]:
        """Get Robinhood account (single account per login)."""
        if not self._connected:
            return []
        
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            
            profile = await loop.run_in_executor(None, rh.load_account_profile)
            portfolio = await loop.run_in_executor(None, rh.load_portfolio_profile)
            
            if not profile or not portfolio:
                return []
            
            return [AccountInfo(
                account_id=profile.get("account_number", ""),
                broker=BrokerType.ROBINHOOD,
                account_type=profile.get("type", "cash"),
                buying_power=float(portfolio.get("withdrawable_amount", 0)),
                cash=float(profile.get("cash", 0)),
                portfolio_value=float(portfolio.get("equity", 0)),
                equity=float(portfolio.get("extended_hours_equity", 0) or portfolio.get("equity", 0)),
                margin_used=float(portfolio.get("margin_limit", 0)) - float(portfolio.get("available_margin", 0)),
                margin_available=float(portfolio.get("available_margin", 0)),
                day_trades_remaining=profile.get("day_trade_count", 3),
                is_pattern_day_trader=profile.get("is_day_trade_flagged", False),
                currency="USD",
                last_updated=datetime.now()
            )]
        except Exception as e:
            logger.error(f"Error getting Robinhood account: {e}")
            return []
    
    async def get_account_info(self, account_id: str) -> AccountInfo:
        """Get Robinhood account info."""
        accounts = await self.get_accounts()
        if accounts:
            return accounts[0]
        raise ValueError("No account found")
    
    async def get_buying_power(self, account_id: str) -> float:
        """Get available buying power."""
        if not self._connected:
            return 0.0
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            profile = await loop.run_in_executor(None, rh.load_account_profile)
            return float(profile.get("buying_power", 0)) if profile else 0.0
        except Exception as e:
            logger.error(f"Error getting buying power: {e}")
            return 0.0
    
    async def get_positions(self, account_id: str) -> List[Position]:
        """Get all open positions."""
        if not self._connected:
            return []
        
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            
            positions = await loop.run_in_executor(
                None, 
                lambda: rh.get_open_stock_positions()
            )
            
            result = []
            for p in positions or []:
                if float(p.get("quantity", 0)) == 0:
                    continue
                
                # Get current price
                symbol = p.get("symbol", "")
                if not symbol:
                    # Try to get symbol from instrument URL
                    instrument_url = p.get("instrument")
                    if instrument_url:
                        instrument = await loop.run_in_executor(
                            None,
                            lambda url=instrument_url: rh.get_instrument_by_url(url)
                        )
                        symbol = instrument.get("symbol", "") if instrument else ""
                
                if not symbol:
                    continue
                
                quantity = float(p.get("quantity", 0))
                avg_cost = float(p.get("average_buy_price", 0))
                
                # Get current quote
                quote = await loop.run_in_executor(
                    None,
                    lambda s=symbol: rh.get_latest_price(s)
                )
                current_price = float(quote[0]) if quote and quote[0] else avg_cost
                
                market_value = quantity * current_price
                unrealized_pnl = market_value - (quantity * avg_cost)
                unrealized_pnl_pct = ((current_price / avg_cost) - 1) * 100 if avg_cost > 0 else 0
                
                result.append(Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    side="long" if quantity > 0 else "short",
                    broker=BrokerType.ROBINHOOD,
                    account_id=account_id,
                    last_updated=datetime.now()
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
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
        time_in_force: str = "gfd",  # Good for day
        **kwargs
    ) -> Order:
        """Submit an order to Robinhood."""
        if not self._connected:
            raise ConnectionError("Not connected to Robinhood")
        
        import robin_stocks.robinhood as rh
        loop = asyncio.get_event_loop()
        
        try:
            # Map order side
            rh_side = "buy" if side == OrderSide.BUY else "sell"
            
            # Map time in force
            tif_map = {
                "day": "gfd",
                "gfd": "gfd",
                "gtc": "gtc",
                "ioc": "ioc",
                "fok": "fok",
            }
            rh_tif = tif_map.get(time_in_force.lower(), "gfd")
            
            # Submit order based on type
            if order_type == OrderType.MARKET:
                order = await loop.run_in_executor(
                    None,
                    lambda: rh.order(
                        symbol=symbol,
                        quantity=quantity,
                        side=rh_side,
                        timeInForce=rh_tif,
                        trigger="immediate",
                        type="market"
                    )
                )
            elif order_type == OrderType.LIMIT:
                order = await loop.run_in_executor(
                    None,
                    lambda: rh.order(
                        symbol=symbol,
                        quantity=quantity,
                        side=rh_side,
                        limitPrice=limit_price,
                        timeInForce=rh_tif,
                        trigger="immediate",
                        type="limit"
                    )
                )
            elif order_type == OrderType.STOP:
                order = await loop.run_in_executor(
                    None,
                    lambda: rh.order(
                        symbol=symbol,
                        quantity=quantity,
                        side=rh_side,
                        stopPrice=stop_price,
                        timeInForce=rh_tif,
                        trigger="stop",
                        type="market"
                    )
                )
            elif order_type == OrderType.STOP_LIMIT:
                order = await loop.run_in_executor(
                    None,
                    lambda: rh.order(
                        symbol=symbol,
                        quantity=quantity,
                        side=rh_side,
                        limitPrice=limit_price,
                        stopPrice=stop_price,
                        timeInForce=rh_tif,
                        trigger="stop",
                        type="limit"
                    )
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            if not order or "id" not in order:
                error_msg = order.get("detail", "Unknown error") if order else "No response"
                raise Exception(f"Order failed: {error_msg}")
            
            logger.info(f"Robinhood order submitted: {order['id']} - {side.value} {quantity} {symbol}")
            
            return Order(
                order_id=order.get("id", ""),
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                limit_price=limit_price,
                stop_price=stop_price,
                status=self._map_order_status(order.get("state", "pending")),
                filled_quantity=float(order.get("cumulative_quantity", 0)),
                avg_fill_price=float(order.get("average_price")) if order.get("average_price") else None,
                broker=BrokerType.ROBINHOOD,
                account_id=account_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error submitting Robinhood order: {e}")
            raise
    
    async def cancel_order(self, account_id: str, order_id: str) -> bool:
        """Cancel an open order."""
        if not self._connected:
            return False
        
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: rh.cancel_stock_order(order_id)
            )
            success = result is not None
            if success:
                logger.info(f"Robinhood order cancelled: {order_id}")
            return success
        except Exception as e:
            logger.error(f"Error cancelling Robinhood order: {e}")
            return False
    
    async def get_order(self, account_id: str, order_id: str) -> Optional[Order]:
        """Get order details."""
        if not self._connected:
            return None
        
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            order = await loop.run_in_executor(
                None,
                lambda: rh.get_stock_order_info(order_id)
            )
            if order:
                return self._convert_order(order, account_id)
        except Exception:
            pass
        return None
    
    async def get_open_orders(self, account_id: str) -> List[Order]:
        """Get all open orders."""
        if not self._connected:
            return []
        
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            orders = await loop.run_in_executor(
                None,
                lambda: rh.get_all_open_stock_orders()
            )
            return [self._convert_order(o, account_id) for o in (orders or [])]
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
        if not self._connected:
            return []
        
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            orders = await loop.run_in_executor(
                None,
                lambda: rh.get_all_stock_orders()
            )
            
            # Filter and limit
            result = []
            for o in (orders or [])[:limit]:
                order = self._convert_order(o, account_id)
                
                # Filter by date if specified
                if start_date and order.created_at < start_date:
                    continue
                if end_date and order.created_at > end_date:
                    continue
                
                result.append(order)
            
            return result
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return []
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote from Robinhood."""
        if not self._connected:
            return None
        
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            
            quote = await loop.run_in_executor(
                None,
                lambda: rh.get_stock_quote_by_symbol(symbol)
            )
            
            if quote:
                return {
                    "symbol": symbol,
                    "bid": float(quote.get("bid_price", 0) or 0),
                    "ask": float(quote.get("ask_price", 0) or 0),
                    "bid_size": int(quote.get("bid_size", 0) or 0),
                    "ask_size": int(quote.get("ask_size", 0) or 0),
                    "last": float(quote.get("last_trade_price", 0) or 0),
                    "timestamp": quote.get("updated_at", datetime.now().isoformat())
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
        """Get historical bars from Robinhood."""
        if not self._connected:
            return None
        
        try:
            import robin_stocks.robinhood as rh
            loop = asyncio.get_event_loop()
            
            # Map timeframe to Robinhood intervals
            interval_map = {
                "1m": "5minute",  # Robinhood minimum is 5min
                "5m": "5minute",
                "10m": "10minute",
                "1h": "hour",
                "1d": "day",
                "1w": "week",
            }
            interval = interval_map.get(timeframe, "day")
            
            # Map to span
            span_map = {
                "5minute": "day",
                "10minute": "week",
                "hour": "month",
                "day": "year",
                "week": "5year",
            }
            span = span_map.get(interval, "year")
            
            historicals = await loop.run_in_executor(
                None,
                lambda: rh.get_stock_historicals(
                    symbol,
                    interval=interval,
                    span=span
                )
            )
            
            if historicals:
                return [
                    {
                        "timestamp": h.get("begins_at", ""),
                        "open": float(h.get("open_price", 0)),
                        "high": float(h.get("high_price", 0)),
                        "low": float(h.get("low_price", 0)),
                        "close": float(h.get("close_price", 0)),
                        "volume": int(h.get("volume", 0))
                    }
                    for h in historicals[-limit:]
                ]
        except Exception as e:
            logger.error(f"Error getting bars: {e}")
        return None
    
    def _map_order_status(self, status: str) -> OrderStatus:
        """Map Robinhood order status to our OrderStatus."""
        status_map = {
            "queued": OrderStatus.PENDING,
            "unconfirmed": OrderStatus.PENDING,
            "confirmed": OrderStatus.SUBMITTED,
            "pending": OrderStatus.PENDING,
            "filled": OrderStatus.FILLED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "cancelled": OrderStatus.CANCELLED,
            "canceled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "failed": OrderStatus.REJECTED,
        }
        return status_map.get(status.lower(), OrderStatus.PENDING)
    
    def _convert_order(self, order: Dict[str, Any], account_id: str) -> Order:
        """Convert Robinhood order dict to our Order type."""
        # Parse created_at
        created_at = datetime.now()
        if "created_at" in order and order["created_at"]:
            try:
                created_at = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
            except Exception:
                pass
        
        return Order(
            order_id=order.get("id", ""),
            symbol=order.get("symbol", ""),
            side=OrderSide.BUY if order.get("side") == "buy" else OrderSide.SELL,
            order_type=OrderType.MARKET if order.get("type") == "market" else OrderType.LIMIT,
            quantity=float(order.get("quantity", 0)),
            limit_price=float(order.get("price")) if order.get("price") else None,
            stop_price=float(order.get("stop_price")) if order.get("stop_price") else None,
            status=self._map_order_status(order.get("state", "pending")),
            filled_quantity=float(order.get("cumulative_quantity", 0)),
            avg_fill_price=float(order.get("average_price")) if order.get("average_price") else None,
            broker=BrokerType.ROBINHOOD,
            account_id=account_id,
            created_at=created_at,
            updated_at=datetime.now()
        )

