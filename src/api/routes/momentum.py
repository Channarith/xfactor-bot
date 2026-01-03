"""
Momentum API Routes - Endpoints for momentum screening and rankings.

Provides:
- Scanner status and manual triggers
- Sector rankings and heatmaps
- Social and news momentum
- Composite rankings and leaderboards
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class ScanStatusResponse(BaseModel):
    """Status of background scans."""
    hot_100: dict
    active_1000: dict
    full_universe: dict


class SectorInfo(BaseModel):
    """Sector information."""
    id: str
    name: str
    category: str
    etf: str
    momentum_score: float
    symbol_count: int


class MomentumResult(BaseModel):
    """Single momentum score result."""
    rank: int
    symbol: str
    sector: str
    composite_score: float
    price_momentum: float
    volume_ratio: float
    social_buzz: float
    price_change_pct: float


class TopMomentumResponse(BaseModel):
    """Response for top momentum stocks."""
    count: int
    timestamp: str
    results: List[MomentumResult]


class SectorHeatmapResponse(BaseModel):
    """Sector heatmap response."""
    sectors: dict
    timestamp: str


# ============================================================================
# Scanner Endpoints
# ============================================================================

@router.get("/scan/status", response_model=ScanStatusResponse)
async def get_scan_status():
    """Get status of all background scans."""
    from src.data.universe_scanner import get_universe_scanner
    
    scanner = get_universe_scanner()
    status = scanner.get_status()
    
    return ScanStatusResponse(
        hot_100=status.get("hot_100", {}),
        active_1000=status.get("active_1000", {}),
        full_universe=status.get("full_universe", {}),
    )


@router.post("/scan/trigger/{tier}")
async def trigger_scan(
    tier: str,
    background_tasks: BackgroundTasks,
):
    """
    Manually trigger a scan for a specific tier.
    
    Tiers: hot_100, active_1000, full_universe
    """
    from src.data.universe_scanner import get_universe_scanner, ScanTier
    
    valid_tiers = [t.value for t in ScanTier]
    if tier not in valid_tiers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: {valid_tiers}"
        )
    
    scanner = get_universe_scanner()
    
    # Run scan in background
    if tier == "hot_100":
        background_tasks.add_task(scanner.scan_hot_100)
    elif tier == "active_1000":
        background_tasks.add_task(scanner.scan_active_1000)
    elif tier == "full_universe":
        background_tasks.add_task(scanner.scan_full_universe)
    
    return {
        "status": "scan_started",
        "tier": tier,
        "message": f"Scan for {tier} started in background",
    }


# ============================================================================
# Sector Endpoints
# ============================================================================

@router.get("/sectors")
async def get_sectors():
    """Get all sectors with their momentum scores."""
    from src.data.sectors import ALL_SECTORS, SECTOR_SYMBOLS
    from src.data.momentum_screener import get_momentum_screener
    
    screener = get_momentum_screener()
    heatmap = screener.get_sector_heatmap()
    
    sectors = []
    for sector_id, definition in ALL_SECTORS.items():
        sectors.append({
            "id": sector_id,
            "name": definition.name,
            "category": definition.category.value,
            "etf": definition.etf,
            "etf_leveraged": definition.etf_leveraged,
            "momentum_score": heatmap.get(sector_id, 0),
            "symbol_count": len(SECTOR_SYMBOLS.get(sector_id, [])),
        })
    
    # Sort by momentum score
    sectors.sort(key=lambda x: x["momentum_score"], reverse=True)
    
    return {
        "count": len(sectors),
        "timestamp": datetime.now().isoformat(),
        "sectors": sectors,
    }


@router.get("/sectors/{sector_id}/top")
async def get_sector_top(
    sector_id: str,
    count: int = Query(12, ge=1, le=50),
):
    """Get top momentum stocks in a sector."""
    from src.data.sectors import ALL_SECTORS
    from src.data.momentum_screener import get_momentum_screener
    
    if sector_id not in ALL_SECTORS:
        raise HTTPException(status_code=404, detail=f"Sector not found: {sector_id}")
    
    screener = get_momentum_screener()
    top_stocks = screener.get_top_by_sector(sector_id, count=count)
    
    return {
        "sector": sector_id,
        "sector_name": ALL_SECTORS[sector_id].name,
        "count": len(top_stocks),
        "timestamp": datetime.now().isoformat(),
        "stocks": [
            {
                "rank": s.sector_rank,
                "symbol": s.symbol,
                "composite_score": round(s.composite_score, 1),
                "price_momentum": round(s.price_momentum, 1),
                "price_change_pct": round(s.price_change_pct, 2),
                "volume_ratio": round(s.volume_ratio, 2),
            }
            for s in top_stocks
        ],
    }


@router.get("/sectors/heatmap", response_model=SectorHeatmapResponse)
async def get_sector_heatmap():
    """Get sector momentum heatmap."""
    from src.data.momentum_screener import get_momentum_screener
    
    screener = get_momentum_screener()
    heatmap = screener.get_sector_heatmap()
    
    return SectorHeatmapResponse(
        sectors=heatmap,
        timestamp=datetime.now().isoformat(),
    )


@router.get("/sectors/leaders")
async def get_sector_leaders(
    count_per_sector: int = Query(3, ge=1, le=10),
):
    """Get top N leaders from each sector."""
    from src.data.momentum_screener import get_momentum_screener
    
    screener = get_momentum_screener()
    leaders = screener.get_sector_leaders(count_per_sector=count_per_sector)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "sectors": {
            sector: [
                {
                    "rank": s.sector_rank,
                    "symbol": s.symbol,
                    "composite_score": round(s.composite_score, 1),
                }
                for s in stocks
            ]
            for sector, stocks in leaders.items()
        },
    }


# ============================================================================
# Social Momentum Endpoints
# ============================================================================

@router.get("/social/trending")
async def get_social_trending(
    count: int = Query(12, ge=1, le=50),
):
    """Get top trending stocks on social media."""
    from src.forecasting.social_sentiment import get_social_sentiment_engine
    
    engine = get_social_sentiment_engine()
    trending = await engine.get_top_trending(count=count)
    
    return {
        "count": len(trending),
        "timestamp": datetime.now().isoformat(),
        "trending": trending,
    }


@router.get("/social/viral")
async def get_viral_stocks(
    min_buzz: float = Query(80, ge=0, le=100),
):
    """Get viral stocks (high buzz score)."""
    from src.forecasting.social_sentiment import get_social_sentiment_engine
    
    engine = get_social_sentiment_engine()
    viral = await engine.get_viral_stocks(min_buzz_score=min_buzz)
    
    return {
        "count": len(viral),
        "min_buzz_threshold": min_buzz,
        "timestamp": datetime.now().isoformat(),
        "viral": viral,
    }


@router.get("/social/influencers")
async def get_influencer_picks(
    min_followers: int = Query(10000, ge=1000),
):
    """Get stocks mentioned by influencers."""
    from src.forecasting.social_sentiment import get_social_sentiment_engine
    
    engine = get_social_sentiment_engine()
    picks = await engine.get_influencer_picks(min_followers=min_followers)
    
    return {
        "count": len(picks),
        "min_followers": min_followers,
        "timestamp": datetime.now().isoformat(),
        "picks": picks,
    }


# ============================================================================
# News Momentum Endpoints
# ============================================================================

@router.get("/news/hot")
async def get_hot_news(
    count: int = Query(12, ge=1, le=50),
):
    """Get stocks with highest news volume."""
    from src.data.news_momentum import get_news_momentum
    
    news = get_news_momentum()
    top_news = news.get_top_news_momentum(count=count)
    
    return {
        "count": len(top_news),
        "timestamp": datetime.now().isoformat(),
        "stocks": [n.to_dict() for n in top_news],
    }


@router.get("/news/breaking")
async def get_breaking_news():
    """Get breaking news items."""
    from src.data.news_momentum import get_news_momentum
    
    news = get_news_momentum()
    breaking = news.get_breaking_news()
    
    return {
        "count": len(breaking),
        "timestamp": datetime.now().isoformat(),
        "news": [n.to_dict() for n in breaking],
    }


@router.get("/news/positive")
async def get_positive_news(
    min_sentiment: float = Query(0.3, ge=0, le=1),
    count: int = Query(12, ge=1, le=50),
):
    """Get stocks with positive news sentiment."""
    from src.data.news_momentum import get_news_momentum
    
    news = get_news_momentum()
    positive = news.get_positive_momentum(min_sentiment=min_sentiment, count=count)
    
    return {
        "count": len(positive),
        "min_sentiment": min_sentiment,
        "timestamp": datetime.now().isoformat(),
        "stocks": [n.to_dict() for n in positive],
    }


@router.get("/news/catalyst/{catalyst_type}")
async def get_by_catalyst(
    catalyst_type: str,
):
    """Get stocks by catalyst type (earnings, fda, merger, etc.)."""
    from src.data.news_momentum import get_news_momentum, CATALYST_PATTERNS
    
    valid_catalysts = list(CATALYST_PATTERNS.keys())
    if catalyst_type not in valid_catalysts:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid catalyst type. Must be one of: {valid_catalysts}"
        )
    
    news = get_news_momentum()
    stocks = news.get_by_catalyst(catalyst_type)
    
    return {
        "catalyst": catalyst_type,
        "count": len(stocks),
        "timestamp": datetime.now().isoformat(),
        "stocks": [s.to_dict() for s in stocks],
    }


# ============================================================================
# Composite Momentum Endpoints
# ============================================================================

@router.get("/top")
async def get_top_momentum(
    count: int = Query(12, ge=1, le=100),
):
    """Get top stocks by composite momentum score."""
    from src.data.momentum_screener import get_momentum_screener
    
    screener = get_momentum_screener()
    top_scores = screener.get_top(count=count)
    
    return {
        "count": len(top_scores),
        "timestamp": datetime.now().isoformat(),
        "stocks": [
            {
                "rank": s.overall_rank,
                "symbol": s.symbol,
                "sector": s.sector,
                "composite_score": round(s.composite_score, 1),
                "price_momentum": round(s.price_momentum, 1),
                "volume_momentum": round(s.volume_momentum, 1),
                "social_buzz": round(s.social_buzz, 1),
                "news_volume": round(s.news_volume, 1),
                "price_change_pct": round(s.price_change_pct, 2),
                "volume_ratio": round(s.volume_ratio, 2),
            }
            for s in top_scores
        ],
    }


@router.get("/leaderboard")
async def get_leaderboard(
    count: int = Query(20, ge=1, le=100),
):
    """Get momentum leaderboard for display."""
    from src.data.momentum_screener import get_momentum_screener
    
    screener = get_momentum_screener()
    leaderboard = screener.get_leaderboard(count=count)
    
    return {
        "count": len(leaderboard),
        "timestamp": datetime.now().isoformat(),
        "leaderboard": leaderboard,
    }


@router.get("/search")
async def search_momentum(
    sector: Optional[str] = Query(None),
    min_score: float = Query(0, ge=0, le=100),
    min_volume_ratio: float = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Search/filter momentum scores."""
    from src.data.momentum_screener import get_momentum_screener
    
    screener = get_momentum_screener()
    results = screener.search(
        sector=sector,
        min_score=min_score,
        min_volume_ratio=min_volume_ratio,
        limit=limit,
    )
    
    return {
        "filters": {
            "sector": sector,
            "min_score": min_score,
            "min_volume_ratio": min_volume_ratio,
        },
        "count": len(results),
        "timestamp": datetime.now().isoformat(),
        "results": [s.to_dict() for s in results],
    }


