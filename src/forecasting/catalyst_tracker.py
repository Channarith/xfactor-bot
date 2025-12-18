"""
Catalyst Tracker

Tracks upcoming events that could move stock prices:
- Earnings announcements
- Product launches
- FDA approvals
- IPO lockup expirations
- Insider transactions
- Conference presentations
- Partnership announcements
- Patent filings
- Regulatory decisions
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from enum import Enum

from loguru import logger


class CatalystType(Enum):
    """Types of price catalysts."""
    EARNINGS = "earnings"
    PRODUCT_LAUNCH = "product_launch"
    FDA_APPROVAL = "fda_approval"
    ACQUISITION = "acquisition"
    IPO_LOCKUP = "ipo_lockup"
    INSIDER_BUYING = "insider_buying"
    INSIDER_SELLING = "insider_selling"
    SHORT_SQUEEZE = "short_squeeze"
    OPTIONS_EXPIRY = "options_expiry"
    CONFERENCE = "conference"
    PARTNERSHIP = "partnership"
    REGULATORY = "regulatory"
    STOCK_SPLIT = "stock_split"
    DIVIDEND = "dividend"
    PATENT = "patent"
    ANALYST_DAY = "analyst_day"
    SHAREHOLDER_MEETING = "shareholder_meeting"
    MERGER = "merger"
    SPINOFF = "spinoff"
    BUYBACK = "buyback"


class CatalystImpact(Enum):
    """Expected impact level."""
    MAJOR = "major"           # Can move stock 10%+
    SIGNIFICANT = "significant"  # 5-10% move expected
    MODERATE = "moderate"     # 2-5% move expected
    MINOR = "minor"           # <2% move expected


@dataclass
class CatalystEvent:
    """A price catalyst event."""
    id: str
    symbol: str
    catalyst_type: CatalystType
    title: str
    description: str
    expected_date: datetime
    impact: CatalystImpact
    
    # Expected outcomes
    bullish_outcome: str = ""
    bearish_outcome: str = ""
    expected_move_pct: float = 0.0
    
    # Confidence and source
    confidence: float = 50.0    # 0-100
    source: str = ""
    verified: bool = False
    
    # Additional metadata
    sector: str = ""
    related_symbols: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Tracking
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def days_until(self) -> int:
        """Days until event."""
        delta = self.expected_date - datetime.now(timezone.utc)
        return max(0, delta.days)
    
    @property
    def is_imminent(self) -> bool:
        """Event within 3 days."""
        return 0 <= self.days_until <= 3
    
    @property
    def is_past(self) -> bool:
        """Event has passed."""
        return self.expected_date < datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "catalyst_type": self.catalyst_type.value,
            "title": self.title,
            "description": self.description,
            "expected_date": self.expected_date.isoformat(),
            "days_until": self.days_until,
            "is_imminent": self.is_imminent,
            "impact": self.impact.value,
            "bullish_outcome": self.bullish_outcome,
            "bearish_outcome": self.bearish_outcome,
            "expected_move_pct": self.expected_move_pct,
            "confidence": round(self.confidence, 1),
            "source": self.source,
            "verified": self.verified,
            "sector": self.sector,
            "related_symbols": self.related_symbols,
            "tags": self.tags,
        }


class CatalystTracker:
    """
    Tracks and manages price catalyst events.
    
    Usage:
        tracker = CatalystTracker()
        
        # Add a catalyst
        tracker.add_catalyst(event)
        
        # Get upcoming catalysts
        upcoming = tracker.get_upcoming_catalysts("NVDA")
        
        # Get imminent catalysts across all symbols
        imminent = tracker.get_imminent_catalysts()
    """
    
    def __init__(self):
        self._catalysts: Dict[str, List[CatalystEvent]] = {}
        self._all_catalysts: List[CatalystEvent] = []
        
        # Load sample data
        self._load_sample_catalysts()
    
    def _load_sample_catalysts(self):
        """Load sample catalyst data for demo."""
        now = datetime.now(timezone.utc)
        
        samples = [
            CatalystEvent(
                id="nvda_earnings_q4",
                symbol="NVDA",
                catalyst_type=CatalystType.EARNINGS,
                title="NVIDIA Q4 2024 Earnings",
                description="Quarterly earnings announcement with AI/datacenter revenue focus",
                expected_date=now + timedelta(days=14),
                impact=CatalystImpact.MAJOR,
                bullish_outcome="Beat expectations, raised guidance on AI demand",
                bearish_outcome="Miss on margins or guidance concerns",
                expected_move_pct=8.0,
                confidence=95,
                source="SEC filings",
                verified=True,
                sector="Technology",
                related_symbols=["AMD", "SMCI", "MRVL"],
                tags=["AI", "datacenter", "GPU"],
            ),
            CatalystEvent(
                id="tsla_product",
                symbol="TSLA",
                catalyst_type=CatalystType.PRODUCT_LAUNCH,
                title="Tesla Robotaxi Reveal",
                description="Official unveiling of Tesla's autonomous robotaxi service",
                expected_date=now + timedelta(days=30),
                impact=CatalystImpact.MAJOR,
                bullish_outcome="Working demo, clear path to commercialization",
                bearish_outcome="Delays, unclear timeline, regulatory concerns",
                expected_move_pct=15.0,
                confidence=70,
                source="Elon Musk Twitter",
                verified=False,
                sector="Automotive/Tech",
                related_symbols=["UBER", "LYFT", "GOOGL"],
                tags=["robotaxi", "autonomous", "FSD"],
            ),
            CatalystEvent(
                id="mrna_fda",
                symbol="MRNA",
                catalyst_type=CatalystType.FDA_APPROVAL,
                title="Moderna RSV Vaccine FDA Decision",
                description="FDA PDUFA date for RSV vaccine approval",
                expected_date=now + timedelta(days=21),
                impact=CatalystImpact.MAJOR,
                bullish_outcome="Full approval, strong label",
                bearish_outcome="Rejection or request for more data",
                expected_move_pct=20.0,
                confidence=80,
                source="FDA calendar",
                verified=True,
                sector="Biotech",
                related_symbols=["PFE", "GSK", "BNTX"],
                tags=["FDA", "vaccine", "RSV"],
            ),
            CatalystEvent(
                id="aapl_wwdc",
                symbol="AAPL",
                catalyst_type=CatalystType.CONFERENCE,
                title="Apple WWDC 2025",
                description="Developer conference with iOS, macOS, AI announcements",
                expected_date=now + timedelta(days=45),
                impact=CatalystImpact.SIGNIFICANT,
                bullish_outcome="Major AI features, Vision Pro updates",
                bearish_outcome="Incremental updates, no surprises",
                expected_move_pct=5.0,
                confidence=95,
                source="Apple Events",
                verified=True,
                sector="Technology",
                related_symbols=["MSFT", "GOOGL", "META"],
                tags=["AI", "iOS", "developer"],
            ),
            CatalystEvent(
                id="gme_insider",
                symbol="GME",
                catalyst_type=CatalystType.INSIDER_BUYING,
                title="Ryan Cohen Insider Purchase",
                description="CEO/Chairman significant stock purchase",
                expected_date=now - timedelta(days=2),  # Recent
                impact=CatalystImpact.SIGNIFICANT,
                bullish_outcome="Signals confidence in turnaround",
                bearish_outcome="May be priced in",
                expected_move_pct=10.0,
                confidence=90,
                source="SEC Form 4",
                verified=True,
                sector="Retail",
                related_symbols=["AMC", "BBBY", "KOSS"],
                tags=["insider", "meme stock", "turnaround"],
            ),
            CatalystEvent(
                id="rivn_lockup",
                symbol="RIVN",
                catalyst_type=CatalystType.IPO_LOCKUP,
                title="Rivian Lockup Expiration",
                description="180-day IPO lockup expiration allowing insider sales",
                expected_date=now + timedelta(days=10),
                impact=CatalystImpact.SIGNIFICANT,
                bullish_outcome="Insiders hold, confidence signal",
                bearish_outcome="Heavy insider selling, supply flood",
                expected_move_pct=12.0,
                confidence=95,
                source="IPO prospectus",
                verified=True,
                sector="Automotive",
                related_symbols=["LCID", "TSLA", "FSR"],
                tags=["IPO", "lockup", "EV"],
            ),
            CatalystEvent(
                id="spy_opex",
                symbol="SPY",
                catalyst_type=CatalystType.OPTIONS_EXPIRY,
                title="Monthly Options Expiration (OPEX)",
                description="Third Friday monthly options expiration - high gamma exposure",
                expected_date=now + timedelta(days=5),
                impact=CatalystImpact.MODERATE,
                bullish_outcome="Gamma squeeze higher if above key strikes",
                bearish_outcome="Pin to max pain, volatility crush",
                expected_move_pct=2.0,
                confidence=100,
                source="Options calendar",
                verified=True,
                sector="Index",
                related_symbols=["QQQ", "IWM", "DIA"],
                tags=["options", "gamma", "OPEX"],
            ),
            CatalystEvent(
                id="coin_split",
                symbol="COIN",
                catalyst_type=CatalystType.STOCK_SPLIT,
                title="Coinbase 10:1 Stock Split",
                description="Stock split to increase retail accessibility",
                expected_date=now + timedelta(days=60),
                impact=CatalystImpact.MODERATE,
                bullish_outcome="Increased retail interest, liquidity",
                bearish_outcome="Split doesn't change fundamentals",
                expected_move_pct=5.0,
                confidence=60,
                source="Rumored",
                verified=False,
                sector="Fintech",
                related_symbols=["HOOD", "MSTR", "SQ"],
                tags=["split", "crypto", "retail"],
            ),
        ]
        
        for catalyst in samples:
            self.add_catalyst(catalyst)
    
    def add_catalyst(self, event: CatalystEvent) -> None:
        """Add a catalyst event."""
        symbol = event.symbol.upper()
        
        if symbol not in self._catalysts:
            self._catalysts[symbol] = []
        
        # Check for duplicates
        existing_ids = [c.id for c in self._catalysts[symbol]]
        if event.id not in existing_ids:
            self._catalysts[symbol].append(event)
            self._all_catalysts.append(event)
            
            # Sort by date
            self._catalysts[symbol].sort(key=lambda c: c.expected_date)
    
    def remove_catalyst(self, event_id: str) -> bool:
        """Remove a catalyst by ID."""
        for symbol, catalysts in self._catalysts.items():
            for i, catalyst in enumerate(catalysts):
                if catalyst.id == event_id:
                    del catalysts[i]
                    self._all_catalysts = [c for c in self._all_catalysts if c.id != event_id]
                    return True
        return False
    
    def get_catalysts(
        self,
        symbol: str,
        days_ahead: int = 90,
        catalyst_types: Optional[List[CatalystType]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming catalysts for a symbol.
        
        Args:
            symbol: Stock symbol
            days_ahead: Look-ahead window
            catalyst_types: Filter by catalyst types
        
        Returns:
            List of catalyst dictionaries
        """
        symbol = symbol.upper()
        catalysts = self._catalysts.get(symbol, [])
        
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)
        
        filtered = [c for c in catalysts if now <= c.expected_date <= cutoff]
        
        if catalyst_types:
            filtered = [c for c in filtered if c.catalyst_type in catalyst_types]
        
        return [c.to_dict() for c in filtered]
    
    def get_imminent_catalysts(
        self,
        days: int = 7,
        min_impact: CatalystImpact = CatalystImpact.MODERATE,
    ) -> List[Dict[str, Any]]:
        """
        Get imminent catalysts across all symbols.
        
        Args:
            days: Days to look ahead
            min_impact: Minimum impact level
        
        Returns:
            List of imminent catalysts sorted by date
        """
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days)
        
        impact_order = [
            CatalystImpact.MAJOR,
            CatalystImpact.SIGNIFICANT,
            CatalystImpact.MODERATE,
            CatalystImpact.MINOR,
        ]
        min_index = impact_order.index(min_impact)
        allowed_impacts = impact_order[:min_index + 1]
        
        imminent = [
            c.to_dict() for c in self._all_catalysts
            if now <= c.expected_date <= cutoff and c.impact in allowed_impacts
        ]
        
        return sorted(imminent, key=lambda x: x["expected_date"])
    
    def get_major_catalysts(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get major impact catalysts only."""
        return self.get_imminent_catalysts(days, CatalystImpact.MAJOR)
    
    def get_by_type(
        self,
        catalyst_type: CatalystType,
        days_ahead: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get catalysts by type across all symbols."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)
        
        filtered = [
            c.to_dict() for c in self._all_catalysts
            if c.catalyst_type == catalyst_type and now <= c.expected_date <= cutoff
        ]
        
        return sorted(filtered, key=lambda x: x["expected_date"])
    
    def get_earnings_calendar(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get upcoming earnings announcements."""
        return self.get_by_type(CatalystType.EARNINGS, days)
    
    def get_fda_calendar(self, days: int = 90) -> List[Dict[str, Any]]:
        """Get upcoming FDA decisions."""
        return self.get_by_type(CatalystType.FDA_APPROVAL, days)
    
    def get_product_launches(self, days: int = 90) -> List[Dict[str, Any]]:
        """Get upcoming product launches."""
        return self.get_by_type(CatalystType.PRODUCT_LAUNCH, days)
    
    def get_insider_activity(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent and upcoming insider transactions."""
        results = []
        
        for catalyst_type in [CatalystType.INSIDER_BUYING, CatalystType.INSIDER_SELLING]:
            results.extend(self.get_by_type(catalyst_type, days))
        
        return sorted(results, key=lambda x: x["expected_date"])
    
    def get_lockup_expirations(self, days: int = 60) -> List[Dict[str, Any]]:
        """Get upcoming IPO lockup expirations."""
        return self.get_by_type(CatalystType.IPO_LOCKUP, days)
    
    def get_catalyst_density(
        self,
        symbol: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get catalyst density analysis for a symbol.
        
        Returns:
            Analysis of catalyst concentration
        """
        catalysts = self.get_catalysts(symbol, days)
        
        if not catalysts:
            return {
                "symbol": symbol,
                "catalyst_count": 0,
                "density_score": 0,
                "nearest_catalyst": None,
                "risk_level": "low",
            }
        
        # Count by type
        by_type = {}
        for c in catalysts:
            ctype = c["catalyst_type"]
            by_type[ctype] = by_type.get(ctype, 0) + 1
        
        # Calculate density score
        major_count = len([c for c in catalysts if c["impact"] == "major"])
        significant_count = len([c for c in catalysts if c["impact"] == "significant"])
        
        density_score = (major_count * 30 + significant_count * 15 + len(catalysts) * 5)
        
        # Determine risk level
        if density_score >= 60:
            risk_level = "very_high"
        elif density_score >= 40:
            risk_level = "high"
        elif density_score >= 20:
            risk_level = "moderate"
        else:
            risk_level = "low"
        
        return {
            "symbol": symbol,
            "catalyst_count": len(catalysts),
            "by_type": by_type,
            "major_count": major_count,
            "significant_count": significant_count,
            "density_score": density_score,
            "nearest_catalyst": catalysts[0] if catalysts else None,
            "risk_level": risk_level,
        }
    
    def search_catalysts(
        self,
        query: str,
        days_ahead: int = 90,
    ) -> List[Dict[str, Any]]:
        """Search catalysts by keyword."""
        query_lower = query.lower()
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)
        
        results = []
        for catalyst in self._all_catalysts:
            if catalyst.expected_date < now or catalyst.expected_date > cutoff:
                continue
            
            # Search in title, description, tags
            searchable = (
                catalyst.title.lower() +
                catalyst.description.lower() +
                " ".join(catalyst.tags).lower()
            )
            
            if query_lower in searchable:
                results.append(catalyst.to_dict())
        
        return sorted(results, key=lambda x: x["expected_date"])


# Singleton instance
_catalyst_tracker: Optional[CatalystTracker] = None


def get_catalyst_tracker() -> CatalystTracker:
    """Get or create the catalyst tracker singleton."""
    global _catalyst_tracker
    if _catalyst_tracker is None:
        _catalyst_tracker = CatalystTracker()
    return _catalyst_tracker

