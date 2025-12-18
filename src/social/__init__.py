"""
Social Trading Module

Provides social trading features including strategy sharing,
copy trading, and leaderboards.
"""

from src.social.trading import (
    SocialTradingPlatform,
    get_social_trading_platform,
    SharedStrategy,
    CopyRelationship,
    CopyMode,
    PrivacyLevel,
)

__all__ = [
    "SocialTradingPlatform",
    "get_social_trading_platform",
    "SharedStrategy",
    "CopyRelationship",
    "CopyMode",
    "PrivacyLevel",
]

