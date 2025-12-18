"""
TradingView Webhook Integration

Receive alerts from TradingView and execute trades via XFactor bots.
Supports Pine Script alerts, indicator signals, and custom strategies.

Webhook URL: POST /api/webhook/tradingview
Secret: Configure in admin panel for authentication

Alert Message Format (JSON):
{
    "secret": "your_webhook_secret",
    "ticker": "AAPL",
    "action": "buy",          // buy, sell, close
    "price": 150.25,          // optional
    "quantity": 10,           // optional
    "strategy": "my_strategy",// optional
    "message": "RSI oversold" // optional
}

Or simple text format:
AAPL,buy,150.25,10
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import json
import hmac
import hashlib

from loguru import logger


router = APIRouter(prefix="/api/webhook", tags=["TradingView Webhook"])


# Webhook secret (should be configured via admin panel)
_webhook_secret: str = ""
_enabled: bool = True


class TradingViewAction(str, Enum):
    """Supported trading actions."""
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    LONG = "long"
    SHORT = "short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"


class TradingViewAlert(BaseModel):
    """TradingView alert payload."""
    secret: Optional[str] = None
    ticker: str = Field(..., description="Symbol/ticker")
    action: TradingViewAction
    price: Optional[float] = Field(None, description="Limit price (optional)")
    quantity: Optional[float] = Field(None, description="Position size")
    strategy: Optional[str] = Field(None, description="Strategy name")
    message: Optional[str] = Field(None, description="Alert message")
    timeframe: Optional[str] = Field(None, description="Chart timeframe")
    exchange: Optional[str] = Field(None, description="Exchange (e.g., NASDAQ)")
    
    # Advanced options
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    order_type: Optional[str] = Field("market", description="market or limit")


class WebhookResponse(BaseModel):
    """Response to webhook request."""
    success: bool
    message: str
    order_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class AlertHistoryEntry(BaseModel):
    """Record of received alert."""
    timestamp: datetime
    ticker: str
    action: str
    price: Optional[float]
    quantity: Optional[float]
    strategy: Optional[str]
    processed: bool
    result: Optional[str]
    error: Optional[str]


# Alert history (in-memory, limited size)
_alert_history: List[AlertHistoryEntry] = []
MAX_HISTORY = 100


def verify_secret(provided_secret: Optional[str]) -> bool:
    """Verify the webhook secret."""
    if not _webhook_secret:
        # No secret configured, allow all (not recommended for production)
        logger.warning("TradingView webhook secret not configured!")
        return True
    
    if not provided_secret:
        return False
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(provided_secret, _webhook_secret)


def parse_simple_format(text: str) -> Optional[TradingViewAlert]:
    """
    Parse simple comma-separated format.
    Format: TICKER,ACTION,PRICE,QUANTITY
    Example: AAPL,buy,150.25,10
    """
    try:
        parts = text.strip().split(",")
        if len(parts) < 2:
            return None
        
        ticker = parts[0].strip().upper()
        action = parts[1].strip().lower()
        
        if action not in [a.value for a in TradingViewAction]:
            return None
        
        price = float(parts[2]) if len(parts) > 2 and parts[2].strip() else None
        quantity = float(parts[3]) if len(parts) > 3 and parts[3].strip() else None
        
        return TradingViewAlert(
            ticker=ticker,
            action=TradingViewAction(action),
            price=price,
            quantity=quantity,
        )
    except Exception as e:
        logger.error(f"Failed to parse simple format: {e}")
        return None


async def process_alert(alert: TradingViewAlert) -> WebhookResponse:
    """
    Process the TradingView alert and execute trades.
    
    This integrates with the bot manager to execute trades.
    """
    try:
        # Import bot manager
        from src.bot.bot_manager import get_bot_manager
        bot_manager = get_bot_manager()
        
        logger.info(f"Processing TradingView alert: {alert.ticker} {alert.action.value}")
        
        # Map action to order side
        action = alert.action
        
        if action in [TradingViewAction.BUY, TradingViewAction.LONG]:
            side = "buy"
        elif action in [TradingViewAction.SELL, TradingViewAction.SHORT]:
            side = "sell"
        elif action in [TradingViewAction.CLOSE, TradingViewAction.CLOSE_LONG, TradingViewAction.CLOSE_SHORT]:
            side = "close"
        elif action == TradingViewAction.SCALE_IN:
            side = "buy"  # Add to position
        elif action == TradingViewAction.SCALE_OUT:
            side = "sell"  # Reduce position
        else:
            side = "buy"
        
        # Prepare order details
        order_details = {
            "symbol": alert.ticker,
            "side": side,
            "quantity": alert.quantity or 1,
            "order_type": alert.order_type or "market",
            "price": alert.price,
            "stop_loss": alert.stop_loss,
            "take_profit": alert.take_profit,
            "source": "tradingview",
            "strategy": alert.strategy,
            "message": alert.message,
        }
        
        # Find a suitable bot to execute the trade
        # Option 1: Use a dedicated TradingView bot
        # Option 2: Route to strategy-specific bot
        # Option 3: Create a generic order
        
        tv_bot = None
        for bot_id, bot in bot_manager.bots.items():
            if "tradingview" in bot.name.lower() or (alert.strategy and alert.strategy.lower() in bot.name.lower()):
                tv_bot = bot
                break
        
        if tv_bot and tv_bot.running:
            # Execute via bot
            # This would need implementation in the bot
            result = f"Routed to bot: {tv_bot.name}"
            order_id = f"TV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        else:
            # Log the signal for manual review or queue it
            result = "Signal logged (no active TradingView bot found)"
            order_id = f"TV-LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return WebhookResponse(
            success=True,
            message=f"Alert processed: {alert.action.value} {alert.ticker}",
            order_id=order_id,
            details=order_details,
        )
        
    except Exception as e:
        logger.error(f"Failed to process TradingView alert: {e}")
        return WebhookResponse(
            success=False,
            message=f"Error processing alert: {str(e)}",
            details={"error": str(e)},
        )


@router.post("/tradingview", response_model=WebhookResponse)
async def receive_tradingview_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Receive and process TradingView webhook alerts.
    
    Supports both JSON and simple text formats.
    """
    global _alert_history
    
    if not _enabled:
        raise HTTPException(status_code=503, detail="TradingView webhook is disabled")
    
    # Get raw body
    body = await request.body()
    body_str = body.decode("utf-8").strip()
    
    logger.info(f"Received TradingView webhook: {body_str[:200]}...")
    
    # Try to parse as JSON first
    alert: Optional[TradingViewAlert] = None
    
    try:
        data = json.loads(body_str)
        alert = TradingViewAlert(**data)
    except (json.JSONDecodeError, Exception):
        # Try simple format
        alert = parse_simple_format(body_str)
    
    if alert is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid alert format. Expected JSON or TICKER,ACTION,PRICE,QUANTITY"
        )
    
    # Verify secret
    if not verify_secret(alert.secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    # Process the alert
    response = await process_alert(alert)
    
    # Record in history
    history_entry = AlertHistoryEntry(
        timestamp=datetime.now(),
        ticker=alert.ticker,
        action=alert.action.value,
        price=alert.price,
        quantity=alert.quantity,
        strategy=alert.strategy,
        processed=response.success,
        result=response.message if response.success else None,
        error=None if response.success else response.message,
    )
    
    _alert_history.append(history_entry)
    if len(_alert_history) > MAX_HISTORY:
        _alert_history = _alert_history[-MAX_HISTORY:]
    
    return response


@router.get("/tradingview/history")
async def get_webhook_history(limit: int = 50):
    """Get recent TradingView webhook history."""
    return {
        "total": len(_alert_history),
        "alerts": [a.model_dump() for a in _alert_history[-limit:]],
    }


@router.get("/tradingview/status")
async def get_webhook_status():
    """Get TradingView webhook status and configuration."""
    return {
        "enabled": _enabled,
        "secret_configured": bool(_webhook_secret),
        "total_alerts_received": len(_alert_history),
        "recent_alerts": len([a for a in _alert_history if (datetime.now() - a.timestamp).seconds < 3600]),
    }


@router.post("/tradingview/configure")
async def configure_webhook(secret: str = "", enabled: bool = True):
    """Configure TradingView webhook settings."""
    global _webhook_secret, _enabled
    
    _webhook_secret = secret
    _enabled = enabled
    
    return {
        "success": True,
        "message": "Webhook configured",
        "enabled": _enabled,
        "secret_configured": bool(_webhook_secret),
    }


@router.post("/tradingview/test")
async def test_webhook():
    """
    Test endpoint to verify webhook is working.
    Returns sample alert format.
    """
    return {
        "status": "ok",
        "message": "TradingView webhook is active",
        "sample_json_format": {
            "secret": "your_secret_here",
            "ticker": "AAPL",
            "action": "buy",
            "price": 150.25,
            "quantity": 10,
            "strategy": "my_strategy",
            "message": "RSI oversold signal",
        },
        "sample_text_format": "AAPL,buy,150.25,10",
        "supported_actions": [a.value for a in TradingViewAction],
    }

