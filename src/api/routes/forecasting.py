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


# =============================================================================
# Analysis with News References & Sources
# =============================================================================

class NewsReference(BaseModel):
    """A news article reference."""
    title: str
    url: str
    source: str
    published: str
    relevance: str  # "high", "medium", "low"
    sentiment_impact: Optional[str] = None  # "bullish", "bearish", "neutral"


class ScoreBreakdown(BaseModel):
    """Breakdown of how a score was calculated."""
    component: str
    value: float
    weight: float
    contribution: float
    explanation: str
    sources: List[str] = []


class AnalysisWithReferences(BaseModel):
    """Comprehensive analysis with references and explanations."""
    symbol: str
    current_price: float
    
    # Overall scores
    speculation_score: float
    sentiment_score: float
    probability_pct: float
    trend_direction: str
    
    # Score breakdowns with explanations
    score_breakdown: List[ScoreBreakdown]
    
    # News references
    news_articles: List[NewsReference]
    
    # Key factors
    bullish_factors: List[str]
    bearish_factors: List[str]
    
    # Methodology explanation
    methodology: Dict[str, str]
    
    # Data sources used
    data_sources: List[Dict[str, str]]
    
    # Reliability assessment
    reliability: Dict[str, Any]
    
    updated_at: str


@router.get("/analysis-with-sources/{symbol}")
async def get_analysis_with_sources(symbol: str):
    """
    Get comprehensive analysis with news references and source explanations.
    
    Returns:
    - Score breakdowns with how each component is calculated
    - News articles that influenced the analysis
    - Bullish/bearish factors with sources
    - Methodology explanations
    - Reliability assessment
    """
    try:
        import yfinance as yf
        import numpy as np
        from src.forecasting.social_sentiment import get_social_sentiment
        from src.forecasting.speculation_scorer import get_speculation_scorer
        from src.forecasting.catalyst_tracker import get_catalyst_tracker
        from src.forecasting.hypothesis_generator import get_hypothesis_generator
        
        symbol = symbol.upper()
        
        # Fetch stock data
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        if not info or not info.get("symbol"):
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
        
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        
        # Fetch news from yfinance
        news_articles = []
        try:
            yf_news = ticker.news
            if yf_news:
                for article in yf_news[:10]:
                    # Determine sentiment impact based on keywords
                    title = article.get("title", "").lower()
                    sentiment_impact = "neutral"
                    if any(w in title for w in ["surge", "rally", "beat", "profit", "growth", "upgrade", "buy"]):
                        sentiment_impact = "bullish"
                    elif any(w in title for w in ["fall", "drop", "miss", "loss", "decline", "downgrade", "sell"]):
                        sentiment_impact = "bearish"
                    
                    news_articles.append(NewsReference(
                        title=article.get("title", ""),
                        url=article.get("link", ""),
                        source=article.get("publisher", "Unknown"),
                        published=datetime.fromtimestamp(article.get("providerPublishTime", 0)).isoformat(),
                        relevance="high" if symbol in article.get("title", "").upper() else "medium",
                        sentiment_impact=sentiment_impact,
                    ))
        except Exception as e:
            logger.debug(f"Could not fetch news: {e}")
        
        # Get analysis components
        sentiment_engine = get_social_sentiment()
        speculation_scorer = get_speculation_scorer()
        catalyst_tracker = get_catalyst_tracker()
        hypothesis_generator = get_hypothesis_generator()
        
        sentiment = sentiment_engine.get_sentiment(symbol)
        catalysts = catalyst_tracker.get_catalysts(symbol, 30)
        
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
        
        # Build score breakdown with explanations
        score_breakdown = [
            ScoreBreakdown(
                component="Social Buzz",
                value=forecast.social_score,
                weight=0.20,
                contribution=forecast.social_score * 0.20,
                explanation="Measures social media activity and engagement. Higher scores indicate more discussion and interest from retail investors.",
                sources=["Twitter/X mentions", "Reddit r/wallstreetbets", "StockTwits", "Discord communities"],
            ),
            ScoreBreakdown(
                component="Sentiment Momentum",
                value=forecast.sentiment_score,
                weight=0.15,
                contribution=forecast.sentiment_score * 0.15,
                explanation="Analyzes the tone of discussions. Positive sentiment suggests bullish outlook, negative suggests bearish.",
                sources=["NLP analysis of social posts", "News article sentiment", "Analyst report tone"],
            ),
            ScoreBreakdown(
                component="Catalyst Score",
                value=forecast.catalyst_score,
                weight=0.25,
                contribution=forecast.catalyst_score * 0.25,
                explanation="Evaluates upcoming events that could move the stock price, such as earnings, FDA approvals, or product launches.",
                sources=["Earnings calendar", "SEC filings", "Company announcements", "Industry events"],
            ),
            ScoreBreakdown(
                component="Technical Setup",
                value=forecast.technical_score,
                weight=0.15,
                contribution=forecast.technical_score * 0.15,
                explanation="Analyzes chart patterns and technical indicators for potential breakouts or breakdowns.",
                sources=["Moving averages", "RSI", "MACD", "Volume analysis", "Support/resistance levels"],
            ),
            ScoreBreakdown(
                component="Momentum Score",
                value=forecast.momentum_score,
                weight=0.15,
                contribution=forecast.momentum_score * 0.15,
                explanation="Measures price trend strength and sector performance relative to the market.",
                sources=["Price action analysis", "Relative strength vs S&P 500", "Sector ETF performance"],
            ),
            ScoreBreakdown(
                component="Squeeze Potential",
                value=forecast.squeeze_score,
                weight=0.10,
                contribution=forecast.squeeze_score * 0.10,
                explanation="Evaluates short squeeze potential based on short interest and borrowing costs.",
                sources=["Short interest data", "Days to cover", "Cost to borrow", "Options market activity"],
            ),
        ]
        
        # Identify bullish and bearish factors
        bullish_factors = []
        bearish_factors = []
        
        # From news
        for article in news_articles:
            if article.sentiment_impact == "bullish":
                bullish_factors.append(f"📰 {article.title} ({article.source})")
            elif article.sentiment_impact == "bearish":
                bearish_factors.append(f"📰 {article.title} ({article.source})")
        
        # From catalysts
        for catalyst in catalysts[:3]:
            if catalyst.get("impact") in ["major", "significant"]:
                bullish_factors.append(f"🎯 Upcoming: {catalyst.get('title')} in {catalyst.get('days_until')} days")
        
        # From technicals
        if forecast.technical_score > 70:
            bullish_factors.append("📈 Strong technical setup - potential breakout pattern")
        elif forecast.technical_score < 30:
            bearish_factors.append("📉 Weak technical setup - potential breakdown pattern")
        
        if forecast.momentum_score > 70:
            bullish_factors.append("🚀 Strong momentum - outperforming the market")
        elif forecast.momentum_score < 30:
            bearish_factors.append("🐢 Weak momentum - underperforming the market")
        
        if forecast.squeeze_score > 60:
            bullish_factors.append("🔥 High short squeeze potential")
        
        # Determine trend direction
        if sentiment and sentiment.sentiment_score > 20:
            trend_direction = "bullish"
        elif sentiment and sentiment.sentiment_score < -20:
            trend_direction = "bearish"
        else:
            trend_direction = "neutral"
        
        # Methodology explanation
        methodology = {
            "speculation_score": "Weighted average of 6 components: Social Buzz (20%), Sentiment (15%), Catalysts (25%), Technical (15%), Momentum (15%), Squeeze (10%). Range: 0-100.",
            "sentiment_score": "Natural Language Processing analysis of social media posts and news articles. Range: -100 (very bearish) to +100 (very bullish).",
            "probability": "AI-generated estimate based on historical pattern matching and factor analysis. This is speculative and not financial advice.",
            "confidence_levels": "High (>70%), Medium (40-70%), Low (<40%) based on data quality and signal agreement.",
        }
        
        # Data sources
        data_sources = [
            {"name": "Yahoo Finance", "type": "Price & News", "reliability": "High"},
            {"name": "yfinance API", "type": "Historical Data", "reliability": "High"},
            {"name": "Social Sentiment Engine", "type": "Social Analysis", "reliability": "Medium"},
            {"name": "Catalyst Tracker", "type": "Events", "reliability": "High"},
            {"name": "Technical Indicators", "type": "Chart Analysis", "reliability": "High"},
        ]
        
        # Reliability assessment
        news_count = len(news_articles)
        reliability = {
            "overall": "high" if news_count >= 5 else "medium" if news_count >= 2 else "low",
            "news_coverage": news_count,
            "data_freshness": "Real-time" if news_count > 0 else "Limited",
            "confidence_factors": {
                "has_recent_news": news_count > 0,
                "has_analyst_coverage": info.get("numberOfAnalystOpinions", 0) > 0,
                "has_social_data": sentiment is not None,
                "has_upcoming_catalysts": len(catalysts) > 0,
            },
            "disclaimer": "This analysis is for informational purposes only and should not be considered financial advice. Past performance does not guarantee future results.",
        }
        
        return AnalysisWithReferences(
            symbol=symbol,
            current_price=round(float(current_price), 2),
            speculation_score=round(forecast.speculation_score, 1),
            sentiment_score=round(sentiment.sentiment_score if sentiment else 50, 1),
            probability_pct=round(hypothesis.probability_pct, 1),
            trend_direction=trend_direction,
            score_breakdown=score_breakdown,
            news_articles=news_articles,
            bullish_factors=bullish_factors[:5],
            bearish_factors=bearish_factors[:5],
            methodology=methodology,
            data_sources=data_sources,
            reliability=reliability,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating analysis with sources for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate analysis: {str(e)}")


# =============================================================================
# Price Projections / Extrapolation Forecasting
# =============================================================================

class ProjectionPoint(BaseModel):
    """A single point in the projection."""
    date: str
    value: float
    is_projection: bool = False


class PriceProjectionResponse(BaseModel):
    """Price projection response with historical and forecasted data."""
    symbol: str
    current_price: float
    projection_method: str
    confidence: str
    
    # Historical data
    historical: List[Dict[str, Any]]
    
    # Projections for different horizons
    projection_1m: List[Dict[str, Any]]
    projection_3m: List[Dict[str, Any]]
    projection_6m: List[Dict[str, Any]]
    projection_1y: List[Dict[str, Any]]
    
    # Price targets
    target_1m: Dict[str, float]
    target_3m: Dict[str, float]
    target_6m: Dict[str, float]
    target_1y: Dict[str, float]
    
    # Analyst targets if available
    analyst_targets: Dict[str, Any]
    
    # Trend analysis
    trend_direction: str
    trend_strength: float
    volatility: float
    
    updated_at: str


def calculate_linear_regression(prices: List[float]) -> tuple:
    """Calculate linear regression slope and intercept."""
    import numpy as np
    n = len(prices)
    if n < 2:
        return 0, prices[-1] if prices else 0
    
    x = np.arange(n)
    y = np.array(prices)
    
    # Calculate slope and intercept
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)
    
    if denominator == 0:
        return 0, y_mean
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    return float(slope), float(intercept)


