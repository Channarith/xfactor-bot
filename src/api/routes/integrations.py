"""
API routes for managing broker and data source integrations.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

from src.brokers import BrokerType, get_broker_registry
from src.brokers.saved_connections import get_saved_connections
from src.data_sources import DataSourceType, get_data_registry
from src.banking import get_plaid_client


router = APIRouter()


# =========================================================================
# Request/Response Models
# =========================================================================

class BrokerConnectRequest(BaseModel):
    """Request to connect a broker."""
    broker_type: str
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    api_secret: Optional[str] = None  # Alias for secret_key (backwards compatibility)
    account_id: Optional[str] = None
    paper: bool = True
    # IBKR-specific fields
    host: Optional[str] = None
    port: Optional[int] = None
    client_id: Optional[int] = None
    paper_trading: Optional[bool] = None
    # Save connection options
    save_connection: bool = False
    connection_name: Optional[str] = None
    auto_connect: bool = False
    # Additional config can be passed
    config: Dict[str, Any] = {}
    
    @property
    def effective_secret_key(self) -> Optional[str]:
        """Get secret key from either field."""
        return self.secret_key or self.api_secret


class CredentialLoginRequest(BaseModel):
    """Request for credential-based broker login (deprecated - use /brokers/connect)."""
    broker_type: str
    username: str
    password: str
    mfa_code: str = ""
    device_token: Optional[str] = None


class DataSourceConnectRequest(BaseModel):
    """Request to connect a data source."""
    source_type: str
    api_key: str = ""
    config: Dict[str, Any] = {}


class PlaidLinkRequest(BaseModel):
    """Request for Plaid link token."""
    user_id: str
    redirect_uri: Optional[str] = None


class PlaidExchangeRequest(BaseModel):
    """Request to exchange Plaid public token."""
    public_token: str


class TransferRequest(BaseModel):
    """Bank transfer request."""
    bank_account_id: str
    brokerage_account_id: str
    broker_name: str
    amount: float
    direction: str  # "deposit" or "withdraw"
    description: str = ""


# =========================================================================
# Broker Routes
# =========================================================================

@router.get("/brokers")
async def get_brokers() -> Dict[str, Any]:
    """Get all available and connected brokers."""
    registry = get_broker_registry()
    return {
        "available": [b.value for b in BrokerType],
        "connected": registry.to_dict(),
    }


@router.post("/brokers/connect")
async def connect_broker(request: BrokerConnectRequest) -> Dict[str, Any]:
    """Connect to a broker."""
    from loguru import logger
    logger.info(f"Connecting to broker: {request.broker_type}")
    
    # Use effective_secret_key which handles both 'secret_key' and 'api_secret' fields
    effective_secret = request.effective_secret_key
    logger.debug(f"API key provided: {bool(request.api_key)}, Secret key provided: {bool(effective_secret)}")
    
    registry = get_broker_registry()
    logger.debug(f"Available brokers: {[b.value for b in registry.available_brokers]}")
    
    try:
        broker_type = BrokerType(request.broker_type.lower())
    except ValueError:
        raise HTTPException(400, f"Unknown broker type: {request.broker_type}")
    
    # Validate required credentials for API-key based brokers
    if broker_type.value == "alpaca":
        if not request.api_key:
            raise HTTPException(400, "API key is required for Alpaca")
        if not effective_secret:
            raise HTTPException(400, "Secret key is required for Alpaca")
        logger.info(f"Alpaca credentials: api_key={request.api_key[:8]}..., secret_len={len(effective_secret)}")
    
    config = {
        "api_key": request.api_key,
        "secret_key": effective_secret,  # Use effective_secret_key
        "account_id": request.account_id,
        "paper": request.paper_trading if request.paper_trading is not None else request.paper,
        # IBKR-specific
        "host": request.host or "127.0.0.1",
        "port": request.port or 7497,
        "client_id": request.client_id or 1,
        **request.config
    }
    
    success, error_msg = await registry.connect_broker(
        broker_type,
        save_connection=request.save_connection,
        connection_name=request.connection_name,
        auto_connect=request.auto_connect,
        **config
    )
    
    if success:
        # Fetch account data after successful connection
        response_data = {
            "status": "connected", 
            "broker": broker_type.value,
            "account_id": config.get("account_id"),
            "account_type": "paper" if config.get("paper") else "live",
            "saved": request.save_connection,
            "auto_connect": request.auto_connect if request.save_connection else False,
        }
        
        # Try to get real account data (with timeout to prevent blocking)
        try:
            broker = registry.get_broker(broker_type)
            if broker and broker.is_connected:
                import asyncio
                try:
                    accounts = await asyncio.wait_for(broker.get_accounts(), timeout=10.0)
                    if accounts:
                        account = accounts[0]
                        response_data["account_id"] = account.account_id
                        response_data["portfolio_value"] = account.equity
                        response_data["buying_power"] = account.buying_power
                        response_data["cash"] = account.cash
                        
                        # Log and validate account limits
                        logger.info(f"✅ Account Connected: {broker_type.value}")
                        logger.info(f"   Account ID: {account.account_id}")
                        logger.info(f"   Equity: ${account.equity:,.2f}")
                        logger.info(f"   Cash: ${account.cash:,.2f}")
                        logger.info(f"   Buying Power: ${account.buying_power:,.2f}")
                        
                        # Validate expected limits for paper trading
                        if config.get("paper"):
                            if broker_type.value == "alpaca":
                                expected_equity = 100_000.0
                                if abs(account.equity - expected_equity) > 1000 and account.equity < expected_equity:
                                    logger.warning(f"⚠️ Alpaca paper account equity (${account.equity:,.2f}) differs from expected (${expected_equity:,.2f})")
                                    response_data["warning"] = f"Paper account has ${account.equity:,.2f}, expected ${expected_equity:,.2f}. You can reset your paper account at alpaca.markets"
                            elif broker_type.value == "ibkr":
                                expected_equity = 1_000_000.0
                                if account.equity < 100_000:  # Flag if significantly lower
                                    logger.warning(f"⚠️ IBKR paper account equity (${account.equity:,.2f}) is below ${100_000:,.2f}")
                                    
                except asyncio.TimeoutError:
                    logger.warning("Timed out fetching account data, but connection succeeded")
        except Exception as e:
            logger.warning(f"Could not fetch account data after connect: {e}")
        
        if request.save_connection:
            logger.info(f"Connection saved for future use (auto_connect={request.auto_connect})")
        
        return response_data
    else:
        raise HTTPException(500, error_msg or f"Failed to connect to {broker_type.value}")


@router.post("/brokers/login")
async def credential_login(request: CredentialLoginRequest) -> Dict[str, Any]:
    """
    Login to a credential-based broker.
    
    Note: Credential-based login (username/password) is not currently supported.
    All supported brokers use API key authentication via /brokers/connect.
    """
    raise HTTPException(400, "Credential-based login is not supported. Use /brokers/connect with API keys instead.")


@router.post("/brokers/disconnect/{broker_type}")
async def disconnect_broker(broker_type: str) -> Dict[str, Any]:
    """Disconnect from a broker."""
    registry = get_broker_registry()
    
    try:
        bt = BrokerType(broker_type.lower())
    except ValueError:
        raise HTTPException(400, f"Unknown broker type: {broker_type}")
    
    await registry.disconnect_broker(bt)
    return {"status": "disconnected", "broker": broker_type}


@router.post("/brokers/reconnect/{broker_type}")
async def reconnect_broker(broker_type: str) -> Dict[str, Any]:
    """
    Force reconnection to a broker.
    
    Useful when TWS/Gateway has restarted and you need to reconnect.
    Uses stored connection config from the initial connection.
    """
    registry = get_broker_registry()
    
    try:
        bt = BrokerType(broker_type.lower())
    except ValueError:
        raise HTTPException(400, f"Unknown broker type: {broker_type}")
    
    success = await registry.force_reconnect(bt)
    
    if success:
        return {"status": "reconnected", "broker": broker_type}
    else:
        raise HTTPException(500, f"Failed to reconnect to {broker_type}")


@router.get("/brokers/connection-events")
async def get_connection_events(limit: int = 50) -> Dict[str, Any]:
    """
    Get recent broker connection events.
    
    Useful for debugging connection issues and monitoring auto-reconnection.
    """
    registry = get_broker_registry()
    
    return {
        "events": registry.get_connection_events(limit),
        "auto_reconnect_enabled": registry._auto_reconnect_enabled,
        "health_check_interval": registry._health_check_interval,
        "last_health_check": registry._last_health_check.isoformat() if registry._last_health_check else None,
    }


@router.post("/brokers/auto-reconnect")
async def set_auto_reconnect(enabled: bool = True) -> Dict[str, Any]:
    """Enable or disable automatic broker reconnection."""
    registry = get_broker_registry()
    registry.set_auto_reconnect(enabled)
    
    return {
        "auto_reconnect_enabled": enabled,
        "message": f"Auto-reconnect {'enabled' if enabled else 'disabled'}",
    }


# =========================================================================
# Saved Connections Management
# =========================================================================

@router.get("/brokers/saved")
async def get_saved_broker_connections() -> Dict[str, Any]:
    """
    Get all saved broker connections.
    
    Credentials are masked in the response for security.
    """
    saved = get_saved_connections()
    return saved.to_dict()


@router.post("/brokers/saved/connect/{connection_id}")
async def connect_saved_broker(connection_id: str) -> Dict[str, Any]:
    """
    Connect using a previously saved connection.
    
    Args:
        connection_id: The ID of the saved connection to use.
    """
    registry = get_broker_registry()
    success, error = await registry.connect_saved(connection_id)
    
    if success:
        return {
            "status": "connected",
            "connection_id": connection_id,
            "message": "Successfully connected using saved connection",
        }
    else:
        raise HTTPException(400, error or "Failed to connect")


@router.post("/brokers/saved/auto-connect")
async def auto_connect_saved_brokers() -> Dict[str, Any]:
    """
    Connect to all brokers marked for auto-connect.
    
    This is typically called on application startup.
    """
    registry = get_broker_registry()
    results = await registry.auto_connect_all()
    
    successful = sum(1 for v in results.values() if v)
    failed = len(results) - successful
    
    return {
        "results": results,
        "successful": successful,
        "failed": failed,
        "message": f"Auto-connected {successful} of {len(results)} saved connections",
    }


class SaveConnectionRequest(BaseModel):
    """Request to update a saved connection."""
    name: Optional[str] = None
    auto_connect: Optional[bool] = None
    set_as_default: Optional[bool] = None


@router.patch("/brokers/saved/{connection_id}")
async def update_saved_connection(
    connection_id: str,
    request: SaveConnectionRequest
) -> Dict[str, Any]:
    """Update a saved connection's settings."""
    saved = get_saved_connections()
    
    conn = saved.update_connection(
        connection_id,
        name=request.name,
        auto_connect=request.auto_connect,
        set_as_default=request.set_as_default,
    )
    
    if not conn:
        raise HTTPException(404, "Saved connection not found")
    
    return {
        "status": "updated",
        "connection": {
            "id": conn.id,
            "name": conn.name,
            "auto_connect": conn.auto_connect,
            "is_default": conn.is_default,
        }
    }


