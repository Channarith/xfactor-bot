"""
Redis cache for real-time data and pub/sub messaging.
"""

import json
from datetime import timedelta
from typing import Optional, Any, Callable
import asyncio

import redis.asyncio as redis
from loguru import logger

from src.config.settings import get_settings


class RedisCache:
    """
    Redis client for caching and real-time messaging.
    
    Used for:
    - Real-time market data caching
    - News article deduplication
    - Pub/sub for strategy signals
    - Session state management
    """
    
    def __init__(self):
        """Initialize Redis client."""
        self.settings = get_settings()
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._subscriptions: dict[str, Callable] = {}
    
    async def connect(self) -> bool:
        """Connect to Redis."""
        try:
            self._client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            logger.info("Connected to Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._client:
            await self._client.close()
            logger.info("Disconnected from Redis")
    
    # =========================================================================
    # Basic Cache Operations
    # =========================================================================
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        if not self._client:
            return None
        return await self._client.get(key)
    
    async def set(
        self,
        key: str,
        value: str,
        expire_seconds: int = None,
    ) -> bool:
        """Set a value in cache."""
        if not self._client:
            return False
        await self._client.set(key, value, ex=expire_seconds)
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self._client:
            return False
        await self._client.delete(key)
        return True
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self._client:
            return False
        return await self._client.exists(key) > 0
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get a JSON value from cache."""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set_json(
        self,
        key: str,
        value: Any,
        expire_seconds: int = None,
    ) -> bool:
        """Set a JSON value in cache."""
        return await self.set(key, json.dumps(value), expire_seconds)
    
    # =========================================================================
    # Market Data Cache
    # =========================================================================
    
    async def cache_market_price(
        self,
        symbol: str,
        price: float,
        bid: float = None,
        ask: float = None,
        volume: int = None,
    ) -> None:
        """Cache real-time market price."""
        data = {
            "price": price,
            "bid": bid,
            "ask": ask,
            "volume": volume,
            "timestamp": asyncio.get_event_loop().time(),
        }
        await self.set_json(f"price:{symbol}", data, expire_seconds=60)
    
    async def get_market_price(self, symbol: str) -> Optional[dict]:
        """Get cached market price."""
        return await self.get_json(f"price:{symbol}")
    
    async def cache_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        bars: list[dict],
    ) -> None:
        """Cache OHLCV bars."""
        await self.set_json(
            f"ohlcv:{symbol}:{timeframe}",
            bars,
            expire_seconds=300,  # 5 minutes
        )
    
    async def get_ohlcv(self, symbol: str, timeframe: str) -> Optional[list[dict]]:
        """Get cached OHLCV bars."""
        return await self.get_json(f"ohlcv:{symbol}:{timeframe}")
    
    # =========================================================================
    # News Deduplication
    # =========================================================================
    
    async def is_article_seen(self, article_id: str) -> bool:
        """Check if we've already processed this article."""
        return await self.exists(f"news:seen:{article_id}")
    
    async def mark_article_seen(
        self,
        article_id: str,
        expire_hours: int = 24,
    ) -> None:
        """Mark an article as seen."""
        await self.set(
            f"news:seen:{article_id}",
            "1",
            expire_seconds=expire_hours * 3600,
        )
    
    # =========================================================================
    # Trading State
    # =========================================================================
    
    async def set_trading_paused(self, paused: bool) -> None:
        """Set trading pause state."""
        await self.set("trading:paused", "1" if paused else "0")
    
    async def is_trading_paused(self) -> bool:
        """Check if trading is paused."""
        value = await self.get("trading:paused")
        return value == "1"
    
    async def set_kill_switch_active(self, active: bool) -> None:
        """Set kill switch state."""
        await self.set("trading:kill_switch", "1" if active else "0")
    
    async def is_kill_switch_active(self) -> bool:
        """Check if kill switch is active."""
        value = await self.get("trading:kill_switch")
        return value == "1"
    
    async def increment_order_count(self) -> int:
        """Increment and get today's order count."""
        if not self._client:
            return 0
        key = "trading:order_count"
        count = await self._client.incr(key)
        # Set expiry to end of day if this is the first order
        if count == 1:
            await self._client.expire(key, 86400)  # 24 hours
        return count
    
    # =========================================================================
    # Pub/Sub Messaging
    # =========================================================================
    
    async def publish(self, channel: str, message: Any) -> None:
        """Publish a message to a channel."""
        if not self._client:
            return
        if isinstance(message, dict):
            message = json.dumps(message)
        await self._client.publish(channel, message)
    
    async def subscribe(self, channel: str, callback: Callable) -> None:
        """Subscribe to a channel with a callback."""
        if not self._client:
            return
        
        if not self._pubsub:
            self._pubsub = self._client.pubsub()
        
        await self._pubsub.subscribe(channel)
        self._subscriptions[channel] = callback
        logger.info(f"Subscribed to Redis channel: {channel}")
    
    async def start_listening(self) -> None:
        """Start listening for pub/sub messages."""
        if not self._pubsub:
            return
        
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"]
                data = message["data"]
                
                # Try to parse as JSON
                try:
                    data = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    pass
                
                # Call the callback
                callback = self._subscriptions.get(channel)
                if callback:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        logger.error(f"Error in pubsub callback for {channel}: {e}")
    
    # =========================================================================
    # Strategy Signals
    # =========================================================================
    
    async def publish_signal(
        self,
        strategy: str,
        symbol: str,
        signal: str,
        strength: float,
        metadata: dict = None,
    ) -> None:
        """Publish a trading signal."""
        message = {
            "strategy": strategy,
            "symbol": symbol,
            "signal": signal,
            "strength": strength,
            "metadata": metadata or {},
        }
        await self.publish("signals", message)
    
    async def publish_news_alert(
        self,
        symbol: str,
        headline: str,
        sentiment: float,
        urgency: float,
        source: str,
    ) -> None:
        """Publish a news alert."""
        message = {
            "symbol": symbol,
            "headline": headline,
            "sentiment": sentiment,
            "urgency": urgency,
            "source": source,
        }
        await self.publish("news_alerts", message)

