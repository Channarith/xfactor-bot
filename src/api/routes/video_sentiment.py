"""
Video Platform Sentiment API Routes

Endpoints for YouTube, TikTok, and Instagram trading content:
- Trending financial videos
- Influencer tracking
- Symbol mentions
- Viral alerts
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from loguru import logger


router = APIRouter(prefix="/api/video", tags=["Video Platforms"])


# =============================================================================
# Trending Content
# =============================================================================

@router.get("/trending")
async def get_trending_content(
    platform: Optional[str] = Query(None, description="youtube, tiktok, instagram"),
    category: Optional[str] = Query(None, description="stock_analysis, trading_tips, etc."),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
):
    """Get trending financial content from video platforms."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    trending = analyzer.get_trending_content(platform, category, hours, limit)
    
    return {
        "platform": platform or "all",
        "category": category,
        "hours": hours,
        "count": len(trending),
        "trending": trending,
    }


@router.get("/trending/youtube")
async def get_trending_youtube(
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
):
    """Get trending financial YouTube videos."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    return {
        "platform": "youtube",
        "trending": analyzer.get_trending_content("youtube", category, 24, limit),
    }


@router.get("/trending/tiktok")
async def get_trending_tiktok(
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
):
    """Get trending financial TikTok videos."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    return {
        "platform": "tiktok",
        "trending": analyzer.get_trending_content("tiktok", category, 24, limit),
    }


@router.get("/trending/instagram")
async def get_trending_instagram(
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
):
    """Get trending financial Instagram content."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    return {
        "platform": "instagram",
        "trending": analyzer.get_trending_content("instagram", category, 24, limit),
    }


# =============================================================================
# Symbol Content
# =============================================================================

@router.get("/symbol/{symbol}")
async def get_symbol_video_content(
    symbol: str,
    hours: int = Query(72, ge=1, le=168),
    limit: int = Query(20, ge=1, le=50),
):
    """Get all video content mentioning a symbol."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    return analyzer.get_content_for_symbol(symbol, hours, limit)


@router.get("/symbol/{symbol}/youtube")
async def get_symbol_youtube(symbol: str, limit: int = Query(10, ge=1, le=30)):
    """Get YouTube videos mentioning a symbol."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    content = analyzer.get_content_for_symbol(symbol, 72, 50)
    
    youtube_content = [
        c for c in content.get("top_content", [])
        if c.get("platform") == "youtube"
    ][:limit]
    
    return {
        "symbol": symbol.upper(),
        "platform": "youtube",
        "count": len(youtube_content),
        "content": youtube_content,
    }


@router.get("/symbol/{symbol}/tiktok")
async def get_symbol_tiktok(symbol: str, limit: int = Query(10, ge=1, le=30)):
    """Get TikTok videos mentioning a symbol."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    content = analyzer.get_content_for_symbol(symbol, 72, 50)
    
    tiktok_content = [
        c for c in content.get("top_content", [])
        if c.get("platform") == "tiktok"
    ][:limit]
    
    return {
        "symbol": symbol.upper(),
        "platform": "tiktok",
        "count": len(tiktok_content),
        "content": tiktok_content,
    }


# =============================================================================
# Influencers
# =============================================================================