def calculate_volatility(prices: List[float]) -> float:
    """Calculate annualized volatility."""
    import numpy as np
    if len(prices) < 2:
        return 0
    
    returns = np.diff(prices) / prices[:-1]
    daily_vol = np.std(returns)
    annualized_vol = daily_vol * np.sqrt(252)
    
    return float(annualized_vol)


def generate_projections(
    prices: List[float],
    dates: List[str],
    days_ahead: int,
    volatility: float,
    slope: float,
    intercept: float
) -> List[Dict[str, Any]]:
    """Generate price projections with confidence bands."""
    from datetime import datetime, timedelta
    import numpy as np
    
    projections = []
    last_date = datetime.strptime(dates[-1], '%Y-%m-%d')
    n = len(prices)
    last_price = prices[-1]
    
    for i in range(1, days_ahead + 1):
        future_date = last_date + timedelta(days=i)
        
        # Skip weekends
        if future_date.weekday() >= 5:
            continue
        
        # Linear projection
        projected_idx = n + i
        linear_price = slope * projected_idx + intercept
        
        # Add some mean reversion towards linear trend
        weight = min(i / 30, 1.0)  # Gradually shift to linear
        projected_price = last_price * (1 - weight) + linear_price * weight
        
        # Daily growth rate from slope
        daily_return = slope / last_price if last_price > 0 else 0
        projected_price = last_price * (1 + daily_return) ** i
        
        # Ensure positive
        projected_price = max(projected_price, last_price * 0.5)
        
        # Calculate confidence bands based on volatility and time
        std_dev = volatility * np.sqrt(i / 252) * last_price
        
        projections.append({
            "date": future_date.strftime('%Y-%m-%d'),
            "value": round(float(projected_price), 2),
            "low": round(float(projected_price - 2 * std_dev), 2),
            "high": round(float(projected_price + 2 * std_dev), 2),
            "is_projection": True,
        })
    
    return projections


