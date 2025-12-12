"""Tests for Bot Manager and Bot Instance."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.bot.bot_instance import BotConfig, BotInstance, BotStatus
from src.bot.bot_manager import BotManager


class TestBotConfig:
    """Tests for BotConfig dataclass."""

    def test_default_config(self):
        """Test BotConfig with default values."""
        config = BotConfig(name="Test Bot")
        
        assert config.name == "Test Bot"
        assert config.description == ""
        assert len(config.symbols) > 0
        assert len(config.strategies) > 0
        assert config.max_position_size > 0
        assert config.max_positions > 0
        assert config.max_daily_loss_pct > 0
        assert config.instrument_type == "STK"

    def test_custom_config(self):
        """Test BotConfig with custom values."""
        config = BotConfig(
            name="Custom Bot",
            description="A custom trading bot",
            symbols=["AAPL", "MSFT"],
            strategies=["Technical"],
            max_position_size=50000,
            max_positions=5,
            max_daily_loss_pct=3.0,
            trade_frequency_seconds=120,
            enable_news_trading=False,
        )
        
        assert config.name == "Custom Bot"
        assert config.symbols == ["AAPL", "MSFT"]
        assert config.max_position_size == 50000
        assert config.enable_news_trading is False

    def test_options_config(self):
        """Test BotConfig for options trading."""
        config = BotConfig(
            name="Options Bot",
            instrument_type="OPT",
            options_type="call",
            options_dte_min=7,
            options_dte_max=45,
            options_delta_min=0.3,
            options_delta_max=0.7,
        )
        
        assert config.instrument_type == "OPT"
        assert config.options_type == "call"
        assert config.options_dte_min == 7

    def test_futures_config(self):
        """Test BotConfig for futures trading."""
        config = BotConfig(
            name="Futures Bot",
            instrument_type="FUT",
            futures_contracts=["ES", "NQ"],
            futures_use_micro=True,
            futures_session="rth",
        )
        
        assert config.instrument_type == "FUT"
        assert "ES" in config.futures_contracts
        assert config.futures_use_micro is True


class TestBotInstance:
    """Tests for BotInstance class."""

    @pytest.fixture
    def bot(self):
        """Create a test bot instance."""
        config = BotConfig(
            name="Test Bot",
            symbols=["AAPL", "MSFT"],
            strategies=["Technical", "Momentum"]
        )
        return BotInstance(config)

    def test_initialization(self, bot):
        """Test bot initialization."""
        assert bot.id is not None
        assert bot.config.name == "Test Bot"
        assert bot.status == BotStatus.STOPPED
        assert bot.created_at is not None

    def test_start_bot(self, bot):
        """Test starting a bot."""
        result = bot.start()
        assert result is True
        assert bot.status == BotStatus.RUNNING
        assert bot.started_at is not None

    def test_stop_bot(self, bot):
        """Test stopping a bot."""
        bot.start()
        result = bot.stop()
        assert result is True
        assert bot.status == BotStatus.STOPPED

    def test_pause_bot(self, bot):
        """Test pausing a bot."""
        bot.start()
        result = bot.pause()
        assert result is True
        assert bot.status == BotStatus.PAUSED

    def test_resume_bot(self, bot):
        """Test resuming a paused bot."""
        bot.start()
        bot.pause()
        result = bot.resume()
        assert result is True
        assert bot.status == BotStatus.RUNNING

    def test_cannot_pause_stopped_bot(self, bot):
        """Test that stopped bot cannot be paused."""
        result = bot.pause()
        assert result is False
        assert bot.status == BotStatus.STOPPED

    def test_cannot_resume_running_bot(self, bot):
        """Test that running bot cannot be resumed."""
        bot.start()
        result = bot.resume()
        assert result is False  # Already running

    def test_get_status(self, bot):
        """Test getting bot status."""
        status = bot.get_status()
        
        assert "id" in status
        assert "name" in status
        assert "status" in status
        assert "config" in status
        assert "stats" in status
        assert status["name"] == "Test Bot"

    def test_update_config(self, bot):
        """Test updating bot configuration."""
        bot.update_config({
            "name": "Updated Bot",
            "max_position_size": 75000,
        })
        
        assert bot.config.name == "Updated Bot"
        assert bot.config.max_position_size == 75000

    def test_uptime_calculation(self, bot):
        """Test uptime calculation."""
        assert bot.uptime_seconds == 0
        
        bot.start()
        # Uptime should be positive after starting
        assert bot.uptime_seconds >= 0


class TestBotManager:
    """Tests for BotManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh bot manager."""
        mgr = BotManager()
        mgr._bots = {}  # Clear any existing bots
        return mgr

    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.bot_count == 0
        assert manager.running_count == 0
        assert manager.MAX_BOTS == 25

    def test_create_bot(self, manager):
        """Test creating a bot."""
        config = BotConfig(name="New Bot")
        bot = manager.create_bot(config)
        
        assert bot is not None
        assert manager.bot_count == 1
        assert bot.id in manager._bots

    def test_create_bot_with_custom_id(self, manager):
        """Test creating a bot with custom ID."""
        config = BotConfig(name="Custom ID Bot")
        bot = manager.create_bot(config, bot_id="custom-123")
        
        assert bot.id == "custom-123"

    def test_cannot_exceed_max_bots(self, manager):
        """Test that max bots limit is enforced."""
        # Fill up to max
        for i in range(manager.MAX_BOTS):
            config = BotConfig(name=f"Bot {i}")
            manager.create_bot(config)
        
        assert manager.bot_count == manager.MAX_BOTS
        assert not manager.can_create_bot
        
        # Try to create one more
        config = BotConfig(name="Overflow Bot")
        bot = manager.create_bot(config)
        assert bot is None

    def test_get_bot(self, manager):
        """Test getting a specific bot."""
        config = BotConfig(name="Find Me")
        created = manager.create_bot(config)
        
        found = manager.get_bot(created.id)
        assert found is not None
        assert found.id == created.id

    def test_get_nonexistent_bot(self, manager):
        """Test getting a bot that doesn't exist."""
        bot = manager.get_bot("nonexistent")
        assert bot is None

    def test_delete_bot(self, manager):
        """Test deleting a bot."""
        config = BotConfig(name="Delete Me")
        bot = manager.create_bot(config)
        
        result = manager.delete_bot(bot.id)
        assert result is True
        assert manager.bot_count == 0
        assert manager.get_bot(bot.id) is None

    def test_delete_nonexistent_bot(self, manager):
        """Test deleting a bot that doesn't exist."""
        result = manager.delete_bot("nonexistent")
        assert result is False

    def test_start_all(self, manager):
        """Test starting all bots."""
        for i in range(3):
            config = BotConfig(name=f"Bot {i}")
            manager.create_bot(config)
        
        results = manager.start_all()
        assert len(results) == 3
        assert all(v is True for v in results.values())
        assert manager.running_count == 3

    def test_stop_all(self, manager):
        """Test stopping all bots."""
        for i in range(3):
            config = BotConfig(name=f"Bot {i}")
            bot = manager.create_bot(config)
            bot.start()
        
        results = manager.stop_all()
        assert len(results) == 3
        assert manager.running_count == 0

    def test_pause_all(self, manager):
        """Test pausing all bots."""
        for i in range(3):
            config = BotConfig(name=f"Bot {i}")
            bot = manager.create_bot(config)
            bot.start()
        
        results = manager.pause_all()
        assert len(results) == 3

    def test_get_bot_summary(self, manager):
        """Test getting bot summary."""
        config = BotConfig(name="Summary Bot", symbols=["AAPL", "MSFT"])
        bot = manager.create_bot(config)
        bot.start()
        
        summary = manager.get_bot_summary()
        assert len(summary) == 1
        assert summary[0]["name"] == "Summary Bot"
        assert summary[0]["status"] == "running"
        assert summary[0]["symbols_count"] == 2

    def test_get_status(self, manager):
        """Test getting overall status."""
        for i in range(3):
            config = BotConfig(name=f"Bot {i}")
            manager.create_bot(config)
        
        status = manager.get_status()
        assert "bots" in status
        assert "count" in status or "bot_count" in status

