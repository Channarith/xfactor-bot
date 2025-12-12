"""Tests for trading strategies."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategies.base_strategy import Signal, SignalType
from src.strategies.technical import TechnicalStrategy
from src.strategies.momentum import MomentumStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.news_sentiment import NewsSentimentStrategy


def create_sample_ohlcv(days: int = 100, trend: str = "up") -> pd.DataFrame:
    """Create sample OHLCV data for testing."""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    if trend == "up":
        close = 100 + np.cumsum(np.random.randn(days) * 0.5 + 0.1)
    elif trend == "down":
        close = 100 + np.cumsum(np.random.randn(days) * 0.5 - 0.1)
    else:
        close = 100 + np.cumsum(np.random.randn(days) * 0.5)
    
    high = close * (1 + np.random.rand(days) * 0.02)
    low = close * (1 - np.random.rand(days) * 0.02)
    open_price = low + (high - low) * np.random.rand(days)
    volume = np.random.randint(1000000, 10000000, days)
    
    return pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }, index=dates)


class TestSignal:
    """Tests for Signal dataclass."""
    
    def test_signal_creation(self):
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strategy="Test",
            strength=0.8,
            confidence=0.7,
        )
        
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.is_actionable
        assert signal.composite_score > 0
    
    def test_signal_not_actionable_for_hold(self):
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.HOLD,
            strategy="Test",
            strength=0,
            confidence=0,
        )
        
        assert not signal.is_actionable
        assert signal.composite_score == 0


class TestTechnicalStrategy:
    """Tests for Technical Strategy."""
    
    @pytest.fixture
    def strategy(self):
        return TechnicalStrategy(weight=0.6)
    
    def test_initialization(self, strategy):
        assert strategy.name == "Technical"
        assert strategy.weight == 0.6
        assert strategy.is_enabled
    
    @pytest.mark.asyncio
    async def test_analyze_with_uptrend(self, strategy):
        data = create_sample_ohlcv(100, trend="up")
        signal = await strategy.analyze("AAPL", data)
        
        # May or may not generate signal depending on indicators
        # Just verify it doesn't crash
        assert signal is None or isinstance(signal, Signal)
    
    @pytest.mark.asyncio
    async def test_analyze_insufficient_data(self, strategy):
        data = create_sample_ohlcv(10)  # Too few days
        signal = await strategy.analyze("AAPL", data)
        
        assert signal is None
    
    def test_disable_strategy(self, strategy):
        strategy.disable()
        assert not strategy.is_enabled


class TestMomentumStrategy:
    """Tests for Momentum Strategy."""
    
    @pytest.fixture
    def strategy(self):
        return MomentumStrategy(weight=0.5)
    
    def test_initialization(self, strategy):
        assert strategy.name == "Momentum"
        assert strategy.weight == 0.5
    
    @pytest.mark.asyncio
    async def test_analyze_strong_momentum(self, strategy):
        data = create_sample_ohlcv(100, trend="up")
        signal = await strategy.analyze("NVDA", data)
        
        # Verify no crash
        assert signal is None or isinstance(signal, Signal)
    
    @pytest.mark.asyncio
    async def test_rank_symbols(self, strategy):
        data = {
            "AAPL": create_sample_ohlcv(100, trend="up"),
            "MSFT": create_sample_ohlcv(100, trend="neutral"),
            "TSLA": create_sample_ohlcv(100, trend="down"),
        }
        
        rankings = await strategy.rank_symbols(list(data.keys()), data)
        
        assert len(rankings) == 3
        # Rankings should be sorted by momentum descending
        assert all(isinstance(r[1], float) for r in rankings)


class TestMeanReversionStrategy:
    """Tests for Mean Reversion Strategy."""
    
    @pytest.fixture
    def strategy(self):
        return MeanReversionStrategy(weight=0.4)
    
    def test_initialization(self, strategy):
        assert strategy.name == "MeanReversion"
        assert strategy.weight == 0.4
    
    @pytest.mark.asyncio
    async def test_analyze(self, strategy):
        data = create_sample_ohlcv(50)
        signal = await strategy.analyze("AMD", data)
        
        assert signal is None or isinstance(signal, Signal)


class TestNewsSentimentStrategy:
    """Tests for News Sentiment Strategy."""
    
    @pytest.fixture
    def strategy(self):
        return NewsSentimentStrategy(weight=0.4)
    
    def test_initialization(self, strategy):
        assert strategy.name == "NewsSentiment"
        assert strategy.weight == 0.4
    
    def test_add_news(self, strategy):
        strategy.add_news(
            symbol="NVDA",
            sentiment=0.8,
            urgency=0.9,
            confidence=0.85,
            source="Reuters",
            headline="NVIDIA beats earnings",
            is_breaking=True,
        )
        
        # News should be stored
        assert "NVDA" in strategy._recent_news
        assert len(strategy._recent_news["NVDA"]) == 1
    
    @pytest.mark.asyncio
    async def test_analyze_with_positive_news(self, strategy):
        strategy.add_news(
            symbol="AAPL",
            sentiment=0.75,
            urgency=0.8,
            confidence=0.9,
            source="Bloomberg",
            headline="Apple announces record sales",
        )
        
        signal = await strategy.analyze("AAPL")
        
        assert signal is not None
        assert signal.signal_type.is_bullish
    
    @pytest.mark.asyncio
    async def test_analyze_with_no_news(self, strategy):
        signal = await strategy.analyze("UNKNOWN")
        
        assert signal is None
    
    def test_clear_news(self, strategy):
        strategy.add_news("AAPL", 0.5, 0.5, 0.5, "Test", "Test headline")
        strategy.add_news("MSFT", 0.5, 0.5, 0.5, "Test", "Test headline")
        
        strategy.clear_news("AAPL")
        assert "AAPL" not in strategy._recent_news
        assert "MSFT" in strategy._recent_news
        
        strategy.clear_news()
        assert len(strategy._recent_news) == 0