@router.get("/projections/{symbol}")
async def get_price_projections(
    symbol: str,
    history_period: str = Query("1y", description="Historical data period: 3m, 6m, 1y, 2y"),
):
    """
    Get price projections/forecasts for a symbol.
    
    Returns:
    - Historical price data
    - Projected prices for 1 month, 3 months, 6 months, and 1 year ahead
    - Confidence bands based on historical volatility
    - Trend direction and strength
    - Analyst price targets (if available)
    """
    try:
        import yfinance as yf
        import numpy as np
        
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        
        if not info or not info.get("symbol"):
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
        
        # Get historical data
        hist = ticker.history(period=history_period, interval="1d")
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No historical data for '{symbol}'")
        
        # Extract prices and dates
        prices = list(hist['Close'].values)
        dates = [d.strftime('%Y-%m-%d') for d in hist.index]
        current_price = float(prices[-1])
        
        # Calculate trend metrics
        slope, intercept = calculate_linear_regression(prices)
        volatility = calculate_volatility(prices)
        
        # Determine trend direction and strength
        if len(prices) >= 20:
            short_ma = np.mean(prices[-20:])
            long_ma = np.mean(prices[-50:]) if len(prices) >= 50 else np.mean(prices)
            
            if short_ma > long_ma * 1.02:
                trend_direction = "bullish"
                trend_strength = min((short_ma / long_ma - 1) * 10, 1.0)
            elif short_ma < long_ma * 0.98:
                trend_direction = "bearish"
                trend_strength = min((1 - short_ma / long_ma) * 10, 1.0)
            else:
                trend_direction = "neutral"
                trend_strength = 0.3
        else:
            trend_direction = "neutral"
            trend_strength = 0.5
        
        # Generate historical data points
        historical = [
            {"date": d, "value": round(float(p), 2), "is_projection": False}
            for d, p in zip(dates, prices)
        ]
        
        # Generate projections for different horizons
        # Adjust slope based on analyst targets if available
        analyst_mean_target = info.get("targetMeanPrice", 0)
        if analyst_mean_target and analyst_mean_target > 0:
            # Blend linear projection with analyst target
            implied_annual_return = (analyst_mean_target / current_price) - 1
            adjusted_slope = (implied_annual_return * current_price) / 252  # Daily slope
            slope = (slope + adjusted_slope) / 2  # Average of both
        
        projection_1m = generate_projections(prices, dates, 22, volatility, slope, intercept)  # ~1 month
        projection_3m = generate_projections(prices, dates, 66, volatility, slope, intercept)  # ~3 months
        projection_6m = generate_projections(prices, dates, 126, volatility, slope, intercept)  # ~6 months
        projection_1y = generate_projections(prices, dates, 252, volatility, slope, intercept)  # ~1 year
        
        # Calculate target prices for each horizon
        def get_target(projections: List[Dict]) -> Dict[str, float]:
            if not projections:
                return {"low": current_price, "mid": current_price, "high": current_price}
            last = projections[-1]
            return {
                "low": last.get("low", current_price),
                "mid": last.get("value", current_price),
                "high": last.get("high", current_price),
            }
        
        # Get analyst targets
        analyst_targets = {
            "low": float(info.get("targetLowPrice") or 0),
            "mean": float(info.get("targetMeanPrice") or 0),
            "high": float(info.get("targetHighPrice") or 0),
            "num_analysts": info.get("numberOfAnalystOpinions", 0),
            "recommendation": info.get("recommendationKey", "none"),
        }
        
        # Determine confidence based on volatility and data quality
        if volatility < 0.2:
            confidence = "high"
        elif volatility < 0.4:
            confidence = "medium"
        else:
            confidence = "low"
        
        return PriceProjectionResponse(
            symbol=symbol.upper(),
            current_price=round(current_price, 2),
            projection_method="trend_extrapolation_with_volatility",
            confidence=confidence,
            historical=historical[-252:],  # Last year of history
            projection_1m=projection_1m,
            projection_3m=projection_3m,
            projection_6m=projection_6m,
            projection_1y=projection_1y,
            target_1m=get_target(projection_1m),
            target_3m=get_target(projection_3m),
            target_6m=get_target(projection_6m),
            target_1y=get_target(projection_1y),
            analyst_targets=analyst_targets,
            trend_direction=trend_direction,
            trend_strength=round(float(trend_strength), 2),
            volatility=round(float(volatility * 100), 2),  # As percentage
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating projections for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate projections: {str(e)}")

