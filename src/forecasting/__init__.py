"""
XFactor Bot Market Forecasting & Speculation Engine

AI-powered market forecasting using social sentiment, trend detection,
and speculation analysis to identify stocks with high growth potential.

Features:
- Social Media Sentiment (Twitter/X, Reddit, StockTwits)
- Video Platform Analysis (YouTube, TikTok, Instagram)
- Buzz & Viral Trend Detection
- Tech/IPO/Patent Tracker
- Influencer & Insider Signal Detection
- AI Hypothesis Generator
- Growth Potential Scoring
- Catalyst Timeline Prediction
"""

from src.forecasting.social_sentiment import (
    SocialSentimentEngine,
    SentimentSource,
    get_social_sentiment,
)
from src.forecasting.buzz_detector import (
    BuzzDetector,
    TrendSignal,
    get_buzz_detector,
)
from src.forecasting.speculation_scorer import (
    SpeculationScorer,
    GrowthForecast,
    get_speculation_scorer,
)
from src.forecasting.catalyst_tracker import (
    CatalystTracker,
    CatalystEvent,
    get_catalyst_tracker,
)
from src.forecasting.hypothesis_generator import (
    HypothesisGenerator,
    MarketHypothesis,
    get_hypothesis_generator,
)
from src.forecasting.video_platforms import (
    VideoPlatformAnalyzer,
    VideoContent,
    FinancialInfluencer,
    get_video_analyzer,
)

__all__ = [
    # Social Sentiment
    "SocialSentimentEngine",
    "SentimentSource",
    "get_social_sentiment",
    # Video Platforms
    "VideoPlatformAnalyzer",
    "VideoContent",
    "FinancialInfluencer",
    "get_video_analyzer",
    # Buzz Detection
    "BuzzDetector",
    "TrendSignal",
    "get_buzz_detector",
    # Speculation Scoring
    "SpeculationScorer",
    "GrowthForecast",
    "get_speculation_scorer",
    # Catalyst Tracking
    "CatalystTracker",
    "CatalystEvent",
    "get_catalyst_tracker",
    # Hypothesis Generation
    "HypothesisGenerator",
    "MarketHypothesis",
    "get_hypothesis_generator",
]