@router.delete("/brokers/saved/{connection_id}")
async def delete_saved_connection(connection_id: str) -> Dict[str, Any]:
    """Delete a saved connection."""
    saved = get_saved_connections()
    
    if not saved.delete_connection(connection_id):
        raise HTTPException(404, "Saved connection not found")
    
    return {"status": "deleted", "connection_id": connection_id}


@router.get("/broker/status")
async def get_broker_status() -> Dict[str, Any]:
    """Get the current broker connection status."""
    registry = get_broker_registry()
    
    if not registry.connected_brokers:
        return {"connected": False}
    
    # Get the first connected broker
    broker_type = list(registry.connected_brokers)[0]
    broker = registry.get_broker(broker_type)
    
    if not broker or not broker.is_connected:
        return {"connected": False}
    
    response = {
        "connected": True,
        "provider": broker_type.value,
    }
    
    try:
        accounts = await broker.get_accounts()
        if accounts:
            account = accounts[0]
            response["account_id"] = account.account_id
            response["account_type"] = account.account_type
            response["portfolio_value"] = account.equity
            response["buying_power"] = account.buying_power
            response["cash"] = account.cash
            response["last_sync"] = account.last_updated.isoformat() if account.last_updated else None
    except Exception as e:
        logger.warning(f"Could not fetch account data for status: {e}")
    
    return response


