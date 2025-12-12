"""
Multi-Account Manager for XFactor Bot

Supports managing multiple trading accounts across different brokers
with unified portfolio view and cross-account trading capabilities.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)


class AccountType(str, Enum):
    """Types of trading accounts."""
    INDIVIDUAL = "individual"
    JOINT = "joint"
    IRA_TRADITIONAL = "ira_traditional"
    IRA_ROTH = "ira_roth"
    IRA_SEP = "ira_sep"
    TRUST = "trust"
    CORPORATE = "corporate"
    PAPER = "paper"


class BrokerType(str, Enum):
    """Supported broker types."""
    IBKR = "ibkr"
    ALPACA = "alpaca"
    SCHWAB = "schwab"
    TRADIER = "tradier"


@dataclass
class AccountCredentials:
    """Credentials for a trading account."""
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1
    account_id: str = ""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    is_paper: bool = True


@dataclass
class Account:
    """Represents a trading account."""
    id: str
    name: str
    broker: BrokerType
    account_type: AccountType
    credentials: AccountCredentials
    
    # Status
    is_connected: bool = False
    is_active: bool = True
    last_sync: Optional[datetime] = None
    
    # Balances
    cash: float = 0.0
    buying_power: float = 0.0
    portfolio_value: float = 0.0
    margin_used: float = 0.0
    
    # Settings
    max_position_pct: float = 0.1
    max_daily_trades: int = 50
    enable_margin: bool = False
    enable_options: bool = False
    enable_futures: bool = False
    
    # Permissions
    can_trade_stocks: bool = True
    can_trade_options: bool = False
    can_trade_futures: bool = False
    can_trade_crypto: bool = False
    can_trade_forex: bool = False


@dataclass
class AccountPosition:
    """Position in an account."""
    account_id: str
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class AccountOrder:
    """Order placed in an account."""
    account_id: str
    order_id: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    status: str
    filled_qty: float = 0
    avg_fill_price: float = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AggregatedPortfolio:
    """Aggregated view across all accounts."""
    total_value: float = 0.0
    total_cash: float = 0.0
    total_positions_value: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_unrealized_pnl_pct: float = 0.0
    
    # By account
    accounts: list[dict] = field(default_factory=list)
    
    # Consolidated positions
    positions: dict[str, dict] = field(default_factory=dict)
    
    # Allocation
    allocation_by_account: dict[str, float] = field(default_factory=dict)
    allocation_by_broker: dict[str, float] = field(default_factory=dict)
    allocation_by_type: dict[str, float] = field(default_factory=dict)


class AccountManager:
    """
    Multi-account management system.
    
    Features:
    - Connect to multiple brokers simultaneously
    - Unified portfolio view across accounts
    - Cross-account position tracking
    - Account-specific trading rules
    - Aggregated performance metrics
    """
    
    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self.broker_connections: dict[str, Any] = {}
        self.positions_cache: dict[str, list[AccountPosition]] = {}
        
    def add_account(self, account: Account) -> bool:
        """Add a new account to manage."""
        if account.id in self.accounts:
            logger.warning(f"Account {account.id} already exists")
            return False
        
        self.accounts[account.id] = account
        logger.info(f"Added account: {account.name} ({account.broker.value})")
        return True
    
    def remove_account(self, account_id: str) -> bool:
        """Remove an account."""
        if account_id not in self.accounts:
            return False
        
        # Disconnect first
        self.disconnect_account(account_id)
        
        del self.accounts[account_id]
        if account_id in self.positions_cache:
            del self.positions_cache[account_id]
        
        logger.info(f"Removed account: {account_id}")
        return True
    
    async def connect_account(self, account_id: str) -> bool:
        """Connect to a specific account's broker."""
        if account_id not in self.accounts:
            logger.error(f"Account {account_id} not found")
            return False
        
        account = self.accounts[account_id]
        
        try:
            if account.broker == BrokerType.IBKR:
                from ..connectors.ibkr_connector import IBKRConnector
                connector = IBKRConnector(
                    host=account.credentials.host,
                    port=account.credentials.port,
                    client_id=account.credentials.client_id,
                )
                connected = await connector.connect()
                
            elif account.broker == BrokerType.ALPACA:
                from ..brokers.alpaca_broker import AlpacaBroker
                connector = AlpacaBroker(
                    api_key=account.credentials.api_key,
                    api_secret=account.credentials.api_secret,
                    paper=account.credentials.is_paper,
                )
                connected = await connector.connect()
                
            else:
                logger.warning(f"Broker {account.broker} not yet implemented")
                return False
            
            if connected:
                self.broker_connections[account_id] = connector
                account.is_connected = True
                account.last_sync = datetime.now()
                
                # Fetch initial data
                await self._sync_account_data(account_id)
                
                logger.info(f"Connected to {account.name}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to connect account {account_id}: {e}")
        
        return False
    
    def disconnect_account(self, account_id: str) -> None:
        """Disconnect from an account's broker."""
        if account_id in self.broker_connections:
            try:
                connector = self.broker_connections[account_id]
                if hasattr(connector, 'disconnect'):
                    connector.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting {account_id}: {e}")
            
            del self.broker_connections[account_id]
        
        if account_id in self.accounts:
            self.accounts[account_id].is_connected = False
    
    async def connect_all(self) -> dict[str, bool]:
        """Connect to all configured accounts."""
        results = {}
        
        tasks = [
            self.connect_account(account_id)
            for account_id in self.accounts
        ]
        
        connections = await asyncio.gather(*tasks, return_exceptions=True)
        
        for account_id, result in zip(self.accounts.keys(), connections):
            if isinstance(result, Exception):
                results[account_id] = False
                logger.error(f"Error connecting {account_id}: {result}")
            else:
                results[account_id] = result
        
        return results
    
    def disconnect_all(self) -> None:
        """Disconnect from all accounts."""
        for account_id in list(self.broker_connections.keys()):
            self.disconnect_account(account_id)
    
    async def sync_all_accounts(self) -> None:
        """Sync data from all connected accounts."""
        for account_id in self.broker_connections:
            await self._sync_account_data(account_id)
    
    async def _sync_account_data(self, account_id: str) -> None:
        """Sync data from a specific account."""
        if account_id not in self.broker_connections:
            return
        
        account = self.accounts[account_id]
        connector = self.broker_connections[account_id]
        
        try:
            # Get account info
            if hasattr(connector, 'get_account'):
                info = await connector.get_account()
                if info:
                    account.cash = info.get('cash', 0)
                    account.buying_power = info.get('buying_power', 0)
                    account.portfolio_value = info.get('portfolio_value', 0)
                    account.margin_used = info.get('margin_used', 0)
            
            # Get positions
            if hasattr(connector, 'get_positions'):
                positions = await connector.get_positions()
                self.positions_cache[account_id] = [
                    AccountPosition(
                        account_id=account_id,
                        symbol=p.get('symbol'),
                        quantity=p.get('quantity', 0),
                        avg_cost=p.get('avg_cost', 0),
                        current_price=p.get('current_price', 0),
                        market_value=p.get('market_value', 0),
                        unrealized_pnl=p.get('unrealized_pnl', 0),
                        unrealized_pnl_pct=p.get('unrealized_pnl_pct', 0),
                    )
                    for p in positions
                ]
            
            account.last_sync = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to sync account {account_id}: {e}")
    
    def get_aggregated_portfolio(self) -> AggregatedPortfolio:
        """Get aggregated portfolio view across all accounts."""
        portfolio = AggregatedPortfolio()
        
        # Aggregate account data
        for account_id, account in self.accounts.items():
            if not account.is_active:
                continue
            
            portfolio.total_value += account.portfolio_value
            portfolio.total_cash += account.cash
            
            portfolio.accounts.append({
                'id': account_id,
                'name': account.name,
                'broker': account.broker.value,
                'type': account.account_type.value,
                'value': account.portfolio_value,
                'cash': account.cash,
                'connected': account.is_connected,
            })
            
            # Allocation by account
            portfolio.allocation_by_account[account_id] = account.portfolio_value
            
            # Allocation by broker
            broker_key = account.broker.value
            portfolio.allocation_by_broker[broker_key] = \
                portfolio.allocation_by_broker.get(broker_key, 0) + account.portfolio_value
            
            # Allocation by type
            type_key = account.account_type.value
            portfolio.allocation_by_type[type_key] = \
                portfolio.allocation_by_type.get(type_key, 0) + account.portfolio_value
        
        # Aggregate positions
        for account_id, positions in self.positions_cache.items():
            for pos in positions:
                if pos.symbol not in portfolio.positions:
                    portfolio.positions[pos.symbol] = {
                        'symbol': pos.symbol,
                        'total_quantity': 0,
                        'total_value': 0,
                        'total_unrealized_pnl': 0,
                        'accounts': [],
                    }
                
                portfolio.positions[pos.symbol]['total_quantity'] += pos.quantity
                portfolio.positions[pos.symbol]['total_value'] += pos.market_value
                portfolio.positions[pos.symbol]['total_unrealized_pnl'] += pos.unrealized_pnl
                portfolio.positions[pos.symbol]['accounts'].append({
                    'account_id': account_id,
                    'quantity': pos.quantity,
                    'value': pos.market_value,
                })
        
        portfolio.total_positions_value = sum(
            p['total_value'] for p in portfolio.positions.values()
        )
        portfolio.total_unrealized_pnl = sum(
            p['total_unrealized_pnl'] for p in portfolio.positions.values()
        )
        
        if portfolio.total_positions_value > 0:
            portfolio.total_unrealized_pnl_pct = \
                portfolio.total_unrealized_pnl / portfolio.total_positions_value
        
        # Convert allocations to percentages
        if portfolio.total_value > 0:
            for key in portfolio.allocation_by_account:
                portfolio.allocation_by_account[key] /= portfolio.total_value
            for key in portfolio.allocation_by_broker:
                portfolio.allocation_by_broker[key] /= portfolio.total_value
            for key in portfolio.allocation_by_type:
                portfolio.allocation_by_type[key] /= portfolio.total_value
        
        return portfolio
    
    async def place_order(self,
                          account_id: str,
                          symbol: str,
                          side: str,
                          quantity: float,
                          order_type: str = 'market',
                          **kwargs) -> Optional[AccountOrder]:
        """Place an order in a specific account."""
        if account_id not in self.broker_connections:
            logger.error(f"Account {account_id} not connected")
            return None
        
        account = self.accounts[account_id]
        connector = self.broker_connections[account_id]
        
        # Check permissions
        # (In production, add checks for options, futures, etc.)
        
        try:
            result = await connector.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                **kwargs
            )
            
            if result:
                return AccountOrder(
                    account_id=account_id,
                    order_id=result.get('order_id', ''),
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_type=order_type,
                    status=result.get('status', 'submitted'),
                )
                
        except Exception as e:
            logger.error(f"Failed to place order in {account_id}: {e}")
        
        return None
    
    async def place_cross_account_order(self,
                                        symbol: str,
                                        side: str,
                                        total_quantity: float,
                                        allocation: Optional[dict[str, float]] = None) -> list[AccountOrder]:
        """
        Place orders across multiple accounts.
        
        Args:
            symbol: Symbol to trade
            side: 'buy' or 'sell'
            total_quantity: Total quantity to trade
            allocation: Optional allocation by account_id (defaults to equal)
            
        Returns:
            List of AccountOrders placed
        """
        orders = []
        
        # Default to equal allocation
        if allocation is None:
            connected_accounts = [
                aid for aid, acc in self.accounts.items()
                if acc.is_connected and acc.is_active
            ]
            if not connected_accounts:
                return orders
            
            qty_per_account = total_quantity / len(connected_accounts)
            allocation = {aid: qty_per_account for aid in connected_accounts}
        
        # Place orders
        for account_id, quantity in allocation.items():
            if quantity <= 0:
                continue
            
            order = await self.place_order(
                account_id=account_id,
                symbol=symbol,
                side=side,
                quantity=int(quantity),
            )
            
            if order:
                orders.append(order)
        
        return orders
    
    def get_account_summary(self) -> dict:
        """Get summary of all accounts."""
        return {
            'total_accounts': len(self.accounts),
            'connected_accounts': sum(1 for a in self.accounts.values() if a.is_connected),
            'total_value': sum(a.portfolio_value for a in self.accounts.values()),
            'total_cash': sum(a.cash for a in self.accounts.values()),
            'accounts': [
                {
                    'id': a.id,
                    'name': a.name,
                    'broker': a.broker.value,
                    'type': a.account_type.value,
                    'connected': a.is_connected,
                    'value': a.portfolio_value,
                    'cash': a.cash,
                    'last_sync': a.last_sync.isoformat() if a.last_sync else None,
                }
                for a in self.accounts.values()
            ],
        }

