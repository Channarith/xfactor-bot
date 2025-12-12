"""
News Sentiment Trading Strategy.

Generates trading signals based on news sentiment analysis.
"""

from typing import Optional, Any
from datetime import datetime, timedelta

import pandas as pd
from loguru import logger

from src.strategies.base_strategy import BaseStrategy, Signal, SignalType
from src.config.settings import get_settings


class NewsSentimentStrategy(BaseStrategy):
    """
    News sentiment strategy that trades based on breaking news and sentiment.
    
    Key concepts:
    - React to breaking news with high urgency
    - Combine sentiment from multiple sources
    - Weight by source credibility and recency
    """
    
    def __init__(self, weight: float = 0.4):
        """Initialize news sentiment strategy."""
        super().__init__(name="NewsSentiment", weight=weight)
        
        settings = get_settings()
        self._parameters = {
            # Sentiment thresholds
            "min_sentiment": settings.news_sentiment_threshold,
            "strong_sentiment": 0.7,
            "min_confidence": settings.news_min_confidence,
            "min_urgency": settings.news_min_urgency,
            
            # Source weights
            "breaking_news_weight": 1.5,
            "financial_news_weight": 1.2,
            "social_media_weight": 0.8,
            "local_file_weight": 1.0,
            
            # Time decay
            "news_decay_hours": 4,  # News signal decays over 4 hours
            "max_news_age_hours": 24,  # Ignore news older than 24 hours
            
            # Aggregation
            "min_sources": 1,  # Minimum sources for signal
            "source_agreement_bonus": 0.1,  # Bonus per agreeing source
            
            # LLM usage
            "use_llm": settings.llm_analysis_enabled,
            "llm_weight": 1.3,  # LLM analysis weighted higher
        }
        
        # Store recent news for aggregation
        self._recent_news: dict[str, list[dict]] = {}
    
    def get_parameters(self) -> dict[str, Any]:
        """Get current parameters."""
        return self._parameters.copy()
    
    def add_news(
        self,
        symbol: str,
        sentiment: float,
        urgency: float,
        confidence: float,
        source: str,
        headline: str,
        is_breaking: bool = False,
        llm_analyzed: bool = False,
        timestamp: datetime = None,
    ) -> None:
        """
        Add a news item for a symbol.
        
        Args:
            symbol: Stock symbol
            sentiment: Sentiment score (-1 to 1)
            urgency: Urgency score (0 to 1)
            confidence: Confidence score (0 to 1)
            source: News source name
            headline: News headline
            is_breaking: Whether this is breaking news
            llm_analyzed: Whether LLM analysis was used
            timestamp: News timestamp
        """
        if symbol not in self._recent_news:
            self._recent_news[symbol] = []
        
        news_item = {
            "sentiment": sentiment,
            "urgency": urgency,
            "confidence": confidence,
            "source": source,
            "headline": headline,
            "is_breaking": is_breaking,
            "llm_analyzed": llm_analyzed,
            "timestamp": timestamp or datetime.utcnow(),
        }
        
        self._recent_news[symbol].append(news_item)
        
        # Keep only recent news
        max_age = timedelta(hours=self._parameters["max_news_age_hours"])
        cutoff = datetime.utcnow() - max_age
        self._recent_news[symbol] = [
            n for n in self._recent_news[symbol]
            if n["timestamp"] > cutoff
        ]
        
        logger.debug(f"Added news for {symbol}: {headline[:50]}...")
    
    def clear_news(self, symbol: str = None) -> None:
        """Clear news for a symbol or all symbols."""
        if symbol:
            self._recent_news.pop(symbol, None)
        else:
            self._recent_news.clear()
    
    async def analyze(
        self,
        symbol: str,
        data: pd.DataFrame = None,
        **kwargs,
    ) -> Optional[Signal]:
        """
        Analyze news sentiment for a symbol.
        
        Args:
            symbol: Stock symbol
            data: Optional OHLCV data (for price context)
            
        Returns:
            Signal or None
        """
        if not self.is_enabled:
            return None
        
        news_items = self._recent_news.get(symbol, [])
        
        if not news_items:
            return None
        
        try:
            # Aggregate news sentiment
            aggregated = self._aggregate_news(news_items)
            
            if aggregated["source_count"] < self._parameters["min_sources"]:
                return None
            
            # Generate signal
            signal_type, strength, confidence = self._generate_signal(aggregated)
            
            if signal_type == SignalType.HOLD:
                return None
            
            # Get current price if data available
            entry_price = None
            stop_loss = None
            take_profit = None
            
            if data is not None and not data.empty:
                entry_price = data["close"].iloc[-1]
                atr = self._calculate_simple_atr(data)
                
                if signal_type.is_bullish:
                    stop_loss = entry_price - (2 * atr)
                    take_profit = entry_price + (3 * atr)
                else:
                    stop_loss = entry_price + (2 * atr)
                    take_profit = entry_price - (3 * atr)
            
            signal = Signal(
                symbol=symbol,
                signal_type=signal_type,
                strategy=self.name,
                strength=strength,
                confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "aggregated_sentiment": aggregated["sentiment"],
                    "aggregated_urgency": aggregated["urgency"],
                    "source_count": aggregated["source_count"],
                    "has_breaking_news": aggregated["has_breaking"],
                    "recent_headlines": [n["headline"] for n in news_items[:3]],
                }
            )
            
            self.on_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing news for {symbol}: {e}")
            return None
    
    def _aggregate_news(self, news_items: list[dict]) -> dict[str, Any]:
        """Aggregate multiple news items into a single sentiment score."""
        now = datetime.utcnow()
        decay_hours = self._parameters["news_decay_hours"]
        
        weighted_sentiment = 0.0
        weighted_urgency = 0.0
        total_weight = 0.0
        sources = set()
        has_breaking = False
        
        for item in news_items:
            # Calculate time decay
            age_hours = (now - item["timestamp"]).total_seconds() / 3600
            if age_hours > self._parameters["max_news_age_hours"]:
                continue
            
            time_decay = max(0, 1 - (age_hours / decay_hours))
            
            # Calculate source weight
            source = item["source"].lower()
            if "breaking" in source or item["is_breaking"]:
                source_weight = self._parameters["breaking_news_weight"]
                has_breaking = True
            elif any(s in source for s in ["bloomberg", "reuters", "wsj", "ft"]):
                source_weight = self._parameters["financial_news_weight"]
            elif any(s in source for s in ["reddit", "twitter", "stocktwits"]):
                source_weight = self._parameters["social_media_weight"]
            else:
                source_weight = self._parameters["local_file_weight"]
            
            # LLM bonus
            if item["llm_analyzed"]:
                source_weight *= self._parameters["llm_weight"]
            
            # Combined weight
            weight = source_weight * time_decay * item["confidence"]
            
            weighted_sentiment += item["sentiment"] * weight
            weighted_urgency += item["urgency"] * weight
            total_weight += weight
            sources.add(item["source"])
        
        if total_weight == 0:
            return {
                "sentiment": 0,
                "urgency": 0,
                "confidence": 0,
                "source_count": 0,
                "has_breaking": False,
            }
        
        avg_sentiment = weighted_sentiment / total_weight
        avg_urgency = weighted_urgency / total_weight
        
        # Source agreement bonus
        source_count = len(sources)
        agreement_bonus = min(0.3, (source_count - 1) * self._parameters["source_agreement_bonus"])
        
        return {
            "sentiment": avg_sentiment,
            "urgency": avg_urgency,
            "confidence": min(1.0, 0.5 + agreement_bonus + (0.2 if has_breaking else 0)),
            "source_count": source_count,
            "has_breaking": has_breaking,
        }
    
    def _generate_signal(
        self,
        aggregated: dict[str, Any],
    ) -> tuple[SignalType, float, float]:
        """Generate signal from aggregated news."""
        
        sentiment = aggregated["sentiment"]
        urgency = aggregated["urgency"]
        confidence = aggregated["confidence"]
        
        min_sent = self._parameters["min_sentiment"]
        strong_sent = self._parameters["strong_sentiment"]
        min_urg = self._parameters["min_urgency"]
        min_conf = self._parameters["min_confidence"]
        
        # Check minimum thresholds
        if abs(sentiment) < min_sent:
            return SignalType.HOLD, 0, 0
        
        if confidence < min_conf:
            return SignalType.HOLD, 0, 0
        
        # Determine signal type
        if sentiment >= strong_sent and urgency >= min_urg and confidence >= 0.7:
            signal_type = SignalType.STRONG_BUY
        elif sentiment >= min_sent:
            signal_type = SignalType.BUY
        elif sentiment <= -strong_sent and urgency >= min_urg and confidence >= 0.7:
            signal_type = SignalType.STRONG_SELL
        elif sentiment <= -min_sent:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD
        
        strength = abs(sentiment)
        
        # Boost for breaking news
        if aggregated["has_breaking"]:
            strength = min(1.0, strength * 1.2)
            confidence = min(1.0, confidence * 1.1)
        
        return signal_type, strength, confidence
    
    def _calculate_simple_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Simple ATR calculation."""
        if len(data) < period:
            return data["close"].iloc[-1] * 0.02
        
        high = data["high"]
        low = data["low"]
        close = data["close"]
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr if pd.notna(atr) else data["close"].iloc[-1] * 0.02
    
    async def process_news_batch(
        self,
        news_batch: list[dict],
    ) -> dict[str, Signal]:
        """
        Process a batch of news items and generate signals.
        
        Args:
            news_batch: List of news items with symbol, sentiment, etc.
            
        Returns:
            Dictionary of symbol -> Signal
        """
        # Add all news items
        for item in news_batch:
            self.add_news(
                symbol=item["symbol"],
                sentiment=item["sentiment"],
                urgency=item.get("urgency", 0.5),
                confidence=item.get("confidence", 0.7),
                source=item.get("source", "unknown"),
                headline=item.get("headline", ""),
                is_breaking=item.get("is_breaking", False),
                llm_analyzed=item.get("llm_analyzed", False),
            )
        
        # Generate signals for all affected symbols
        signals = {}
        affected_symbols = set(item["symbol"] for item in news_batch)
        
        for symbol in affected_symbols:
            signal = await self.analyze(symbol)
            if signal:
                signals[symbol] = signal
        
        return signals