@router.get("/brokers/{broker_type}/diagnostics")
async def get_broker_diagnostics(broker_type: str) -> Dict[str, Any]:
    """
    Get detailed diagnostic information for a broker.
    
    Useful for debugging connection issues, timeouts, and caching behavior.
    """
    registry = get_broker_registry()
    
    try:
        bt = BrokerType(broker_type.lower())
    except ValueError:
        raise HTTPException(400, f"Unknown broker type: {broker_type}")
    
    broker = registry.get_broker(bt)
    if not broker:
        return {
            "broker": broker_type,
            "connected": False,
            "message": "Broker not connected",
            "available": bt in registry.available_brokers,
        }
    
    # Get diagnostics if method exists
    diagnostics = {}
    if hasattr(broker, 'get_diagnostics'):
        diagnostics = broker.get_diagnostics()
    else:
        diagnostics = {
            "connected": broker.is_connected,
            "error_message": getattr(broker, '_error_message', None),
        }
    
    # Add health check
    try:
        health = await broker.health_check()
        diagnostics["health_check"] = "OK" if health else "FAILED"
    except Exception as e:
        diagnostics["health_check"] = f"ERROR: {e}"
    
    # Add registry info
    diagnostics["broker"] = broker_type
    diagnostics["is_default"] = registry._default_broker == bt
    diagnostics["reconnect_attempts"] = registry._reconnect_attempts.get(bt, 0)
    
    return diagnostics


