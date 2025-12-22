"""
Webull Broker Integration.

Supports both:
1. Official Webull SDK (requires $5k minimum, API approval)
2. Unofficial webull library (username/password login, no minimum)

The unofficial API uses reverse-engineered endpoints and may break
if Webull changes their internal APIs.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from loguru import logger

from src.brokers.base import (
    BaseBroker, BrokerType, Position, Order, AccountInfo,
    OrderStatus, OrderType, OrderSide
)


class WebullBroker(BaseBroker):
    """
    Webull broker implementation.
    
    Supports two modes:
    1. Official API (app_key/app_secret) - requires $5k minimum
    2. Unofficial API (username/password) - no minimum, but may break
    """
    
    def __init__(
        self,
        # Official API credentials
        app_key: str = "",
        app_secret: str = "",
        api_key: str = "",  # Alias for app_key
        secret_key: str = "",  # Alias for app_secret
        # Unofficial API credentials
        username: str = "",
        password: str = "",
        mfa_code: str = "",
        device_id: str = "",
        # Common settings
        region: str = "us",
        paper: bool = True,
        **kwargs
    ):
        super().__init__(BrokerType.WEBULL)
        
        # Official API credentials
        self.app_key = app_key or api_key
        self.app_secret = app_secret or secret_key
        
        # Unofficial API credentials
        self.username = username
        self.password = password
        self.mfa_code = mfa_code
        self.device_id = device_id
        
        self.region = region.lower()
        self.paper = paper
        
        # Clients
        self._official_client = None
        self._unofficial_client = None
        self._trade_api = None
        self._account_id = None
        self._error_message = None
        self._requires_mfa = False
        self._mfa_type = None
        
        # Determine which mode to use
        self._use_official = bool(self.app_key and self.app_secret)
    
    @property
    def requires_mfa(self) -> bool:
        return self._requires_mfa
    
    @property
    def mfa_type(self) -> Optional[str]:
        return self._mfa_type
    
    async def connect(self) -> bool:
        """
        Connect to Webull.
        
        Uses official API if app_key/app_secret provided,
        otherwise falls back to unofficial API with username/password.
        """
        if self._use_official:
            return await self._connect_official()
        else:
            return await self._connect_unofficial()
    
    async def _connect_official(self) -> bool:
        """Connect using official Webull SDK."""
        try:
            from webullsdkcore.client import ApiClient
            from webullsdkcore.common.region import Region
            
            region_map = {
                "us": Region.US.value,
                "hk": Region.HK.value,
            }
            region_value = region_map.get(self.region, Region.US.value)
            
            logger.info(f"Connecting to Webull Official API (region: {self.region})")
            
            self._official_client = ApiClient(self.app_key, self.app_secret, region_value)
            
            from webullsdktrade.api import API
            self._trade_api = API(self._official_client)
            
            response = self._trade_api.account.get_app_subscriptions()
            
            if response.status_code == 200:
                self._connected = True
                subscriptions = response.json()
                logger.info(f"Connected to Webull Official API")
                
                if subscriptions and isinstance(subscriptions, list) and len(subscriptions) > 0:
                    self._account_id = subscriptions[0].get("account_id")
                
                return True
            else:
                self._error_message = f"Connection failed: {response.text}"
                logger.error(self._error_message)
                return False
                
        except ImportError:
            self._error_message = "Webull Official SDK not installed"
            logger.error(self._error_message)
            return False
        except Exception as e:
            self._error_message = f"Connection failed: {str(e)}"
            logger.error(f"Failed to connect to Webull Official API: {e}")
            return False
    
    async def _connect_unofficial(self) -> bool:
        """Connect using unofficial webull library."""
        try:
            from webull import webull, paper_webull
            import asyncio
            
            logger.info("Connecting to Webull Unofficial API")
            
            # Use paper trading or live
            loop = asyncio.get_event_loop()
            if self.paper:
                self._unofficial_client = await loop.run_in_executor(None, paper_webull)
            else:
                self._unofficial_client = await loop.run_in_executor(None, webull)
            
            # If we have device_id, set it
            if self.device_id:
                self._unofficial_client.device_id = self.device_id
            
            # Attempt login
            if self.username and self.password:
                login_result = await loop.run_in_executor(
                    None,
                    lambda: self._unofficial_client.login(
                        self.username,
                        self.password,
                        mfa=self.mfa_code if self.mfa_code else None
                    )
                )
                
                logger.info(f"Webull login result: {login_result}")
                
                if login_result:
                    # Check if MFA is required
                    if isinstance(login_result, dict):
                        if login_result.get('msg') == 'MFA_REQUIRED' or 'mfa' in str(login_result).lower():
                            self._requires_mfa = True
                            self._mfa_type = "sms"
                            self._error_message = "MFA verification required. Check your phone."
                            return False
                        elif login_result.get('accessToken') or login_result.get('access_token'):
                            self._connected = True
                            self._account_id = await loop.run_in_executor(
                                None, self._unofficial_client.get_account_id
                            )
                            logger.info(f"Connected to Webull - Account: {self._account_id}")
                            return True
                    elif login_result == True:
                        self._connected = True
                        self._account_id = await loop.run_in_executor(
                            None, self._unofficial_client.get_account_id
                        )
                        logger.info(f"Connected to Webull - Account: {self._account_id}")
                        return True
                
                self._error_message = f"Login failed: {login_result}"
                logger.error(self._error_message)
                return False
            else:
                self._error_message = "Username and password required for unofficial API"
                return False
                
        except ImportError:
            self._error_message = "Webull unofficial library not installed. Run: pip install webull"
            logger.error(self._error_message)
            return False
        except Exception as e:
            error_str = str(e).lower()
            if 'mfa' in error_str or 'verification' in error_str:
                self._requires_mfa = True
                self._mfa_type = "sms"
                self._error_message = "MFA verification required. Check your phone."
            else:
                self._error_message = f"Connection failed: {str(e)}"
            logger.error(f"Failed to connect to Webull: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Webull."""
        if self._unofficial_client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._unofficial_client.logout)
            except:
                pass
        
        self._official_client = None
        self._unofficial_client = None
        self._trade_api = None
        self._connected = False
        logger.info("Disconnected from Webull")
    
    async def health_check(self) -> bool:
        """Check Webull connection health."""
        if self._use_official and self._trade_api:
            try:
                response = self._trade_api.account.get_app_subscriptions()
                return response.status_code == 200
            except:
                return False
        elif self._unofficial_client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                account = await loop.run_in_executor(
                    None, self._unofficial_client.get_account
                )
                return account is not None
            except:
                return False
        return False
    
    async def get_accounts(self) -> List[AccountInfo]:
        """Get Webull accounts."""
        if self._use_official:
            return await self._get_accounts_official()
        else:
            return await self._get_accounts_unofficial()
    
    async def _get_accounts_official(self) -> List[AccountInfo]:
        """Get accounts using official API."""
        if not self._trade_api:
            return []
        
        try:
            response = self._trade_api.account.get_account_balance(self._account_id)
            if response.status_code != 200:
                return []
            
            balance = response.json()
            
            return [AccountInfo(
                account_id=self._account_id or "",
                broker=BrokerType.WEBULL,
                account_type="margin",
                buying_power=float(balance.get("buying_power", 0)),
                cash=float(balance.get("cash", 0)),
                portfolio_value=float(balance.get("total_market_value", 0)),
                equity=float(balance.get("net_liquidation", 0)),
                margin_used=0,
                margin_available=0,
                day_trades_remaining=3,
                is_pattern_day_trader=False,
                currency="USD",
                last_updated=datetime.now()
            )]
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return []
    
    async def _get_accounts_unofficial(self) -> List[AccountInfo]:
        """Get accounts using unofficial API."""
        if not self._unofficial_client:
            return []
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            account = await loop.run_in_executor(
                None, self._unofficial_client.get_account
            )
            
            if not account:
                return []
            
            return [AccountInfo(
                account_id=str(account.get("secAccountId", self._account_id or "")),
                broker=BrokerType.WEBULL,
                account_type=account.get("accountType", "margin"),
                buying_power=float(account.get("dayBuyingPower", 0)),
                cash=float(account.get("cashBalance", 0)),
                portfolio_value=float(account.get("accountMembers", [{}])[0].get("marketValue", 0) if account.get("accountMembers") else 0),
                equity=float(account.get("netLiquidation", 0)),
                margin_used=float(account.get("marginUsed", 0)),
                margin_available=float(account.get("marginAvailable", 0)),
                day_trades_remaining=int(account.get("dayTradesRemaining", 3)),
                is_pattern_day_trader=account.get("pdt", False),
                currency="USD",
                last_updated=datetime.now()
            )]
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return []
    
    async def get_account_info(self, account_id: str) -> AccountInfo:
        """Get Webull account info."""
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
        """Get all open positions."""
        if self._use_official:
            return await self._get_positions_official(account_id)
        else:
            return await self._get_positions_unofficial()
    
    async def _get_positions_official(self, account_id: str) -> List[Position]:
        """Get positions using official API."""
        if not self._trade_api:
            return []
        
        try:
            response = self._trade_api.account.get_positions(account_id)
            if response.status_code != 200:
                return []
            
            positions = []
            for p in response.json():
                quantity = float(p.get("quantity", 0))
                avg_cost = float(p.get("average_cost", 0))
                current_price = float(p.get("last_price", avg_cost))
                market_value = quantity * current_price
                unrealized_pnl = market_value - (quantity * avg_cost)
                
                positions.append(Position(
                    symbol=p.get("symbol", ""),
                    quantity=quantity,
                    avg_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=((current_price / avg_cost) - 1) * 100 if avg_cost else 0,
                    side="long" if quantity > 0 else "short",
                    broker=BrokerType.WEBULL,
                    account_id=account_id,
                    last_updated=datetime.now()
                ))
            return positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def _get_positions_unofficial(self) -> List[Position]:
        """Get positions using unofficial API."""
        if not self._unofficial_client:
            return []
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            positions_data = await loop.run_in_executor(
                None, self._unofficial_client.get_positions
            )
            
            if not positions_data:
                return []
            
            positions = []
            for p in positions_data:
                quantity = float(p.get("position", 0))
                avg_cost = float(p.get("costPrice", 0))
                current_price = float(p.get("lastPrice", avg_cost))
                market_value = float(p.get("marketValue", quantity * current_price))
                unrealized_pnl = float(p.get("unrealizedProfitLoss", 0))
                
                positions.append(Position(
                    symbol=p.get("ticker", {}).get("symbol", ""),
                    quantity=quantity,
                    avg_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=float(p.get("unrealizedProfitLossRate", 0)) * 100,
                    side="long" if quantity > 0 else "short",
                    broker=BrokerType.WEBULL,
                    account_id=self._account_id or "",
                    last_updated=datetime.now()
                ))
            return positions
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
        time_in_force: str = "day",
        **kwargs
    ) -> Order:
        """Submit an order to Webull."""
        if self._use_official:
            return await self._submit_order_official(
                account_id, symbol, side, quantity, order_type,
                limit_price, stop_price, time_in_force
            )
        else:
            return await self._submit_order_unofficial(
                symbol, side, quantity, order_type,
                limit_price, stop_price, time_in_force
            )
    
    async def _submit_order_official(
        self, account_id: str, symbol: str, side: OrderSide, quantity: float,
        order_type: OrderType, limit_price: Optional[float], stop_price: Optional[float],
        time_in_force: str
    ) -> Order:
        """Submit order using official API."""
        if not self._trade_api:
            raise ConnectionError("Not connected to Webull")
        
        order_request = {
            "account_id": account_id,
            "symbol": symbol.upper(),
            "side": "BUY" if side == OrderSide.BUY else "SELL",
            "quantity": int(quantity),
            "time_in_force": time_in_force.upper(),
            "order_type": order_type.value.upper(),
        }
        
        if limit_price:
            order_request["limit_price"] = limit_price
        if stop_price:
            order_request["stop_price"] = stop_price
        
        response = self._trade_api.order.place_order(**order_request)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Order failed: {response.text}")
        
        order_data = response.json()
        order_id = order_data.get("order_id", "")
        
        return Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            status=OrderStatus.SUBMITTED,
            filled_quantity=0,
            avg_fill_price=None,
            broker=BrokerType.WEBULL,
            account_id=account_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    async def _submit_order_unofficial(
        self, symbol: str, side: OrderSide, quantity: float,
        order_type: OrderType, limit_price: Optional[float], stop_price: Optional[float],
        time_in_force: str
    ) -> Order:
        """Submit order using unofficial API."""
        if not self._unofficial_client:
            raise ConnectionError("Not connected to Webull")
        
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Map order type
        action = "BUY" if side == OrderSide.BUY else "SELL"
        
        if order_type == OrderType.MARKET:
            order_result = await loop.run_in_executor(
                None,
                lambda: self._unofficial_client.place_order(
                    stock=symbol,
                    action=action,
                    orderType="MKT",
                    quant=int(quantity),
                    enforce=time_in_force.upper()
                )
            )
        elif order_type == OrderType.LIMIT:
            order_result = await loop.run_in_executor(
                None,
                lambda: self._unofficial_client.place_order(
                    stock=symbol,
                    action=action,
                    orderType="LMT",
                    quant=int(quantity),
                    price=limit_price,
                    enforce=time_in_force.upper()
                )
            )
        elif order_type == OrderType.STOP:
            order_result = await loop.run_in_executor(
                None,
                lambda: self._unofficial_client.place_order(
                    stock=symbol,
                    action=action,
                    orderType="STP",
                    quant=int(quantity),
                    stpPrice=stop_price,
                    enforce=time_in_force.upper()
                )
            )
        elif order_type == OrderType.STOP_LIMIT:
            order_result = await loop.run_in_executor(
                None,
                lambda: self._unofficial_client.place_order(
                    stock=symbol,
                    action=action,
                    orderType="STP LMT",
                    quant=int(quantity),
                    price=limit_price,
                    stpPrice=stop_price,
                    enforce=time_in_force.upper()
                )
            )
        else:
            raise ValueError(f"Unsupported order type: {order_type}")
        
        logger.info(f"Webull order result: {order_result}")
        
        order_id = ""
        if isinstance(order_result, dict):
            order_id = str(order_result.get("orderId", order_result.get("data", {}).get("orderId", "")))
        
        return Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            status=OrderStatus.SUBMITTED if order_id else OrderStatus.REJECTED,
            filled_quantity=0,
            avg_fill_price=None,
            broker=BrokerType.WEBULL,
            account_id=self._account_id or "",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    async def cancel_order(self, account_id: str, order_id: str) -> bool:
        """Cancel an open order."""
        if self._use_official and self._trade_api:
            try:
                response = self._trade_api.order.cancel_order(account_id, order_id)
                return response.status_code in [200, 204]
            except Exception as e:
                logger.error(f"Error cancelling order: {e}")
                return False
        elif self._unofficial_client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._unofficial_client.cancel_order(order_id)
                )
                return bool(result)
            except Exception as e:
                logger.error(f"Error cancelling order: {e}")
                return False
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
        if self._use_official and self._trade_api:
            try:
                response = self._trade_api.order.get_open_orders(account_id)
                if response.status_code == 200:
                    return [self._convert_order(o, account_id) for o in response.json()]
            except Exception as e:
                logger.error(f"Error getting open orders: {e}")
            return []
        elif self._unofficial_client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                orders = await loop.run_in_executor(
                    None, self._unofficial_client.get_current_orders
                )
                return [self._convert_unofficial_order(o) for o in (orders or [])]
            except Exception as e:
                logger.error(f"Error getting open orders: {e}")
            return []
        return []
    
    async def get_order_history(
        self,
        account_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Order]:
        """Get order history."""
        if self._unofficial_client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                orders = await loop.run_in_executor(
                    None, self._unofficial_client.get_history_orders
                )
                return [self._convert_unofficial_order(o) for o in (orders or [])[:limit]]
            except Exception as e:
                logger.error(f"Error getting order history: {e}")
        return []
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote."""
        if self._unofficial_client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                quote = await loop.run_in_executor(
                    None,
                    lambda: self._unofficial_client.get_quote(symbol.upper())
                )
                if quote:
                    return {
                        "symbol": symbol.upper(),
                        "bid": float(quote.get("bidPrice", 0)),
                        "ask": float(quote.get("askPrice", 0)),
                        "last": float(quote.get("close", quote.get("lastPrice", 0))),
                        "volume": int(quote.get("volume", 0)),
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                logger.error(f"Error getting quote: {e}")
        return None
    
    def _convert_order(self, order: Dict[str, Any], account_id: str) -> Order:
        """Convert official API order dict to Order."""
        return Order(
            order_id=str(order.get("order_id", "")),
            symbol=order.get("symbol", ""),
            side=OrderSide.BUY if order.get("side", "").upper() == "BUY" else OrderSide.SELL,
            order_type=OrderType.MARKET if order.get("order_type", "").upper() == "MARKET" else OrderType.LIMIT,
            quantity=float(order.get("quantity", 0)),
            limit_price=float(order.get("limit_price")) if order.get("limit_price") else None,
            stop_price=float(order.get("stop_price")) if order.get("stop_price") else None,
            status=self._map_order_status(order.get("status", "PENDING")),
            filled_quantity=float(order.get("filled_quantity", 0)),
            avg_fill_price=float(order.get("avg_fill_price")) if order.get("avg_fill_price") else None,
            broker=BrokerType.WEBULL,
            account_id=account_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _convert_unofficial_order(self, order: Dict[str, Any]) -> Order:
        """Convert unofficial API order dict to Order."""
        return Order(
            order_id=str(order.get("orderId", "")),
            symbol=order.get("ticker", {}).get("symbol", ""),
            side=OrderSide.BUY if order.get("action", "").upper() == "BUY" else OrderSide.SELL,
            order_type=self._map_unofficial_order_type(order.get("orderType", "")),
            quantity=float(order.get("totalQuantity", 0)),
            limit_price=float(order.get("lmtPrice")) if order.get("lmtPrice") else None,
            stop_price=float(order.get("auxPrice")) if order.get("auxPrice") else None,
            status=self._map_unofficial_status(order.get("status", "")),
            filled_quantity=float(order.get("filledQuantity", 0)),
            avg_fill_price=float(order.get("avgFilledPrice")) if order.get("avgFilledPrice") else None,
            broker=BrokerType.WEBULL,
            account_id=self._account_id or "",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _map_order_status(self, status: str) -> OrderStatus:
        """Map official order status."""
        status_map = {
            "PENDING": OrderStatus.PENDING,
            "WORKING": OrderStatus.SUBMITTED,
            "FILLED": OrderStatus.FILLED,
            "PARTIAL_FILLED": OrderStatus.PARTIALLY_FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.EXPIRED,
        }
        return status_map.get(status.upper(), OrderStatus.PENDING)
    
    def _map_unofficial_status(self, status: str) -> OrderStatus:
        """Map unofficial order status."""
        status_map = {
            "Pending": OrderStatus.PENDING,
            "Working": OrderStatus.SUBMITTED,
            "Filled": OrderStatus.FILLED,
            "Partially Filled": OrderStatus.PARTIALLY_FILLED,
            "Cancelled": OrderStatus.CANCELLED,
            "Canceled": OrderStatus.CANCELLED,
            "Failed": OrderStatus.REJECTED,
            "Expired": OrderStatus.EXPIRED,
        }
        return status_map.get(status, OrderStatus.PENDING)
    
    def _map_unofficial_order_type(self, order_type: str) -> OrderType:
        """Map unofficial order type."""
        type_map = {
            "MKT": OrderType.MARKET,
            "LMT": OrderType.LIMIT,
            "STP": OrderType.STOP,
            "STP LMT": OrderType.STOP_LIMIT,
        }
        return type_map.get(order_type.upper(), OrderType.MARKET)
