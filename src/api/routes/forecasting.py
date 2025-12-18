"""
Market Forecasting & Speculation API Routes

AI-powered market forecasting endpoints:
- Social sentiment analysis
- Buzz & trend detection
- Speculation scoring
- Catalyst tracking
- AI hypothesis generation
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from loguru import logger


router = APIRouter(prefix="/api/forecast", tags=["Forecasting"])


# =============================================================================
# Social Sentiment
# =============================================================================

@router.get("/sentiment/{symbol}")
async def get_symbol_sentiment(symbol: str):
    """Get social sentiment analysis for a symbol."""
    from src.forecasting.social_sentiment import get_social_sentiment
    
    engine = get_social_sentiment()
    sentiment = engine.get_sentiment(symbol)
    
    if not sentiment:
        return {
            "symbol": symbol.upper(),
            "message": "Insufficient data for sentiment analysis",
            "suggestion": "Add social posts via POST /api/forecast/sentiment/posts",
        }
    
    return sentiment.to_dict()


@router.get("/sentiment/trending/symbols")
async def get_trending_symbols(limit: int = Query(20, ge=1, le=100)):
    """Get trending symbols by social activity."""
    from src.forecasting.social_sentiment import get_social_sentiment
    
    engine = get_social_sentiment()
    return {
        "trending_symbols": engine.get_trending_symbols(limit),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sentiment/movers")
async def get_sentiment_movers(hours: int = Query(24, ge=1, le=168)):
    """Get symbols with biggest sentiment changes."""
    from src.forecasting.social_sentiment import get_social_sentiment
    
    engine = get_social_sentiment()
    return engine.get_sentiment_movers(hours)


class SocialPostInput(BaseModel):
    source: str = Field(..., description="twitter, reddit, stocktwits, etc.")
    author: str
    content: str
    likes: int = 0
    shares: int = 0
    comments: int = 0
    followers: int = 0
    is_influencer: bool = False


@router.post("/sentiment/posts")
async def add_social_post(post: SocialPostInput):
    """Add a social media post for analysis."""
    from src.forecasting.social_sentiment import get_social_sentiment, SocialPost, SentimentSource
    
    engine = get_social_sentiment()
    
    try:
        source = SentimentSource(post.source.lower())
    except ValueError:
        source = SentimentSource.TWITTER
    
    social_post = SocialPost(
        id=f"post_{datetime.now().timestamp()}",
        source=source,
        author=post.author,
        content=post.content,
        timestamp=datetime.now(timezone.utc),
        likes=post.likes,
        shares=post.shares,
        comments=post.comments,
        followers=post.followers,
        is_influencer=post.is_influencer,
    )
    
    engine.add_post(social_post)
    
    return {
        "success": True,
        "symbols_detected": social_post.symbols_mentioned,
        "sentiment_score": round(social_post.sentiment_score, 2),
    }


# =============================================================================
# Buzz & Trend Detection
# =============================================================================

@router.get("/buzz/trending")
async def get_trending_signals(min_confidence: float = Query(30.0, ge=0, le=100)):
    """Get all active trending signals."""
    from src.forecasting.buzz_detector import get_buzz_detector
    
    detector = get_buzz_detector()
    return {
        "trending_signals": detector.get_trending_signals(min_confidence),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/buzz/early-movers")
async def get_early_movers(max_age_hours: float = Query(3.0, ge=0.5, le=24)):
    """Get early-stage trends (potential breakouts before they go viral)."""
    from src.forecasting.buzz_detector import get_buzz_detector
    
    detector = get_buzz_detector()
    return {
        "early_movers": detector.get_early_movers(max_age_hours),
        "opportunity_window": f"Trends under {max_age_hours} hours old",
    }


@router.get("/buzz/viral")
async def get_viral_alerts():
    """Get viral trend alerts (10x+ normal activity)."""
    from src.forecasting.buzz_detector import get_buzz_detector
    
    detector = get_buzz_detector()
    return {"viral_alerts": detector.get_viral_alerts()}


@router.get("/buzz/influencer-alerts")
async def get_influencer_alerts(hours: int = Query(24, ge=1, le=168)):
    """Get recent influencer mentions."""
    from src.forecasting.buzz_detector import get_buzz_detector
    
    detector = get_buzz_detector()
    return {"influencer_alerts": detector.get_influencer_alerts(hours)}


@router.get("/buzz/cross-platform")
async def get_cross_platform_movers():
    """Get stocks trending across multiple platforms."""
    from src.forecasting.buzz_detector import get_buzz_detector
    
    detector = get_buzz_detector()
    return {"cross_platform_movers": detector.get_cross_platform_movers()}


class MentionInput(BaseModel):
    symbol: str
    source: str
    engagement: int = 0
    followers: int = 0
    is_influencer: bool = False
    influencer_name: Optional[str] = None
    content: str = ""
    sentiment: float = 0.0


@router.post("/buzz/mention")
async def record_mention(mention: MentionInput):
    """Record a stock mention for buzz analysis."""
    from src.forecasting.buzz_detector import get_buzz_detector
    
    detector = get_buzz_detector()
    detector.record_mention(
        symbol=mention.symbol,
        source=mention.source,
        engagement=mention.engagement,
        followers=mention.followers,
        is_influencer=mention.is_influencer,
        influencer_name=mention.influencer_name,
        content=mention.content,
        sentiment=mention.sentiment,
    )
    
    return {"success": True, "symbol": mention.symbol.upper()}


# =============================================================================
# Speculation Scoring
# =============================================================================

@router.get("/speculation/{symbol}")
async def get_speculation_forecast(symbol: str):
    """Get speculation/growth forecast for a symbol."""
    from src.forecasting.speculation_scorer import get_speculation_scorer
    from src.forecasting.social_sentiment import get_social_sentiment
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    scorer = get_speculation_scorer()
    
    # Check for cached forecast
    forecast = scorer.get_forecast(symbol)
    if forecast:
        return forecast.to_dict()
    
    # Generate new forecast with available data
    sentiment_engine = get_social_sentiment()
    catalyst_tracker = get_catalyst_tracker()
    
    sentiment = sentiment_engine.get_sentiment(symbol)
    catalysts = catalyst_tracker.get_catalysts(symbol, days_ahead=30)
    
    social_data = sentiment.to_dict() if sentiment else {}
    catalyst_data = [{"event": c["title"], "days_until": c["days_until"], "impact": c["impact"]} for c in catalysts]
    
    forecast = scorer.generate_forecast(
        symbol=symbol,
        social_data=social_data,
        catalyst_data=catalyst_data,
    )
    
    return forecast.to_dict()


@router.get("/speculation/top-picks")
async def get_top_speculative_picks(
    min_score: float = Query(60, ge=0, le=100),
    limit: int = Query(10, ge=1, le=50),
):
    """Get top speculative picks by speculation score."""
    from src.forecasting.speculation_scorer import get_speculation_scorer
    
    scorer = get_speculation_scorer()
    return {"top_picks": scorer.get_top_speculative_picks(min_score, limit)}


@router.get("/speculation/squeeze-candidates")
async def get_squeeze_candidates(min_score: float = Query(50, ge=0, le=100)):
    """Find potential short squeeze candidates."""
    from src.forecasting.speculation_scorer import get_speculation_scorer
    
    scorer = get_speculation_scorer()
    return {"squeeze_candidates": scorer.find_squeeze_candidates(min_score)}


class ShortInterestUpdate(BaseModel):
    symbol: str
    short_interest_pct: float


@router.post("/speculation/short-interest")
async def update_short_interest(data: ShortInterestUpdate):
    """Update short interest data for squeeze detection."""
    from src.forecasting.speculation_scorer import get_speculation_scorer
    
    scorer = get_speculation_scorer()
    scorer.update_short_interest(data.symbol, data.short_interest_pct)
    
    return {"success": True, "symbol": data.symbol.upper()}


# =============================================================================
# Catalyst Tracking
# =============================================================================

@router.get("/catalysts/{symbol}")
async def get_symbol_catalysts(
    symbol: str,
    days: int = Query(90, ge=1, le=365),
):
    """Get upcoming catalysts for a symbol."""
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    tracker = get_catalyst_tracker()
    return {
        "symbol": symbol.upper(),
        "catalysts": tracker.get_catalysts(symbol, days),
    }


@router.get("/catalysts/imminent")
async def get_imminent_catalysts(days: int = Query(7, ge=1, le=30)):
    """Get imminent catalysts across all symbols."""
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    tracker = get_catalyst_tracker()
    return {"imminent_catalysts": tracker.get_imminent_catalysts(days)}


@router.get("/catalysts/major")
async def get_major_catalysts(days: int = Query(30, ge=1, le=90)):
    """Get major impact catalysts only."""
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    tracker = get_catalyst_tracker()
    return {"major_catalysts": tracker.get_major_catalysts(days)}


@router.get("/catalysts/earnings")
async def get_earnings_calendar(days: int = Query(30, ge=1, le=90)):
    """Get upcoming earnings announcements."""
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    tracker = get_catalyst_tracker()
    return {"earnings_calendar": tracker.get_earnings_calendar(days)}


@router.get("/catalysts/fda")
async def get_fda_calendar(days: int = Query(90, ge=1, le=365)):
    """Get upcoming FDA decisions."""
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    tracker = get_catalyst_tracker()
    return {"fda_calendar": tracker.get_fda_calendar(days)}


@router.get("/catalysts/lockups")
async def get_lockup_expirations(days: int = Query(60, ge=1, le=180)):
    """Get upcoming IPO lockup expirations."""
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    tracker = get_catalyst_tracker()
    return {"lockup_expirations": tracker.get_lockup_expirations(days)}


@router.get("/catalysts/insider")
async def get_insider_activity(days: int = Query(30, ge=1, le=90)):
    """Get recent and upcoming insider transactions."""
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    tracker = get_catalyst_tracker()
    return {"insider_activity": tracker.get_insider_activity(days)}


@router.get("/catalysts/density/{symbol}")
async def get_catalyst_density(symbol: str, days: int = Query(30, ge=1, le=90)):
    """Get catalyst density analysis for a symbol."""
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    tracker = get_catalyst_tracker()
    return tracker.get_catalyst_density(symbol, days)


@router.get("/catalysts/search")
async def search_catalysts(
    query: str = Query(..., min_length=2),
    days: int = Query(90, ge=1, le=365),
):
    """Search catalysts by keyword."""
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    tracker = get_catalyst_tracker()
    return {"results": tracker.search_catalysts(query, days)}


# =============================================================================
# AI Hypothesis Generation
# =============================================================================

@router.get("/hypothesis/{symbol}")
async def generate_symbol_hypothesis(symbol: str):
    """Generate AI trading hypothesis for a symbol."""
    from src.forecasting.hypothesis_generator import get_hypothesis_generator
    from src.forecasting.social_sentiment import get_social_sentiment
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    
    generator = get_hypothesis_generator()
    sentiment_engine = get_social_sentiment()
    catalyst_tracker = get_catalyst_tracker()
    
    # Build context
    sentiment = sentiment_engine.get_sentiment(symbol)
    catalysts = catalyst_tracker.get_catalysts(symbol, days_ahead=30)
    
    context = {
        "sentiment_score": sentiment.sentiment_score if sentiment else 50,
        "mentions_24h": sentiment.total_mentions if sentiment else 0,
        "trending_score": sentiment.trending_score if sentiment else 0,
        "catalysts": catalysts,
    }
    
    hypothesis = await generator.generate_hypothesis(symbol, context)
    
    return hypothesis.to_dict()


@router.get("/hypothesis/theme/{theme}")
async def generate_thematic_hypotheses(
    theme: str,
    limit: int = Query(5, ge=1, le=10),
):
    """Generate hypotheses around a market theme."""
    from src.forecasting.hypothesis_generator import get_hypothesis_generator
    
    generator = get_hypothesis_generator()
    hypotheses = await generator.generate_thematic_hypotheses(theme, limit)
    
    return {
        "theme": theme,
        "hypotheses": [h.to_dict() for h in hypotheses],
    }


@router.get("/hypothesis/discovery")
async def run_discovery_scan():
    """Scan for new speculative opportunities."""
    from src.forecasting.hypothesis_generator import get_hypothesis_generator
    
    generator = get_hypothesis_generator()
    discoveries = await generator.generate_discovery_scan()
    
    return {
        "discoveries": [h.to_dict() for h in discoveries],
        "scan_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/hypothesis/active")
async def get_active_hypotheses(
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """Get all active (non-expired) hypotheses."""
    from src.forecasting.hypothesis_generator import get_hypothesis_generator, HypothesisCategory
    
    generator = get_hypothesis_generator()
    
    cat = None
    if category:
        try:
            cat = HypothesisCategory(category)
        except ValueError:
            pass
    
    return {"active_hypotheses": generator.get_active_hypotheses(cat)}


# =============================================================================
# Combined Analysis
# =============================================================================

@router.get("/analysis/{symbol}")
async def get_full_analysis(symbol: str):
    """Get comprehensive speculation analysis for a symbol."""
    from src.forecasting.social_sentiment import get_social_sentiment
    from src.forecasting.buzz_detector import get_buzz_detector
    from src.forecasting.speculation_scorer import get_speculation_scorer
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    from src.forecasting.hypothesis_generator import get_hypothesis_generator
    
    symbol = symbol.upper()
    
    # Gather all data
    sentiment_engine = get_social_sentiment()
    buzz_detector = get_buzz_detector()
    speculation_scorer = get_speculation_scorer()
    catalyst_tracker = get_catalyst_tracker()
    hypothesis_generator = get_hypothesis_generator()
    
    sentiment = sentiment_engine.get_sentiment(symbol)
    catalysts = catalyst_tracker.get_catalysts(symbol, 30)
    density = catalyst_tracker.get_catalyst_density(symbol, 30)
    
    # Generate forecast
    forecast = speculation_scorer.generate_forecast(
        symbol=symbol,
        social_data=sentiment.to_dict() if sentiment else {},
        catalyst_data=[{"event": c["title"], "days_until": c["days_until"], "impact": c["impact"]} for c in catalysts],
    )
    
    # Generate hypothesis
    hypothesis = await hypothesis_generator.generate_hypothesis(
        symbol,
        {
            "sentiment_score": sentiment.sentiment_score if sentiment else 50,
            "mentions_24h": sentiment.total_mentions if sentiment else 0,
            "catalysts": catalysts,
        }
    )
    
    return {
        "symbol": symbol,
        "analysis_time": datetime.now(timezone.utc).isoformat(),
        "sentiment": sentiment.to_dict() if sentiment else None,
        "forecast": forecast.to_dict(),
        "hypothesis": hypothesis.to_dict(),
        "catalyst_density": density,
        "upcoming_catalysts": catalysts[:5],
        "recommendation": {
            "action": hypothesis.direction.upper(),
            "confidence": hypothesis.confidence.value,
            "timeframe": hypothesis.timeframe.value,
            "key_thesis": hypothesis.thesis[:200] + "..." if len(hypothesis.thesis) > 200 else hypothesis.thesis,
        },
    }


@router.get("/dashboard")
async def get_forecasting_dashboard():
    """Get overview dashboard of all forecasting data."""
    from src.forecasting.social_sentiment import get_social_sentiment
    from src.forecasting.buzz_detector import get_buzz_detector
    from src.forecasting.catalyst_tracker import get_catalyst_tracker
    from src.forecasting.hypothesis_generator import get_hypothesis_generator
    
    sentiment_engine = get_social_sentiment()
    buzz_detector = get_buzz_detector()
    catalyst_tracker = get_catalyst_tracker()
    hypothesis_generator = get_hypothesis_generator()
    
    return {
        "trending_symbols": sentiment_engine.get_trending_symbols(10),
        "viral_alerts": buzz_detector.get_viral_alerts(),
        "early_movers": buzz_detector.get_early_movers(3),
        "influencer_alerts": buzz_detector.get_influencer_alerts(24)[:5],
        "imminent_catalysts": catalyst_tracker.get_imminent_catalysts(7)[:5],
        "active_hypotheses": hypothesis_generator.get_active_hypotheses()[:5],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