@router.get("/brokers/{broker_type}/accounts")
async def get_broker_accounts(broker_type: str) -> Dict[str, Any]:
    """Get accounts for a connected broker."""
    registry = get_broker_registry()
    
    try:
        bt = BrokerType(broker_type.lower())
    except ValueError:
        raise HTTPException(400, f"Unknown broker type: {broker_type}")
    
    broker = registry.get_broker(bt)
    if not broker:
        raise HTTPException(404, f"Broker not connected: {broker_type}")
    
    accounts = await broker.get_accounts()
    return {
        "broker": broker_type,
        "accounts": [
            {
                "account_id": a.account_id,
                "type": a.account_type,
                "buying_power": a.buying_power,
                "portfolio_value": a.portfolio_value,
                "cash": a.cash,
            }
            for a in accounts
        ]
    }


@router.get("/brokers/portfolio")
async def get_total_portfolio() -> Dict[str, Any]:
    """Get aggregated portfolio across all brokers."""
    registry = get_broker_registry()
    
    total_value = await registry.get_total_portfolio_value()
    total_buying_power = await registry.get_total_buying_power()
    all_accounts = await registry.get_all_accounts()
    
    return {
        "total_portfolio_value": total_value,
        "total_buying_power": total_buying_power,
        "by_broker": {
            bt.value: [
                {
                    "account_id": a.account_id,
                    "portfolio_value": a.portfolio_value,
                    "buying_power": a.buying_power,
                }
                for a in accounts
            ]
            for bt, accounts in all_accounts.items()
        }
    }


class OrderRequest(BaseModel):
    """Order request model."""
    broker_type: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    order_type: str = "market"  # "market", "limit", "stop"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None


@router.post("/brokers/order")
async def submit_order(request: OrderRequest) -> Dict[str, Any]:
    """
    Submit an order through a connected broker.
    
    This endpoint allows testing broker connectivity with real orders.
    Use with caution - this will execute real trades if connected to a live account!
    """
    from src.brokers.base import OrderSide, OrderType
    
    registry = get_broker_registry()
    
    # Validate broker type
    try:
        bt = BrokerType(request.broker_type.lower())
    except ValueError:
        raise HTTPException(400, f"Unknown broker type: {request.broker_type}")
    
    # Get broker
    broker = registry.get_broker(bt)
    if not broker:
        raise HTTPException(404, f"Broker not connected: {request.broker_type}")
    
    if not broker.is_connected:
        raise HTTPException(400, f"Broker {request.broker_type} is not connected")
    
    # Get account
    try:
        accounts = await broker.get_accounts()
        if not accounts:
            raise HTTPException(400, "No accounts available")
        account_id = accounts[0].account_id
    except Exception as e:
        raise HTTPException(500, f"Failed to get account: {e}")
    
    # Map order side
    try:
        side = OrderSide(request.side.upper())
    except ValueError:
        raise HTTPException(400, f"Invalid side: {request.side}. Use 'buy' or 'sell'")
    
    # Map order type
    order_type_map = {
        "market": OrderType.MARKET,
        "limit": OrderType.LIMIT,
        "stop": OrderType.STOP,
    }
    order_type = order_type_map.get(request.order_type.lower())
    if not order_type:
        raise HTTPException(400, f"Invalid order type: {request.order_type}")
    
    # Submit order
    try:
        order = await broker.submit_order(
            account_id=account_id,
            symbol=request.symbol.upper(),
            side=side,
            quantity=request.quantity,
            order_type=order_type,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
        )
        
        return {
            "status": "success",
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "order_type": order.order_type.value,
            "order_status": order.status.value,
            "broker": request.broker_type,
        }
    except Exception as e:
        logger.error(f"Order submission failed: {e}")
        raise HTTPException(500, f"Order failed: {str(e)}")


# =========================================================================
# Data Source Routes
# =========================================================================

@router.get("/data-sources")
async def get_data_sources() -> Dict[str, Any]:
    """Get available and connected data sources."""
    registry = get_data_registry()
    return {
        "available": [s.value for s in DataSourceType],
        "connected": registry.to_dict(),
    }