@router.get("/symbol/{symbol}")
async def get_symbol_momentum(symbol: str):
    """Get momentum data for a specific symbol."""
    from src.data.momentum_screener import get_momentum_screener
    
    screener = get_momentum_screener()
    score = screener.get_symbol_score(symbol.upper())
    
    if not score:
        raise HTTPException(status_code=404, detail=f"No momentum data for {symbol}")
    
    return {
        "symbol": score.symbol,
        "sector": score.sector,
        "overall_rank": score.overall_rank,
        "sector_rank": score.sector_rank,
        "composite_score": round(score.composite_score, 1),
        "price_momentum": round(score.price_momentum, 1),
        "volume_momentum": round(score.volume_momentum, 1),
        "social_buzz": round(score.social_buzz, 1),
        "news_volume": round(score.news_volume, 1),
        "news_sentiment": round(score.news_sentiment, 2),
        "price_change_pct": round(score.price_change_pct, 2),
        "volume_ratio": round(score.volume_ratio, 2),
        "tier": score.tier,
        "timestamp": score.timestamp,
    }


@router.post("/refresh")
async def refresh_rankings(background_tasks: BackgroundTasks):
    """Refresh momentum rankings from latest scan data."""
    from src.data.momentum_screener import get_momentum_screener
    
    screener = get_momentum_screener()
    background_tasks.add_task(screener.refresh_rankings)
    
    return {
        "status": "refresh_started",
        "message": "Momentum rankings refresh started in background",
    }


