"""
Currency Strength Meter

Analyzes the relative strength of major currencies by comparing
their performance across multiple pairs.

Features:
- Real-time currency strength scoring (0-100)
- Currency correlation matrix
- Strength-based pair selection
- Divergence detection for trade opportunities
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics

from loguru import logger


# Major currencies for strength analysis
MAJOR_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]

# Currency pair relationships for strength calculation
CURRENCY_PAIRS = {
    "USD": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD"],
    "EUR": ["EUR/USD", "EUR/GBP", "EUR/JPY", "EUR/CHF", "EUR/AUD", "EUR/CAD", "EUR/NZD"],
    "GBP": ["GBP/USD", "EUR/GBP", "GBP/JPY", "GBP/CHF", "GBP/AUD", "GBP/CAD", "GBP/NZD"],
    "JPY": ["USD/JPY", "EUR/JPY", "GBP/JPY", "CHF/JPY", "AUD/JPY", "CAD/JPY", "NZD/JPY"],
    "CHF": ["USD/CHF", "EUR/CHF", "GBP/CHF", "CHF/JPY", "AUD/CHF", "CAD/CHF", "NZD/CHF"],
    "AUD": ["AUD/USD", "EUR/AUD", "GBP/AUD", "AUD/JPY", "AUD/CHF", "AUD/CAD", "AUD/NZD"],
    "CAD": ["USD/CAD", "EUR/CAD", "GBP/CAD", "CAD/JPY", "CAD/CHF", "AUD/CAD", "NZD/CAD"],
    "NZD": ["NZD/USD", "EUR/NZD", "GBP/NZD", "NZD/JPY", "NZD/CHF", "NZD/CAD", "AUD/NZD"],
}


class StrengthTrend(Enum):
    """Currency strength trend."""
    VERY_STRONG = "very_strong"
    STRONG = "strong"
    NEUTRAL = "neutral"
    WEAK = "weak"
    VERY_WEAK = "very_weak"


@dataclass
class CurrencyStrength:
    """Currency strength analysis result."""
    currency: str
    strength: float              # 0-100 scale
    rank: int                    # 1 = strongest
    trend: StrengthTrend
    change_1h: float = 0.0       # Change in last hour
    change_4h: float = 0.0       # Change in last 4 hours
    change_24h: float = 0.0      # Change in last 24 hours
    contributing_pairs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "currency": self.currency,
            "strength": round(self.strength, 2),
            "rank": self.rank,
            "trend": self.trend.value,
            "change_1h": round(self.change_1h, 2),
            "change_4h": round(self.change_4h, 2),
            "change_24h": round(self.change_24h, 2),
            "contributing_pairs": self.contributing_pairs,
        }


@dataclass
class PairCorrelation:
    """Correlation between two pairs."""
    pair1: str
    pair2: str
    correlation: float           # -1 to +1
    period: str                  # e.g., "1h", "4h", "1d"
    relationship: str            # "positive", "negative", "neutral"


class CurrencyStrengthMeter:
    """
    Calculates and tracks currency strength across major currencies.
    
    Usage:
        meter = CurrencyStrengthMeter()
        meter.update_price("EUR/USD", 1.0850, 1.0875)  # Update with price change
        strengths = meter.get_all_strengths()
        best_pair = meter.get_best_pair()  # Returns strongest vs weakest
    """
    
    def __init__(self):
        # Store price changes for each pair
        self._price_changes: Dict[str, List[float]] = {}
        
        # Calculated strengths
        self._strengths: Dict[str, CurrencyStrength] = {}
        
        # Historical strength for trend
        self._strength_history: Dict[str, List[Tuple[datetime, float]]] = {
            currency: [] for currency in MAJOR_CURRENCIES
        }
        
        # Correlation cache
        self._correlations: Dict[str, float] = {}
        
        self._last_update: Optional[datetime] = None
    
    def update_price(
        self,
        pair: str,
        previous_price: float,
        current_price: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Update strength meter with new price data.
        
        Args:
            pair: Currency pair (e.g., "EUR/USD")
            previous_price: Previous price
            current_price: Current price
            timestamp: Price timestamp
        """
        if previous_price == 0:
            return
        
        # Calculate percentage change
        pct_change = ((current_price - previous_price) / previous_price) * 100
        
        # Store price change
        if pair not in self._price_changes:
            self._price_changes[pair] = []
        self._price_changes[pair].append(pct_change)
        
        # Keep only recent changes (last 100)
        if len(self._price_changes[pair]) > 100:
            self._price_changes[pair] = self._price_changes[pair][-100:]
        
        self._last_update = timestamp or datetime.now()
    
    def calculate_strengths(self) -> Dict[str, CurrencyStrength]:
        """
        Calculate strength for all major currencies.
        
        Returns:
            Dict of currency -> CurrencyStrength
        """
        raw_strengths: Dict[str, float] = {}
        
        for currency in MAJOR_CURRENCIES:
            pairs = CURRENCY_PAIRS.get(currency, [])
            strength_sum = 0.0
            valid_pairs = 0
            contributing = []
            
            for pair in pairs:
                if pair not in self._price_changes or not self._price_changes[pair]:
                    continue
                
                # Get average recent change
                changes = self._price_changes[pair][-10:]  # Last 10 updates
                avg_change = statistics.mean(changes) if changes else 0
                
                # Determine if currency benefits from this change
                # If currency is base (first), positive change = strength
                # If currency is quote (second), negative change = strength
                base, quote = pair.split("/")
                
                if currency == base:
                    strength_sum += avg_change
                    contributing.append(pair)
                elif currency == quote:
                    strength_sum -= avg_change
                    contributing.append(pair)
                
                valid_pairs += 1
            
            # Average strength
            raw_strengths[currency] = strength_sum / max(valid_pairs, 1)
        
        # Normalize to 0-100 scale
        if raw_strengths:
            min_str = min(raw_strengths.values())
            max_str = max(raw_strengths.values())
            range_str = max_str - min_str if max_str != min_str else 1
            
            normalized = {
                currency: ((strength - min_str) / range_str) * 100
                for currency, strength in raw_strengths.items()
            }
        else:
            normalized = {currency: 50.0 for currency in MAJOR_CURRENCIES}
        
        # Sort by strength for ranking
        sorted_currencies = sorted(normalized.items(), key=lambda x: x[1], reverse=True)
        
        # Create CurrencyStrength objects
        for rank, (currency, strength) in enumerate(sorted_currencies, 1):
            # Determine trend
            if strength >= 80:
                trend = StrengthTrend.VERY_STRONG
            elif strength >= 60:
                trend = StrengthTrend.STRONG
            elif strength >= 40:
                trend = StrengthTrend.NEUTRAL
            elif strength >= 20:
                trend = StrengthTrend.WEAK
            else:
                trend = StrengthTrend.VERY_WEAK
            
            # Calculate historical changes
            history = self._strength_history.get(currency, [])
            now = datetime.now()
            
            change_1h = 0.0
            change_4h = 0.0
            change_24h = 0.0
            
            for ts, hist_strength in reversed(history):
                age = (now - ts).total_seconds() / 3600  # Hours
                if age <= 1:
                    change_1h = strength - hist_strength
                elif age <= 4:
                    change_4h = strength - hist_strength
                elif age <= 24:
                    change_24h = strength - hist_strength
                    break
            
            self._strengths[currency] = CurrencyStrength(
                currency=currency,
                strength=strength,
                rank=rank,
                trend=trend,
                change_1h=change_1h,
                change_4h=change_4h,
                change_24h=change_24h,
                contributing_pairs=CURRENCY_PAIRS.get(currency, [])[:5],
            )
            
            # Update history
            self._strength_history[currency].append((now, strength))
            # Keep last 24 hours
            cutoff = now - timedelta(hours=24)
            self._strength_history[currency] = [
                (ts, s) for ts, s in self._strength_history[currency]
                if ts > cutoff
            ]
        
        return self._strengths
    
    def get_all_strengths(self) -> List[Dict[str, Any]]:
        """Get all currency strengths sorted by strength."""
        if not self._strengths:
            self.calculate_strengths()
        
        return sorted(
            [s.to_dict() for s in self._strengths.values()],
            key=lambda x: x["strength"],
            reverse=True,
        )
    
    def get_strength(self, currency: str) -> Optional[CurrencyStrength]:
        """Get strength for a specific currency."""
        if not self._strengths:
            self.calculate_strengths()
        return self._strengths.get(currency.upper())
    
    def get_best_pair(self) -> Dict[str, Any]:
        """
        Get the best trading pair (strongest vs weakest currency).
        
        Returns:
            Dict with pair recommendation and analysis
        """
        if not self._strengths:
            self.calculate_strengths()
        
        sorted_strengths = sorted(
            self._strengths.values(),
            key=lambda x: x.strength,
            reverse=True,
        )
        
        if len(sorted_strengths) < 2:
            return {"error": "Not enough data"}
        
        strongest = sorted_strengths[0]
        weakest = sorted_strengths[-1]
        
        # Find the pair between these currencies
        pair = f"{strongest.currency}/{weakest.currency}"
        # Check if this pair exists or reverse it
        all_pairs = []
        for pairs in CURRENCY_PAIRS.values():
            all_pairs.extend(pairs)
        
        if pair not in all_pairs:
            pair = f"{weakest.currency}/{strongest.currency}"
            direction = "SELL"
        else:
            direction = "BUY"
        
        strength_diff = strongest.strength - weakest.strength
        
        return {
            "recommended_pair": pair,
            "direction": direction,
            "strongest_currency": strongest.currency,
            "weakest_currency": weakest.currency,
            "strength_differential": round(strength_diff, 2),
            "confidence": "high" if strength_diff > 40 else "medium" if strength_diff > 20 else "low",
            "analysis": f"{direction} {pair}: {strongest.currency} is {strongest.trend.value}, {weakest.currency} is {weakest.trend.value}",
        }
    
    def get_divergences(self) -> List[Dict[str, Any]]:
        """
        Find diverging currency pairs (strength changing in opposite directions).
        
        Returns:
            List of divergence opportunities
        """
        if not self._strengths:
            self.calculate_strengths()
        
        divergences = []
        
        for currency, strength in self._strengths.items():
            # Look for currencies with large 4h change opposite to current trend
            if (strength.trend in [StrengthTrend.STRONG, StrengthTrend.VERY_STRONG] 
                and strength.change_4h < -5):
                divergences.append({
                    "currency": currency,
                    "type": "bearish_divergence",
                    "current_strength": strength.strength,
                    "change_4h": strength.change_4h,
                    "description": f"{currency} showing strength but momentum fading",
                })
            elif (strength.trend in [StrengthTrend.WEAK, StrengthTrend.VERY_WEAK]
                  and strength.change_4h > 5):
                divergences.append({
                    "currency": currency,
                    "type": "bullish_divergence",
                    "current_strength": strength.strength,
                    "change_4h": strength.change_4h,
                    "description": f"{currency} showing weakness but momentum building",
                })
        
        return divergences
    
    def calculate_correlation(
        self,
        pair1: str,
        pair2: str,
        period: int = 20,
    ) -> Optional[PairCorrelation]:
        """
        Calculate correlation between two pairs.
        
        Args:
            pair1: First currency pair
            pair2: Second currency pair
            period: Number of data points to use
        
        Returns:
            PairCorrelation object
        """
        changes1 = self._price_changes.get(pair1, [])[-period:]
        changes2 = self._price_changes.get(pair2, [])[-period:]
        
        if len(changes1) < 5 or len(changes2) < 5:
            return None
        
        # Align lengths
        min_len = min(len(changes1), len(changes2))
        changes1 = changes1[-min_len:]
        changes2 = changes2[-min_len:]
        
        # Calculate Pearson correlation
        mean1 = statistics.mean(changes1)
        mean2 = statistics.mean(changes2)
        
        numerator = sum((a - mean1) * (b - mean2) for a, b in zip(changes1, changes2))
        
        std1 = statistics.stdev(changes1) if len(changes1) > 1 else 1
        std2 = statistics.stdev(changes2) if len(changes2) > 1 else 1
        
        denominator = std1 * std2 * (min_len - 1)
        
        correlation = numerator / denominator if denominator != 0 else 0
        
        # Classify relationship
        if correlation > 0.7:
            relationship = "strong_positive"
        elif correlation > 0.3:
            relationship = "positive"
        elif correlation < -0.7:
            relationship = "strong_negative"
        elif correlation < -0.3:
            relationship = "negative"
        else:
            relationship = "neutral"
        
        return PairCorrelation(
            pair1=pair1,
            pair2=pair2,
            correlation=round(correlation, 3),
            period=f"{min_len} bars",
            relationship=relationship,
        )
    
    def get_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Get full correlation matrix for major pairs.
        
        Returns:
            Nested dict of pair -> pair -> correlation
        """
        major_pairs = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD"]
        matrix = {}
        
        for pair1 in major_pairs:
            matrix[pair1] = {}
            for pair2 in major_pairs:
                if pair1 == pair2:
                    matrix[pair1][pair2] = 1.0
                else:
                    corr = self.calculate_correlation(pair1, pair2)
                    matrix[pair1][pair2] = corr.correlation if corr else 0.0
        
        return matrix


# Singleton instance
_strength_meter: Optional[CurrencyStrengthMeter] = None


def get_currency_strength() -> CurrencyStrengthMeter:
    """Get or create the currency strength meter singleton."""
    global _strength_meter
    if _strength_meter is None:
        _strength_meter = CurrencyStrengthMeter()
    return _strength_meter