@router.get("/influencers")
async def get_financial_influencers(
    platform: Optional[str] = Query(None, description="youtube, tiktok, instagram"),
    min_followers: int = Query(100000, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    """Get top financial influencers."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    influencers = analyzer.get_top_influencers(platform, limit)
    
    return {
        "platform": platform or "all",
        "min_followers": min_followers,
        "count": len(influencers),
        "influencers": influencers,
    }


@router.get("/influencers/{symbol}")
async def get_influencers_mentioning_symbol(
    symbol: str,
    platform: Optional[str] = None,
    min_followers: int = Query(50000, ge=0),
):
    """Get influencers who have mentioned a symbol."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    influencers = analyzer.get_influencer_mentions(symbol, platform, min_followers)
    
    return {
        "symbol": symbol.upper(),
        "platform": platform or "all",
        "count": len(influencers),
        "influencers": influencers,
    }


@router.get("/influencers/youtube/top")
async def get_top_youtube_influencers():
    """Get top YouTube financial influencers."""
    from src.forecasting.video_platforms import VideoPlatformAnalyzer
    
    # Return known influencers
    return {
        "platform": "youtube",
        "influencers": VideoPlatformAnalyzer.KNOWN_INFLUENCERS["youtube"],
    }


@router.get("/influencers/tiktok/top")
async def get_top_tiktok_influencers():
    """Get top TikTok financial influencers (FinTok)."""
    from src.forecasting.video_platforms import VideoPlatformAnalyzer
    
    return {
        "platform": "tiktok",
        "influencers": VideoPlatformAnalyzer.KNOWN_INFLUENCERS["tiktok"],
    }


@router.get("/influencers/instagram/top")
async def get_top_instagram_influencers():
    """Get top Instagram financial influencers."""
    from src.forecasting.video_platforms import VideoPlatformAnalyzer
    
    return {
        "platform": "instagram",
        "influencers": VideoPlatformAnalyzer.KNOWN_INFLUENCERS["instagram"],
    }


# =============================================================================
# Viral Alerts
# =============================================================================

@router.get("/viral")
async def get_viral_content(
    min_viral_score: float = Query(70, ge=0, le=100),
    hours: int = Query(24, ge=1, le=72),
):
    """Get viral financial content alerts."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    viral = analyzer.get_viral_alerts(min_viral_score, hours)
    
    return {
        "min_viral_score": min_viral_score,
        "hours": hours,
        "count": len(viral),
        "viral_content": viral,
    }


# =============================================================================
# Search & Categories
# =============================================================================

@router.get("/search")
async def search_video_content(
    query: str = Query(..., min_length=2),
    platform: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
):
    """Search video content by keyword."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    results = analyzer.search_content(query, platform, limit)
    
    return {
        "query": query,
        "platform": platform or "all",
        "count": len(results),
        "results": results,
    }


@router.get("/categories")
async def get_content_categories():
    """Get available content categories."""
    from src.forecasting.video_platforms import ContentCategory
    
    return {
        "categories": [
            {"id": cat.value, "name": cat.value.replace("_", " ").title()}
            for cat in ContentCategory
        ]
    }


@router.get("/hashtags")
async def get_tracked_hashtags():
    """Get tracked financial hashtags by platform."""
    from src.forecasting.video_platforms import VideoPlatformAnalyzer
    
    return {
        "hashtags": VideoPlatformAnalyzer.FINANCIAL_HASHTAGS
    }


# =============================================================================
# Platform Summary
# =============================================================================

@router.get("/summary")
async def get_platform_summary():
    """Get summary across all video platforms."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    return {
        "platforms": analyzer.get_platform_summary(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/dashboard")
async def get_video_dashboard():
    """Get video platform dashboard data."""
    from src.forecasting.video_platforms import get_video_analyzer
    
    analyzer = get_video_analyzer()
    
    return {
        "summary": analyzer.get_platform_summary(),
        "trending_youtube": analyzer.get_trending_content("youtube", None, 24, 5),
        "trending_tiktok": analyzer.get_trending_content("tiktok", None, 24, 5),
        "trending_instagram": analyzer.get_trending_content("instagram", None, 24, 5),
        "viral_alerts": analyzer.get_viral_alerts(75, 24),
        "top_influencers": analyzer.get_top_influencers(None, 10),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Add Content (for ingestion)
# =============================================================================

class VideoContentInput(BaseModel):
    """Input for adding video content."""
    platform: str = Field(..., description="youtube, tiktok, instagram")
    content_type: str = Field("video", description="video, short, reel, post")
    
    creator_id: str
    creator_name: str
    creator_handle: str
    creator_followers: int = 0
    creator_verified: bool = False
    
    title: str
    description: str = ""
    url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: int = 0
    
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    
    hashtags: List[str] = Field(default_factory=list)


@router.post("/content")
async def add_video_content(content: VideoContentInput):
    """Add video content for analysis."""
    from src.forecasting.video_platforms import (
        get_video_analyzer,
        VideoContent,
        VideoPlatform,
        ContentType,
    )
    
    analyzer = get_video_analyzer()
    
    try:
        platform = VideoPlatform(content.platform.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {content.platform}")
    
    try:
        content_type = ContentType(content.content_type.lower())
    except ValueError:
        content_type = ContentType.VIDEO
    
    video = VideoContent(
        id=f"{content.platform}_{datetime.now().timestamp()}",
        platform=platform,
        content_type=content_type,
        creator_id=content.creator_id,
        creator_name=content.creator_name,
        creator_handle=content.creator_handle,
        creator_followers=content.creator_followers,
        creator_verified=content.creator_verified,
        title=content.title,
        description=content.description,
        url=content.url,
        thumbnail_url=content.thumbnail_url,
        duration_seconds=content.duration_seconds,
        views=content.views,
        likes=content.likes,
        comments=content.comments,
        shares=content.shares,
        saves=content.saves,
        hashtags=content.hashtags,
    )
    
    analyzer.add_content(video)
    
    return {
        "success": True,
        "content_id": video.id,
        "symbols_detected": video.symbols_mentioned,
        "sentiment_score": round(video.sentiment_score, 2),
        "viral_score": round(video.viral_score, 1),
        "categories": [c.value for c in video.categories],
    }


@router.post("/content/batch")
async def add_video_content_batch(contents: List[VideoContentInput]):
    """Add multiple video contents for analysis."""
    from src.forecasting.video_platforms import (
        get_video_analyzer,
        VideoContent,
        VideoPlatform,
        ContentType,
    )
    
    analyzer = get_video_analyzer()
    results = []
    
    for content in contents:
        try:
            platform = VideoPlatform(content.platform.lower())
            content_type = ContentType(content.content_type.lower()) if content.content_type else ContentType.VIDEO
            
            video = VideoContent(
                id=f"{content.platform}_{datetime.now().timestamp()}_{len(results)}",
                platform=platform,
                content_type=content_type,
                creator_id=content.creator_id,
                creator_name=content.creator_name,
                creator_handle=content.creator_handle,
                creator_followers=content.creator_followers,
                creator_verified=content.creator_verified,
                title=content.title,
                description=content.description,
                url=content.url,
                views=content.views,
                likes=content.likes,
                comments=content.comments,
                shares=content.shares,
                saves=content.saves,
                hashtags=content.hashtags,
            )
            
            analyzer.add_content(video)
            results.append({"success": True, "id": video.id})
            
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    
    return {
        "total": len(contents),
        "success_count": sum(1 for r in results if r.get("success")),
        "results": results,
    }

