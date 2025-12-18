"""
Forex Economic Calendar

Tracks major economic events that impact currency markets.
Provides alerts and trading adjustments for high-impact news.

Features:
- Real-time economic event calendar
- Impact assessment (high, medium, low)
- Currency impact mapping
- News trading signals
- Event-based risk management
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
import asyncio

from loguru import logger


class EventImpact(Enum):
    """Economic event impact level."""
    HIGH = "high"           # Major market movers (NFP, FOMC, ECB)
    MEDIUM = "medium"       # Moderate impact (GDP, CPI, retail sales)
    LOW = "low"             # Minor impact (housing data, etc.)


class EventCategory(Enum):
    """Economic event category."""
    CENTRAL_BANK = "central_bank"     # Interest rate decisions, speeches
    EMPLOYMENT = "employment"          # NFP, unemployment, jobless claims
    INFLATION = "inflation"            # CPI, PPI, PCE
    GDP = "gdp"                        # GDP releases
    TRADE = "trade"                    # Trade balance, imports/exports
    MANUFACTURING = "manufacturing"    # PMI, industrial production
    CONSUMER = "consumer"              # Retail sales, consumer confidence
    HOUSING = "housing"                # Housing starts, home sales
    OTHER = "other"


@dataclass
class EconomicEvent:
    """A single economic event."""
    id: str
    title: str
    country: str                       # Country code (US, EU, GB, JP, etc.)
    currency: str                      # Affected currency (USD, EUR, GBP, etc.)
    datetime_utc: datetime
    impact: EventImpact
    category: EventCategory
    
    # Forecast and actual values
    previous: Optional[str] = None     # Previous reading
    forecast: Optional[str] = None     # Consensus forecast
    actual: Optional[str] = None       # Actual result (after release)
    
    # Trading implications
    bullish_scenario: Optional[str] = None   # What makes this bullish for the currency
    bearish_scenario: Optional[str] = None   # What makes this bearish
    typical_pip_move: int = 0                # Average pip move on release
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "country": self.country,
            "currency": self.currency,
            "datetime_utc": self.datetime_utc.isoformat(),
            "impact": self.impact.value,
            "category": self.category.value,
            "previous": self.previous,
            "forecast": self.forecast,
            "actual": self.actual,
            "bullish_scenario": self.bullish_scenario,
            "bearish_scenario": self.bearish_scenario,
            "typical_pip_move": self.typical_pip_move,
        }
    
    @property
    def time_until(self) -> timedelta:
        """Time until event."""
        return self.datetime_utc - datetime.now(timezone.utc)
    
    @property
    def is_past(self) -> bool:
        """Check if event has passed."""
        return self.datetime_utc < datetime.now(timezone.utc)
    
    @property
    def is_imminent(self) -> bool:
        """Check if event is within 15 minutes."""
        delta = self.time_until
        return timedelta(0) < delta <= timedelta(minutes=15)


class EconomicCalendar:
    """
    Manages economic events and provides trading insights.
    
    Usage:
        calendar = EconomicCalendar()
        events = calendar.get_upcoming_events(hours=24)
        high_impact = calendar.get_high_impact_events(currency="USD")
        calendar.should_avoid_trading("EUR/USD")  # Check if news imminent
    """
    
    def __init__(self):
        self._events: List[EconomicEvent] = []
        self._load_sample_events()
    
    def _load_sample_events(self):
        """Load sample/demo events."""
        now = datetime.now(timezone.utc)
        
        # Sample high-impact events
        self._events = [
            # FOMC
            EconomicEvent(
                id="fomc_rate_dec",
                title="FOMC Interest Rate Decision",
                country="US",
                currency="USD",
                datetime_utc=now + timedelta(days=7),
                impact=EventImpact.HIGH,
                category=EventCategory.CENTRAL_BANK,
                previous="5.25%",
                forecast="5.25%",
                bullish_scenario="Rate hike or hawkish statement",
                bearish_scenario="Rate cut or dovish statement",
                typical_pip_move=100,
            ),
            # NFP
            EconomicEvent(
                id="us_nfp",
                title="Non-Farm Payrolls",
                country="US",
                currency="USD",
                datetime_utc=now + timedelta(days=3),
                impact=EventImpact.HIGH,
                category=EventCategory.EMPLOYMENT,
                previous="180K",
                forecast="200K",
                bullish_scenario="Actual > Forecast (stronger job market)",
                bearish_scenario="Actual < Forecast (weaker job market)",
                typical_pip_move=80,
            ),
            # ECB
            EconomicEvent(
                id="ecb_rate",
                title="ECB Interest Rate Decision",
                country="EU",
                currency="EUR",
                datetime_utc=now + timedelta(days=10),
                impact=EventImpact.HIGH,
                category=EventCategory.CENTRAL_BANK,
                previous="4.00%",
                forecast="4.00%",
                bullish_scenario="Rate hike or hawkish forward guidance",
                bearish_scenario="Rate cut or dovish forward guidance",
                typical_pip_move=80,
            ),
            # BOE
            EconomicEvent(
                id="boe_rate",
                title="Bank of England Rate Decision",
                country="GB",
                currency="GBP",
                datetime_utc=now + timedelta(days=5),
                impact=EventImpact.HIGH,
                category=EventCategory.CENTRAL_BANK,
                previous="5.00%",
                forecast="5.00%",
                bullish_scenario="Hawkish policy statement",
                bearish_scenario="Dovish policy statement",
                typical_pip_move=70,
            ),
            # US CPI
            EconomicEvent(
                id="us_cpi",
                title="US Consumer Price Index (CPI)",
                country="US",
                currency="USD",
                datetime_utc=now + timedelta(days=2),
                impact=EventImpact.HIGH,
                category=EventCategory.INFLATION,
                previous="3.2%",
                forecast="3.1%",
                bullish_scenario="Higher than expected (Fed may stay hawkish)",
                bearish_scenario="Lower than expected (Fed may cut rates)",
                typical_pip_move=60,
            ),
            # UK GDP
            EconomicEvent(
                id="uk_gdp",
                title="UK GDP (Quarterly)",
                country="GB",
                currency="GBP",
                datetime_utc=now + timedelta(days=4),
                impact=EventImpact.MEDIUM,
                category=EventCategory.GDP,
                previous="0.2%",
                forecast="0.3%",
                bullish_scenario="Growth above expectations",
                bearish_scenario="Contraction or below expectations",
                typical_pip_move=40,
            ),
            # Eurozone PMI
            EconomicEvent(
                id="eu_pmi",
                title="Eurozone Manufacturing PMI",
                country="EU",
                currency="EUR",
                datetime_utc=now + timedelta(hours=12),
                impact=EventImpact.MEDIUM,
                category=EventCategory.MANUFACTURING,
                previous="45.2",
                forecast="46.0",
                bullish_scenario="Above 50 (expansion territory)",
                bearish_scenario="Below forecast, deeper contraction",
                typical_pip_move=30,
            ),
            # Japan BOJ
            EconomicEvent(
                id="boj_rate",
                title="Bank of Japan Policy Statement",
                country="JP",
                currency="JPY",
                datetime_utc=now + timedelta(days=14),
                impact=EventImpact.HIGH,
                category=EventCategory.CENTRAL_BANK,
                previous="-0.10%",
                forecast="-0.10%",
                bullish_scenario="Hint at YCC adjustment or rate hike",
                bearish_scenario="Continued ultra-loose policy",
                typical_pip_move=100,
            ),
            # Australia RBA
            EconomicEvent(
                id="rba_rate",
                title="RBA Interest Rate Decision",
                country="AU",
                currency="AUD",
                datetime_utc=now + timedelta(days=8),
                impact=EventImpact.HIGH,
                category=EventCategory.CENTRAL_BANK,
                previous="4.10%",
                forecast="4.10%",
                bullish_scenario="Rate hike to combat inflation",
                bearish_scenario="Rate pause with dovish statement",
                typical_pip_move=60,
            ),
            # Canada Employment
            EconomicEvent(
                id="cad_employment",
                title="Canada Employment Change",
                country="CA",
                currency="CAD",
                datetime_utc=now + timedelta(days=3, hours=4),
                impact=EventImpact.MEDIUM,
                category=EventCategory.EMPLOYMENT,
                previous="25.0K",
                forecast="15.0K",
                bullish_scenario="Strong job gains",
                bearish_scenario="Job losses",
                typical_pip_move=40,
            ),
            # US Retail Sales
            EconomicEvent(
                id="us_retail",
                title="US Retail Sales",
                country="US",
                currency="USD",
                datetime_utc=now + timedelta(hours=6),
                impact=EventImpact.MEDIUM,
                category=EventCategory.CONSUMER,
                previous="0.5%",
                forecast="0.3%",
                bullish_scenario="Higher consumer spending",
                bearish_scenario="Consumer pullback",
                typical_pip_move=35,
            ),
            # NZ GDP
            EconomicEvent(
                id="nz_gdp",
                title="New Zealand GDP",
                country="NZ",
                currency="NZD",
                datetime_utc=now + timedelta(days=6),
                impact=EventImpact.MEDIUM,
                category=EventCategory.GDP,
                previous="0.6%",
                forecast="0.4%",
                bullish_scenario="Above forecast",
                bearish_scenario="Below forecast or negative",
                typical_pip_move=50,
            ),
        ]
        
        # Sort by datetime
        self._events.sort(key=lambda e: e.datetime_utc)
    
    def add_event(self, event: EconomicEvent) -> None:
        """Add an event to the calendar."""
        self._events.append(event)
        self._events.sort(key=lambda e: e.datetime_utc)
    
    def get_upcoming_events(
        self,
        hours: int = 24,
        currency: Optional[str] = None,
        impact: Optional[EventImpact] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming events within specified hours.
        
        Args:
            hours: Look-ahead window in hours
            currency: Filter by currency (e.g., "USD")
            impact: Filter by impact level
        
        Returns:
            List of event dictionaries
        """
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours)
        
        events = [e for e in self._events if now <= e.datetime_utc <= cutoff]
        
        if currency:
            events = [e for e in events if e.currency == currency.upper()]
        
        if impact:
            events = [e for e in events if e.impact == impact]
        
        return [e.to_dict() for e in events]
    
    def get_high_impact_events(
        self,
        hours: int = 24,
        currency: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get high-impact events only."""
        return self.get_upcoming_events(hours, currency, EventImpact.HIGH)
    
    def get_events_for_pair(self, pair: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get events affecting a specific currency pair.
        
        Args:
            pair: Currency pair (e.g., "EUR/USD")
            hours: Look-ahead window
        
        Returns:
            Events affecting either currency in the pair
        """
        try:
            base, quote = pair.upper().split("/")
        except ValueError:
            return []
        
        all_events = self.get_upcoming_events(hours)
        return [e for e in all_events if e["currency"] in [base, quote]]
    
    def should_avoid_trading(
        self,
        pair: str,
        minutes_before: int = 15,
        minutes_after: int = 30,
    ) -> Dict[str, Any]:
        """
        Check if trading should be avoided due to imminent news.
        
        Args:
            pair: Currency pair
            minutes_before: Minutes before event to avoid
            minutes_after: Minutes after event to avoid
        
        Returns:
            Dict with recommendation and reasoning
        """
        try:
            base, quote = pair.upper().split("/")
        except ValueError:
            return {"avoid": False, "reason": "Invalid pair format"}
        
        now = datetime.now(timezone.utc)
        
        for event in self._events:
            if event.currency not in [base, quote]:
                continue
            
            if event.impact != EventImpact.HIGH:
                continue
            
            # Check if we're in the danger zone
            time_until = (event.datetime_utc - now).total_seconds() / 60
            
            if -minutes_after <= time_until <= minutes_before:
                return {
                    "avoid": True,
                    "reason": f"High-impact event: {event.title}",
                    "event": event.to_dict(),
                    "minutes_until": round(time_until, 1),
                    "recommendation": "Close positions or widen stops",
                }
        
        return {
            "avoid": False,
            "reason": "No high-impact news imminent",
            "next_high_impact": self._get_next_high_impact(base, quote),
        }
    
    def _get_next_high_impact(self, *currencies: str) -> Optional[Dict[str, Any]]:
        """Get next high-impact event for currencies."""
        now = datetime.now(timezone.utc)
        
        for event in self._events:
            if event.datetime_utc <= now:
                continue
            if event.impact != EventImpact.HIGH:
                continue
            if event.currency in currencies:
                return event.to_dict()
        
        return None
    
    def get_news_trade_setup(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get trading setup for a specific news event.
        
        Args:
            event_id: Event ID
        
        Returns:
            Trading setup with entry/exit recommendations
        """
        event = next((e for e in self._events if e.id == event_id), None)
        if not event:
            return None
        
        if event.impact != EventImpact.HIGH:
            return {
                "event": event.to_dict(),
                "tradeable": False,
                "reason": "Only trade high-impact events",
            }
        
        return {
            "event": event.to_dict(),
            "tradeable": True,
            "strategy": "straddle" if event.typical_pip_move >= 50 else "fade",
            "setup": {
                "entry_timing": "After release, wait for initial spike to settle (30-60 seconds)",
                "target_pips": event.typical_pip_move // 2,
                "stop_loss_pips": event.typical_pip_move // 3,
                "max_spread_pips": 5,
            },
            "scenarios": {
                "bullish": event.bullish_scenario,
                "bearish": event.bearish_scenario,
            },
            "risk_warning": "News trading is high-risk. Slippage and widened spreads common.",
        }
    
    def get_weekly_preview(self) -> Dict[str, Any]:
        """Get weekly economic calendar preview."""
        events = self.get_upcoming_events(hours=168)  # 7 days
        
        # Group by day
        by_day: Dict[str, List[Dict]] = {}
        for event in events:
            day = event["datetime_utc"][:10]  # YYYY-MM-DD
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(event)
        
        # Count by impact
        high_impact = [e for e in events if e["impact"] == "high"]
        
        # Identify busiest day
        busiest_day = max(by_day.items(), key=lambda x: len(x[1]))[0] if by_day else None
        
        return {
            "total_events": len(events),
            "high_impact_count": len(high_impact),
            "high_impact_events": high_impact,
            "by_day": by_day,
            "busiest_day": busiest_day,
            "currencies_affected": list(set(e["currency"] for e in events)),
        }


# Singleton instance
_calendar: Optional[EconomicCalendar] = None


def get_economic_calendar() -> EconomicCalendar:
    """Get or create the economic calendar singleton."""
    global _calendar
    if _calendar is None:
        _calendar = EconomicCalendar()
    return _calendar

