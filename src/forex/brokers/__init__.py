"""
Forex Broker Integrations

Supports multiple Forex brokers:
- MetaTrader 4/5
- OANDA
- FXCM
- IG Markets
"""

from src.forex.brokers.metatrader import (
    MetaTraderClient,
    MT5Config,
    MT5OrderType,
    MT5Timeframe,
    get_metatrader_client,
)
from src.forex.brokers.oanda import (
    OANDAClient,
    OANDAConfig,
    get_oanda_client,
)

__all__ = [
    # MetaTrader
    "MetaTraderClient",
    "MT5Config",
    "MT5OrderType",
    "MT5Timeframe",
    "get_metatrader_client",
    # OANDA
    "OANDAClient",
    "OANDAConfig",
    "get_oanda_client",
]

