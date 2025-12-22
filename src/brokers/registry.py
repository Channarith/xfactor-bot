"""
Broker Registry - Manages all broker connections.
Allows connecting to multiple brokers simultaneously.
"""

from typing import Dict, List, Optional, Type
from loguru import logger

from src.brokers.base import BaseBroker, BrokerType, AccountInfo


class BrokerRegistry:
    """
    Central registry for managing multiple broker connections.
    
    Allows the trading system to:
    - Connect to multiple brokers simultaneously
    - Route orders to specific brokers
    - Aggregate positions across all accounts
    - Manage account funding
    """
    
    def __init__(self):
        self._brokers: Dict[BrokerType, BaseBroker] = {}
        self._broker_classes: Dict[BrokerType, Type[BaseBroker]] = {}
        self._default_broker: Optional[BrokerType] = None
    
    def register_broker_class(
        self,
        broker_type: BrokerType,
        broker_class: Type[BaseBroker]
    ) -> None:
        """
        Register a broker implementation class.
        
        Args:
            broker_type: The broker type identifier.
            broker_class: The broker implementation class.
        """
        self._broker_classes[broker_type] = broker_class
        logger.info(f"Registered broker class: {broker_type.value}")
    
    async def connect_broker(
        self,
        broker_type: BrokerType,
        **config
    ) -> bool:
        """
        Connect to a broker.
        
        Args:
            broker_type: The broker to connect to.
            **config: Broker-specific configuration.
            
        Returns:
            True if connection successful.
        """
        if broker_type not in self._broker_classes:
            logger.error(f"Broker not registered: {broker_type.value}")
            return False
        
        try:
            broker_class = self._broker_classes[broker_type]
            broker = broker_class(**config)
            
            if await broker.connect():
                self._brokers[broker_type] = broker
                logger.info(f"Connected to broker: {broker_type.value}")
                
                # Set as default if first broker
                if self._default_broker is None:
                    self._default_broker = broker_type
                
                return True, None
            else:
                error_msg = getattr(broker, '_error_message', None) or f"Failed to connect to {broker_type.value}"
                logger.error(f"Failed to connect to broker: {broker_type.value} - {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"Error connecting to {broker_type.value}: {e}")
            return False, str(e)
    
    async def disconnect_broker(self, broker_type: BrokerType) -> None:
        """Disconnect from a broker."""
        if broker_type in self._brokers:
            await self._brokers[broker_type].disconnect()
            del self._brokers[broker_type]
            logger.info(f"Disconnected from broker: {broker_type.value}")
            
            if self._default_broker == broker_type:
                self._default_broker = next(iter(self._brokers.keys()), None)
    
    async def disconnect_all(self) -> None:
        """Disconnect from all brokers."""
        for broker_type in list(self._brokers.keys()):
            await self.disconnect_broker(broker_type)
    
    def get_broker(self, broker_type: BrokerType) -> Optional[BaseBroker]:
        """Get a specific broker instance."""
        return self._brokers.get(broker_type)
    
    def get_default_broker(self) -> Optional[BaseBroker]:
        """Get the default broker."""
        if self._default_broker:
            return self._brokers.get(self._default_broker)
        return None
    
    def set_default_broker(self, broker_type: BrokerType) -> bool:
        """Set the default broker for trading."""
        if broker_type in self._brokers:
            self._default_broker = broker_type
            logger.info(f"Default broker set to: {broker_type.value}")
            return True
        return False
    
    @property
    def connected_brokers(self) -> List[BrokerType]:
        """Get list of connected brokers."""
        return list(self._brokers.keys())
    
    @property
    def available_brokers(self) -> List[BrokerType]:
        """Get list of available (registered) broker types."""
        return list(self._broker_classes.keys())
    
    async def get_all_accounts(self) -> Dict[BrokerType, List[AccountInfo]]:
        """Get all accounts across all connected brokers."""
        all_accounts = {}
        for broker_type, broker in self._brokers.items():
            try:
                accounts = await broker.get_accounts()
                all_accounts[broker_type] = accounts
            except Exception as e:
                logger.error(f"Error getting accounts from {broker_type.value}: {e}")
                all_accounts[broker_type] = []
        return all_accounts
    
    async def get_total_portfolio_value(self) -> float:
        """Get total portfolio value across all brokers."""
        total = 0.0
        for broker in self._brokers.values():
            try:
                accounts = await broker.get_accounts()
                for account in accounts:
                    total += account.portfolio_value
            except Exception as e:
                logger.error(f"Error getting portfolio value: {e}")
        return total
    
    async def get_total_buying_power(self) -> float:
        """Get total buying power across all brokers."""
        total = 0.0
        for broker in self._brokers.values():
            try:
                accounts = await broker.get_accounts()
                for account in accounts:
                    total += account.buying_power
            except Exception as e:
                logger.error(f"Error getting buying power: {e}")
        return total
    
    def to_dict(self) -> Dict:
        """Get registry status as dictionary."""
        return {
            "connected_brokers": [b.value for b in self.connected_brokers],
            "available_brokers": [b.value for b in self.available_brokers],
            "default_broker": self._default_broker.value if self._default_broker else None,
            "broker_status": {
                b.value: self._brokers[b].is_connected 
                for b in self._brokers
            }
        }


# Global registry instance
_registry: Optional[BrokerRegistry] = None


def get_broker_registry() -> BrokerRegistry:
    """Get or create the global broker registry."""
    global _registry
    if _registry is None:
        _registry = BrokerRegistry()
        _register_default_brokers(_registry)
    return _registry


def _register_default_brokers(registry: BrokerRegistry) -> None:
    """Register all available broker implementations."""
    # Import and register broker implementations
    try:
        from src.brokers.alpaca_broker import AlpacaBroker
        registry.register_broker_class(BrokerType.ALPACA, AlpacaBroker)
    except ImportError:
        logger.debug("Alpaca broker not available")
    
    try:
        from src.brokers.ibkr_broker import IBKRBroker
        registry.register_broker_class(BrokerType.IBKR, IBKRBroker)
    except ImportError:
        logger.debug("IBKR broker not available")
    
    try:
        from src.brokers.schwab_broker import SchwabBroker
        registry.register_broker_class(BrokerType.SCHWAB, SchwabBroker)
    except ImportError:
        logger.debug("Schwab broker not available")
    
    try:
        from src.brokers.tradier_broker import TradierBroker
        registry.register_broker_class(BrokerType.TRADIER, TradierBroker)
    except ImportError:
        logger.debug("Tradier broker not available")

