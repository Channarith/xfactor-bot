"""
Base broker interface for multi-broker support.
All broker implementations must inherit from BaseBroker.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class BrokerType(str, Enum):
    """Supported broker types."""
    IBKR = "ibkr"
    ALPACA = "alpaca"
    SCHWAB = "schwab"
    TD_AMERITRADE = "td_ameritrade"
    TRADIER = "tradier"
    ETRADE = "etrade"
    FIDELITY = "fidelity"
    COINBASE = "coinbase"
    BINANCE = "binance"


class OrderStatus(str, Enum):
    """Order status enum."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(str, Enum):
    """Order type enum."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(str, Enum):
    """Order side enum."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Position:
    """Position data class."""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    side: str  # 'long' or 'short'
    broker: BrokerType
    account_id: str
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def is_long(self) -> bool:
        return self.side == "long"
    
    @property
    def is_short(self) -> bool:
        return self.side == "short"


@dataclass
class Order:
    """Order data class."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0
    avg_fill_price: Optional[float] = None
    broker: BrokerType = BrokerType.IBKR
    account_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountInfo:
    """Account information."""
    account_id: str
    broker: BrokerType
    account_type: str  # 'cash', 'margin', 'ira', etc.
    buying_power: float
    cash: float
    portfolio_value: float
    equity: float
    margin_used: float = 0
    margin_available: float = 0
    day_trades_remaining: int = 3  # PDT rule
    is_pattern_day_trader: bool = False
    currency: str = "USD"
    last_updated: datetime = field(default_factory=datetime.now)


class BaseBroker(ABC):
    """
    Abstract base class for all broker implementations.
    
    All brokers must implement these methods to ensure
    consistent behavior across the trading system.
    """
    
    def __init__(self, broker_type: BrokerType):
        self.broker_type = broker_type
        self._connected = False
        self._accounts: Dict[str, AccountInfo] = {}
    
    @property
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        return self._connected
    
    @property
    def name(self) -> str:
        """Human-readable broker name."""
        return self.broker_type.value.upper()
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the broker.
        
        Returns:
            True if connection successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the broker."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the broker connection is healthy.
        
        Returns:
            True if connection is healthy.
        """
        pass
    
    # =========================================================================
    # Account Management
    # =========================================================================
    
    @abstractmethod
    async def get_accounts(self) -> List[AccountInfo]:
        """
        Get all accounts associated with this broker.
        
        Returns:
            List of AccountInfo objects.
        """
        pass
    
    @abstractmethod
    async def get_account_info(self, account_id: str) -> AccountInfo:
        """
        Get detailed account information.
        
        Args:
            account_id: The account identifier.
            
        Returns:
            AccountInfo object with current account state.
        """
        pass
    
    @abstractmethod
    async def get_buying_power(self, account_id: str) -> float:
        """
        Get available buying power for an account.
        
        Args:
            account_id: The account identifier.
            
        Returns:
            Available buying power in account currency.
        """
        pass
    
    # =========================================================================
    # Position Management
    # =========================================================================
    
    @abstractmethod
    async def get_positions(self, account_id: str) -> List[Position]:
        """
        Get all open positions for an account.
        
        Args:
            account_id: The account identifier.
            
        Returns:
            List of Position objects.
        """
        pass
    
    @abstractmethod
    async def get_position(self, account_id: str, symbol: str) -> Optional[Position]:
        """
        Get position for a specific symbol.
        
        Args:
            account_id: The account identifier.
            symbol: The ticker symbol.
            
        Returns:
            Position object or None if no position.
        """
        pass
    
    # =========================================================================
    # Order Management
    # =========================================================================
    
    @abstractmethod
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
        """
        Submit a new order.
        
        Args:
            account_id: The account to trade in.
            symbol: The ticker symbol.
            side: Buy or sell.
            quantity: Number of shares.
            order_type: Type of order (market, limit, etc.)
            limit_price: Limit price for limit orders.
            stop_price: Stop price for stop orders.
            time_in_force: Order duration (day, gtc, ioc, etc.)
            
        Returns:
            Order object with order details.
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, account_id: str, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            account_id: The account identifier.
            order_id: The order to cancel.
            
        Returns:
            True if cancellation successful.
        """
        pass
    
    @abstractmethod
    async def get_order(self, account_id: str, order_id: str) -> Optional[Order]:
        """
        Get order details.
        
        Args:
            account_id: The account identifier.
            order_id: The order identifier.
            
        Returns:
            Order object or None if not found.
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self, account_id: str) -> List[Order]:
        """
        Get all open orders for an account.
        
        Args:
            account_id: The account identifier.
            
        Returns:
            List of open Order objects.
        """
        pass
    
    @abstractmethod
    async def get_order_history(
        self,
        account_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Order]:
        """
        Get order history.
        
        Args:
            account_id: The account identifier.
            start_date: Start of date range.
            end_date: End of date range.
            limit: Maximum number of orders to return.
            
        Returns:
            List of Order objects.
        """
        pass
    
    # =========================================================================
    # Market Data (if supported by broker)
    # =========================================================================
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current quote for a symbol.
        Override if broker provides market data.
        
        Args:
            symbol: The ticker symbol.
            
        Returns:
            Quote data or None if not supported.
        """
        return None
    
    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical bars for a symbol.
        Override if broker provides market data.
        
        Args:
            symbol: The ticker symbol.
            timeframe: Bar timeframe (1m, 5m, 1h, 1d, etc.)
            start: Start datetime.
            end: End datetime.
            limit: Maximum bars to return.
            
        Returns:
            List of bar data or None if not supported.
        """
        return None
    
    # =========================================================================
    # Funding (if supported)
    # =========================================================================
    
    async def get_bank_accounts(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Get linked bank accounts.
        Override if broker supports ACH transfers.
        
        Returns:
            List of linked bank accounts.
        """
        return []
    
    async def initiate_transfer(
        self,
        account_id: str,
        amount: float,
        direction: str,  # 'deposit' or 'withdraw'
        bank_account_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Initiate a bank transfer.
        Override if broker supports ACH transfers.
        
        Args:
            account_id: The brokerage account.
            amount: Amount to transfer.
            direction: 'deposit' or 'withdraw'.
            bank_account_id: The linked bank account.
            
        Returns:
            Transfer details or None if not supported.
        """
        return None

