"""
Multi-Broker Integration Layer for XFactor Bot.
Supports multiple brokers for trading execution.
"""

from src.brokers.base import BaseBroker, BrokerType, OrderStatus, Position, Order
from src.brokers.registry import BrokerRegistry, get_broker_registry
from src.brokers.saved_connections import (
    SavedConnection,
    SavedConnectionsManager,
    get_saved_connections,
)

# v1.0.1 - NinjaTrader integration
from src.brokers.ninjatrader import (
    NinjaTraderClient,
    NTConnectionConfig,
    NTOrderAction,
    NTOrderType,
    get_ninjatrader_client,
)

__all__ = [
    "BaseBroker",
    "BrokerType", 
    "OrderStatus",
    "Position",
    "Order",
    "BrokerRegistry",
    "get_broker_registry",
    # Saved Connections
    "SavedConnection",
    "SavedConnectionsManager",
    "get_saved_connections",
    # NinjaTrader
    "NinjaTraderClient",
    "NTConnectionConfig",
    "NTOrderAction",
    "NTOrderType",
    "get_ninjatrader_client",
]

