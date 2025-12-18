"""
Speculation Scoring Algorithm

Combines multiple signals to generate a growth forecast score
for stocks based on speculation, sentiment, and catalysts.

Scoring Factors:
- Social buzz score
- Sentiment momentum
- Influencer attention
- Upcoming catalysts
- Technical breakout potential
- Sector momentum
- Short interest (squeeze potential)
- Options activity (unusual volume)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from enum import Enum

from loguru import logger


class GrowthTimeframe(Enum):
    """Expected growth timeframe."""
    DAYS = "days"           # 1-7 days
    WEEKS = "weeks"         # 1-4 weeks
    MONTHS = "months"       # 1-3 months
    QUARTERS = "quarters"   # 3-12 months


class RiskLevel(Enum):
    """Risk classification."""
    VERY_HIGH = "very_high"   # Highly speculative
    HIGH = "high"             # Speculative
    MODERATE = "moderate"     # Balanced risk/reward
    LOW = "low"               # Established patterns


class CatalystType(Enum):
    """Types of price catalysts."""
    EARNINGS = "earnings"
    PRODUCT_LAUNCH = "product_launch"
    FDA_APPROVAL = "fda_approval"
    ACQUISITION = "acquisition"
    IPO_LOCKUP = "ipo_lockup"
    INSIDER_BUYING = "insider_buying"
    SHORT_SQUEEZE = "short_squeeze"
    OPTIONS_EXPIRY = "options_expiry"
    CONFERENCE = "conference"
    PARTNERSHIP = "partnership"
    REGULATORY = "regulatory"
    STOCK_SPLIT = "stock_split"


@dataclass
class GrowthForecast:
    """Growth forecast for a stock."""
    symbol: str
    speculation_score: float       # 0-100 (main score)
    growth_potential: str          # "explosive", "strong", "moderate", "limited"
    expected_timeframe: GrowthTimeframe
    risk_level: RiskLevel
    confidence: float              # 0-100
    
    # Component scores
    social_score: float = 0.0      # Social buzz
    sentiment_score: float = 0.0   # Sentiment momentum
    catalyst_score: float = 0.0    # Upcoming catalysts
    technical_score: float = 0.0   # Technical setup
    momentum_score: float = 0.0    # Price/sector momentum
    squeeze_score: float = 0.0     # Short squeeze potential
    
    # Supporting data
    key_catalysts: List[str] = field(default_factory=list)
    bull_case: str = ""
    bear_case: str = ""
    price_targets: Dict[str, float] = field(default_factory=dict)  # bullish, base, bearish
    
    # Metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=7))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "speculation_score": round(self.speculation_score, 1),
            "growth_potential": self.growth_potential,
            "expected_timeframe": self.expected_timeframe.value,
            "risk_level": self.risk_level.value,
            "confidence": round(self.confidence, 1),
            "component_scores": {
                "social": round(self.social_score, 1),
                "sentiment": round(self.sentiment_score, 1),
                "catalyst": round(self.catalyst_score, 1),
                "technical": round(self.technical_score, 1),
                "momentum": round(self.momentum_score, 1),
                "squeeze": round(self.squeeze_score, 1),
            },
            "key_catalysts": self.key_catalysts,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "price_targets": self.price_targets,
            "generated_at": self.generated_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
        }


@dataclass
class SpeculativeOpportunity:
    """A speculative trading opportunity."""
    symbol: str
    opportunity_type: str          # "breakout", "squeeze", "catalyst", "momentum"
    description: str
    entry_range: Dict[str, float]  # low, high
    target_price: float
    stop_loss: float
    risk_reward_ratio: float
    probability_score: float       # 0-100
    timeframe: str
    supporting_signals: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "opportunity_type": self.opportunity_type,
            "description": self.description,
            "entry_range": self.entry_range,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "risk_reward_ratio": round(self.risk_reward_ratio, 2),
            "probability_score": round(self.probability_score, 1),
            "timeframe": self.timeframe,
            "supporting_signals": self.supporting_signals,
        }


class SpeculationScorer:
    """
    Generates speculation scores and growth forecasts.
    
    Usage:
        scorer = SpeculationScorer()
        
        # Get forecast for a symbol
        forecast = scorer.generate_forecast("NVDA")
        
        # Get top speculative picks
        picks = scorer.get_top_speculative_picks()
        
        # Find squeeze candidates
        squeezes = scorer.find_squeeze_candidates()
    """
    
    # Weights for scoring components
    WEIGHTS = {
        "social": 0.20,
        "sentiment": 0.15,
        "catalyst": 0.25,
        "technical": 0.15,
        "momentum": 0.15,
        "squeeze": 0.10,
    }
    
    def __init__(self):
        self._forecasts: Dict[str, GrowthForecast] = {}
        self._opportunities: List[SpeculativeOpportunity] = []
        
        # Cache for external data
        self._short_interest: Dict[str, float] = {}
        self._options_volume: Dict[str, Dict] = {}
    
    def generate_forecast(
        self,
        symbol: str,
        social_data: Optional[Dict] = None,
        price_data: Optional[Dict] = None,
        catalyst_data: Optional[List[Dict]] = None,
    ) -> GrowthForecast:
        """
        Generate a comprehensive growth forecast.
        
        Args:
            symbol: Stock symbol
            social_data: Social sentiment data
            price_data: Price and technical data
            catalyst_data: Upcoming catalyst events
        
        Returns:
            GrowthForecast with speculation score
        """
        symbol = symbol.upper()
        
        # Get component scores
        social_score = self._calculate_social_score(symbol, social_data or {})
        sentiment_score = self._calculate_sentiment_score(symbol, social_data or {})
        catalyst_score = self._calculate_catalyst_score(symbol, catalyst_data or [])
        technical_score = self._calculate_technical_score(symbol, price_data or {})
        momentum_score = self._calculate_momentum_score(symbol, price_data or {})
        squeeze_score = self._calculate_squeeze_score(symbol)
        
        # Calculate weighted speculation score
        speculation_score = (
            social_score * self.WEIGHTS["social"] +
            sentiment_score * self.WEIGHTS["sentiment"] +
            catalyst_score * self.WEIGHTS["catalyst"] +
            technical_score * self.WEIGHTS["technical"] +
            momentum_score * self.WEIGHTS["momentum"] +
            squeeze_score * self.WEIGHTS["squeeze"]
        )
        
        # Determine growth potential
        if speculation_score >= 80:
            growth_potential = "explosive"
        elif speculation_score >= 60:
            growth_potential = "strong"
        elif speculation_score >= 40:
            growth_potential = "moderate"
        else:
            growth_potential = "limited"
        
        # Determine timeframe based on catalyst proximity
        if catalyst_data and any(c.get("days_until", 30) <= 7 for c in catalyst_data):
            timeframe = GrowthTimeframe.DAYS
        elif catalyst_data and any(c.get("days_until", 30) <= 30 for c in catalyst_data):
            timeframe = GrowthTimeframe.WEEKS
        elif squeeze_score > 60:
            timeframe = GrowthTimeframe.DAYS
        else:
            timeframe = GrowthTimeframe.MONTHS
        
        # Determine risk level
        volatility = price_data.get("volatility", 50) if price_data else 50
        if speculation_score > 70 and volatility > 60:
            risk_level = RiskLevel.VERY_HIGH
        elif speculation_score > 50 and volatility > 40:
            risk_level = RiskLevel.HIGH
        elif speculation_score > 30:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.LOW
        
        # Calculate confidence
        data_quality = self._assess_data_quality(social_data, price_data, catalyst_data)
        confidence = min(100, (speculation_score * 0.5) + (data_quality * 0.5))
        
        # Extract key catalysts
        key_catalysts = []
        if catalyst_data:
            key_catalysts = [c.get("event", "Unknown") for c in catalyst_data[:3]]
        if squeeze_score > 50:
            key_catalysts.append("Short Squeeze Potential")
        if social_score > 70:
            key_catalysts.append("High Social Buzz")
        
        # Generate bull/bear cases
        bull_case = self._generate_bull_case(symbol, social_score, catalyst_data, squeeze_score)
        bear_case = self._generate_bear_case(symbol, risk_level, volatility)
        
        # Estimate price targets
        current_price = price_data.get("current_price", 100) if price_data else 100
        price_targets = self._estimate_price_targets(speculation_score, current_price, volatility)
        
        forecast = GrowthForecast(
            symbol=symbol,
            speculation_score=speculation_score,
            growth_potential=growth_potential,
            expected_timeframe=timeframe,
            risk_level=risk_level,
            confidence=confidence,
            social_score=social_score,
            sentiment_score=sentiment_score,
            catalyst_score=catalyst_score,
            technical_score=technical_score,
            momentum_score=momentum_score,
            squeeze_score=squeeze_score,
            key_catalysts=key_catalysts,
            bull_case=bull_case,
            bear_case=bear_case,
            price_targets=price_targets,
        )
        
        self._forecasts[symbol] = forecast
        return forecast
    
    def _calculate_social_score(self, symbol: str, social_data: Dict) -> float:
        """Calculate social buzz score (0-100)."""
        mentions = social_data.get("total_mentions", 0)
        engagement = social_data.get("total_engagement", 0)
        trending_rank = social_data.get("trending_rank", 100)
        
        # Normalize mentions (assume 1000 mentions = 100 score)
        mention_score = min(100, mentions / 10)
        
        # Engagement score
        engagement_score = min(100, engagement / 10000 * 100)
        
        # Trending bonus
        trending_bonus = max(0, (100 - trending_rank) / 2) if trending_rank <= 100 else 0
        
        return (mention_score * 0.4 + engagement_score * 0.4 + trending_bonus * 0.2)
    
    def _calculate_sentiment_score(self, symbol: str, social_data: Dict) -> float:
        """Calculate sentiment momentum score (0-100)."""
        sentiment = social_data.get("sentiment_score", 0)  # -100 to +100
        momentum = social_data.get("momentum", "stable")
        
        # Convert sentiment to 0-100
        sentiment_normalized = (sentiment + 100) / 2
        
        # Momentum adjustment
        if momentum == "rising":
            sentiment_normalized *= 1.2
        elif momentum == "falling":
            sentiment_normalized *= 0.8
        
        return min(100, sentiment_normalized)
    
    def _calculate_catalyst_score(self, symbol: str, catalyst_data: List[Dict]) -> float:
        """Calculate catalyst proximity score (0-100)."""
        if not catalyst_data:
            return 30  # Base score
        
        score = 30
        
        for catalyst in catalyst_data:
            days_until = catalyst.get("days_until", 30)
            impact = catalyst.get("impact", "medium")
            
            # Proximity bonus
            if days_until <= 7:
                proximity_bonus = 40
            elif days_until <= 14:
                proximity_bonus = 30
            elif days_until <= 30:
                proximity_bonus = 20
            else:
                proximity_bonus = 10
            
            # Impact multiplier
            impact_mult = {"high": 1.5, "medium": 1.0, "low": 0.5}.get(impact, 1.0)
            
            score += proximity_bonus * impact_mult
        
        return min(100, score)
    
    def _calculate_technical_score(self, symbol: str, price_data: Dict) -> float:
        """Calculate technical setup score (0-100)."""
        score = 50  # Base score
        
        # Breakout potential
        if price_data.get("near_resistance", False):
            score += 15
        if price_data.get("consolidating", False):
            score += 10
        if price_data.get("volume_surge", False):
            score += 15
        
        # Trend alignment
        trend = price_data.get("trend", "neutral")
        if trend == "bullish":
            score += 10
        elif trend == "bearish":
            score -= 10
        
        return min(100, max(0, score))
    
    def _calculate_momentum_score(self, symbol: str, price_data: Dict) -> float:
        """Calculate price momentum score (0-100)."""
        score = 50
        
        # Recent performance
        change_1d = price_data.get("change_1d", 0)
        change_5d = price_data.get("change_5d", 0)
        change_20d = price_data.get("change_20d", 0)
        
        # Weight recent performance more
        score += change_1d * 2  # -2 to +2 per % change
        score += change_5d * 0.5
        score += change_20d * 0.2
        
        # Sector momentum
        sector_momentum = price_data.get("sector_momentum", 0)
        score += sector_momentum * 0.3
        
        return min(100, max(0, score))
    
    def _calculate_squeeze_score(self, symbol: str) -> float:
        """Calculate short squeeze potential score (0-100)."""
        short_interest = self._short_interest.get(symbol, 5)  # Default 5%
        options_data = self._options_volume.get(symbol, {})
        
        score = 0
        
        # Short interest contribution
        if short_interest >= 30:
            score += 50
        elif short_interest >= 20:
            score += 40
        elif short_interest >= 15:
            score += 30
        elif short_interest >= 10:
            score += 20
        else:
            score += 5
        
        # Options gamma squeeze potential
        call_volume = options_data.get("call_volume", 0)
        put_volume = options_data.get("put_volume", 1)
        call_put_ratio = call_volume / max(put_volume, 1)
        
        if call_put_ratio >= 3:
            score += 30
        elif call_put_ratio >= 2:
            score += 20
        elif call_put_ratio >= 1.5:
            score += 10
        
        # Unusual options volume
        if options_data.get("unusual_volume", False):
            score += 20
        
        return min(100, score)
    
    def _assess_data_quality(
        self,
        social_data: Optional[Dict],
        price_data: Optional[Dict],
        catalyst_data: Optional[List],
    ) -> float:
        """Assess quality/completeness of input data (0-100)."""
        score = 0
        
        if social_data and social_data.get("total_mentions", 0) > 10:
            score += 35
        if price_data and "current_price" in price_data:
            score += 35
        if catalyst_data and len(catalyst_data) > 0:
            score += 30
        
        return score
    
    def _generate_bull_case(
        self,
        symbol: str,
        social_score: float,
        catalyst_data: Optional[List[Dict]],
        squeeze_score: float,
    ) -> str:
        """Generate bull case narrative."""
        points = []
        
        if social_score > 60:
            points.append("Strong social momentum with viral potential")
        
        if catalyst_data:
            catalysts = [c.get("event", "") for c in catalyst_data[:2]]
            if catalysts:
                points.append(f"Upcoming catalysts: {', '.join(catalysts)}")
        
        if squeeze_score > 50:
            points.append("Elevated short interest creates squeeze potential")
        
        if not points:
            points.append("Standard growth trajectory based on fundamentals")
        
        return " | ".join(points)
    
    def _generate_bear_case(
        self,
        symbol: str,
        risk_level: RiskLevel,
        volatility: float,
    ) -> str:
        """Generate bear case narrative."""
        points = []
        
        if risk_level in [RiskLevel.VERY_HIGH, RiskLevel.HIGH]:
            points.append("Highly speculative - significant downside risk")
        
        if volatility > 60:
            points.append(f"High volatility ({volatility:.0f}%) - rapid reversals possible")
        
        points.append("Social momentum can reverse quickly")
        points.append("Speculation may not materialize in price action")
        
        return " | ".join(points)
    
    def _estimate_price_targets(
        self,
        speculation_score: float,
        current_price: float,
        volatility: float,
    ) -> Dict[str, float]:
        """Estimate price targets based on speculation score."""
        # Base expected move on speculation score
        if speculation_score >= 80:
            bullish_mult = 1.5 + (volatility / 100)
            base_mult = 1.2
            bearish_mult = 0.8
        elif speculation_score >= 60:
            bullish_mult = 1.3 + (volatility / 200)
            base_mult = 1.1
            bearish_mult = 0.85
        elif speculation_score >= 40:
            bullish_mult = 1.15
            base_mult = 1.05
            bearish_mult = 0.9
        else:
            bullish_mult = 1.1
            base_mult = 1.0
            bearish_mult = 0.95
        
        return {
            "bullish": round(current_price * bullish_mult, 2),
            "base": round(current_price * base_mult, 2),
            "bearish": round(current_price * bearish_mult, 2),
        }
    
    def get_forecast(self, symbol: str) -> Optional[GrowthForecast]:
        """Get cached forecast for a symbol."""
        forecast = self._forecasts.get(symbol.upper())
        
        if forecast and forecast.valid_until > datetime.now(timezone.utc):
            return forecast
        
        return None
    
    def get_top_speculative_picks(
        self,
        min_score: float = 60,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top speculative picks by score."""
        picks = [
            f.to_dict() for f in self._forecasts.values()
            if f.speculation_score >= min_score and f.valid_until > datetime.now(timezone.utc)
        ]
        
        return sorted(picks, key=lambda x: x["speculation_score"], reverse=True)[:limit]
    
    def find_squeeze_candidates(self, min_squeeze_score: float = 50) -> List[Dict[str, Any]]:
        """Find potential short squeeze candidates."""
        candidates = [
            f.to_dict() for f in self._forecasts.values()
            if f.squeeze_score >= min_squeeze_score
        ]
        
        return sorted(candidates, key=lambda x: x["component_scores"]["squeeze"], reverse=True)
    
    def update_short_interest(self, symbol: str, short_interest_pct: float) -> None:
        """Update short interest data for a symbol."""
        self._short_interest[symbol.upper()] = short_interest_pct
    
    def update_options_data(self, symbol: str, options_data: Dict) -> None:
        """Update options data for squeeze detection."""
        self._options_volume[symbol.upper()] = options_data


# Singleton instance
_speculation_scorer: Optional[SpeculationScorer] = None


def get_speculation_scorer() -> SpeculationScorer:
    """Get or create the speculation scorer singleton."""
    global _speculation_scorer
    if _speculation_scorer is None:
        _speculation_scorer = SpeculationScorer()
    return _speculation_scorer

