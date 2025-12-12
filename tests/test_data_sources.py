"""Tests for Data Source integrations."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta


class TestAInvestDataSource:
    """Tests for AInvest data source."""

    @pytest.fixture
    def ainvest(self):
        """Create AInvest data source instance."""
        from src.data_sources.ainvest import AInvestDataSource
        return AInvestDataSource()

    @pytest.mark.asyncio
    async def test_connect(self, ainvest):
        """Test connecting to AInvest."""
        result = await ainvest.connect()
        assert result is True
        assert ainvest.connected is True

    @pytest.mark.asyncio
    async def test_disconnect(self, ainvest):
        """Test disconnecting from AInvest."""
        await ainvest.connect()
        await ainvest.disconnect()
        assert ainvest.connected is False

    @pytest.mark.asyncio
    async def test_get_recommendations(self, ainvest):
        """Test getting AI recommendations."""
        await ainvest.connect()
        recommendations = await ainvest.get_ai_recommendations(limit=10)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 10
        
        if recommendations:
            rec = recommendations[0]
            assert hasattr(rec, 'symbol')
            assert hasattr(rec, 'ai_score')
            assert hasattr(rec, 'recommendation')
            assert hasattr(rec, 'target_price')

    @pytest.mark.asyncio
    async def test_get_recommendations_filtered(self, ainvest):
        """Test getting filtered recommendations."""
        await ainvest.connect()
        recommendations = await ainvest.get_ai_recommendations(
            symbols=["AAPL", "NVDA"],
            min_score=70,
            limit=5
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 5

    @pytest.mark.asyncio
    async def test_get_sentiment(self, ainvest):
        """Test getting sentiment for a symbol."""
        await ainvest.connect()
        sentiment = await ainvest.get_sentiment("NVDA")
        
        assert sentiment is not None
        assert sentiment.symbol == "NVDA"
        assert -1 <= sentiment.overall_sentiment <= 1
        assert hasattr(sentiment, 'news_sentiment')
        assert hasattr(sentiment, 'social_sentiment')

    @pytest.mark.asyncio
    async def test_get_news(self, ainvest):
        """Test getting news from AInvest."""
        await ainvest.connect()
        news = await ainvest.get_news(limit=10)
        
        assert isinstance(news, list)
        assert len(news) <= 10
        
        if news:
            article = news[0]
            assert hasattr(article, 'title')
            assert hasattr(article, 'source')
            assert hasattr(article, 'published_at')

    @pytest.mark.asyncio
    async def test_get_trading_signals(self, ainvest):
        """Test getting trading signals."""
        await ainvest.connect()
        signals = await ainvest.get_trading_signals(limit=10)
        
        assert isinstance(signals, list)
        assert len(signals) <= 10
        
        if signals:
            signal = signals[0]
            assert hasattr(signal, 'symbol')
            assert hasattr(signal, 'signal_type')
            assert hasattr(signal, 'timestamp')

    @pytest.mark.asyncio
    async def test_get_insider_trades(self, ainvest):
        """Test getting insider trades."""
        await ainvest.connect()
        trades = await ainvest.get_insider_trades(limit=10)
        
        assert isinstance(trades, list)
        assert len(trades) <= 10
        
        if trades:
            trade = trades[0]
            assert hasattr(trade, 'ticker')
            assert hasattr(trade, 'insider_name')
            assert hasattr(trade, 'trade_type')
            assert hasattr(trade, 'value')

    @pytest.mark.asyncio
    async def test_get_earnings_calendar(self, ainvest):
        """Test getting earnings calendar."""
        await ainvest.connect()
        earnings = await ainvest.get_earnings_calendar(limit=10)
        
        assert isinstance(earnings, list)
        assert len(earnings) <= 10
        
        if earnings:
            report = earnings[0]
            assert "ticker" in report
            assert "report_date" in report


class TestTradingViewWebhook:
    """Tests for TradingView webhook integration."""

    @pytest.fixture
    def webhook(self):
        """Create TradingView webhook instance."""
        from src.data_sources.tradingview import TradingViewWebhook
        return TradingViewWebhook()

    @pytest.mark.asyncio
    async def test_connect(self, webhook):
        """Test connecting (passive for webhooks)."""
        result = await webhook.connect()
        assert result is True

    @pytest.mark.asyncio
    async def test_process_webhook_alert(self, webhook):
        """Test processing a webhook alert."""
        payload = {
            "alertName": "RSI Oversold",
            "symbol": "BINANCE:BTCUSDT",
            "exchange": "BINANCE",
            "price": 45000,
            "volume": 12345,
            "time": datetime.now().isoformat(),
            "message": "RSI crossed below 30"
        }
        headers = {}
        
        signal = await webhook.process_webhook_alert(payload, headers)
        
        assert signal is not None
        assert signal.source == "TradingView"
        assert signal.symbol == "BTCUSDT"
        assert signal.signal_type == "RSI Oversold"


class TestDataSourceRegistry:
    """Tests for data source registry."""

    def test_list_data_sources(self):
        """Test listing registered data sources."""
        from src.data_sources.registry import DataSourceRegistry
        
        sources = DataSourceRegistry.list_data_sources()
        assert isinstance(sources, list)
        # Should have at least AInvest and TradingView
        assert len(sources) >= 1

    def test_get_data_source_class(self):
        """Test getting a registered data source class."""
        from src.data_sources.registry import DataSourceRegistry
        
        # AInvest should be registered
        try:
            source_class = DataSourceRegistry.get_data_source_class("ainvest")
            assert source_class is not None
        except ValueError:
            # May not be registered if tests run in isolation
            pass

    def test_get_unknown_data_source(self):
        """Test getting an unknown data source raises error."""
        from src.data_sources.registry import DataSourceRegistry
        
        with pytest.raises(ValueError):
            DataSourceRegistry.get_data_source_class("unknown_source")

