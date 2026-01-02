"""
Broker Registry - Manages all broker connections.
Allows connecting to multiple brokers simultaneously.
Includes automatic reconnection for dropped connections.
Supports saving connections for auto-connect on startup.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Type, Any
from loguru import logger

from src.brokers.base import BaseBroker, BrokerType, AccountInfo
from src.brokers.saved_connections import get_saved_connections, SavedConnection


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
        
        # Store connection configs for auto-reconnection
        self._connection_configs: Dict[BrokerType, Dict[str, Any]] = {}
        
        # Auto-reconnection settings
        self._auto_reconnect_enabled = True
        self._reconnect_interval = 30  # seconds between reconnection attempts
        self._max_reconnect_attempts = 10
        self._health_check_interval = 60  # seconds between health checks
        
        # Monitoring state
        self._monitor_task: Optional[asyncio.Task] = None
        self._reconnect_attempts: Dict[BrokerType, int] = {}
        self._last_health_check: Optional[datetime] = None
        self._connection_events: List[Dict] = []  # Log of connection events
    
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
        save_connection: bool = False,
        connection_name: Optional[str] = None,
        auto_connect: bool = False,
        **config
    ) -> bool:
        """
        Connect to a broker.
        
        Args:
            broker_type: The broker to connect to.
            save_connection: Whether to save this connection for future use.
            connection_name: Name for the saved connection.
            auto_connect: Whether to auto-connect on startup.
            **config: Broker-specific configuration.
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if broker_type not in self._broker_classes:
            logger.error(f"Broker not registered: {broker_type.value}")
            return False, f"Broker not registered: {broker_type.value}"
        
        try:
            broker_class = self._broker_classes[broker_type]
            broker = broker_class(**config)
            
            if await broker.connect():
                self._brokers[broker_type] = broker
                
                # Store config for auto-reconnection
                self._connection_configs[broker_type] = config.copy()
                self._reconnect_attempts[broker_type] = 0
                
                self._log_connection_event(broker_type, "connected", "Successfully connected")
                logger.info(f"Connected to broker: {broker_type.value}")
                
                # Set as default if first broker
                if self._default_broker is None:
                    self._default_broker = broker_type
                
                # Save connection if requested
                if save_connection:
                    saved_conns = get_saved_connections()
                    saved_conns.save_connection(
                        broker_type=broker_type.value,
                        config=config,
                        name=connection_name,
                        auto_connect=auto_connect,
                        set_as_default=True,
                    )
                    logger.info(f"Saved connection for {broker_type.value}")
                
                # Start connection monitor if not running
                self._start_connection_monitor()
                
                return True, None
            else:
                error_msg = getattr(broker, '_error_message', None) or f"Failed to connect to {broker_type.value}"
                self._log_connection_event(broker_type, "failed", error_msg)
                logger.error(f"Failed to connect to broker: {broker_type.value} - {error_msg}")
                return False, error_msg
                
        except Exception as e:
            self._log_connection_event(broker_type, "error", str(e))
            logger.error(f"Error connecting to {broker_type.value}: {e}")
            return False, str(e)
    
    async def connect_saved(self, connection_id: str) -> tuple[bool, Optional[str]]:
        """
        Connect using a saved connection configuration.
        
        Args:
            connection_id: ID of the saved connection to use.
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        saved_conns = get_saved_connections()
        config = saved_conns.get_connection_config(connection_id)
        
        if not config:
            return False, f"Saved connection not found: {connection_id}"
        
        conn = saved_conns.get_connection(connection_id)
        if not conn:
            return False, "Connection not found"
        
        try:
            broker_type = BrokerType(conn.broker_type)
        except ValueError:
            return False, f"Unknown broker type: {conn.broker_type}"
        
        # Mark as used
        saved_conns.mark_used(connection_id)
        
        # Connect using saved config
        success, error = await self.connect_broker(broker_type, **config)
        
        if success:
            logger.info(f"Connected using saved connection: {conn.name}")
        
        return success, error
    
    async def auto_connect_all(self) -> Dict[str, bool]:
        """
        Connect to all saved connections marked for auto-connect.
        
        Returns:
            Dict of connection_id -> success status
        """
        saved_conns = get_saved_connections()
        auto_connect_list = saved_conns.get_auto_connect_connections()
        
        if not auto_connect_list:
            logger.info("No auto-connect connections configured")
            return {}
        
        logger.info(f"Auto-connecting to {len(auto_connect_list)} saved connections...")
        results = {}
        
        for conn in auto_connect_list:
            success, error = await self.connect_saved(conn.id)
            results[conn.id] = success
            
            if success:
                logger.info(f"✅ Auto-connected: {conn.name}")
            else:
                logger.warning(f"❌ Auto-connect failed for {conn.name}: {error}")
        
        return results
    
    def _log_connection_event(self, broker_type: BrokerType, event: str, message: str):
        """Log a connection event for diagnostics."""
        self._connection_events.append({
            "timestamp": datetime.now().isoformat(),
            "broker": broker_type.value,
            "event": event,
            "message": message,
        })
        # Keep last 100 events
        if len(self._connection_events) > 100:
            self._connection_events = self._connection_events[-100:]
    
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
            },
            "auto_reconnect_enabled": self._auto_reconnect_enabled,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "recent_events": self._connection_events[-10:],
        }
    
    # =========================================================================
    # Auto-Reconnection System
    # =========================================================================
    
    def _start_connection_monitor(self):
        """Start the background connection monitor task."""
        if self._monitor_task is None or self._monitor_task.done():
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    self._monitor_task = asyncio.create_task(self._connection_monitor_loop())
                    logger.info("Started broker connection monitor")
            except RuntimeError:
                # No event loop running yet
                pass
    
    def stop_connection_monitor(self):
        """Stop the connection monitor."""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            logger.info("Stopped broker connection monitor")
    
    async def _connection_monitor_loop(self):
        """Background task that monitors broker connections and reconnects if needed."""
        logger.info("Connection monitor started - will check every {self._health_check_interval}s")
        
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if not self._auto_reconnect_enabled:
                    continue
                
                self._last_health_check = datetime.now()
                
                # Check each connected broker
                for broker_type in list(self._brokers.keys()):
                    await self._check_and_reconnect(broker_type)
                
                # Also try to reconnect brokers that were previously connected but dropped
                for broker_type in list(self._connection_configs.keys()):
                    if broker_type not in self._brokers:
                        await self._attempt_reconnect(broker_type)
                
            except asyncio.CancelledError:
                logger.info("Connection monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Connection monitor error: {e}")
                await asyncio.sleep(10)  # Brief pause on error
    
    async def _check_and_reconnect(self, broker_type: BrokerType):
        """Check if a broker is connected and reconnect if needed."""
        broker = self._brokers.get(broker_type)
        if not broker:
            return
        
        try:
            # Check actual connection status
            is_healthy = await broker.health_check()
            
            if not is_healthy:
                logger.warning(f"Broker {broker_type.value} health check failed - attempting reconnect")
                self._log_connection_event(broker_type, "disconnected", "Health check failed")
                
                # Remove from active brokers
                del self._brokers[broker_type]
                
                # Attempt reconnection
                await self._attempt_reconnect(broker_type)
            else:
                # Reset reconnect attempts on successful health check
                self._reconnect_attempts[broker_type] = 0
                
        except Exception as e:
            logger.error(f"Error checking broker {broker_type.value}: {e}")
            self._log_connection_event(broker_type, "error", f"Health check error: {e}")
    
    async def _attempt_reconnect(self, broker_type: BrokerType):
        """Attempt to reconnect to a broker."""
        if broker_type not in self._connection_configs:
            logger.debug(f"No stored config for {broker_type.value}, cannot reconnect")
            return
        
        attempts = self._reconnect_attempts.get(broker_type, 0)
        
        if attempts >= self._max_reconnect_attempts:
            logger.warning(f"Max reconnect attempts ({self._max_reconnect_attempts}) reached for {broker_type.value}")
            return
        
        self._reconnect_attempts[broker_type] = attempts + 1
        
        config = self._connection_configs[broker_type]
        logger.info(f"Attempting to reconnect to {broker_type.value} (attempt {attempts + 1}/{self._max_reconnect_attempts})")
        self._log_connection_event(broker_type, "reconnecting", f"Attempt {attempts + 1}")
        
        try:
            broker_class = self._broker_classes[broker_type]
            broker = broker_class(**config)
            
            if await broker.connect():
                self._brokers[broker_type] = broker
                self._reconnect_attempts[broker_type] = 0
                
                self._log_connection_event(broker_type, "reconnected", "Successfully reconnected")
                logger.info(f"Successfully reconnected to {broker_type.value}")
                
                # Restore as default if it was the default
                if self._default_broker is None:
                    self._default_broker = broker_type
            else:
                error_msg = getattr(broker, '_error_message', None) or "Unknown error"
                self._log_connection_event(broker_type, "reconnect_failed", error_msg)
                logger.warning(f"Reconnection to {broker_type.value} failed: {error_msg}")
                
        except Exception as e:
            self._log_connection_event(broker_type, "reconnect_error", str(e))
            logger.error(f"Reconnection error for {broker_type.value}: {e}")
    
    async def force_reconnect(self, broker_type: BrokerType) -> bool:
        """Force a reconnection attempt for a specific broker."""
        if broker_type not in self._connection_configs:
            logger.error(f"No stored config for {broker_type.value}")
            return False
        
        # Disconnect if currently connected
        if broker_type in self._brokers:
            await self.disconnect_broker(broker_type)
        
        # Reset attempts and reconnect
        self._reconnect_attempts[broker_type] = 0
        
        config = self._connection_configs[broker_type]
        success, _ = await self.connect_broker(broker_type, **config)
        return success
    
    def set_auto_reconnect(self, enabled: bool):
        """Enable or disable auto-reconnection."""
        self._auto_reconnect_enabled = enabled
        logger.info(f"Auto-reconnect {'enabled' if enabled else 'disabled'}")
    
    def get_connection_events(self, limit: int = 50) -> List[Dict]:
        """Get recent connection events."""
        return self._connection_events[-limit:]


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
    logger.info("Registering default broker implementations...")
    
    # Import and register broker implementations
    try:
        from src.brokers.alpaca_broker import AlpacaBroker
        registry.register_broker_class(BrokerType.ALPACA, AlpacaBroker)
    except ImportError as e:
        logger.debug(f"Alpaca broker not available: {e}")
    
    try:
        from src.brokers.ibkr_broker import IBKRBroker
        registry.register_broker_class(BrokerType.IBKR, IBKRBroker)
        logger.info("IBKR broker registered successfully")
    except ImportError as e:
        logger.warning(f"IBKR broker not available: {e}")
    
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

