"""
NinjaTrader Integration Module

Connects XFactor Bot to NinjaTrader 8 for futures and forex trading.
Uses the NinjaTrader ATI (Automated Trading Interface) for order execution.

Features:
- Connect via ATI socket connection
- Real-time position sync
- Order execution with SL/TP
- Account information retrieval
- Multi-account support

Requirements:
- NinjaTrader 8 running with ATI enabled
- ATI configured to accept connections on port 36973
"""

import asyncio
import socket
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from datetime import datetime
import json

from loguru import logger


class NTOrderAction(Enum):
    """NinjaTrader order actions."""
    BUY = "BUY"
    SELL = "SELL"
    BUY_TO_COVER = "BUYTOCOVER"
    SELL_SHORT = "SELLSHORT"


class NTOrderType(Enum):
    """NinjaTrader order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOPLIMIT"
    MIT = "MIT"  # Market if Touched


class NTTimeInForce(Enum):
    """Order time in force."""
    DAY = "DAY"
    GTC = "GTC"  # Good Till Cancelled
    GTD = "GTD"  # Good Till Date
    IOC = "IOC"  # Immediate or Cancel


@dataclass
class NTConnectionConfig:
    """NinjaTrader connection configuration."""
    host: str = "127.0.0.1"
    port: int = 36973
    account: str = "Sim101"  # Default simulation account
    timeout: int = 10
    auto_reconnect: bool = True
    reconnect_delay: int = 5


@dataclass
class NTPosition:
    """NinjaTrader position."""
    account: str
    instrument: str
    quantity: int
    avg_entry_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float


@dataclass
class NTOrder:
    """NinjaTrader order."""
    order_id: str
    account: str
    instrument: str
    action: NTOrderAction
    order_type: NTOrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    tif: NTTimeInForce = NTTimeInForce.DAY
    status: str = "pending"
    filled_quantity: int = 0
    avg_fill_price: float = 0.0


class NinjaTraderClient:
    """
    Client for connecting to NinjaTrader 8 via ATI.
    
    Usage:
        client = NinjaTraderClient()
        await client.connect()
        order_id = await client.place_order("ES 03-25", NTOrderAction.BUY, 1)
        await client.disconnect()
    """
    
    def __init__(self, config: Optional[NTConnectionConfig] = None):
        self.config = config or NTConnectionConfig()
        self._socket: Optional[socket.socket] = None
        self._connected = False
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._orders: Dict[str, NTOrder] = {}
        self._positions: Dict[str, NTPosition] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            "order_update": [],
            "position_update": [],
            "connection_change": [],
        }
    
    @property
    def connected(self) -> bool:
        """Check if connected to NinjaTrader."""
        return self._connected
    
    async def connect(self) -> bool:
        """
        Connect to NinjaTrader ATI.
        
        Returns:
            True if connection successful
        """
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.host, self.config.port),
                timeout=self.config.timeout
            )
            self._connected = True
            logger.info(f"Connected to NinjaTrader at {self.config.host}:{self.config.port}")
            
            # Start message handler
            asyncio.create_task(self._message_handler())
            
            # Notify callbacks
            for cb in self._callbacks["connection_change"]:
                cb(True)
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout to NinjaTrader")
            return False
        except ConnectionRefusedError:
            logger.error(f"Connection refused - is NinjaTrader running with ATI enabled?")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to NinjaTrader: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from NinjaTrader."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._connected = False
        self._reader = None
        self._writer = None
        logger.info("Disconnected from NinjaTrader")
        
        for cb in self._callbacks["connection_change"]:
            cb(False)
    
    async def _send_command(self, command: str) -> Optional[str]:
        """Send a command to NinjaTrader and wait for response."""
        if not self._connected or not self._writer:
            logger.error("Not connected to NinjaTrader")
            return None
        
        try:
            # NinjaTrader ATI uses newline-terminated commands
            self._writer.write(f"{command}\n".encode())
            await self._writer.drain()
            
            # Read response
            if self._reader:
                response = await asyncio.wait_for(
                    self._reader.readline(),
                    timeout=self.config.timeout
                )
                return response.decode().strip()
            return None
            
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None
    
    async def _message_handler(self) -> None:
        """Handle incoming messages from NinjaTrader."""
        while self._connected and self._reader:
            try:
                data = await self._reader.readline()
                if not data:
                    break
                
                message = data.decode().strip()
                await self._process_message(message)
                
            except Exception as e:
                if self._connected:
                    logger.error(f"Error in message handler: {e}")
                break
        
        if self._connected:
            self._connected = False
            if self.config.auto_reconnect:
                logger.info(f"Reconnecting in {self.config.reconnect_delay}s...")
                await asyncio.sleep(self.config.reconnect_delay)
                await self.connect()
    
    async def _process_message(self, message: str) -> None:
        """Process incoming message from NinjaTrader."""
        # Parse NinjaTrader messages
        # Format varies by message type
        logger.debug(f"NT Message: {message}")
        
        if message.startswith("ORDER"):
            # Order update
            await self._handle_order_update(message)
        elif message.startswith("POSITION"):
            # Position update
            await self._handle_position_update(message)
    
    async def _handle_order_update(self, message: str) -> None:
        """Handle order update message."""
        # Parse and update order state
        for cb in self._callbacks["order_update"]:
            cb(message)
    
    async def _handle_position_update(self, message: str) -> None:
        """Handle position update message."""
        for cb in self._callbacks["position_update"]:
            cb(message)
    
    # =========================================================================
    # Trading Methods
    # =========================================================================
    
    async def place_order(
        self,
        instrument: str,
        action: NTOrderAction,
        quantity: int,
        order_type: NTOrderType = NTOrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        tif: NTTimeInForce = NTTimeInForce.DAY,
    ) -> Optional[str]:
        """
        Place an order in NinjaTrader.
        
        Args:
            instrument: Instrument symbol (e.g., "ES 03-25", "NQ 03-25")
            action: Buy, Sell, etc.
            quantity: Number of contracts
            order_type: Market, Limit, Stop, etc.
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            tif: Time in force
        
        Returns:
            Order ID if successful, None otherwise
        """
        # Build ATI command
        # Format: PLACE;ACCOUNT;INSTRUMENT;ACTION;QTY;TYPE;LIMIT;STOP;TIF
        parts = [
            "PLACE",
            self.config.account,
            instrument,
            action.value,
            str(quantity),
            order_type.value,
            str(price or 0),
            str(stop_price or 0),
            tif.value,
        ]
        
        command = ";".join(parts)
        response = await self._send_command(command)
        
        if response and response.startswith("ORDER"):
            # Parse order ID from response
            order_id = response.split(";")[1] if ";" in response else None
            
            if order_id:
                # Store order
                self._orders[order_id] = NTOrder(
                    order_id=order_id,
                    account=self.config.account,
                    instrument=instrument,
                    action=action,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    stop_price=stop_price,
                    tif=tif,
                )
                
                logger.info(f"Order placed: {order_id} - {action.value} {quantity} {instrument}")
                
                # Place bracket orders if SL/TP specified
                if stop_loss:
                    await self._place_bracket_stop(order_id, instrument, quantity, stop_loss, is_long=action == NTOrderAction.BUY)
                if take_profit:
                    await self._place_bracket_target(order_id, instrument, quantity, take_profit, is_long=action == NTOrderAction.BUY)
                
                return order_id
        
        logger.error(f"Order failed: {response}")
        return None
    
    async def _place_bracket_stop(self, parent_id: str, instrument: str, quantity: int, stop_price: float, is_long: bool) -> None:
        """Place a stop loss order as part of a bracket."""
        action = NTOrderAction.SELL if is_long else NTOrderAction.BUY_TO_COVER
        command = f"PLACE;{self.config.account};{instrument};{action.value};{quantity};STOP;0;{stop_price};GTC"
        await self._send_command(command)
    
    async def _place_bracket_target(self, parent_id: str, instrument: str, quantity: int, target_price: float, is_long: bool) -> None:
        """Place a take profit order as part of a bracket."""
        action = NTOrderAction.SELL if is_long else NTOrderAction.BUY_TO_COVER
        command = f"PLACE;{self.config.account};{instrument};{action.value};{quantity};LIMIT;{target_price};0;GTC"
        await self._send_command(command)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        command = f"CANCEL;{self.config.account};{order_id}"
        response = await self._send_command(command)
        
        if response and "CANCELLED" in response:
            if order_id in self._orders:
                self._orders[order_id].status = "cancelled"
            logger.info(f"Order cancelled: {order_id}")
            return True
        
        logger.error(f"Failed to cancel order {order_id}: {response}")
        return False
    
    async def cancel_all_orders(self) -> int:
        """Cancel all open orders."""
        command = f"CANCELALLORDERS;{self.config.account}"
        response = await self._send_command(command)
        
        cancelled = 0
        for order_id, order in self._orders.items():
            if order.status == "pending":
                order.status = "cancelled"
                cancelled += 1
        
        logger.info(f"Cancelled {cancelled} orders")
        return cancelled
    
    async def flatten_position(self, instrument: str) -> bool:
        """Flatten (close) all positions for an instrument."""
        command = f"FLATTEN;{self.config.account};{instrument}"
        response = await self._send_command(command)
        
        if response and "FLAT" in response:
            logger.info(f"Position flattened: {instrument}")
            return True
        return False
    
    async def flatten_all(self) -> bool:
        """Flatten all positions."""
        command = f"FLATTENALL;{self.config.account}"
        response = await self._send_command(command)
        
        if response and "FLAT" in response:
            logger.info("All positions flattened")
            return True
        return False
    
    # =========================================================================
    # Account Methods
    # =========================================================================
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information."""
        command = f"ACCOUNTINFO;{self.config.account}"
        response = await self._send_command(command)
        
        if response:
            # Parse account info
            # Format: ACCOUNTINFO;buying_power;cash_value;realized_pnl;unrealized_pnl
            parts = response.split(";")
            if len(parts) >= 5:
                return {
                    "account": self.config.account,
                    "buying_power": float(parts[1]),
                    "cash_value": float(parts[2]),
                    "realized_pnl": float(parts[3]),
                    "unrealized_pnl": float(parts[4]),
                }
        return None
    
    async def get_positions(self) -> List[NTPosition]:
        """Get all open positions."""
        command = f"POSITIONS;{self.config.account}"
        response = await self._send_command(command)
        
        positions = []
        if response:
            # Parse positions
            # Each position on a new line
            for line in response.split("\n"):
                if line.startswith("POSITION"):
                    parts = line.split(";")
                    if len(parts) >= 7:
                        pos = NTPosition(
                            account=parts[1],
                            instrument=parts[2],
                            quantity=int(parts[3]),
                            avg_entry_price=float(parts[4]),
                            market_value=float(parts[5]),
                            unrealized_pnl=float(parts[6]),
                            realized_pnl=float(parts[7]) if len(parts) > 7 else 0.0,
                        )
                        positions.append(pos)
        
        return positions
    
    # =========================================================================
    # Callback Registration
    # =========================================================================
    
    def on_order_update(self, callback: Callable) -> None:
        """Register callback for order updates."""
        self._callbacks["order_update"].append(callback)
    
    def on_position_update(self, callback: Callable) -> None:
        """Register callback for position updates."""
        self._callbacks["position_update"].append(callback)
    
    def on_connection_change(self, callback: Callable) -> None:
        """Register callback for connection status changes."""
        self._callbacks["connection_change"].append(callback)


# Singleton client instance
_nt_client: Optional[NinjaTraderClient] = None


def get_ninjatrader_client(config: Optional[NTConnectionConfig] = None) -> NinjaTraderClient:
    """Get or create the NinjaTrader client singleton."""
    global _nt_client
    if _nt_client is None or config is not None:
        _nt_client = NinjaTraderClient(config)
    return _nt_client

