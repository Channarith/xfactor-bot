"""
Sentiment Engine for analyzing news and social media content.
Uses FinBERT for fast analysis and LLM for deep analysis.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, Any
import re

from loguru import logger

from src.config.settings import get_settings


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    sentiment: float  # -1 to 1
    confidence: float  # 0 to 1
    urgency: float  # 0 to 1
    label: str  # positive, negative, neutral
    method: str  # finbert, llm, rule_based
    
    @property
    def is_positive(self) -> bool:
        return self.sentiment > 0.1
    
    @property
    def is_negative(self) -> bool:
        return self.sentiment < -0.1
    
    @property
    def is_actionable(self) -> bool:
        return abs(self.sentiment) >= 0.3 and self.confidence >= 0.6


class SentimentEngine:
    """
    Multi-method sentiment analysis engine.
    
    Methods:
    1. FinBERT - Fast, local, financial-domain specific
    2. LLM (OpenAI) - Deep analysis for high-impact news
    3. Rule-based - Fallback with keyword matching
    """
    
    def __init__(self):
        """Initialize sentiment engine."""
        self.settings = get_settings()
        self._finbert_model = None
        self._finbert_tokenizer = None
        self._openai_client = None
        self._initialized = False
        
        # Keywords for rule-based analysis
        self._positive_keywords = {
            "beat", "beats", "exceeded", "exceeds", "surpass", "surpassed",
            "upgrade", "upgraded", "buy", "bullish", "growth", "profit",
            "surge", "surged", "soar", "soared", "rally", "rallied",
            "breakthrough", "innovation", "approved", "cleared", "wins",
            "strong", "robust", "record", "outperform", "positive",
        }
        
        self._negative_keywords = {
            "miss", "missed", "below", "disappoints", "disappointed",
            "downgrade", "downgraded", "sell", "bearish", "decline",
            "plunge", "plunged", "crash", "crashed", "tumble", "tumbled",
            "lawsuit", "investigation", "recall", "warning", "weak",
            "loss", "losses", "fails", "failed", "cuts", "layoffs",
            "negative", "concern", "worried", "risk", "threat",
        }
        
        self._urgency_keywords = {
            "breaking", "urgent", "just in", "alert", "flash",
            "developing", "exclusive", "confirmed", "announces",
            "immediate", "now", "today", "halt", "suspended",
        }
    
    async def initialize(self) -> bool:
        """Initialize ML models."""
        try:
            # Initialize FinBERT
            await self._init_finbert()
            
            # Initialize OpenAI client
            if self.settings.openai_api_key:
                await self._init_openai()
            
            self._initialized = True
            logger.info("Sentiment engine initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize sentiment engine: {e}")
            return False
    
    async def _init_finbert(self) -> None:
        """Initialize FinBERT model."""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            model_name = "ProsusAI/finbert"
            
            # Load in separate thread to not block
            loop = asyncio.get_event_loop()
            
            self._finbert_tokenizer = await loop.run_in_executor(
                None, AutoTokenizer.from_pretrained, model_name
            )
            self._finbert_model = await loop.run_in_executor(
                None, AutoModelForSequenceClassification.from_pretrained, model_name
            )
            
            # Set to eval mode
            self._finbert_model.eval()
            
            logger.info("FinBERT model loaded")
            
        except ImportError:
            logger.warning("Transformers not installed, FinBERT unavailable")
        except Exception as e:
            logger.warning(f"Failed to load FinBERT: {e}")
    
    async def _init_openai(self) -> None:
        """Initialize OpenAI client."""
        try:
            from openai import AsyncOpenAI
            
            self._openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            logger.info("OpenAI client initialized")
            
        except ImportError:
            logger.warning("OpenAI not installed")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI: {e}")
    
    async def analyze(
        self,
        text: str,
        use_llm: bool = False,
        context: dict = None,
    ) -> SentimentResult:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            use_llm: Whether to use LLM for deep analysis
            context: Optional context (symbol, source, etc.)
            
        Returns:
            SentimentResult
        """
        if not text or len(text.strip()) < 10:
            return SentimentResult(
                sentiment=0.0,
                confidence=0.0,
                urgency=0.0,
                label="neutral",
                method="none",
            )
        
        # Calculate urgency from keywords
        urgency = self._calculate_urgency(text)
        
        # Try FinBERT first
        if self._finbert_model is not None:
            result = await self._analyze_finbert(text)
            result.urgency = urgency
            
            # Use LLM for high-urgency or uncertain results
            if use_llm and self._openai_client and (urgency > 0.7 or result.confidence < 0.7):
                llm_result = await self._analyze_llm(text, context)
                if llm_result:
                    # Combine results
                    result = self._combine_results(result, llm_result)
            
            return result
        
        # Try LLM
        if use_llm and self._openai_client:
            result = await self._analyze_llm(text, context)
            if result:
                result.urgency = urgency
                return result
        
        # Fallback to rule-based
        return self._analyze_rules(text, urgency)
    
    async def _analyze_finbert(self, text: str) -> SentimentResult:
        """Analyze with FinBERT."""
        try:
            import torch
            
            # Tokenize
            inputs = self._finbert_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            
            # Run inference
            loop = asyncio.get_event_loop()
            with torch.no_grad():
                outputs = await loop.run_in_executor(
                    None,
                    lambda: self._finbert_model(**inputs)
                )
            
            # Get probabilities
            probs = torch.softmax(outputs.logits, dim=1)[0]
            
            # FinBERT labels: positive, negative, neutral
            positive = probs[0].item()
            negative = probs[1].item()
            neutral = probs[2].item()
            
            # Calculate sentiment score
            sentiment = positive - negative
            confidence = max(positive, negative, neutral)
            
            if positive > negative and positive > neutral:
                label = "positive"
            elif negative > positive and negative > neutral:
                label = "negative"
            else:
                label = "neutral"
            
            return SentimentResult(
                sentiment=sentiment,
                confidence=confidence,
                urgency=0.0,  # Will be set by caller
                label=label,
                method="finbert",
            )
            
        except Exception as e:
            logger.error(f"FinBERT analysis failed: {e}")
            return SentimentResult(0.0, 0.0, 0.0, "neutral", "error")
    
    async def _analyze_llm(
        self,
        text: str,
        context: dict = None,
    ) -> Optional[SentimentResult]:
        """Analyze with LLM (OpenAI)."""
        try:
            prompt = f"""Analyze the following financial news/text for trading signals.

Text: "{text}"

{f"Context: {context}" if context else ""}

Respond with a JSON object containing:
- sentiment: float from -1.0 (very bearish) to 1.0 (very bullish)
- confidence: float from 0.0 to 1.0
- urgency: float from 0.0 to 1.0 (how quickly should a trader act)
- reasoning: brief explanation

Respond ONLY with the JSON object, no other text."""

            response = await self._openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            import json
            # Extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                
                sentiment = float(data.get("sentiment", 0))
                confidence = float(data.get("confidence", 0.7))
                urgency = float(data.get("urgency", 0.5))
                
                label = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"
                
                return SentimentResult(
                    sentiment=sentiment,
                    confidence=confidence,
                    urgency=urgency,
                    label=label,
                    method="llm",
                )
            
            return None
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None
    
    def _analyze_rules(self, text: str, urgency: float) -> SentimentResult:
        """Rule-based sentiment analysis fallback."""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        positive_count = len(words & self._positive_keywords)
        negative_count = len(words & self._negative_keywords)
        
        total = positive_count + negative_count
        if total == 0:
            return SentimentResult(
                sentiment=0.0,
                confidence=0.3,
                urgency=urgency,
                label="neutral",
                method="rule_based",
            )
        
        sentiment = (positive_count - negative_count) / max(total, 1)
        sentiment = max(-1.0, min(1.0, sentiment))
        
        confidence = min(0.7, total * 0.1)  # More keywords = more confident
        
        label = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"
        
        return SentimentResult(
            sentiment=sentiment,
            confidence=confidence,
            urgency=urgency,
            label=label,
            method="rule_based",
        )
    
    def _calculate_urgency(self, text: str) -> float:
        """Calculate urgency score from text."""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        urgency_count = len(words & self._urgency_keywords)
        
        # Check for specific patterns
        if "breaking" in text_lower or "just in" in text_lower:
            return min(1.0, 0.8 + urgency_count * 0.1)
        
        return min(1.0, urgency_count * 0.2)
    
    def _combine_results(
        self,
        finbert: SentimentResult,
        llm: SentimentResult,
    ) -> SentimentResult:
        """Combine FinBERT and LLM results."""
        # Weight LLM higher if it has higher confidence
        finbert_weight = 0.4
        llm_weight = 0.6
        
        combined_sentiment = (
            finbert.sentiment * finbert_weight +
            llm.sentiment * llm_weight
        )
        
        combined_confidence = max(finbert.confidence, llm.confidence)
        combined_urgency = max(finbert.urgency, llm.urgency)
        
        label = "positive" if combined_sentiment > 0.1 else "negative" if combined_sentiment < -0.1 else "neutral"
        
        return SentimentResult(
            sentiment=combined_sentiment,
            confidence=combined_confidence,
            urgency=combined_urgency,
            label=label,
            method="finbert+llm",
        )
    
    async def analyze_batch(
        self,
        texts: list[str],
        use_llm: bool = False,
    ) -> list[SentimentResult]:
        """Analyze multiple texts."""
        tasks = [self.analyze(text, use_llm) for text in texts]
        return await asyncio.gather(*tasks)

