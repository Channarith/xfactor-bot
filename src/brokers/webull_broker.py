"""
Webull Broker Integration.

Uses the official Webull Python SDK for trading.

Requirements:
- Webull account with $5,000 minimum balance
- API access approved (1-2 business days after application)
- App Key and App Secret from Webull API Management

Features:
- Official API (unlike Robinhood)
- Stocks, ETFs, Options trading
- Extended hours trading
- Real-time market data
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
    Webull broker implementation using official Webull SDK.
    
    This uses Webull's OFFICIAL API which requires:
    1. Webull account with $5,000+ balance
    2. API application approval (1-2 business days)
    3. App Key and App Secret
    
    Authentication:
    - App Key (from Webull API Management)
    - App Secret (from Webull API Management)
    - Region (US, HK, etc.)
    """
    
    def __init__(
        self,
        app_key: str = "",
        app_secret: str = "",
        api_key: str = "",  # Alias for app_key
        secret_key: str = "",  # Alias for app_secret
        region: str = "us",
        **kwargs
    ):
        super().__init__(BrokerType.WEBULL)
        # Support both naming conventions
        self.app_key = app_key or api_key
        self.app_secret = app_secret or secret_key
        self.region = region.lower()
        self._client = None
        self._trade_api = None
        self._account_id = None
        self._error_message = None
    
    async def connect(self) -> bool:
        """
        Connect to Webull using official SDK.
        
        Returns True if connected successfully.
        """
        try:
            from webullsdkcore.client import ApiClient
            from webullsdkcore.common.region import Region
            
            # Map region string to Region enum
            region_map = {
                "us": Region.US.value,
                "hk": Region.HK.value,
            }
            region_value = region_map.get(self.region, Region.US.value)
            
            logger.info(f"Connecting to Webull API (region: {self.region})")
            
            # Initialize API client
            self._client = ApiClient(self.app_key, self.app_secret, region_value)
            
            # Test connection by getting subscriptions
            from webullsdktrade.api import API
            self._trade_api = API(self._client)
            
            # Get account subscriptions to verify connection
            response = self._trade_api.account.get_app_subscriptions()
            
            if response.status_code == 200:
                self._connected = True
                subscriptions = response.json()
                logger.info(f"Connected to Webull - Subscriptions: {subscriptions}")
                
                # Get account ID from first subscription
                if subscriptions and isinstance(subscriptions, list) and len(subscriptions) > 0:
                    self._account_id = subscriptions[0].get("account_id")
                
                return True
            else:
                self._error_message = f"Failed to connect: {response.status_code} - {response.text}"
                logger.error(self._error_message)
                return False
                
        except ImportError as e:
            self._error_message = f"Webull SDK not installed. Run: pip install webull-python-sdk-core webull-python-sdk-trade"
            logger.error(self._error_message)
            return False
        except Exception as e:
            self._error_message = f"Connection failed: {str(e)}"
            logger.error(f"Failed to connect to Webull: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Webull."""
        self._client = None
        self._trade_api = None
        self._connected = False
        logger.info("Disconnected from Webull")
    
    async def health_check(self) -> bool:
        """Check Webull connection health."""
        if not self._trade_api:
            return False
        try:
            response = self._trade_api.account.get_app_subscriptions()
            return response.status_code == 200
        except Exception:
            return False
    
    async def get_accounts(self) -> List[AccountInfo]:
        """Get Webull accounts."""
        if not self._trade_api:
            return []
        
        try:
            # Get account details
            response = self._trade_api.account.get_account_profile(self._account_id)
            
            if response.status_code != 200:
                logger.error(f"Failed to get account: {response.text}")
                return []
            
            profile = response.json()
            
            # Get account balance
            balance_response = self._trade_api.account.get_account_balance(self._account_id)
            balance = balance_response.json() if balance_response.status_code == 200 else {}
            
            return [AccountInfo(
                account_id=self._account_id or profile.get("account_id", ""),
                broker=BrokerType.WEBULL,
                account_type=profile.get("account_type", "margin"),
                buying_power=float(balance.get("buying_power", 0)),
                cash=float(balance.get("cash", 0)),
                portfolio_value=float(balance.get("total_market_value", 0)),
                equity=float(balance.get("net_liquidation", 0)),
                margin_used=float(balance.get("margin_used", 0)),
                margin_available=float(balance.get("margin_available", 0)),
                day_trades_remaining=balance.get("day_trades_remaining", 3),
                is_pattern_day_trader=balance.get("is_pdt", False),
                currency="USD",
                last_updated=datetime.now()
            )]
        except Exception as e:
            logger.error(f"Error getting Webull account: {e}")
            return []
    
    async def get_account_info(self, account_id: str) -> AccountInfo:
        """Get Webull account info."""
        accounts = await self.get_accounts()
        if accounts:
            return accounts[0]
        raise ValueError("No account found")
    
    async def get_buying_power(self, account_id: str) -> float:
        """Get available buying power."""
        if not self._trade_api:
            return 0.0
        try:
            response = self._trade_api.account.get_account_balance(account_id)
            if response.status_code == 200:
                return float(response.json().get("buying_power", 0))
        except Exception as e:
            logger.error(f"Error getting buying power: {e}")
        return 0.0
    
    async def get_positions(self, account_id: str) -> List[Position]:
        """Get all open positions."""
        if not self._trade_api:
            return []
        
        try:
            response = self._trade_api.account.get_positions(account_id)
            
            if response.status_code != 200:
                logger.error(f"Failed to get positions: {response.text}")
                return []
            
            positions_data = response.json()
            positions = []
            
            for p in positions_data:
                quantity = float(p.get("quantity", 0))
                avg_cost = float(p.get("average_cost", 0))
                current_price = float(p.get("last_price", avg_cost))
                market_value = quantity * current_price
                unrealized_pnl = market_value - (quantity * avg_cost)
                unrealized_pnl_pct = ((current_price / avg_cost) - 1) * 100 if avg_cost > 0 else 0
                
                positions.append(Position(
                    symbol=p.get("symbol", ""),
                    quantity=quantity,
                    avg_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    side="long" if quantity > 0 else "short",
                    broker=BrokerType.WEBULL,
                    account_id=account_id,
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
        if not self._trade_api:
            raise ConnectionError("Not connected to Webull")
        
        try:
            # Build order request
            order_request = {
                "account_id": account_id,
                "symbol": symbol.upper(),
                "side": "BUY" if side == OrderSide.BUY else "SELL",
                "quantity": int(quantity),
                "time_in_force": time_in_force.upper(),
            }
            
            if order_type == OrderType.MARKET:
                order_request["order_type"] = "MARKET"
            elif order_type == OrderType.LIMIT:
                order_request["order_type"] = "LIMIT"
                order_request["limit_price"] = limit_price
            elif order_type == OrderType.STOP:
                order_request["order_type"] = "STOP"
                order_request["stop_price"] = stop_price
            elif order_type == OrderType.STOP_LIMIT:
                order_request["order_type"] = "STOP_LIMIT"
                order_request["limit_price"] = limit_price
                order_request["stop_price"] = stop_price
            
            # Submit order
            response = self._trade_api.order.place_order(**order_request)
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Order failed: {response.text}")
            
            order_data = response.json()
            order_id = order_data.get("order_id", "")
            
            logger.info(f"Webull order submitted: {order_id} - {side.value} {quantity} {symbol}")
            
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
            
        except Exception as e:
            logger.error(f"Error submitting Webull order: {e}")
            raise
    
    async def cancel_order(self, account_id: str, order_id: str) -> bool:
        """Cancel an open order."""
        if not self._trade_api:
            return False
        
        try:
            response = self._trade_api.order.cancel_order(account_id, order_id)
            success = response.status_code in [200, 204]
            if success:
                logger.info(f"Webull order cancelled: {order_id}")
            return success
        except Exception as e:
            logger.error(f"Error cancelling Webull order: {e}")
            return False
    
    async def get_order(self, account_id: str, order_id: str) -> Optional[Order]:
        """Get order details."""
        if not self._trade_api:
            return None
        
        try:
            response = self._trade_api.order.get_order(account_id, order_id)
            if response.status_code == 200:
                return self._convert_order(response.json(), account_id)
        except Exception:
            pass
        return None
    
    async def get_open_orders(self, account_id: str) -> List[Order]:
        """Get all open orders."""
        if not self._trade_api:
            return []
        
        try:
            response = self._trade_api.order.get_open_orders(account_id)
            if response.status_code == 200:
                orders = response.json()
                return [self._convert_order(o, account_id) for o in orders]
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
        if not self._trade_api:
            return []
        
        try:
            params = {"limit": limit}
            if start_date:
                params["start_date"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["end_date"] = end_date.strftime("%Y-%m-%d")
            
            response = self._trade_api.order.get_order_history(account_id, **params)
            if response.status_code == 200:
                orders = response.json()
                return [self._convert_order(o, account_id) for o in orders]
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
        return []
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote from Webull."""
        if not self._client:
            return None
        
        try:
            from webullsdkmdata.quotes.grpc.api import API as QuotesAPI
            
            quotes_api = QuotesAPI(self._client)
            response = quotes_api.get_quote(symbol.upper())
            
            if response:
                return {
                    "symbol": symbol.upper(),
                    "bid": float(response.get("bid", 0)),
                    "ask": float(response.get("ask", 0)),
                    "last": float(response.get("last", 0)),
                    "volume": int(response.get("volume", 0)),
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting quote: {e}")
        return None
    
    def _map_order_status(self, status: str) -> OrderStatus:
        """Map Webull order status to our OrderStatus."""
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
    
    def _convert_order(self, order: Dict[str, Any], account_id: str) -> Order:
        """Convert Webull order dict to our Order type."""
        return Order(
            order_id=order.get("order_id", ""),
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

