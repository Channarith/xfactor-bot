"""
Admin panel API routes for enabling/disabling features.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from src.api.auth import (
    LoginRequest,
    LoginResponse,
    AdminUser,
    get_admin_user,
    verify_password,
    create_session_token,
    revoke_token,
)

router = APIRouter()


# In-memory feature flags (in production, store in Redis/DB)
_feature_flags = {
    # Strategies
    "strategy_technical": True,
    "strategy_momentum": True,
    "strategy_mean_reversion": True,
    "strategy_news_sentiment": True,
    
    # News sources by category
    "news_us_sources": True,
    "news_asia_sources": True,
    "news_europe_sources": True,
    "news_latam_sources": True,
    "news_crypto_sources": True,
    "news_social_media": True,
    "news_local_files": True,
    
    # Individual major news sources
    "news_bloomberg": True,
    "news_reuters": True,
    "news_wsj": True,
    "news_cnbc": True,
    "news_finnhub_api": True,
    "news_polygon_api": True,
    "news_newsapi": True,
    
    # Risk features
    "risk_daily_loss_limit": True,
    "risk_weekly_loss_limit": True,
    "risk_max_drawdown": True,
    "risk_vix_controls": True,
    "risk_position_limits": True,
    "risk_sector_limits": True,
    
    # Circuit breakers
    "circuit_breaker_loss": True,
    "circuit_breaker_vix": True,
    "circuit_breaker_connection": True,
    "circuit_breaker_anomaly": True,
    
    # Analysis features
    "analysis_finbert": True,
    "analysis_llm": True,
    "analysis_entity_extraction": True,
    "analysis_translation": True,
    
    # Trading features
    "trading_enabled": True,
    "trading_new_entries": True,
    "trading_exits": True,
    "trading_options": False,  # Disabled by default
    "trading_futures": False,  # Disabled by default
    
    # Monitoring
    "monitoring_prometheus": True,
    "monitoring_alerts": True,
    "monitoring_audit_log": True,
}


class FeatureToggle(BaseModel):
    """Feature toggle request."""
    enabled: bool


class FeatureStatus(BaseModel):
    """Feature status response."""
    feature: str
    enabled: bool
    category: str


class BulkToggle(BaseModel):
    """Bulk toggle request."""
    features: dict[str, bool]


# =========================================================================
# Authentication
# =========================================================================

@router.post("/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """
    Login to admin panel.
    
    Use password: 106431
    """
    if not verify_password(request.password):
        logger.warning("Failed admin login attempt")
        raise HTTPException(status_code=401, detail="Invalid password")
    
    token, expires_at = create_session_token()
    logger.info("Admin logged in successfully")
    
    return LoginResponse(
        success=True,
        token=token,
        expires_at=expires_at.isoformat(),
        message="Login successful",
    )


@router.post("/logout")
async def admin_logout(admin: AdminUser = Depends(get_admin_user)):
    """Logout from admin panel."""
    revoke_token(admin.token)
    logger.info("Admin logged out")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/verify")
async def verify_session(admin: AdminUser = Depends(get_admin_user)):
    """Verify current session is valid."""
    return {"valid": True, "authenticated_at": admin.authenticated_at.isoformat()}


# =========================================================================
# Public Strategy Status (no auth required)
# =========================================================================

@router.get("/strategies/status")
async def get_strategy_status():
    """
    Get enabled/disabled status of all strategies.
    This endpoint is PUBLIC (no auth) so the UI can check strategy availability.
    """
    strategy_flags = {
        key: value 
        for key, value in _feature_flags.items() 
        if key.startswith("strategy_")
    }
    
    # Map to a more usable format for the frontend
    strategies = [
        {"id": "Technical", "enabled": strategy_flags.get("strategy_technical", True)},
        {"id": "Momentum", "enabled": strategy_flags.get("strategy_momentum", True)},
        {"id": "MeanReversion", "enabled": strategy_flags.get("strategy_mean_reversion", True)},
        {"id": "NewsSentiment", "enabled": strategy_flags.get("strategy_news_sentiment", True)},
        {"id": "Breakout", "enabled": strategy_flags.get("strategy_technical", True)},  # Part of technical
        {"id": "TrendFollowing", "enabled": strategy_flags.get("strategy_momentum", True)},  # Part of momentum
        {"id": "Scalping", "enabled": strategy_flags.get("strategy_technical", True)},
        {"id": "SwingTrading", "enabled": strategy_flags.get("strategy_momentum", True)},
        {"id": "VWAP", "enabled": strategy_flags.get("strategy_technical", True)},
        {"id": "RSI", "enabled": strategy_flags.get("strategy_technical", True)},
        {"id": "MACD", "enabled": strategy_flags.get("strategy_technical", True)},
        {"id": "BollingerBands", "enabled": strategy_flags.get("strategy_technical", True)},
        {"id": "MovingAverageCrossover", "enabled": strategy_flags.get("strategy_technical", True)},
        {"id": "InsiderFollowing", "enabled": strategy_flags.get("strategy_news_sentiment", True)},
        {"id": "SocialSentiment", "enabled": strategy_flags.get("strategy_news_sentiment", True)},
        {"id": "AIAnalysis", "enabled": True},  # AI always available
    ]
    
    return {
        "strategies": strategies,
        "flags": strategy_flags,
    }


# =========================================================================
# Feature Management
# =========================================================================

@router.get("/features")
async def get_all_features(admin: AdminUser = Depends(get_admin_user)):
    """Get all feature flags."""
    features = []
    
    for feature, enabled in _feature_flags.items():
        # Determine category from feature name
        if feature.startswith("strategy_"):
            category = "Strategies"
        elif feature.startswith("news_"):
            category = "News Sources"
        elif feature.startswith("risk_"):
            category = "Risk Management"
        elif feature.startswith("circuit_breaker_"):
            category = "Circuit Breakers"
        elif feature.startswith("analysis_"):
            category = "Analysis"
        elif feature.startswith("trading_"):
            category = "Trading"
        elif feature.startswith("monitoring_"):
            category = "Monitoring"
        else:
            category = "Other"
        
        features.append({
            "feature": feature,
            "enabled": enabled,
            "category": category,
            "display_name": feature.replace("_", " ").title(),
        })
    
    # Group by category
    grouped = {}
    for f in features:
        cat = f["category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(f)
    
    return {
        "features": features,
        "grouped": grouped,
        "total": len(features),
        "enabled_count": sum(1 for f in features if f["enabled"]),
    }


@router.get("/features/{feature}")
async def get_feature(feature: str, admin: AdminUser = Depends(get_admin_user)):
    """Get a specific feature flag."""
    if feature not in _feature_flags:
        raise HTTPException(status_code=404, detail=f"Feature '{feature}' not found")
    
    return {
        "feature": feature,
        "enabled": _feature_flags[feature],
    }


@router.patch("/features/{feature}")
async def toggle_feature(
    feature: str,
    toggle: FeatureToggle,
    admin: AdminUser = Depends(get_admin_user),
):
    """Enable or disable a feature."""
    if feature not in _feature_flags:
        raise HTTPException(status_code=404, detail=f"Feature '{feature}' not found")
    
    old_value = _feature_flags[feature]
    _feature_flags[feature] = toggle.enabled
    
    action = "enabled" if toggle.enabled else "disabled"
    logger.info(f"Admin {action} feature: {feature}")
    
    return {
        "feature": feature,
        "enabled": toggle.enabled,
        "previous": old_value,
        "message": f"Feature '{feature}' {action}",
    }


@router.post("/features/bulk")
async def bulk_toggle_features(
    bulk: BulkToggle,
    admin: AdminUser = Depends(get_admin_user),
):
    """Toggle multiple features at once."""
    results = []
    
    for feature, enabled in bulk.features.items():
        if feature in _feature_flags:
            old_value = _feature_flags[feature]
            _feature_flags[feature] = enabled
            results.append({
                "feature": feature,
                "enabled": enabled,
                "previous": old_value,
                "success": True,
            })
        else:
            results.append({
                "feature": feature,
                "success": False,
                "error": "Feature not found",
            })
    
    logger.info(f"Admin bulk updated {len(bulk.features)} features")
    
    return {
        "results": results,
        "updated": sum(1 for r in results if r.get("success")),
    }


@router.post("/features/category/{category}/toggle")
async def toggle_category(
    category: str,
    toggle: FeatureToggle,
    admin: AdminUser = Depends(get_admin_user),
):
    """Enable or disable all features in a category."""
    prefix_map = {
        "strategies": "strategy_",
        "news": "news_",
        "risk": "risk_",
        "circuit_breakers": "circuit_breaker_",
        "analysis": "analysis_",
        "trading": "trading_",
        "monitoring": "monitoring_",
    }
    
    prefix = prefix_map.get(category.lower())
    if not prefix:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
    
    updated = []
    for feature in _feature_flags:
        if feature.startswith(prefix):
            _feature_flags[feature] = toggle.enabled
            updated.append(feature)
    
    action = "enabled" if toggle.enabled else "disabled"
    logger.info(f"Admin {action} category: {category} ({len(updated)} features)")
    
    return {
        "category": category,
        "enabled": toggle.enabled,
        "updated_features": updated,
        "count": len(updated),
    }


# =========================================================================
# Emergency Controls
# =========================================================================

@router.post("/emergency/disable-all-trading")
async def emergency_disable_trading(admin: AdminUser = Depends(get_admin_user)):
    """Emergency: Disable all trading features."""
    trading_features = [f for f in _feature_flags if f.startswith("trading_")]
    
    for feature in trading_features:
        _feature_flags[feature] = False
    
    logger.warning("EMERGENCY: All trading features disabled by admin")
    
    return {
        "success": True,
        "message": "All trading features disabled",
        "disabled_features": trading_features,
    }


@router.post("/emergency/disable-all-news")
async def emergency_disable_news(admin: AdminUser = Depends(get_admin_user)):
    """Emergency: Disable all news sources."""
    news_features = [f for f in _feature_flags if f.startswith("news_")]
    
    for feature in news_features:
        _feature_flags[feature] = False
    
    logger.warning("EMERGENCY: All news sources disabled by admin")
    
    return {
        "success": True,
        "message": "All news sources disabled",
        "disabled_features": news_features,
    }


@router.post("/emergency/enable-all")
async def emergency_enable_all(admin: AdminUser = Depends(get_admin_user)):
    """Emergency: Enable all features (except options/futures)."""
    for feature in _feature_flags:
        # Keep options and futures disabled by default
        if feature not in ("trading_options", "trading_futures"):
            _feature_flags[feature] = True
    
    logger.info("Admin enabled all features")
    
    return {
        "success": True,
        "message": "All features enabled (except options/futures)",
    }


# =========================================================================
# Helper function for checking features
# =========================================================================

def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled."""
    return _feature_flags.get(feature, False)


def get_feature_flags() -> dict[str, bool]:
    """Get all feature flags (for use in other modules)."""
    return _feature_flags.copy()