@router.post("/data-sources/connect")
async def connect_data_source(request: DataSourceConnectRequest) -> Dict[str, Any]:
    """Connect to a data source."""
    registry = get_data_registry()
    
    try:
        source_type = DataSourceType(request.source_type.lower())
    except ValueError:
        raise HTTPException(400, f"Unknown data source: {request.source_type}")
    
    config = {"api_key": request.api_key, **request.config}
    success = await registry.connect_source(source_type, **config)
    
    if success:
        return {"status": "connected", "source": source_type.value}
    else:
        raise HTTPException(500, f"Failed to connect to {source_type.value}")


@router.get("/data-sources/quote/{symbol}")
async def get_quote(symbol: str, source: Optional[str] = None) -> Dict[str, Any]:
    """Get quote for a symbol."""
    registry = get_data_registry()
    
    source_type = None
    if source:
        try:
            source_type = DataSourceType(source.lower())
        except ValueError:
            raise HTTPException(400, f"Unknown data source: {source}")
    
    quote = await registry.get_quote(symbol.upper(), source_type)
    
    if quote:
        return {
            "symbol": quote.symbol,
            "bid": quote.bid,
            "ask": quote.ask,
            "last": quote.last,
            "volume": quote.volume,
            "source": quote.source.value,
            "timestamp": quote.timestamp.isoformat(),
        }
    else:
        raise HTTPException(404, f"No quote available for {symbol}")


# =========================================================================
# Banking Routes (Plaid)
# =========================================================================

@router.get("/banking/status")
async def get_banking_status() -> Dict[str, Any]:
    """Get Plaid banking integration status."""
    client = get_plaid_client()
    return client.to_dict()


@router.post("/banking/link-token")
async def create_link_token(request: PlaidLinkRequest) -> Dict[str, Any]:
    """Create Plaid Link token for frontend."""
    client = get_plaid_client()
    
    if not await client.initialize():
        raise HTTPException(500, "Plaid not configured")
    
    token = await client.create_link_token(
        user_id=request.user_id,
        redirect_uri=request.redirect_uri
    )
    
    if token:
        return {"link_token": token}
    else:
        raise HTTPException(500, "Failed to create link token")


@router.post("/banking/exchange-token")
async def exchange_public_token(request: PlaidExchangeRequest) -> Dict[str, Any]:
    """Exchange Plaid public token for access token."""
    client = get_plaid_client()
    
    access_token = await client.exchange_public_token(request.public_token)
    
    if access_token:
        accounts = await client.get_linked_accounts()
        return {
            "status": "linked",
            "accounts": [
                {
                    "account_id": a.account_id,
                    "institution": a.institution_name,
                    "name": a.account_name,
                    "type": a.account_type,
                    "mask": a.account_mask,
                }
                for a in accounts
            ]
        }
    else:
        raise HTTPException(500, "Failed to exchange token")


@router.get("/banking/accounts")
async def get_linked_bank_accounts() -> Dict[str, Any]:
    """Get all linked bank accounts."""
    client = get_plaid_client()
    accounts = await client.get_linked_accounts()
    
    return {
        "accounts": [
            {
                "account_id": a.account_id,
                "institution": a.institution_name,
                "name": a.account_name,
                "type": a.account_type,
                "mask": a.account_mask,
                "available_balance": a.available_balance,
                "current_balance": a.current_balance,
                "verified": a.verified,
            }
            for a in accounts
        ]
    }


@router.post("/banking/transfer")
async def initiate_transfer(request: TransferRequest) -> Dict[str, Any]:
    """Initiate a bank transfer."""
    from src.banking.plaid_client import TransferDirection
    
    client = get_plaid_client()
    
    try:
        direction = TransferDirection(request.direction.lower())
    except ValueError:
        raise HTTPException(400, "Direction must be 'deposit' or 'withdraw'")
    
    transfer = await client.initiate_transfer(
        account_id=request.bank_account_id,
        amount=request.amount,
        direction=direction,
        brokerage_account_id=request.brokerage_account_id,
        broker_name=request.broker_name,
        description=request.description
    )
    
    if transfer:
        return {
            "transfer_id": transfer.transfer_id,
            "status": transfer.status.value,
            "amount": transfer.amount,
            "direction": transfer.direction.value,
        }
    else:
        raise HTTPException(500, "Failed to initiate transfer")


# =========================================================================
# TradingView Webhook
# =========================================================================

