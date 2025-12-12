"""
Kill Switch for emergency trading halt.
"""

from datetime import datetime
from typing import Optional, Callable

from loguru import logger

from src.connectors.ibkr_connector import IBKRConnector
from src.data.redis_cache import RedisCache


class KillSwitch:
    """
    Emergency kill switch for halting all trading activity.
    
    Actions:
    - Cancel all open orders
    - Close all positions (optional)
    - Prevent new orders
    - Alert operators
    """
    
    def __init__(
        self,
        ibkr: IBKRConnector,
        cache: RedisCache,
        alert_callback: Callable = None,
    ):
        """Initialize kill switch."""
        self.ibkr = ibkr
        self.cache = cache
        self.alert_callback = alert_callback
        
        self._active = False
        self._activated_at: Optional[datetime] = None
        self._reason: str = ""
    
    @property
    def is_active(self) -> bool:
        """Check if kill switch is active."""
        return self._active
    
    async def activate(
        self,
        reason: str,
        close_positions: bool = False,
    ) -> dict:
        """
        Activate the kill switch.
        
        Args:
            reason: Reason for activation
            close_positions: Whether to close all positions
            
        Returns:
            Summary of actions taken
        """
        if self._active:
            return {"status": "already_active", "activated_at": self._activated_at}
        
        self._active = True
        self._activated_at = datetime.utcnow()
        self._reason = reason
        
        logger.error(f"KILL SWITCH ACTIVATED: {reason}")
        
        # Set in Redis
        await self.cache.set_kill_switch_active(True)
        await self.cache.set_trading_paused(True)
        
        results = {
            "status": "activated",
            "activated_at": self._activated_at,
            "reason": reason,
            "orders_cancelled": 0,
            "positions_closed": 0,
        }
        
        # Cancel all orders
        try:
            cancelled = await self.ibkr.cancel_all_orders()
            results["orders_cancelled"] = cancelled
            logger.info(f"Cancelled {cancelled} orders")
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
        
        # Close positions if requested
        if close_positions:
            try:
                closes = await self.ibkr.close_all_positions()
                results["positions_closed"] = len(closes)
                logger.info(f"Closed {len(closes)} positions")
            except Exception as e:
                logger.error(f"Error closing positions: {e}")
        
        # Send alert
        if self.alert_callback:
            try:
                await self.alert_callback(f"KILL SWITCH: {reason}", results)
            except Exception as e:
                logger.error(f"Error sending alert: {e}")
        
        return results
    
    async def deactivate(self, confirmation: str) -> bool:
        """
        Deactivate the kill switch.
        
        Requires explicit confirmation string for safety.
        
        Args:
            confirmation: Must be "CONFIRM_DEACTIVATE"
            
        Returns:
            True if deactivated
        """
        if confirmation != "CONFIRM_DEACTIVATE":
            logger.warning("Kill switch deactivation rejected: invalid confirmation")
            return False
        
        if not self._active:
            return True
        
        self._active = False
        self._reason = ""
        
        await self.cache.set_kill_switch_active(False)
        await self.cache.set_trading_paused(False)
        
        logger.warning("Kill switch deactivated - trading can resume")
        
        return True
    
    def get_status(self) -> dict:
        """Get kill switch status."""
        return {
            "active": self._active,
            "activated_at": self._activated_at.isoformat() if self._activated_at else None,
            "reason": self._reason,
        }

