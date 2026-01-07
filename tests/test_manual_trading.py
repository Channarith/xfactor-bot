"""
Tests for manual trading API endpoints.
"""
import pytest
from datetime import datetime, timedelta

from src.api.routes.manual_trading import (
    TradeSource,
    record_trade,
    get_trade_history,
    get_performance_comparison,
    clear_trade_store,
)


class TestTradeSource:
    """Tests for TradeSource enum"""
    
    def test_trade_sources_exist(self):
        """Test that all trade sources are defined"""
        assert TradeSource.MANUAL == "manual"
        assert TradeSource.BOT == "bot"
        assert TradeSource.TRADINGVIEW == "tradingview"
        assert TradeSource.API == "api"


class TestRecordTrade:
    """Tests for trade recording"""
    
    def setup_method(self):
        """Clear trade store before each test"""
        clear_trade_store()
    
    def test_record_manual_trade(self):
        """Test recording a manual trade"""
        trade = record_trade(
            symbol="AAPL",
            side="buy",
            quantity=10,
            price=150.00,
            order_type="market",
            source=TradeSource.MANUAL,
            broker="alpaca",
            order_id="test-order-123",
            reasoning="Test manual buy",
        )
        
        assert trade["symbol"] == "AAPL"
        assert trade["side"] == "buy"
        assert trade["quantity"] == 10
        assert trade["price"] == 150.00
        assert trade["source"] == "manual"
        assert trade["source_name"] == "Manual Trade"
        assert trade["broker"] == "alpaca"
        assert trade["reasoning"] == "Test manual buy"
        assert trade["total_value"] == 1500.00
        assert "trade_id" in trade
        assert "timestamp" in trade
    
    def test_record_bot_trade(self):
        """Test recording a bot trade"""
        trade = record_trade(
            symbol="TSLA",
            side="sell",
            quantity=5,
            price=250.00,
            order_type="limit",
            source=TradeSource.BOT,
            broker="ibkr",
            order_id="bot-order-456",
            source_id="bot-123",
            source_name="Momentum Bot",
            reasoning="RSI oversold, MACD bullish crossover",
        )
        
        assert trade["symbol"] == "TSLA"
        assert trade["side"] == "sell"
        assert trade["quantity"] == 5
        assert trade["price"] == 250.00
        assert trade["source"] == "bot"
        assert trade["source_id"] == "bot-123"
        assert trade["source_name"] == "Momentum Bot"
        assert trade["reasoning"] == "RSI oversold, MACD bullish crossover"
        assert trade["total_value"] == 1250.00
    
    def test_trade_history_populated(self):
        """Test that trades are added to history"""
        record_trade(
            symbol="GOOG",
            side="buy",
            quantity=2,
            price=140.00,
            order_type="market",
            source=TradeSource.MANUAL,
            broker="alpaca",
            order_id="test-123",
        )
        
        history = get_trade_history()
        assert len(history) == 1
        assert history[0]["symbol"] == "GOOG"


class TestGetTradeHistory:
    """Tests for trade history retrieval"""
    
    def setup_method(self):
        """Clear and populate trade store before each test"""
        clear_trade_store()
        
        # Add some test trades
        record_trade(symbol="AAPL", side="buy", quantity=10, price=150.00, 
                    order_type="market", source=TradeSource.MANUAL, broker="alpaca",
                    order_id="order-1")
        record_trade(symbol="TSLA", side="sell", quantity=5, price=250.00,
                    order_type="limit", source=TradeSource.BOT, broker="ibkr",
                    source_name="Test Bot", order_id="order-2")
        record_trade(symbol="GOOG", side="buy", quantity=3, price=140.00,
                    order_type="market", source=TradeSource.MANUAL, broker="alpaca",
                    order_id="order-3")
    
    def test_get_all_trades(self):
        """Test getting all trades"""
        trades = get_trade_history()
        assert len(trades) == 3
    
    def test_filter_manual_trades(self):
        """Test filtering for manual trades only"""
        trades = get_trade_history(source=TradeSource.MANUAL)
        assert len(trades) == 2
        assert all(t["source"] == "manual" for t in trades)
    
    def test_filter_bot_trades(self):
        """Test filtering for bot trades only"""
        trades = get_trade_history(source=TradeSource.BOT)
        assert len(trades) == 1
        assert trades[0]["source"] == "bot"
    
    def test_filter_by_symbol(self):
        """Test filtering by symbol"""
        trades = get_trade_history(symbol="AAPL")
        assert len(trades) == 1
        assert trades[0]["symbol"] == "AAPL"
    
    def test_limit_results(self):
        """Test limiting number of results"""
        trades = get_trade_history(limit=2)
        assert len(trades) == 2


class TestPerformanceComparison:
    """Tests for performance comparison between bot and manual trades"""
    
    def setup_method(self):
        """Clear trade store before each test"""
        clear_trade_store()
    
    def test_empty_comparison(self):
        """Test comparison with no trades"""
        comparison = get_performance_comparison()
        
        assert comparison["bot_trades"]["count"] == 0
        assert comparison["manual_trades"]["count"] == 0
        assert comparison["comparison"]["pnl_difference"] == 0
    
    def test_comparison_with_trades(self):
        """Test comparison with trades"""
        # Add some trades
        record_trade(symbol="AAPL", side="buy", quantity=10, price=150.00,
                    order_type="market", source=TradeSource.MANUAL, broker="alpaca",
                    order_id="order-1")
        record_trade(symbol="TSLA", side="buy", quantity=5, price=250.00,
                    order_type="market", source=TradeSource.BOT, broker="ibkr",
                    source_name="Test Bot", order_id="order-2")
        
        comparison = get_performance_comparison()
        
        assert comparison["bot_trades"]["count"] == 1
        assert comparison["manual_trades"]["count"] == 1
        assert comparison["bot_trades"]["total_volume"] == 1250.00
        assert comparison["manual_trades"]["total_volume"] == 1500.00
    
    def test_comparison_recommendation(self):
        """Test that comparison includes a recommendation"""
        record_trade(symbol="AAPL", side="buy", quantity=10, price=150.00,
                    order_type="market", source=TradeSource.MANUAL, broker="alpaca",
                    order_id="order-1")
        
        comparison = get_performance_comparison()
        
        assert "recommendation" in comparison["comparison"]
        assert len(comparison["comparison"]["recommendation"]) > 0
