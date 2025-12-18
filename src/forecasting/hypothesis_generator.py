"""
AI Hypothesis Generator

Uses AI/LLM to generate market hypotheses and predictions based on:
- Social sentiment data
- News and announcements
- Technical patterns
- Macro economic indicators
- Historical analogies
- Cross-sector analysis

This is the "speculation brain" that synthesizes all signals
into actionable trading hypotheses.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
import asyncio
import json

from loguru import logger


class HypothesisConfidence(Enum):
    """Confidence level in hypothesis."""
    HIGH = "high"           # 70%+ probability
    MEDIUM = "medium"       # 40-70% probability
    LOW = "low"             # 20-40% probability
    SPECULATIVE = "speculative"  # <20% but interesting


class HypothesisTimeframe(Enum):
    """Expected realization timeframe."""
    IMMEDIATE = "immediate"     # 1-3 days
    SHORT_TERM = "short_term"   # 1-2 weeks
    MEDIUM_TERM = "medium_term" # 1-3 months
    LONG_TERM = "long_term"     # 3-12 months


class HypothesisCategory(Enum):
    """Hypothesis category."""
    EARNINGS_PLAY = "earnings_play"
    SECTOR_ROTATION = "sector_rotation"
    MACRO_THEME = "macro_theme"
    MOMENTUM_TRADE = "momentum_trade"
    VALUE_DISCOVERY = "value_discovery"
    EVENT_DRIVEN = "event_driven"
    TECHNICAL_BREAKOUT = "technical_breakout"
    SOCIAL_MOMENTUM = "social_momentum"
    CONTRARIAN = "contrarian"
    THEMATIC = "thematic"


@dataclass
class MarketHypothesis:
    """A market hypothesis/prediction."""
    id: str
    title: str
    thesis: str                    # Main argument
    category: HypothesisCategory
    confidence: HypothesisConfidence
    timeframe: HypothesisTimeframe
    
    # Trade setup
    symbols: List[str]
    primary_symbol: str
    direction: str                 # "long" or "short"
    entry_strategy: str
    exit_strategy: str
    risk_management: str
    
    # Supporting evidence
    supporting_signals: List[str]
    contrary_signals: List[str]
    key_risks: List[str]
    
    # Probability and targets
    probability_pct: float
    upside_pct: float
    downside_pct: float
    risk_reward_ratio: float
    
    # Validation criteria
    validation_triggers: List[str]   # What would confirm the thesis
    invalidation_triggers: List[str] # What would disprove the thesis
    
    # Metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=7))
    source: str = "AI_generated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "thesis": self.thesis,
            "category": self.category.value,
            "confidence": self.confidence.value,
            "timeframe": self.timeframe.value,
            "symbols": self.symbols,
            "primary_symbol": self.primary_symbol,
            "direction": self.direction,
            "entry_strategy": self.entry_strategy,
            "exit_strategy": self.exit_strategy,
            "risk_management": self.risk_management,
            "supporting_signals": self.supporting_signals,
            "contrary_signals": self.contrary_signals,
            "key_risks": self.key_risks,
            "probability_pct": round(self.probability_pct, 1),
            "upside_pct": round(self.upside_pct, 1),
            "downside_pct": round(self.downside_pct, 1),
            "risk_reward_ratio": round(self.risk_reward_ratio, 2),
            "validation_triggers": self.validation_triggers,
            "invalidation_triggers": self.invalidation_triggers,
            "generated_at": self.generated_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


class HypothesisGenerator:
    """
    AI-powered hypothesis generator for market speculation.
    
    Usage:
        generator = HypothesisGenerator()
        
        # Generate hypothesis for a symbol
        hypothesis = await generator.generate_hypothesis("NVDA")
        
        # Generate based on theme
        hypotheses = await generator.generate_thematic_hypotheses("AI revolution")
        
        # Get all active hypotheses
        active = generator.get_active_hypotheses()
    """
    
    # Pre-built hypothesis templates (for when LLM not available)
    HYPOTHESIS_TEMPLATES = [
        {
            "category": HypothesisCategory.SOCIAL_MOMENTUM,
            "template": "{symbol} is experiencing viral social momentum with {mentions}x normal mention volume. "
                       "Historical patterns suggest a {probability}% chance of a {direction} move of {magnitude}% "
                       "within {timeframe} days when social activity reaches these levels.",
        },
        {
            "category": HypothesisCategory.EARNINGS_PLAY,
            "template": "{symbol} is approaching earnings with {sentiment} sentiment and {beat_rate}% historical beat rate. "
                       "Options are pricing a {implied_move}% move. Historical volatility suggests the actual move "
                       "often {over_under} this expectation, creating a potential {strategy} opportunity.",
        },
        {
            "category": HypothesisCategory.SECTOR_ROTATION,
            "template": "Capital appears to be rotating {direction} {sector} sector based on {signal}. "
                       "{symbol} is positioned as a {beta} beta play on this rotation with "
                       "potential for {magnitude}% move over {timeframe}.",
        },
        {
            "category": HypothesisCategory.CONTRARIAN,
            "template": "{symbol} has seen extreme {sentiment} sentiment reaching {percentile}th percentile historically. "
                       "Contrarian indicators suggest a mean reversion is {probability}% likely within {timeframe}, "
                       "with potential for {magnitude}% {direction} move.",
        },
        {
            "category": HypothesisCategory.EVENT_DRIVEN,
            "template": "The upcoming {event} for {symbol} on {date} represents a binary catalyst. "
                       "Market is pricing {implied_move}% move. Bull case: {bull_case}. Bear case: {bear_case}. "
                       "Historical events of this type have {direction} bias of {probability}%.",
        },
    ]
    
    def __init__(self, llm_client=None):
        self._hypotheses: Dict[str, MarketHypothesis] = {}
        self._llm_client = llm_client  # OpenAI, Anthropic, etc.
        self._hypothesis_counter = 0
    
    async def generate_hypothesis(
        self,
        symbol: str,
        context: Optional[Dict] = None,
    ) -> MarketHypothesis:
        """
        Generate a trading hypothesis for a symbol.
        
        Args:
            symbol: Stock symbol
            context: Additional context (sentiment, catalysts, price data)
        
        Returns:
            MarketHypothesis with trading thesis
        """
        symbol = symbol.upper()
        context = context or {}
        
        # Try LLM-based generation first
        if self._llm_client:
            try:
                return await self._generate_with_llm(symbol, context)
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}, falling back to template")
        
        # Fallback to template-based generation
        return self._generate_from_template(symbol, context)
    
    async def _generate_with_llm(
        self,
        symbol: str,
        context: Dict,
    ) -> MarketHypothesis:
        """Generate hypothesis using LLM."""
        
        prompt = f"""You are an expert market analyst and trader. Generate a trading hypothesis for {symbol}.

