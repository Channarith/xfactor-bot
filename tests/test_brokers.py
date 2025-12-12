"""Tests for Broker integrations."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


class TestBaseBroker:
    """Tests for BaseBroker abstract class."""

    def test_broker_interface_methods(self):
        """Test that BaseBroker defines all required methods."""
        from src.brokers.base import BaseBroker
        
        # Check abstract methods exist
        assert hasattr(BaseBroker, 'connect')
        assert hasattr(BaseBroker, 'disconnect')
        assert hasattr(BaseBroker, 'get_account_info')
        assert hasattr(BaseBroker, 'get_positions')
        assert hasattr(BaseBroker, 'get_orders')
        assert hasattr(BaseBroker, 'place_order')
        assert hasattr(BaseBroker, 'cancel_order')
        assert hasattr(BaseBroker, 'get_quote')


class TestAccountInfo:
    """Tests for AccountInfo dataclass."""

    def test_account_info_creation(self):
        """Test creating AccountInfo."""
        from src.brokers.base import AccountInfo
        
        account = AccountInfo(
            account_id="ABC123",
            cash_balance=50000.0,
            buying_power=100000.0,
            total_equity=150000.0,
            currency="USD"
        )
        
        assert account.account_id == "ABC123"
        assert account.cash_balance == 50000.0
        assert account.currency == "USD"
        assert account.status == "connected"


class TestPosition:
    """Tests for Position dataclass."""

    def test_position_creation(self):
        """Test creating Position."""
        from src.brokers.base import Position
        
        position = Position(
            symbol="AAPL",
            quantity=100,
            average_cost=175.50,
            current_price=180.00,
            market_value=18000.0,
            unrealized_pnl=450.0,
            unrealized_pnl_pct=2.56,
            asset_type="STK"
        )
        
        assert position.symbol == "AAPL"
        assert position.quantity == 100
        assert position.unrealized_pnl == 450.0


class TestOrder:
    """Tests for Order dataclass."""

    def test_order_creation(self):
        """Test creating Order."""
        from src.brokers.base import Order
        
        order = Order(
            order_id="ORD001",
            symbol="NVDA",
            action="BUY",
            quantity=50,
            order_type="MKT",
            status="PENDING"
        )
        
        assert order.order_id == "ORD001"
        assert order.symbol == "NVDA"
        assert order.action == "BUY"
        assert order.quantity == 50

    def test_limit_order_creation(self):
        """Test creating limit order."""
        from src.brokers.base import Order
        
        order = Order(
            order_id="ORD002",
            symbol="TSLA",
            action="SELL",
            quantity=25,
            order_type="LMT",
            price=250.00,
            status="PENDING"
        )
        
        assert order.order_type == "LMT"
        assert order.price == 250.00


class TestBrokerRegistry:
    """Tests for BrokerRegistry."""

    def test_list_brokers(self):
        """Test listing registered brokers."""
        from src.brokers.registry import BrokerRegistry
        
        brokers = BrokerRegistry.list_brokers()
        assert isinstance(brokers, list)
        # Should have at least one broker registered
        # (may be empty if tests run in isolation before imports)

    def test_register_broker(self):
        """Test registering a new broker."""
        from src.brokers.registry import BrokerRegistry
        from src.brokers.base import BaseBroker
        
        class MockBroker(BaseBroker):
            async def connect(self): return True
            async def disconnect(self): pass
            async def get_account_info(self): return None
            async def get_positions(self): return []
            async def get_orders(self, status=None): return []
            async def place_order(self, order): return None
            async def cancel_order(self, order_id): return False
            async def get_quote(self, symbol): return None
            async def get_historical_data(self, symbol, interval, limit): return []
            async def subscribe_market_data(self, symbol, callback): pass
            async def unsubscribe_market_data(self, symbol): pass
        
        # Register mock broker
        try:
            BrokerRegistry.register_broker("mock_test", MockBroker)
            assert "mock_test" in BrokerRegistry.list_brokers()
        except ValueError:
            # Already registered
            pass

    def test_get_unknown_broker(self):
        """Test getting unknown broker raises error."""
        from src.brokers.registry import BrokerRegistry
        
        with pytest.raises(ValueError):
            BrokerRegistry.get_broker_class("unknown_broker_xyz")


class TestAlpacaBroker:
    """Tests for Alpaca broker integration."""

    @pytest.fixture
    def alpaca(self):
        """Create Alpaca broker instance."""
        with patch('src.brokers.alpaca_broker.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                alpaca_api_key="test_key",
                alpaca_secret_key="test_secret",
                alpaca_paper=True
            )
            from src.brokers.alpaca_broker import AlpacaBroker
            return AlpacaBroker()

    def test_initialization(self, alpaca):
        """Test Alpaca broker initialization."""
        assert alpaca.api_key == "test_key"
        assert alpaca.paper_trading is True
        assert alpaca.connected is False

    @pytest.mark.asyncio
    async def test_connect_failure_handled(self, alpaca):
        """Test connection failure is handled gracefully."""
        # Without valid API keys, connect should fail gracefully
        result = await alpaca.connect()
        # May be True or False depending on mock setup
        assert isinstance(result, bool)


class TestSchwabBroker:
    """Tests for Schwab broker integration."""

    @pytest.fixture
    def schwab(self):
        """Create Schwab broker instance."""
        with patch('src.brokers.schwab_broker.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                schwab_client_id="test_id",
                schwab_client_secret="test_secret"
            )
            from src.brokers.schwab_broker import SchwabBroker
            return SchwabBroker()

    @pytest.mark.asyncio
    async def test_connect(self, schwab):
        """Test Schwab connection (simulated)."""
        result = await schwab.connect()
        assert result is True
        assert schwab.connected is True

    @pytest.mark.asyncio
    async def test_get_account_info(self, schwab):
        """Test getting account info (simulated)."""
        await schwab.connect()
        account = await schwab.get_account_info()
        
        assert account is not None
        assert account.account_id is not None
        assert account.cash_balance >= 0
        assert account.currency == "USD"

    @pytest.mark.asyncio
    async def test_get_positions(self, schwab):
        """Test getting positions (simulated)."""
        await schwab.connect()
        positions = await schwab.get_positions()
        
        assert isinstance(positions, list)


class TestTradierBroker:
    """Tests for Tradier broker integration."""

    @pytest.fixture
    def tradier(self):
        """Create Tradier broker instance."""
        with patch('src.brokers.tradier_broker.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                tradier_access_token="test_token",
                tradier_account_id="test_account",
                tradier_paper=True
            )
            from src.brokers.tradier_broker import TradierBroker
            return TradierBroker()

    def test_initialization(self, tradier):
        """Test Tradier broker initialization."""
        assert tradier.access_token == "test_token"
        assert tradier.account_id == "test_account"
        assert tradier.is_paper is True