@router.post("/webhooks/tradingview")
async def tradingview_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle TradingView webhook alerts."""
    from src.data_sources.tradingview import get_tradingview_webhook
    
    webhook = get_tradingview_webhook()
    alert = await webhook.handle_webhook(data)
    
    if alert:
        return {
            "status": "received",
            "action": alert.action.value,
            "symbol": alert.symbol,
            "price": alert.price,
        }
    else:
        raise HTTPException(400, "Invalid webhook payload")


@router.get("/webhooks/tradingview/alerts")
async def get_tradingview_alerts(
    limit: int = 50,
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """Get recent TradingView alerts."""
    from src.data_sources.tradingview import get_tradingview_webhook
    
    webhook = get_tradingview_webhook()
    alerts = webhook.get_recent_alerts(limit=limit, symbol=symbol)
    
    return {
        "alerts": [
            {
                "action": a.action.value,
                "symbol": a.symbol,
                "price": a.price,
                "strategy": a.strategy,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in alerts
        ]
    }


# =========================================================================
# AInvest AI Routes
# =========================================================================

@router.get("/ainvest/recommendations")
async def get_ainvest_recommendations(
    symbols: Optional[str] = None,
    min_score: float = 0,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get AI-powered stock recommendations from AInvest.
    
    Args:
        symbols: Comma-separated list of ticker symbols (optional)
        min_score: Minimum AI score (0-100)
        limit: Maximum number of recommendations (max 100)
    """
    from src.data_sources.ainvest import AInvestDataSource
    
    ainvest = AInvestDataSource()
    await ainvest.connect()
    
    symbol_list = symbols.split(",") if symbols else None
    recommendations = await ainvest.get_ai_recommendations(
        symbols=symbol_list,
        min_score=min_score,
        limit=min(limit, 100)
    )
    
    return {
        "count": len(recommendations),
        "recommendations": [
            {
                "symbol": r.symbol,
                "company": r.company,
                "ai_score": r.ai_score,
                "recommendation": r.recommendation,
                "target_price": r.target_price,
                "current_price": r.current_price,
                "upside_pct": r.upside_pct,
                "signals": r.signals,
                "confidence": r.confidence,
                "analysis_date": r.analysis_date.isoformat(),
            }
            for r in recommendations
        ]
    }


@router.get("/ainvest/sentiment/{symbol}")
async def get_ainvest_sentiment(symbol: str) -> Dict[str, Any]:
    """Get AI sentiment analysis for a stock."""
    from src.data_sources.ainvest import AInvestDataSource
    
    ainvest = AInvestDataSource()
    await ainvest.connect()
    
    sentiment = await ainvest.get_sentiment(symbol.upper())
    
    if sentiment:
        return {
            "symbol": sentiment.symbol,
            "overall_sentiment": sentiment.overall_sentiment,
            "news_sentiment": sentiment.news_sentiment,
            "social_sentiment": sentiment.social_sentiment,
            "analyst_sentiment": sentiment.analyst_sentiment,
            "volume_sentiment": sentiment.volume_sentiment,
            "last_updated": sentiment.last_updated.isoformat(),
        }
    else:
        raise HTTPException(404, f"No sentiment data for {symbol}")


