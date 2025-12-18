"""
Buzz & Viral Trend Detector

Identifies stocks that are gaining unusual social media attention,
potentially before price movements occur.

Features:
- Viral mention detection
- Influencer activity tracking
- Unusual volume of discussion
- Cross-platform trend correlation
- Early mover detection
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
from collections import defaultdict
import math

from loguru import logger


class TrendStrength(Enum):
    """Trend strength classification."""
    VIRAL = "viral"           # Explosive growth (10x+ normal)
    SURGING = "surging"       # Strong growth (5x-10x normal)
    RISING = "rising"         # Moderate growth (2x-5x normal)
    STABLE = "stable"         # Normal activity
    FADING = "fading"         # Declining activity


class TrendStage(Enum):
    """Stage in the trend lifecycle."""
    EARLY = "early"           # Just starting, <1 hour old
    GROWING = "growing"       # Building momentum, 1-6 hours
    PEAK = "peak"             # Maximum activity, 6-24 hours
    MATURE = "mature"         # Established trend, 1-3 days
    DECLINING = "declining"   # Losing steam, >3 days


@dataclass
class TrendSignal:
    """A detected trend signal."""
    symbol: str
    strength: TrendStrength
    stage: TrendStage
    buzz_score: float              # 0-100
    velocity: float                # Rate of change
    acceleration: float            # Change in velocity
    mentions_current: int
    mentions_baseline: int
    first_detected: datetime
    peak_time: Optional[datetime] = None
    influencers_involved: int = 0
    cross_platform_score: float = 0.0  # 0-100 (higher = more platforms)
    predicted_peak: Optional[datetime] = None
    confidence: float = 0.0        # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "strength": self.strength.value,
            "stage": self.stage.value,
            "buzz_score": round(self.buzz_score, 1),
            "velocity": round(self.velocity, 2),
            "acceleration": round(self.acceleration, 2),
            "mentions_current": self.mentions_current,
            "mentions_baseline": self.mentions_baseline,
            "mentions_ratio": round(self.mentions_current / max(self.mentions_baseline, 1), 1),
            "first_detected": self.first_detected.isoformat(),
            "age_hours": round((datetime.now(timezone.utc) - self.first_detected).total_seconds() / 3600, 1),
            "influencers_involved": self.influencers_involved,
            "cross_platform_score": round(self.cross_platform_score, 1),
            "confidence": round(self.confidence, 1),
            "predicted_peak": self.predicted_peak.isoformat() if self.predicted_peak else None,
        }


@dataclass
class InfluencerAlert:
    """Alert when a known influencer mentions a stock."""
    influencer: str
    platform: str
    followers: int
    symbol: str
    content_snippet: str
    sentiment: float
    timestamp: datetime
    engagement_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "influencer": self.influencer,
            "platform": self.platform,
            "followers": self.followers,
            "symbol": self.symbol,
            "content_snippet": self.content_snippet[:200],
            "sentiment": round(self.sentiment, 2),
            "timestamp": self.timestamp.isoformat(),
            "engagement_rate": round(self.engagement_rate, 2),
        }


class BuzzDetector:
    """
    Detects viral trends and unusual activity patterns.
    
    Usage:
        detector = BuzzDetector()
        
        # Update with mention data
        detector.record_mention("NVDA", source="twitter", is_influencer=True)
        
        # Get trending signals
        signals = detector.get_trending_signals()
        
        # Get early movers (potential breakouts)
        early = detector.get_early_movers()
    """
    
    # Known financial influencers (would be much larger in production)
    KNOWN_INFLUENCERS = {
        "twitter": [
            {"handle": "elonmusk", "followers": 150000000, "impact": 10.0},
            {"handle": "jimcramer", "followers": 2000000, "impact": 5.0},
            {"handle": "chaikinadvisors", "followers": 500000, "impact": 4.0},
            {"handle": "stocktok", "followers": 300000, "impact": 3.0},
        ],
        "reddit": [
            {"handle": "DeepFuckingValue", "followers": 0, "impact": 8.0},  # WSB legend
            {"handle": "wallstreetbets mods", "followers": 0, "impact": 5.0},
        ],
        "youtube": [
            {"handle": "MeetKevin", "followers": 2000000, "impact": 4.0},
            {"handle": "Graham Stephan", "followers": 4000000, "impact": 4.0},
        ],
    }
    
    def __init__(self):
        # Mention tracking: symbol -> list of (timestamp, source, is_influencer, engagement)
        self._mentions: Dict[str, List[Dict]] = defaultdict(list)
        
        # Baseline activity (rolling average)
        self._baselines: Dict[str, float] = {}
        
        # Detected trends
        self._active_trends: Dict[str, TrendSignal] = {}
        
        # Influencer alerts
        self._influencer_alerts: List[InfluencerAlert] = []
        
        # Historical data for learning
        self._trend_history: List[TrendSignal] = []
    
    def record_mention(
        self,
        symbol: str,
        source: str,
        is_influencer: bool = False,
        engagement: int = 0,
        followers: int = 0,
        influencer_name: Optional[str] = None,
        content: str = "",
        sentiment: float = 0.0,
    ) -> None:
        """
        Record a stock mention for buzz analysis.
        
        Args:
            symbol: Stock symbol
            source: Platform (twitter, reddit, etc.)
            is_influencer: Whether from known influencer
            engagement: Likes + shares + comments
            followers: Author's follower count
            influencer_name: Name if known influencer
            content: Post content snippet
            sentiment: Sentiment score (-1 to +1)
        """
        symbol = symbol.upper()
        timestamp = datetime.now(timezone.utc)
        
        self._mentions[symbol].append({
            "timestamp": timestamp,
            "source": source,
            "is_influencer": is_influencer,
            "engagement": engagement,
            "followers": followers,
        })
        
        # Clean old mentions (keep last 7 days)
        cutoff = timestamp - timedelta(days=7)
        self._mentions[symbol] = [
            m for m in self._mentions[symbol]
            if m["timestamp"] > cutoff
        ]
        
        # Record influencer alert
        if is_influencer and influencer_name:
            alert = InfluencerAlert(
                influencer=influencer_name,
                platform=source,
                followers=followers,
                symbol=symbol,
                content_snippet=content,
                sentiment=sentiment,
                timestamp=timestamp,
                engagement_rate=engagement / max(followers, 1) * 100,
            )
            self._influencer_alerts.append(alert)
            logger.info(f"🚨 Influencer Alert: {influencer_name} mentioned ${symbol}")
        
        # Update trend detection
        self._update_trend(symbol)
    
    def _update_trend(self, symbol: str) -> None:
        """Update trend detection for a symbol."""
        mentions = self._mentions.get(symbol, [])
        if len(mentions) < 5:
            return
        
        now = datetime.now(timezone.utc)
        
        # Calculate current vs baseline activity
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        mentions_1h = len([m for m in mentions if m["timestamp"] > hour_ago])
        mentions_24h = len([m for m in mentions if m["timestamp"] > day_ago])
        mentions_7d = len([m for m in mentions if m["timestamp"] > week_ago])
        
        # Baseline: average hourly mentions over past week
        hours_of_data = min(168, (now - mentions[0]["timestamp"]).total_seconds() / 3600)
        baseline = (mentions_7d / max(hours_of_data, 1)) if hours_of_data > 24 else mentions_7d / 168
        
        self._baselines[symbol] = baseline
        
        # Calculate buzz metrics
        ratio = mentions_1h / max(baseline, 0.1)
        
        # Determine trend strength
        if ratio >= 10:
            strength = TrendStrength.VIRAL
        elif ratio >= 5:
            strength = TrendStrength.SURGING
        elif ratio >= 2:
            strength = TrendStrength.RISING
        elif ratio >= 0.5:
            strength = TrendStrength.STABLE
        else:
            strength = TrendStrength.FADING
        
        # Calculate velocity and acceleration
        hours_2_ago = now - timedelta(hours=2)
        hours_3_ago = now - timedelta(hours=3)
        
        mentions_2h_ago = len([m for m in mentions if hours_2_ago < m["timestamp"] <= hour_ago])
        mentions_3h_ago = len([m for m in mentions if hours_3_ago < m["timestamp"] <= hours_2_ago])
        
        velocity = mentions_1h - mentions_2h_ago
        acceleration = (mentions_1h - mentions_2h_ago) - (mentions_2h_ago - mentions_3h_ago)
        
        # Determine stage
        existing_trend = self._active_trends.get(symbol)
        if existing_trend:
            age_hours = (now - existing_trend.first_detected).total_seconds() / 3600
        else:
            age_hours = 0
        
        if age_hours < 1:
            stage = TrendStage.EARLY
        elif age_hours < 6:
            stage = TrendStage.GROWING
        elif age_hours < 24 and acceleration >= 0:
            stage = TrendStage.PEAK
        elif age_hours < 72:
            stage = TrendStage.MATURE
        else:
            stage = TrendStage.DECLINING
        
        # Count influencer mentions
        influencer_mentions = len([m for m in mentions if m["is_influencer"] and m["timestamp"] > day_ago])
        
        # Cross-platform score
        sources = set(m["source"] for m in mentions if m["timestamp"] > day_ago)
        cross_platform_score = len(sources) / 5 * 100  # Assume 5 major platforms
        
        # Calculate confidence
        confidence = min(100, (
            (mentions_24h / 10) * 20 +  # Volume factor
            (ratio * 10) +               # Buzz ratio factor
            (influencer_mentions * 10) + # Influencer factor
            (cross_platform_score * 0.3) # Cross-platform factor
        ))
        
        # Predict peak time
        if stage == TrendStage.EARLY and velocity > 0:
            # Simple prediction: peak in 6-12 hours
            predicted_peak = now + timedelta(hours=8)
        elif stage == TrendStage.GROWING:
            predicted_peak = now + timedelta(hours=4)
        else:
            predicted_peak = None
        
        # Create or update trend signal
        if strength in [TrendStrength.VIRAL, TrendStrength.SURGING, TrendStrength.RISING]:
            trend = TrendSignal(
                symbol=symbol,
                strength=strength,
                stage=stage,
                buzz_score=min(100, ratio * 10),
                velocity=velocity,
                acceleration=acceleration,
                mentions_current=mentions_1h,
                mentions_baseline=round(baseline, 2),
                first_detected=existing_trend.first_detected if existing_trend else now,
                influencers_involved=influencer_mentions,
                cross_platform_score=cross_platform_score,
                predicted_peak=predicted_peak,
                confidence=confidence,
            )
            
            self._active_trends[symbol] = trend
        elif symbol in self._active_trends:
            # Trend is fading, move to history
            self._trend_history.append(self._active_trends[symbol])
            del self._active_trends[symbol]
    
    def get_trending_signals(self, min_confidence: float = 30.0) -> List[Dict[str, Any]]:
        """
        Get all active trending signals.
        
        Args:
            min_confidence: Minimum confidence score (0-100)
        
        Returns:
            List of trend signals sorted by buzz score
        """
        signals = [
            t.to_dict() for t in self._active_trends.values()
            if t.confidence >= min_confidence
        ]
        
        return sorted(signals, key=lambda x: x["buzz_score"], reverse=True)
    
    def get_early_movers(self, max_age_hours: float = 3) -> List[Dict[str, Any]]:
        """
        Get early-stage trends (potential breakouts before they go viral).
        
        Args:
            max_age_hours: Maximum trend age in hours
        
        Returns:
            List of early-stage trends
        """
        now = datetime.now(timezone.utc)
        
        early = []
        for symbol, trend in self._active_trends.items():
            age = (now - trend.first_detected).total_seconds() / 3600
            
            if age <= max_age_hours and trend.stage in [TrendStage.EARLY, TrendStage.GROWING]:
                data = trend.to_dict()
                data["opportunity_score"] = round(
                    (trend.velocity * 5) +
                    (trend.acceleration * 10) +
                    (trend.influencers_involved * 15) +
                    (100 - age * 10),  # Earlier = better
                    1
                )
                early.append(data)
        
        return sorted(early, key=lambda x: x["opportunity_score"], reverse=True)
    
    def get_viral_alerts(self) -> List[Dict[str, Any]]:
        """Get viral trend alerts (10x+ normal activity)."""
        return [
            t.to_dict() for t in self._active_trends.values()
            if t.strength == TrendStrength.VIRAL
        ]
    
    def get_influencer_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent influencer mentions."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        alerts = [
            a.to_dict() for a in self._influencer_alerts
            if a.timestamp > cutoff
        ]
        
        return sorted(alerts, key=lambda x: x["followers"], reverse=True)
    
    def get_cross_platform_movers(self) -> List[Dict[str, Any]]:
        """Get stocks trending across multiple platforms."""
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        
        cross_platform = []
        
        for symbol, mentions in self._mentions.items():
            recent = [m for m in mentions if m["timestamp"] > day_ago]
            if len(recent) < 5:
                continue
            
            sources = set(m["source"] for m in recent)
            if len(sources) >= 3:  # At least 3 platforms
                cross_platform.append({
                    "symbol": symbol,
                    "platforms": list(sources),
                    "platform_count": len(sources),
                    "total_mentions": len(recent),
                    "avg_engagement": sum(m["engagement"] for m in recent) / len(recent),
                })
        
        return sorted(cross_platform, key=lambda x: x["platform_count"], reverse=True)


# Singleton instance
_buzz_detector: Optional[BuzzDetector] = None


def get_buzz_detector() -> BuzzDetector:
    """Get or create the buzz detector singleton."""
    global _buzz_detector
    if _buzz_detector is None:
        _buzz_detector = BuzzDetector()
    return _buzz_detector

