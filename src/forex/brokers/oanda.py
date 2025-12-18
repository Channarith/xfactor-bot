"""
OANDA Forex Broker Integration

Connects to OANDA's REST API for Forex trading.
Supports both practice and live accounts.

Features:
- Real-time streaming prices
- Order execution (market, limit, stop)
- Position management
- Account information
- Historical data access

API Documentation: https://developer.oanda.com/rest-live-v20/introduction/
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import asyncio

import httpx
from loguru import logger


class OANDAEnvironment(Enum):
    """OANDA API environments."""
    PRACTICE = "practice"      # Demo/paper trading
    LIVE = "live"              # Real money trading


@dataclass
class OANDAConfig:
    """OANDA API configuration."""
    api_key: str
    account_id: str
    environment: OANDAEnvironment = OANDAEnvironment.PRACTICE
    timeout: int = 30
    
    @property
    def base_url(self) -> str:
        """Get the base API URL."""
        if self.environment == OANDAEnvironment.PRACTICE:
            return "https://api-fxpractice.oanda.com"
        return "https://api-fxtrade.oanda.com"
    
    @property
    def stream_url(self) -> str:
        """Get the streaming API URL."""
        if self.environment == OANDAEnvironment.PRACTICE:
            return "https://stream-fxpractice.oanda.com"
        return "https://stream-fxtrade.oanda.com"


class OANDAClient:
    """
    Client for OANDA REST API v20.
    
    Usage:
        config = OANDAConfig(api_key="xxx", account_id="xxx-xxx-xxx")
        client = OANDAClient(config)
        
        # Get account info
        info = await client.get_account()
        
        # Get quote
        quote = await client.get_price("EUR_USD")
        
        # Place order
        order = await client.buy("EUR_USD", 1000)  # 1000 units
    """
    
    def __init__(self, config: OANDAConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=self.headers,
                timeout=self.config.timeout,
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # =========================================================================
    # Account Methods
    # =========================================================================
    
    async def get_account(self) -> Dict[str, Any]:
        """Get account information."""
        client = await self._get_client()
        response = await client.get(f"/v3/accounts/{self.config.account_id}")
        
        if response.status_code != 200:
            return {"error": response.text}
        
        data = response.json()
        account = data.get("account", {})
        
        return {
            "id": account.get("id"),
            "currency": account.get("currency"),
            "balance": float(account.get("balance", 0)),
            "nav": float(account.get("NAV", 0)),
            "unrealized_pl": float(account.get("unrealizedPL", 0)),
            "margin_used": float(account.get("marginUsed", 0)),
            "margin_available": float(account.get("marginAvailable", 0)),
            "position_value": float(account.get("positionValue", 0)),
            "open_trade_count": int(account.get("openTradeCount", 0)),
            "open_position_count": int(account.get("openPositionCount", 0)),
            "pending_order_count": int(account.get("pendingOrderCount", 0)),
        }
    
    async def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary."""
        client = await self._get_client()
        response = await client.get(f"/v3/accounts/{self.config.account_id}/summary")
        
        if response.status_code != 200:
            return {"error": response.text}
        
        return response.json().get("account", {})
    
    # =========================================================================
    # Pricing Methods
    # =========================================================================
    
    async def get_price(self, instrument: str) -> Optional[Dict[str, Any]]:
        """
        Get current price for an instrument.
        
        Args:
            instrument: OANDA instrument name (e.g., "EUR_USD")
        
        Returns:
            Dict with bid, ask, spread, etc.
        """
        # Convert pair format if needed
        instrument = instrument.replace("/", "_").upper()
        
        client = await self._get_client()
        response = await client.get(
            "/v3/accounts/{}/pricing".format(self.config.account_id),
            params={"instruments": instrument},
        )
        
        if response.status_code != 200:
            logger.warning(f"Failed to get price for {instrument}: {response.text}")
            return None
        
        data = response.json()
        prices = data.get("prices", [])
        
        if not prices:
            return None
        
        price = prices[0]
        bids = price.get("bids", [])
        asks = price.get("asks", [])
        
        bid = float(bids[0].get("price", 0)) if bids else 0
        ask = float(asks[0].get("price", 0)) if asks else 0
        
        return {
            "instrument": instrument,
            "bid": bid,
            "ask": ask,
            "spread": round((ask - bid) * 10000, 1),  # Spread in pips
            "time": price.get("time"),
            "tradeable": price.get("tradeable", True),
        }
    
    async def get_candles(
        self,
        instrument: str,
        granularity: str = "H1",
        count: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get historical candles.
        
        Args:
            instrument: OANDA instrument name
            granularity: Candle granularity (S5, M1, M5, M15, M30, H1, H4, D, W, M)
            count: Number of candles
        
        Returns:
            List of OHLCV dictionaries
        """
        instrument = instrument.replace("/", "_").upper()
        
        client = await self._get_client()
        response = await client.get(
            f"/v3/instruments/{instrument}/candles",
            params={
                "granularity": granularity,
                "count": count,
                "price": "MBA",  # Mid, Bid, Ask
            },
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        candles = data.get("candles", [])
        
        return [
            {
                "time": c.get("time"),
                "open": float(c.get("mid", {}).get("o", 0)),
                "high": float(c.get("mid", {}).get("h", 0)),
                "low": float(c.get("mid", {}).get("l", 0)),
                "close": float(c.get("mid", {}).get("c", 0)),
                "volume": int(c.get("volume", 0)),
                "complete": c.get("complete", True),
            }
            for c in candles
        ]
    
    # =========================================================================
    # Order Methods
    # =========================================================================
    
    async def buy(
        self,
        instrument: str,
        units: int,
        stop_loss_pips: Optional[float] = None,
        take_profit_pips: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Place a market buy order.
        
        Args:
            instrument: Currency pair
            units: Number of units (positive)
            stop_loss_pips: Stop loss in pips
            take_profit_pips: Take profit in pips
            stop_loss_price: Absolute stop loss price
            take_profit_price: Absolute take profit price
        
        Returns:
            Order result
        """
        return await self._place_market_order(
            instrument, abs(units), stop_loss_pips, take_profit_pips,
            stop_loss_price, take_profit_price,
        )
    
    async def sell(
        self,
        instrument: str,
        units: int,
        stop_loss_pips: Optional[float] = None,
        take_profit_pips: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place a market sell order."""
        return await self._place_market_order(
            instrument, -abs(units), stop_loss_pips, take_profit_pips,
            stop_loss_price, take_profit_price,
        )
    
    async def _place_market_order(
        self,
        instrument: str,
        units: int,
        stop_loss_pips: Optional[float] = None,
        take_profit_pips: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place a market order."""
        instrument = instrument.replace("/", "_").upper()
        
        order_data: Dict[str, Any] = {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(units),
            "timeInForce": "FOK",  # Fill or Kill
            "positionFill": "DEFAULT",
        }
        
        # Add stop loss
        if stop_loss_price:
            order_data["stopLossOnFill"] = {"price": str(stop_loss_price)}
        elif stop_loss_pips:
            order_data["stopLossOnFill"] = {"distance": str(stop_loss_pips * 0.0001)}
        
        # Add take profit
        if take_profit_price:
            order_data["takeProfitOnFill"] = {"price": str(take_profit_price)}
        elif take_profit_pips:
            order_data["takeProfitOnFill"] = {"distance": str(take_profit_pips * 0.0001)}
        
        client = await self._get_client()
        response = await client.post(
            f"/v3/accounts/{self.config.account_id}/orders",
            json={"order": order_data},
        )
        
        if response.status_code not in [200, 201]:
            return {"error": response.text}
        
        data = response.json()
        
        if "orderFillTransaction" in data:
            fill = data["orderFillTransaction"]
            return {
                "success": True,
                "order_id": fill.get("id"),
                "instrument": fill.get("instrument"),
                "units": int(fill.get("units", 0)),
                "price": float(fill.get("price", 0)),
                "pl": float(fill.get("pl", 0)),
                "time": fill.get("time"),
            }
        
        if "orderCreateTransaction" in data:
            create = data["orderCreateTransaction"]
            return {
                "pending": True,
                "order_id": create.get("id"),
                "instrument": create.get("instrument"),
                "units": create.get("units"),
            }
        
        return {"error": "Unexpected response", "data": data}
    
    async def place_limit_order(
        self,
        instrument: str,
        units: int,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        gtd_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Place a limit order."""
        instrument = instrument.replace("/", "_").upper()
        
        order_data: Dict[str, Any] = {
            "type": "LIMIT",
            "instrument": instrument,
            "units": str(units),
            "price": str(price),
            "timeInForce": "GTC",
        }
        
        if gtd_time:
            order_data["timeInForce"] = "GTD"
            order_data["gtdTime"] = gtd_time.isoformat()
        
        if stop_loss:
            order_data["stopLossOnFill"] = {"price": str(stop_loss)}
        if take_profit:
            order_data["takeProfitOnFill"] = {"price": str(take_profit)}
        
        client = await self._get_client()
        response = await client.post(
            f"/v3/accounts/{self.config.account_id}/orders",
            json={"order": order_data},
        )
        
        if response.status_code not in [200, 201]:
            return {"error": response.text}
        
        return response.json()
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel a pending order."""
        client = await self._get_client()
        response = await client.put(
            f"/v3/accounts/{self.config.account_id}/orders/{order_id}/cancel"
        )
        
        if response.status_code != 200:
            return {"error": response.text}
        
        return {"success": True, "cancelled_order": order_id}
    
    # =========================================================================
    # Position Methods
    # =========================================================================
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions."""
        client = await self._get_client()
        response = await client.get(
            f"/v3/accounts/{self.config.account_id}/openPositions"
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        positions = data.get("positions", [])
        
        return [
            {
                "instrument": p.get("instrument"),
                "long_units": int(p.get("long", {}).get("units", 0)),
                "long_avg_price": float(p.get("long", {}).get("averagePrice", 0) or 0),
                "long_pl": float(p.get("long", {}).get("pl", 0)),
                "short_units": int(p.get("short", {}).get("units", 0)),
                "short_avg_price": float(p.get("short", {}).get("averagePrice", 0) or 0),
                "short_pl": float(p.get("short", {}).get("pl", 0)),
                "unrealized_pl": float(p.get("unrealizedPL", 0)),
            }
            for p in positions
        ]
    
    async def close_position(self, instrument: str, side: str = "ALL") -> Dict[str, Any]:
        """
        Close a position.
        
        Args:
            instrument: Currency pair
            side: "LONG", "SHORT", or "ALL"
        
        Returns:
            Close result
        """
        instrument = instrument.replace("/", "_").upper()
        
        body = {}
        if side.upper() == "LONG":
            body["longUnits"] = "ALL"
        elif side.upper() == "SHORT":
            body["shortUnits"] = "ALL"
        else:
            body["longUnits"] = "ALL"
            body["shortUnits"] = "ALL"
        
        client = await self._get_client()
        response = await client.put(
            f"/v3/accounts/{self.config.account_id}/positions/{instrument}/close",
            json=body,
        )
        
        if response.status_code != 200:
            return {"error": response.text}
        
        return {"success": True, "instrument": instrument}
    
    async def close_all_positions(self) -> Dict[str, Any]:
        """Close all open positions."""
        positions = await self.get_positions()
        
        results = []
        for pos in positions:
            result = await self.close_position(pos["instrument"])
            results.append(result)
        
        return {
            "closed_count": sum(1 for r in results if r.get("success")),
            "results": results,
        }
    
    # =========================================================================
    # Trade Methods
    # =========================================================================
    
    async def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades."""
        client = await self._get_client()
        response = await client.get(
            f"/v3/accounts/{self.config.account_id}/openTrades"
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        trades = data.get("trades", [])
        
        return [
            {
                "id": t.get("id"),
                "instrument": t.get("instrument"),
                "units": int(t.get("currentUnits", 0)),
                "open_price": float(t.get("price", 0)),
                "unrealized_pl": float(t.get("unrealizedPL", 0)),
                "margin_used": float(t.get("marginUsed", 0)),
                "open_time": t.get("openTime"),
                "stop_loss": t.get("stopLossOrder", {}).get("price"),
                "take_profit": t.get("takeProfitOrder", {}).get("price"),
            }
            for t in trades
        ]
    
    async def close_trade(self, trade_id: str, units: Optional[int] = None) -> Dict[str, Any]:
        """Close a specific trade."""
        client = await self._get_client()
        
        body = {}
        if units:
            body["units"] = str(units)
        else:
            body["units"] = "ALL"
        
        response = await client.put(
            f"/v3/accounts/{self.config.account_id}/trades/{trade_id}/close",
            json=body,
        )
        
        if response.status_code != 200:
            return {"error": response.text}
        
        return {"success": True, "trade_id": trade_id}
    
    async def modify_trade(
        self,
        trade_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trailing_stop_distance: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Modify stop loss and take profit of a trade."""
        client = await self._get_client()
        
        body = {}
        if stop_loss:
            body["stopLoss"] = {"price": str(stop_loss)}
        if take_profit:
            body["takeProfit"] = {"price": str(take_profit)}
        if trailing_stop_distance:
            body["trailingStopLoss"] = {"distance": str(trailing_stop_distance)}
        
        response = await client.put(
            f"/v3/accounts/{self.config.account_id}/trades/{trade_id}/orders",
            json=body,
        )
        
        if response.status_code != 200:
            return {"error": response.text}
        
        return {"success": True, "trade_id": trade_id}


# Singleton instance
_oanda_client: Optional[OANDAClient] = None


def get_oanda_client(config: Optional[OANDAConfig] = None) -> Optional[OANDAClient]:
    """Get or create the OANDA client singleton."""
    global _oanda_client
    if config:
        _oanda_client = OANDAClient(config)
    return _oanda_client