Context:
- Social Sentiment: {context.get('sentiment', 'neutral')} ({context.get('sentiment_score', 0)}/100)
- Trending Rank: #{context.get('trending_rank', 'N/A')}
- Recent Mentions: {context.get('mentions_24h', 0)} in 24h
- Upcoming Catalysts: {context.get('catalysts', [])}
- Current Price: ${context.get('price', 'N/A')}
- 30-day Change: {context.get('change_30d', 0)}%

Generate a specific, actionable trading hypothesis with:
1. Clear thesis statement
2. Trade direction (long/short)
3. Entry and exit strategy
4. Risk management
5. Key risks
6. Probability estimate
7. Target upside/downside

Respond in JSON format."""

        # This would call OpenAI/Anthropic/etc.
        # For now, return template-based
        return self._generate_from_template(symbol, context)
    
    def _generate_from_template(
        self,
        symbol: str,
        context: Dict,
    ) -> MarketHypothesis:
        """Generate hypothesis from templates based on context."""
        
        self._hypothesis_counter += 1
        hypothesis_id = f"hyp_{symbol}_{self._hypothesis_counter}"
        
        # Determine category based on context
        if context.get("trending_score", 0) > 70:
            category = HypothesisCategory.SOCIAL_MOMENTUM
        elif context.get("catalysts"):
            category = HypothesisCategory.EVENT_DRIVEN
        elif context.get("sentiment_score", 50) > 80 or context.get("sentiment_score", 50) < 20:
            category = HypothesisCategory.CONTRARIAN
        else:
            category = HypothesisCategory.MOMENTUM_TRADE
        
        # Generate based on category
        sentiment_score = context.get("sentiment_score", 50)
        mentions = context.get("mentions_24h", 0)
        
        if category == HypothesisCategory.SOCIAL_MOMENTUM:
            thesis = (
                f"{symbol} is experiencing unusually high social media activity with "
                f"{mentions} mentions in the last 24 hours. This viral momentum pattern has "
                f"historically preceded significant price moves. The current sentiment score of "
                f"{sentiment_score}/100 suggests {'bullish' if sentiment_score > 60 else 'bearish'} bias."
            )
            direction = "long" if sentiment_score > 50 else "short"
            confidence = HypothesisConfidence.MEDIUM if mentions > 100 else HypothesisConfidence.LOW
            
        elif category == HypothesisCategory.EVENT_DRIVEN:
            catalysts = context.get("catalysts", [])
            catalyst = catalysts[0] if catalysts else {"event": "upcoming event", "days_until": 7}
            thesis = (
                f"{symbol} has a significant catalyst approaching: {catalyst.get('event', 'event')} "
                f"in approximately {catalyst.get('days_until', 7)} days. This creates an asymmetric "
                f"opportunity as the market may be underpricing the potential impact."
            )
            direction = "long"
            confidence = HypothesisConfidence.MEDIUM
            
        elif category == HypothesisCategory.CONTRARIAN:
            extreme = "bullish" if sentiment_score > 80 else "bearish"
            opposite = "bearish" if sentiment_score > 80 else "bullish"
            thesis = (
                f"{symbol} is showing extreme {extreme} sentiment at {sentiment_score}/100. "
                f"Historically, such extremes tend to mean-revert. A contrarian {opposite} "
                f"position may offer favorable risk/reward as the crowd is often wrong at extremes."
            )
            direction = "short" if sentiment_score > 80 else "long"
            confidence = HypothesisConfidence.SPECULATIVE
            
        else:  # MOMENTUM_TRADE
            thesis = (
                f"{symbol} is showing positive momentum characteristics with improving "
                f"sentiment ({sentiment_score}/100) and growing social attention. "
                f"Momentum tends to persist in the short term, suggesting continuation."
            )
            direction = "long" if sentiment_score > 50 else "short"
            confidence = HypothesisConfidence.LOW
        
        # Calculate probability and targets
        base_probability = {"high": 70, "medium": 50, "low": 35, "speculative": 20}[confidence.value]
        probability = base_probability + (sentiment_score - 50) * 0.2
        
        upside = 15 if confidence in [HypothesisConfidence.HIGH, HypothesisConfidence.MEDIUM] else 10
        downside = 8 if confidence in [HypothesisConfidence.HIGH, HypothesisConfidence.MEDIUM] else 5
        
        if direction == "short":
            upside, downside = downside, upside
        
        risk_reward = upside / max(downside, 1)
        
        # Create hypothesis
        hypothesis = MarketHypothesis(
            id=hypothesis_id,
            title=f"{symbol} {category.value.replace('_', ' ').title()} Opportunity",
            thesis=thesis,
            category=category,
            confidence=confidence,
            timeframe=HypothesisTimeframe.SHORT_TERM,
            symbols=[symbol],
            primary_symbol=symbol,
            direction=direction,
            entry_strategy=f"Enter on confirmation of {direction} momentum; scale in on pullbacks" if direction == "long" else f"Enter on failed bounce; scale in on rallies",
            exit_strategy=f"Take 50% at {upside/2}% gain, trail stop on remainder. Full exit at {upside}% or invalidation.",
            risk_management=f"Stop loss at {downside}% below entry. Maximum position size 5% of portfolio.",
            supporting_signals=[
                f"Social sentiment: {sentiment_score}/100",
                f"Mention velocity: {mentions} / 24h",
                "Momentum alignment" if sentiment_score > 50 else "Oversold bounce potential",
            ],
            contrary_signals=[
                "Broad market risk" if direction == "long" else "Short squeeze risk",
                "Speculation may not materialize",
                "Sentiment can reverse quickly",
            ],
            key_risks=[
                "High volatility expected",
                "Speculative thesis - not fundamental",
                f"Crowded {'long' if direction == 'long' else 'short'} positioning risk",
            ],
            probability_pct=probability,
            upside_pct=upside,
            downside_pct=downside,
            risk_reward_ratio=risk_reward,
            validation_triggers=[
                "Price breaks above recent highs" if direction == "long" else "Price breaks below recent lows",
                "Volume confirms direction",
                "Sentiment continues improving" if direction == "long" else "Sentiment deteriorates further",
            ],
            invalidation_triggers=[
                "Price breaks below support" if direction == "long" else "Price breaks above resistance",
                "Sentiment reverses sharply",
                "Broader market selloff" if direction == "long" else "Broader market rally",
            ],
        )
        
        self._hypotheses[hypothesis_id] = hypothesis
        return hypothesis
    
    async def generate_thematic_hypotheses(
        self,
        theme: str,
        max_results: int = 5,
    ) -> List[MarketHypothesis]:
        """
        Generate hypotheses around a market theme.
        
        Args:
            theme: Theme to analyze (e.g., "AI revolution", "rate cuts", "China reopening")
            max_results: Maximum hypotheses to generate
        
        Returns:
            List of related hypotheses
        """
        # Theme to symbol mapping (simplified)
        theme_symbols = {
            "ai": ["NVDA", "AMD", "MSFT", "GOOGL", "SMCI", "PLTR"],
            "artificial intelligence": ["NVDA", "AMD", "MSFT", "GOOGL", "SMCI", "PLTR"],
            "ev": ["TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI"],
            "electric vehicle": ["TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI"],
            "rate cut": ["TLT", "XLF", "XLU", "REIT", "O", "VNQ"],
            "interest rates": ["TLT", "XLF", "XLU", "REIT", "O", "VNQ"],
            "crypto": ["COIN", "MSTR", "RIOT", "MARA", "HOOD", "SQ"],
            "bitcoin": ["COIN", "MSTR", "RIOT", "MARA", "HOOD"],
            "healthcare": ["UNH", "JNJ", "PFE", "MRNA", "ABBV", "LLY"],
            "biotech": ["MRNA", "BNTX", "BIIB", "REGN", "VRTX", "GILD"],
            "semiconductors": ["NVDA", "AMD", "INTC", "TSM", "ASML", "AVGO"],
            "china": ["BABA", "JD", "PDD", "NIO", "BIDU", "BILI"],
            "energy": ["XOM", "CVX", "COP", "SLB", "OXY", "DVN"],
            "clean energy": ["ENPH", "SEDG", "FSLR", "RUN", "PLUG", "BE"],
            "defense": ["LMT", "RTX", "NOC", "GD", "BA", "HII"],
            "space": ["RKLB", "LUNR", "ASTS", "SPCE", "MNTS", "RDW"],
        }
        
        theme_lower = theme.lower()
        symbols = []
        
        for key, syms in theme_symbols.items():
            if key in theme_lower or theme_lower in key:
                symbols.extend(syms)
                break
        
        if not symbols:
            # Default to trending AI/tech stocks
            symbols = ["NVDA", "TSLA", "AMD", "META", "AAPL"]
        
        symbols = list(set(symbols))[:max_results]
        
        hypotheses = []
        for symbol in symbols:
            h = await self.generate_hypothesis(symbol, {"theme": theme})
            hypotheses.append(h)
        
        return hypotheses
    
    async def generate_discovery_scan(
        self,
        criteria: Optional[Dict] = None,
    ) -> List[MarketHypothesis]:
        """
        Scan for new speculative opportunities.
        
        Args:
            criteria: Scan criteria (min_sentiment, min_mentions, etc.)
        
        Returns:
            List of discovered opportunities
        """
        criteria = criteria or {}
        
        # This would integrate with social sentiment and buzz detector
        # For now, return sample discoveries
        
        discovery_symbols = ["SMCI", "ARM", "PLTR", "RKLB", "IONQ"]
        
        hypotheses = []
        for symbol in discovery_symbols:
            context = {
                "sentiment_score": 65 + (hash(symbol) % 30),
                "mentions_24h": 100 + (hash(symbol) % 500),
                "trending_score": 50 + (hash(symbol) % 40),
            }
            h = await self.generate_hypothesis(symbol, context)
            hypotheses.append(h)
        
        # Sort by probability
        hypotheses.sort(key=lambda x: x.probability_pct, reverse=True)
        
        return hypotheses
    
    def get_active_hypotheses(
        self,
        category: Optional[HypothesisCategory] = None,
        min_confidence: Optional[HypothesisConfidence] = None,
    ) -> List[Dict[str, Any]]:
        """Get all active (non-expired) hypotheses."""
        now = datetime.now(timezone.utc)
        
        active = [
            h.to_dict() for h in self._hypotheses.values()
            if h.expires_at > now
        ]
        
        if category:
            active = [h for h in active if h["category"] == category.value]
        
        if min_confidence:
            confidence_order = ["high", "medium", "low", "speculative"]
            min_index = confidence_order.index(min_confidence.value)
            allowed = confidence_order[:min_index + 1]
            active = [h for h in active if h["confidence"] in allowed]
        
        return sorted(active, key=lambda x: x["probability_pct"], reverse=True)
    
    def get_hypothesis(self, hypothesis_id: str) -> Optional[MarketHypothesis]:
        """Get a specific hypothesis by ID."""
        return self._hypotheses.get(hypothesis_id)
    
    def validate_hypothesis(
        self,
        hypothesis_id: str,
        outcome: str,
        actual_return_pct: float,
    ) -> None:
        """
        Record the outcome of a hypothesis for learning.
        
        Args:
            hypothesis_id: Hypothesis ID
            outcome: "win", "loss", or "expired"
            actual_return_pct: Actual return achieved
        """
        hypothesis = self._hypotheses.get(hypothesis_id)
        if not hypothesis:
            return
        
        # Would store for ML training
        logger.info(
            f"Hypothesis {hypothesis_id} outcome: {outcome}, "
            f"return: {actual_return_pct}%, predicted: {hypothesis.upside_pct}%"
        )


# Singleton instance
_hypothesis_generator: Optional[HypothesisGenerator] = None


def get_hypothesis_generator() -> HypothesisGenerator:
    """Get or create the hypothesis generator singleton."""
    global _hypothesis_generator
    if _hypothesis_generator is None:
        _hypothesis_generator = HypothesisGenerator()
    return _hypothesis_generator