@router.get("/status")
async def get_momentum_status():
    """Get overall momentum system status."""
    from src.data.universe_scanner import get_universe_scanner
    from src.data.momentum_screener import get_momentum_screener
    from src.data.news_momentum import get_news_momentum
    
    scanner = get_universe_scanner()
    screener = get_momentum_screener()
    news = get_news_momentum()
    
    return {
        "scanner": scanner.get_status(),
        "screener": screener.get_status(),
        "news": news.get_status(),
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# Momentum Bot Endpoints
# ============================================================================

@router.get("/bots/templates")
async def get_momentum_bot_templates():
    """Get available momentum bot templates."""
    from src.bot.momentum_bots import get_momentum_bot_templates
    
    templates = get_momentum_bot_templates()
    
    return {
        "count": len(templates),
        "templates": templates,
    }


@router.post("/bots/create/{template_id}")
async def create_momentum_bot(
    template_id: str,
    name: Optional[str] = None,
):
    """Create a new momentum bot from a template."""
    from src.bot.momentum_bots import create_momentum_bot, get_momentum_bot_templates
    from src.bot.bot_manager import get_bot_manager
    
    # Validate template
    templates = {t["id"]: t for t in get_momentum_bot_templates()}
    if template_id not in templates:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template. Must be one of: {list(templates.keys())}"
        )
    
    try:
        # Create bot instance
        bot = create_momentum_bot(template_id, name=name)
        
        # Register with bot manager
        manager = get_bot_manager()
        manager._bots[bot.id] = bot
        
        return {
            "status": "created",
            "bot_id": bot.id,
            "name": bot.config.name,
            "template": template_id,
            "message": f"Momentum bot created. Use POST /api/bots/{bot.id}/start to start.",
        }
        
    except Exception as e:
        logger.error(f"Failed to create momentum bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

