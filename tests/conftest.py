"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Create FastAPI test application."""
    from src.api.main import create_app
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def admin_token():
    """Create a valid admin token for testing."""
    from src.api.auth import create_session_token
    token, _ = create_session_token()
    return token


@pytest.fixture
def auth_headers(admin_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def mock_bot_manager():
    """Create a mock bot manager."""
    with patch('src.bot.bot_manager.get_bot_manager') as mock:
        manager = MagicMock()
        manager.bot_count = 5
        manager.running_count = 3
        manager.MAX_BOTS = 25
        manager.can_create_bot = True
        manager.get_status.return_value = {"bots": [], "count": 5}
        manager.get_bot_summary.return_value = []
        mock.return_value = manager
        yield manager


@pytest.fixture
def sample_bot_config():
    """Sample bot configuration."""
    return {
        "name": "Test Bot",
        "description": "Test bot for unit testing",
        "symbols": ["AAPL", "MSFT", "NVDA"],
        "strategies": ["Technical", "Momentum"],
        "max_position_size": 25000.0,
        "max_positions": 10,
        "max_daily_loss_pct": 2.0,
        "trade_frequency_seconds": 60,
        "enable_news_trading": True,
    }


@pytest.fixture
def sample_position():
    """Sample position data."""
    return {
        "symbol": "AAPL",
        "quantity": 100,
        "avg_cost": 175.50,
        "current_price": 180.25,
        "market_value": 18025.0,
        "unrealized_pnl": 475.0,
        "unrealized_pnl_pct": 2.71,
        "sector": "Technology",
        "strategy": "Technical",
    }


@pytest.fixture
def sample_news_item():
    """Sample news item."""
    return {
        "symbol": "NVDA",
        "headline": "NVIDIA beats earnings expectations",
        "source": "Reuters",
        "sentiment": 0.75,
        "urgency": 0.8,
        "confidence": 0.9,
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch('src.data.redis_cache.RedisCache') as mock:
        redis = MagicMock()
        redis.get.return_value = None
        redis.set.return_value = True
        mock.return_value = redis
        yield redis


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    with patch('openai.AsyncOpenAI') as mock:
        client = MagicMock()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content="Test AI response"))]
        client.chat.completions.create = AsyncMock(return_value=response)
        mock.return_value = client
        yield client
