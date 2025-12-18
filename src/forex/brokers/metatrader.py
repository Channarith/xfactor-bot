"""
MetaTrader 4/5 Integration

Connects XFactor Bot to MetaTrader terminals for Forex trading.
Uses the MetaTrader 5 Python package for direct integration.

Features:
- Real-time quotes and charts
- Order execution (market, limit, stop)
- Position management
- Account information
- Expert Advisor signal integration

Requirements:
- MetaTrader 5 terminal installed
- Python package: pip install MetaTrader5
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timezone
from enum import Enum
import asyncio

from loguru import logger


class MT5OrderType(Enum):
    """MetaTrader 5 order types."""
    BUY = 0              # ORDER_TYPE_BUY
    SELL = 1             # ORDER_TYPE_SELL
    BUY_LIMIT = 2        # ORDER_TYPE_BUY_LIMIT
    SELL_LIMIT = 3       # ORDER_TYPE_SELL_LIMIT
    BUY_STOP = 4         # ORDER_TYPE_BUY_STOP
    SELL_STOP = 5        # ORDER_TYPE_SELL_STOP
    BUY_STOP_LIMIT = 6   # ORDER_TYPE_BUY_STOP_LIMIT
    SELL_STOP_LIMIT = 7  # ORDER_TYPE_SELL_STOP_LIMIT


class MT5Timeframe(Enum):
    """MetaTrader 5 timeframes."""
    M1 = 1               # 1 minute
    M5 = 5               # 5 minutes
    M15 = 15             # 15 minutes
    M30 = 30             # 30 minutes
    H1 = 16385           # 1 hour
    H4 = 16388           # 4 hours
    D1 = 16408           # 1 day
    W1 = 32769           # 1 week
    MN1 = 49153          # 1 month


@dataclass
class MT5Config:
    """MetaTrader 5 connection configuration."""
    terminal_path: Optional[str] = None  # Path to terminal64.exe
    login: Optional[int] = None          # Account number
    password: Optional[str] = None       # Account password
    server: Optional[str] = None         # Broker server
    timeout: int = 10000                  # Connection timeout (ms)
    portable: bool = False               # Portable mode


@dataclass
class MT5AccountInfo:
    """MetaTrader 5 account information."""
    login: int
    name: str
    server: str
    currency: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float
    leverage: int
    trade_mode: int
    company: str


@dataclass
class MT5Position:
    """MetaTrader 5 position."""
    ticket: int
    symbol: str
    type: int               # 0 = Buy, 1 = Sell
    volume: float
    open_price: float
    current_price: float
    sl: float
    tp: float
    profit: float
    swap: float
    open_time: datetime
    magic: int              # Expert Advisor ID
    comment: str


@dataclass
class MT5Order:
    """MetaTrader 5 pending order."""
    ticket: int
    symbol: str
    type: MT5OrderType
    volume: float
    price: float
    sl: float
    tp: float
    time_setup: datetime
    state: int
    comment: str


class MetaTraderClient:
    """
    Client for connecting to MetaTrader 5.
    
    Usage:
        client = MetaTraderClient(config)
        if await client.connect():
            quote = await client.get_quote("EURUSD")
            order = await client.buy("EURUSD", 0.1, sl=1.0800, tp=1.0900)
            await client.disconnect()
    
    Note: Requires MetaTrader 5 package (Windows only)
    """
    
    def __init__(self, config: Optional[MT5Config] = None):
        self.config = config or MT5Config()
        self._connected = False
        self._mt5 = None  # MetaTrader5 module
        self._callbacks: Dict[str, List[Callable]] = {
            "quote": [],
            "trade": [],
            "error": [],
        }
    
    @property
    def connected(self) -> bool:
        """Check if connected to MT5."""
        return self._connected
    
    async def connect(self) -> bool:
        """
        Connect to MetaTrader 5 terminal.
        
        Returns:
            True if connection successful
        """
        try:
            # Try to import MetaTrader5
            import MetaTrader5 as mt5
            self._mt5 = mt5
        except ImportError:
            logger.error("MetaTrader5 package not installed. Run: pip install MetaTrader5")
            logger.error("Note: MetaTrader5 package only works on Windows")
            return False
        
        # Initialize connection
        init_args = {}
        if self.config.terminal_path:
            init_args["path"] = self.config.terminal_path
        if self.config.login:
            init_args["login"] = self.config.login
        if self.config.password:
            init_args["password"] = self.config.password
        if self.config.server:
            init_args["server"] = self.config.server
        init_args["timeout"] = self.config.timeout
        init_args["portable"] = self.config.portable
        
        if not mt5.initialize(**init_args):
            error = mt5.last_error()
            logger.error(f"Failed to connect to MT5: {error}")
            return False
        
        self._connected = True
        logger.info(f"Connected to MetaTrader 5")
        
        # Log account info
        info = await self.get_account_info()
        if info:
            logger.info(f"Account: {info.login} | Balance: {info.balance} {info.currency}")
        
        return True
    
    async def disconnect(self) -> None:
        """Disconnect from MetaTrader 5."""
        if self._mt5 and self._connected:
            self._mt5.shutdown()
            self._connected = False
            logger.info("Disconnected from MetaTrader 5")
    
    async def get_account_info(self) -> Optional[MT5AccountInfo]:
        """Get account information."""
        if not self._connected:
            return None
        
        info = self._mt5.account_info()
        if not info:
            return None
        
        return MT5AccountInfo(
            login=info.login,
            name=info.name,
            server=info.server,
            currency=info.currency,
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            margin_level=info.margin_level,
            profit=info.profit,
            leverage=info.leverage,
            trade_mode=info.trade_mode,
            company=info.company,
        )
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Get current quote for a symbol.
        
        Args:
            symbol: Currency pair (e.g., "EURUSD")
        
        Returns:
            Dict with bid, ask, spread, etc.
        """
        if not self._connected:
            return None
        
        # Ensure symbol is in MT5 format (no slash)
        symbol = symbol.replace("/", "")
        
        tick = self._mt5.symbol_info_tick(symbol)
        if not tick:
            logger.warning(f"No quote available for {symbol}")
            return None
        
        info = self._mt5.symbol_info(symbol)
        
        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": round((tick.ask - tick.bid) / info.point if info else 0, 1),
            "volume": tick.volume,
            "time": datetime.fromtimestamp(tick.time, tz=timezone.utc).isoformat(),
        }
    
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: MT5Timeframe,
        count: int = 100,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get OHLCV data for a symbol.
        
        Args:
            symbol: Currency pair
            timeframe: Candle timeframe
            count: Number of candles
        
        Returns:
            List of OHLCV dictionaries
        """
        if not self._connected:
            return None
        
        symbol = symbol.replace("/", "")
        
        rates = self._mt5.copy_rates_from_pos(symbol, timeframe.value, 0, count)
        if rates is None:
            return None
        
        return [
            {
                "time": datetime.fromtimestamp(r['time'], tz=timezone.utc).isoformat(),
                "open": r['open'],
                "high": r['high'],
                "low": r['low'],
                "close": r['close'],
                "volume": r['tick_volume'],
            }
            for r in rates
        ]
    
    async def buy(
        self,
        symbol: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "XFactor Bot",
        magic: int = 123456,
    ) -> Optional[Dict[str, Any]]:
        """
        Place a market buy order.
        
        Args:
            symbol: Currency pair
            volume: Lot size
            sl: Stop loss price
            tp: Take profit price
            comment: Order comment
            magic: Magic number for EA identification
        
        Returns:
            Order result dictionary
        """
        return await self._place_order(symbol, MT5OrderType.BUY, volume, sl, tp, comment, magic)
    
    async def sell(
        self,
        symbol: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "XFactor Bot",
        magic: int = 123456,
    ) -> Optional[Dict[str, Any]]:
        """Place a market sell order."""
        return await self._place_order(symbol, MT5OrderType.SELL, volume, sl, tp, comment, magic)
    
    async def _place_order(
        self,
        symbol: str,
        order_type: MT5OrderType,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "",
        magic: int = 0,
        price: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Internal method to place orders."""
        if not self._connected:
            return {"error": "Not connected to MT5"}
        
        symbol = symbol.replace("/", "")
        
        # Get current price if not specified
        if price is None:
            tick = self._mt5.symbol_info_tick(symbol)
            if not tick:
                return {"error": f"Cannot get price for {symbol}"}
            
            price = tick.ask if order_type == MT5OrderType.BUY else tick.bid
        
        # Build order request
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type.value,
            "price": price,
            "deviation": 20,  # Slippage in points
            "magic": magic,
            "comment": comment,
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
        }
        
        if sl:
            request["sl"] = sl
        if tp:
            request["tp"] = tp
        
        # Send order
        result = self._mt5.order_send(request)
        
        if result is None:
            error = self._mt5.last_error()
            return {"error": f"Order failed: {error}"}
        
        if result.retcode != self._mt5.TRADE_RETCODE_DONE:
            return {
                "error": f"Order rejected: {result.comment}",
                "retcode": result.retcode,
            }
        
        return {
            "success": True,
            "order_id": result.order,
            "deal_id": result.deal,
            "volume": result.volume,
            "price": result.price,
            "comment": result.comment,
        }
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[MT5Position]:
        """Get open positions."""
        if not self._connected:
            return []
        
        if symbol:
            symbol = symbol.replace("/", "")
            positions = self._mt5.positions_get(symbol=symbol)
        else:
            positions = self._mt5.positions_get()
        
        if not positions:
            return []
        
        return [
            MT5Position(
                ticket=p.ticket,
                symbol=p.symbol,
                type=p.type,
                volume=p.volume,
                open_price=p.price_open,
                current_price=p.price_current,
                sl=p.sl,
                tp=p.tp,
                profit=p.profit,
                swap=p.swap,
                open_time=datetime.fromtimestamp(p.time, tz=timezone.utc),
                magic=p.magic,
                comment=p.comment,
            )
            for p in positions
        ]
    
    async def close_position(self, ticket: int) -> Dict[str, Any]:
        """Close a position by ticket."""
        if not self._connected:
            return {"error": "Not connected"}
        
        position = self._mt5.positions_get(ticket=ticket)
        if not position:
            return {"error": "Position not found"}
        
        pos = position[0]
        
        # Reverse the position
        order_type = MT5OrderType.SELL if pos.type == 0 else MT5OrderType.BUY
        
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type.value,
            "position": ticket,
            "deviation": 20,
            "comment": "Close by XFactor",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
        }
        
        result = self._mt5.order_send(request)
        
        if result and result.retcode == self._mt5.TRADE_RETCODE_DONE:
            return {
                "success": True,
                "closed_ticket": ticket,
                "profit": pos.profit,
            }
        
        return {"error": f"Failed to close: {result.comment if result else 'Unknown error'}"}
    
    async def close_all_positions(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Close all positions, optionally filtered by symbol."""
        positions = await self.get_positions(symbol)
        
        results = []
        for pos in positions:
            result = await self.close_position(pos.ticket)
            results.append(result)
        
        return {
            "closed_count": sum(1 for r in results if r.get("success")),
            "failed_count": sum(1 for r in results if r.get("error")),
            "results": results,
        }
    
    async def modify_position(
        self,
        ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Modify stop loss and take profit of a position."""
        if not self._connected:
            return {"error": "Not connected"}
        
        position = self._mt5.positions_get(ticket=ticket)
        if not position:
            return {"error": "Position not found"}
        
        pos = position[0]
        
        request = {
            "action": self._mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": pos.symbol,
            "sl": sl if sl else pos.sl,
            "tp": tp if tp else pos.tp,
        }
        
        result = self._mt5.order_send(request)
        
        if result and result.retcode == self._mt5.TRADE_RETCODE_DONE:
            return {"success": True, "ticket": ticket}
        
        return {"error": f"Modify failed: {result.comment if result else 'Unknown'}"}


# Singleton instance
_mt5_client: Optional[MetaTraderClient] = None


def get_metatrader_client(config: Optional[MT5Config] = None) -> MetaTraderClient:
    """Get or create the MetaTrader client singleton."""
    global _mt5_client
    if _mt5_client is None or config is not None:
        _mt5_client = MetaTraderClient(config)
    return _mt5_client