@router.get("/ainvest/signals")
async def get_ainvest_signals(
    signal_type: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Get AI-generated trading signals from AInvest."""
    from src.data_sources.ainvest import AInvestDataSource
    
    ainvest = AInvestDataSource()
    await ainvest.connect()
    
    signals = await ainvest.get_trading_signals(
        signal_type=signal_type,
        limit=min(limit, 100)
    )
    
    return {
        "count": len(signals),
        "signals": [
            {
                "source": s.source,
                "signal_type": s.signal_type,
                "symbol": s.symbol,
                "timestamp": s.timestamp.isoformat(),
                "strength": s.strength,
                "price": s.price,
                "target_price": s.target_price,
                "confidence": s.confidence,
                "reasoning": s.reasoning,
            }
            for s in signals
        ]
    }


@router.get("/ainvest/insider-trades")
async def get_ainvest_insider_trades(limit: int = 100) -> Dict[str, Any]:
    """Get insider trading data via AInvest."""
    from src.data_sources.ainvest import AInvestDataSource
    
    ainvest = AInvestDataSource()
    await ainvest.connect()
    
    trades = await ainvest.get_insider_trades(limit=min(limit, 100))
    
    return {
        "count": len(trades),
        "trades": [
            {
                "symbol": t.symbol,
                "insider_name": t.insider_name,
                "title": t.title,
                "transaction_type": t.transaction_type,
                "value": t.value,
                "shares": t.shares,
                "price": t.price,
                "shares_owned_after": t.shares_owned_after,
                "transaction_date": t.transaction_date.isoformat(),
                "filing_date": t.filing_date.isoformat(),
            }
            for t in trades
        ]
    }


@router.get("/ainvest/earnings")
async def get_ainvest_earnings(
    days: int = 30,
    limit: int = 100
) -> Dict[str, Any]:
    """Get upcoming earnings calendar from AInvest."""
    from src.data_sources.ainvest import AInvestDataSource
    from datetime import datetime, timedelta
    
    ainvest = AInvestDataSource()
    await ainvest.connect()
    
    start_date = datetime.now()
    end_date = start_date + timedelta(days=days)
    
    earnings = await ainvest.get_earnings_calendar(
        start_date=start_date,
        end_date=end_date,
        limit=min(limit, 100)
    )
    
    return {
        "count": len(earnings),
        "earnings": earnings
    }


@router.get("/ainvest/news")
async def get_ainvest_news(
    symbols: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Get news articles from AInvest."""
    from src.data_sources.ainvest import AInvestDataSource
    
    ainvest = AInvestDataSource()
    await ainvest.connect()
    
    symbol_list = symbols.split(",") if symbols else None
    news = await ainvest.get_news(
        symbols=symbol_list,
        limit=min(limit, 100)
    )
    
    return {
        "count": len(news),
        "articles": [
            {
                "title": n.title,
                "url": n.url,
                "source": n.source,
                "published_at": n.published.isoformat(),
                "sentiment": n.sentiment,
                "symbols": n.symbols,
            }
            for n in news
        ]
    }


# =========================================================================
# AI Provider Configuration Routes
# =========================================================================

class AIProviderConfigRequest(BaseModel):
    """Request to configure an AI provider."""
    provider: str  # "openai", "ollama", "anthropic"
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True


@router.get("/ai/providers")
async def get_ai_providers() -> Dict[str, Any]:
    """Get all AI providers and their status.
    
    Priority order:
    1. Anthropic Claude (default, best for trading analysis)
    2. Ollama (local fallback, bundled with XFactor)
    3. OpenAI GPT (alternative cloud option)
    """
    from src.config.settings import get_settings
    
    settings = get_settings()
    
    # Check Ollama availability (use resolved host for Docker compatibility)
    ollama_status = "offline"
    ollama_version = None
    ollama_resolved_host = settings.ollama_host_resolved
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_resolved_host}/api/version", timeout=2.0)
            if response.status_code == 200:
                ollama_status = "available"
                ollama_version = response.json().get("version")
    except Exception:
        pass
    
    return {
        "current_provider": settings.llm_provider,
        "fallback_enabled": settings.llm_fallback_to_ollama,
        "providers": [
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "description": "Best for trading analysis (default)",
                "configured": bool(settings.anthropic_api_key),
                "model": settings.anthropic_model,
                "status": "ready" if settings.anthropic_api_key else "not_configured",
                "priority": 1,
                "recommended": True,
            },
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "description": "Local AI, no API key needed (fallback)",
                "configured": True,  # Always configured since it's local
                "model": settings.ollama_model,
                "host": settings.ollama_host,
                "status": ollama_status,
                "version": ollama_version,
                "auto_start": settings.ollama_auto_start,
                "priority": 2,
                "is_fallback": True,
            },
            {
                "id": "openai",
                "name": "OpenAI GPT",
                "description": "Alternative cloud provider",
                "configured": bool(settings.openai_api_key),
                "model": settings.openai_model,
                "status": "ready" if settings.openai_api_key else "not_configured",
                "priority": 3,
            },
        ]
    }


class TestProviderRequest(BaseModel):
    """Optional request body for testing AI provider with custom credentials."""
    api_key: Optional[str] = None
    host: Optional[str] = None


