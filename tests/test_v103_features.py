"""Tests for v1.0.x Features - Basic Integration Tests"""

import pytest
from datetime import datetime


class TestForecastingModule:
    """Tests that the forecasting module can be imported and instantiated"""

    def test_social_sentiment_import(self):
        from src.forecasting.social_sentiment import SocialSentimentEngine
        engine = SocialSentimentEngine()
        assert engine is not None

    def test_buzz_detector_import(self):
        from src.forecasting.buzz_detector import BuzzDetector
        detector = BuzzDetector()
        assert detector is not None

    def test_speculation_scorer_import(self):
        from src.forecasting.speculation_scorer import SpeculationScorer
        scorer = SpeculationScorer()
        assert scorer is not None

    def test_catalyst_tracker_import(self):
        from src.forecasting.catalyst_tracker import CatalystTracker
        tracker = CatalystTracker()
        assert tracker is not None

    def test_hypothesis_generator_import(self):
        from src.forecasting.hypothesis_generator import HypothesisGenerator
        generator = HypothesisGenerator()
        assert generator is not None

    def test_video_platforms_import(self):
        from src.forecasting.video_platforms import VideoPlatformAnalyzer
        analyzer = VideoPlatformAnalyzer()
        assert analyzer is not None


class TestForexModule:
    """Tests that the forex module can be imported and instantiated"""

    def test_forex_pair_import(self):
        from src.forex.core import ForexPair, PairType
        pair = ForexPair(
            symbol="EUR/USD",
            base_currency="EUR",
            quote_currency="USD",
            pair_type=PairType.MAJOR,
            pip_decimal_places=4,
            typical_spread_pips=1.0,
            avg_daily_range_pips=80
        )
        assert pair.symbol == "EUR/USD"

    def test_pip_calculator_import(self):
        from src.forex.core import PipCalculator
        calc = PipCalculator()
        assert calc is not None

    def test_currency_strength_import(self):
        from src.forex.currency_strength import CurrencyStrengthMeter
        meter = CurrencyStrengthMeter()
        assert meter is not None

    def test_economic_calendar_import(self):
        from src.forex.economic_calendar import EconomicCalendar
        calendar = EconomicCalendar()
        assert calendar is not None

    def test_forex_strategies_import(self):
        from src.forex.strategies import CarryTradeStrategy, SessionBreakoutStrategy
        carry = CarryTradeStrategy()
        breakout = SessionBreakoutStrategy()
        assert carry is not None
        assert breakout is not None


class TestBotRiskModule:
    """Tests that the bot risk module can be imported and instantiated"""

    def test_bot_risk_manager_import(self):
        from src.bot.risk_manager import BotRiskManager
        manager = BotRiskManager()
        assert manager is not None


class TestStrategiesV101:
    """Tests for v1.0.1 strategy features"""

    def test_volatility_adaptive_import(self):
        from src.strategies.volatility_adaptive import VolatilityAdaptiveEngine, VolatilityAdaptiveConfig
        config = VolatilityAdaptiveConfig()
        engine = VolatilityAdaptiveEngine(config)
        assert engine is not None

    def test_market_regime_import(self):
        from src.strategies.market_regime import MarketRegimeDetector, MarketRegime
        detector = MarketRegimeDetector()
        assert detector is not None
        # Just verify MarketRegime enum exists
        assert MarketRegime is not None

    def test_martingale_import(self):
        from src.strategies.martingale import MartingalePositionSizer, MartingaleConfig
        config = MartingaleConfig()
        sizer = MartingalePositionSizer(config)
        assert sizer is not None

    def test_strategy_template_import(self):
        from src.strategies.templates import StrategyTemplate
        # Just verify import works
        assert StrategyTemplate is not None

    def test_visual_builder_import(self):
        from src.strategies.visual_builder import VisualStrategyEngine
        engine = VisualStrategyEngine()
        assert engine is not None


class TestAPIRoutes:
    """Tests that API routes can be imported"""

    def test_forecasting_routes(self):
        from src.api.routes import forecasting
        assert forecasting.router is not None

    def test_forex_routes(self):
        from src.api.routes import forex
        assert forex.router is not None

    def test_bot_risk_routes(self):
        from src.api.routes import bot_risk
        assert bot_risk.router is not None

    def test_video_sentiment_routes(self):
        from src.api.routes import video_sentiment
        assert video_sentiment.router is not None

    def test_strategies_routes(self):
        from src.api.routes import strategies
        assert strategies.router is not None

    def test_tradingview_routes(self):
        from src.api.routes import tradingview
        assert tradingview.router is not None


class TestDataclasses:
    """Tests that dataclasses are properly defined"""

    def test_video_content_dataclass(self):
        from src.forecasting.video_platforms import VideoContent, VideoPlatform, ContentType
        content = VideoContent(
            id="test-1",
            platform=VideoPlatform.YOUTUBE,
            content_type=ContentType.VIDEO,
            creator_id="c1",
            creator_name="Test Creator",
            creator_handle="testcreator",
            creator_followers=1000,
            title="Test Video",
            description="Test Description",
            url="https://example.com"
        )
        assert content.id == "test-1"
        assert content.title == "Test Video"

    def test_forex_pair_dataclass(self):
        from src.forex.core import ForexPair, PairType
        pair = ForexPair(
            symbol="GBP/USD",
            base_currency="GBP",
            quote_currency="USD",
            pair_type=PairType.MAJOR,
            pip_decimal_places=4,
            typical_spread_pips=1.5,
            avg_daily_range_pips=100
        )
        assert pair.pip_value == 0.0001

    def test_catalyst_event_dataclass(self):
        from src.forecasting.catalyst_tracker import CatalystEvent, CatalystType, CatalystImpact
        from datetime import datetime, timezone
        event = CatalystEvent(
            id="cat-1",
            symbol="AAPL",
            catalyst_type=CatalystType.EARNINGS,
            title="Q4 Earnings",
            description="Apple quarterly earnings report",
            expected_date=datetime.now(timezone.utc),
            impact=CatalystImpact.MAJOR
        )
        assert event.symbol == "AAPL"