@router.post("/ai/providers/{provider}/test")
async def test_ai_provider(provider: str, request: Optional[TestProviderRequest] = None) -> Dict[str, Any]:
    """Test an AI provider connection.
    
    Optionally accepts credentials in the request body to test before saving.
    If no credentials provided, tests with saved configuration.
    """
    from src.config.settings import get_settings
    
    settings = get_settings()
    
    # Use provided credentials or fall back to saved settings
    test_api_key = request.api_key if request and request.api_key else None
    test_host = request.host if request and request.host else None
    
    if provider == "openai":
        api_key = test_api_key or settings.openai_api_key
        if not api_key:
            return {"status": "error", "message": "OpenAI API key not configured. Set OPENAI_API_KEY in .env"}
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "OpenAI connection successful"}
                elif response.status_code == 401:
                    return {"status": "error", "message": "Invalid API key"}
                else:
                    return {"status": "error", "message": f"OpenAI API error: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to connect to OpenAI: {str(e)}"}
    
    elif provider == "ollama":
        # Use provided host or resolved host for Docker compatibility
        ollama_host = test_host or settings.ollama_host_resolved
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{ollama_host}/api/version", timeout=5.0)
                if response.status_code == 200:
                    version_data = response.json()
                    # Also check if the model is available
                    models_response = await client.get(f"{ollama_host}/api/tags", timeout=5.0)
                    models = []
                    if models_response.status_code == 200:
                        models_data = models_response.json()
                        models = [m.get("name", "") for m in models_data.get("models", [])]
                    
                    model_available = settings.ollama_model in models or any(settings.ollama_model in m for m in models)
                    
                    return {
                        "status": "success",
                        "message": f"Ollama v{version_data.get('version', 'unknown')} is running",
                        "available_models": models[:10],  # Limit to 10
                        "configured_model": settings.ollama_model,
                        "model_available": model_available
                    }
                else:
                    return {"status": "error", "message": "Ollama server not responding"}
        except Exception as e:
            return {"status": "error", "message": f"Ollama not running at {settings.ollama_host}. Start Ollama first."}
    
    elif provider == "anthropic":
        api_key = test_api_key or settings.anthropic_api_key
        if not api_key:
            return {"status": "error", "message": "Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env"}
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01"
                    },
                    timeout=10.0
                )
                # Anthropic might return 404 for /models but we just check auth
                if response.status_code in [200, 404]:
                    return {"status": "success", "message": "Anthropic API key is valid"}
                elif response.status_code == 401:
                    return {"status": "error", "message": "Invalid API key"}
                else:
                    return {"status": "error", "message": f"Anthropic API error: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to connect to Anthropic: {str(e)}"}
    
    else:
        raise HTTPException(400, f"Unknown AI provider: {provider}")


class ConfigureRequest(BaseModel):
    """Request to configure an integration."""
    type: str
    config: Dict[str, Any]


@router.post("/configure")
async def configure_integration(request: ConfigureRequest) -> Dict[str, Any]:
    """Configure an integration by updating .env file.
    
    This writes configuration to .env file for persistence.
    Note: For security, API keys should be set via environment variables in production.
    """
    import os
    from pathlib import Path
    
    env_file = Path(".env")
    env_vars: Dict[str, str] = {}
    
    # Read existing .env if it exists
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # Map configuration type to environment variables
    config_mapping = {
        'anthropic': {
            'api_key': 'ANTHROPIC_API_KEY',
            'model': 'ANTHROPIC_MODEL',
        },
        'openai': {
            'api_key': 'OPENAI_API_KEY',
            'model': 'OPENAI_MODEL',
        },
        'ollama': {
            'host': 'OLLAMA_HOST',
            'model': 'OLLAMA_MODEL',
        },
        'plaid': {
            'client_id': 'PLAID_CLIENT_ID',
            'secret': 'PLAID_SECRET',
            'environment': 'PLAID_ENVIRONMENT',
        },
        'alpaca': {
            'api_key': 'ALPACA_API_KEY',
            'secret_key': 'ALPACA_SECRET_KEY',
            'paper': 'ALPACA_PAPER',
        },
        'polygon': {
            'api_key': 'POLYGON_API_KEY',
        },
        'tradingview': {
            'secret': 'TRADINGVIEW_WEBHOOK_SECRET',
        },
    }
    
    if request.type not in config_mapping:
        raise HTTPException(400, f"Unknown integration type: {request.type}")
    
    mapping = config_mapping[request.type]
    updated_keys = []
    
    for config_key, env_key in mapping.items():
        if config_key in request.config:
            value = request.config[config_key]
            # Convert booleans to lowercase strings
            if isinstance(value, bool):
                value = str(value).lower()
            env_vars[env_key] = str(value)
            updated_keys.append(env_key)
    
    # Write back to .env file
    with open(env_file, 'w') as f:
        f.write("# XFactor Bot Configuration\n")
        f.write("# Auto-generated by configuration panel\n\n")
        for key, value in sorted(env_vars.items()):
            # Quote values that contain spaces or special chars
            if ' ' in value or '=' in value:
                value = f'"{value}"'
            f.write(f"{key}={value}\n")
    
    # Update current settings (clear cache)
    from src.config.settings import get_settings
    get_settings.cache_clear()
    
    return {
        "status": "success",
        "message": f"Configuration saved for {request.type}",
        "updated_keys": updated_keys,
        "note": "Restart may be required for some settings to take effect"
    }

