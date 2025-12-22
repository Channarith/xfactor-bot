"""
AI Trading Assistant.
Provides natural language interface for querying system performance,
analyzing data sources, and getting optimization recommendations.

Supports multiple LLM providers (priority order):
1. Anthropic (Claude) - Default, best for trading analysis
2. Ollama (Local LLMs) - Fallback, bundled with XFactor
3. OpenAI (GPT-4) - Alternative cloud option
"""

import json
import subprocess
import sys
import os
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel

from src.ai.context_builder import ContextBuilder, SystemContext, get_context_builder
from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

LLMProvider = Literal["openai", "ollama", "anthropic"]


async def ensure_ollama_running() -> bool:
    """
    Ensure Ollama is running. If bundled and not running, start it.
    Returns True if Ollama is available.
    """
    settings = get_settings()
    
    # Check if already running
    try:
        import httpx
        # Use resolved host for Docker compatibility
        ollama_host = settings.ollama_host_resolved
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_host}/api/version", timeout=2.0)
            if response.status_code == 200:
                logger.info(f"Ollama is already running at {ollama_host}")
                return True
    except Exception:
        pass
    
    # Try to start Ollama if auto_start is enabled
    if settings.ollama_auto_start:
        logger.info("Ollama not running, attempting to start...")
        try:
            # Check for bundled Ollama binary
            bundled_paths = [
                # macOS app bundle
                os.path.join(os.path.dirname(sys.executable), "..", "Resources", "ollama"),
                os.path.join(os.path.dirname(sys.executable), "ollama"),
                # Linux/Windows
                os.path.join(os.path.dirname(sys.executable), "ollama"),
                # Development
                "/usr/local/bin/ollama",
                "ollama",  # System PATH
            ]
            
            ollama_binary = None
            for path in bundled_paths:
                if os.path.exists(path):
                    ollama_binary = path
                    break
            
            if ollama_binary is None:
                # Try system ollama
                ollama_binary = "ollama"
            
            # Start Ollama serve in background
            subprocess.Popen(
                [ollama_binary, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Wait for startup
            import asyncio
            ollama_host = settings.ollama_host_resolved
            for _ in range(10):  # Wait up to 5 seconds
                await asyncio.sleep(0.5)
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{ollama_host}/api/version", timeout=2.0)
                        if response.status_code == 200:
                            logger.info(f"Ollama started successfully at {ollama_host}")
                            return True
                except Exception:
                    pass
            
            logger.warning("Could not start Ollama")
            return False
            
        except Exception as e:
            logger.error(f"Error starting Ollama: {e}")
            return False
    
    return False


class ChatMessage(BaseModel):
    """A chat message in the conversation."""
    
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = datetime.utcnow()


class ConversationHistory(BaseModel):
    """Conversation history for context."""
    
    messages: list[ChatMessage] = []
    max_messages: int = 20
    
    def add_message(self, role: str, content: str):
        """Add a message to history."""
        self.messages.append(ChatMessage(role=role, content=content))
        # Keep only recent messages
        if len(self.messages) > self.max_messages:
            # Always keep system message
            system_msgs = [m for m in self.messages if m.role == "system"]
            other_msgs = [m for m in self.messages if m.role != "system"]
            self.messages = system_msgs + other_msgs[-(self.max_messages - len(system_msgs)):]
    
    def get_messages(self) -> list[dict[str, str]]:
        """Convert to message format."""
        return [{"role": m.role, "content": m.content} for m in self.messages]
    
    def clear(self):
        """Clear conversation history."""
        self.messages = []


class AIAssistant:
    """
    AI-powered trading assistant for natural language queries.
    Supports multiple LLM providers: OpenAI, Ollama, Anthropic.
    """
    
    SYSTEM_PROMPT = """You are an expert trading assistant for an automated trading bot system. 
Your role is to help users understand their trading performance, analyze data sources, 
and provide actionable recommendations for optimization.

You have access to real-time system context including:
- Account information and balances
- Portfolio positions and P&L
- Strategy performance metrics
- Data source status and health
- Bot status and activity
- Risk metrics and circuit breakers

When answering questions:
1. Be specific and data-driven - reference actual numbers from the context
2. Provide actionable recommendations when appropriate
3. Explain the reasoning behind your suggestions
4. Warn about potential risks when relevant
5. Be concise but thorough

For optimization questions, consider:
- Strategy weight adjustments based on performance
- Position sizing improvements
- Risk parameter tuning
- Data source quality and relevance
- Market condition adaptations

Always format numbers appropriately (e.g., $1,234.56 for currency, 12.5% for percentages).
Use bullet points and clear structure for complex responses.

Current system context will be provided with each query."""

    EXAMPLE_QUESTIONS = [
        "How is my portfolio performing today?",
        "Which strategy is generating the best returns?",
        "What data sources are providing the most signals?",
        "Should I adjust my position sizes?",
        "What's causing the recent drawdown?",
        "How can I improve my win rate?",
        "Are there any risks I should be aware of?",
        "Which stocks are contributing most to my P&L?",
        "How are the news sentiment signals performing?",
        "What optimizations would you recommend?",
    ]
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.settings = get_settings()
        self.context_builder = get_context_builder()
        self.conversations: dict[str, ConversationHistory] = {}
        
        # Determine LLM provider
        self.provider = provider or self.settings.llm_provider
        
        # Client instances (lazy initialized)
        self._openai_client = None
        self._ollama_client = None
        self._anthropic_client = None
        
        logger.info(f"AI Assistant initialized with provider: {self.provider}")
    
    def set_provider(self, provider: LLMProvider):
        """Switch LLM provider at runtime."""
        self.provider = provider
        logger.info(f"Switched LLM provider to: {provider}")
    
    @property
    def openai_client(self):
        """Get or create OpenAI client."""
        if self._openai_client is None:
            from openai import AsyncOpenAI
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
            
            kwargs = {"api_key": self.settings.openai_api_key}
            if self.settings.openai_base_url:
                kwargs["base_url"] = self.settings.openai_base_url
            
            self._openai_client = AsyncOpenAI(**kwargs)
        return self._openai_client
    
    @property
    def ollama_client(self):
        """Get or create Ollama client."""
        if self._ollama_client is None:
            from src.ai.ollama_client import get_ollama_client
            self._ollama_client = get_ollama_client()
        return self._ollama_client
    
    @property
    def anthropic_client(self):
        """Get or create Anthropic client."""
        if self._anthropic_client is None:
            import anthropic
            if not self.settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env")
            self._anthropic_client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        return self._anthropic_client
    
    def get_or_create_conversation(self, session_id: str) -> ConversationHistory:
        """Get or create conversation history for a session."""
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationHistory()
        return self.conversations[session_id]
    
    async def _call_openai(self, messages: list[dict[str, str]]) -> str:
        """Call OpenAI API."""
        response = await self.openai_client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
        )
        return response.choices[0].message.content
    
    async def _call_ollama(self, messages: list[dict[str, str]]) -> str:
        """Call Ollama API."""
        # Check if Ollama is available
        if not await self.ollama_client.is_available():
            raise ConnectionError(
                f"Ollama server not available at {self.settings.ollama_host_resolved}. "
                "Please ensure Ollama is running: 'ollama serve'"
            )
        
        return await self.ollama_client.chat(
            messages=messages,
            model=self.settings.ollama_model,
            temperature=0.7,
            max_tokens=1500,
        )
    
    async def _call_anthropic(self, messages: list[dict[str, str]]) -> str:
        """Call Anthropic API."""
        # Anthropic uses a different message format
        system_content = ""
        filtered_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                filtered_messages.append(msg)
        
        response = await self.anthropic_client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=1500,
            system=system_content,
            messages=filtered_messages,
        )
        return response.content[0].text
    
    async def chat(
        self,
        query: str,
        session_id: str = "default",
        include_context: bool = True,
        provider: Optional[LLMProvider] = None,
    ) -> str:
        """
        Process a chat query and return AI response.
        
        Priority order with fallback:
        1. Use specified provider (or default: Anthropic Claude)
        2. If primary fails and fallback enabled, try Ollama
        3. Return error message if all fail
        
        Args:
            query: The user's question
            session_id: Session identifier for conversation history
            include_context: Whether to include system context
            provider: Override the default LLM provider for this request
            
        Returns:
            AI assistant's response
        """
        current_provider = provider or self.provider
        
        try:
            conversation = self.get_or_create_conversation(session_id)
            
            # Build context if needed
            context_str = ""
            if include_context:
                context = await self.context_builder.build_context()
                context_str = self.context_builder.get_context_summary(context)
            
            # Prepare messages
            messages = []
            
            # System prompt with context
            system_content = self.SYSTEM_PROMPT
            if context_str:
                system_content += f"\n\n--- CURRENT SYSTEM STATE ---\n{context_str}"
            
            messages.append({"role": "system", "content": system_content})
            
            # Add conversation history (excluding old system messages)
            for msg in conversation.messages:
                if msg.role != "system":
                    messages.append({"role": msg.role, "content": msg.content})
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            # Try primary provider, fall back to Ollama if enabled
            assistant_message = None
            used_provider = current_provider
            
            try:
                logger.info(f"Calling {current_provider} for chat (session: {session_id})")
                
                if current_provider == "openai":
                    assistant_message = await self._call_openai(messages)
                elif current_provider == "ollama":
                    assistant_message = await self._call_ollama(messages)
                elif current_provider == "anthropic":
                    assistant_message = await self._call_anthropic(messages)
                else:
                    raise ValueError(f"Unknown LLM provider: {current_provider}")
                    
            except Exception as primary_error:
                logger.warning(f"Primary provider {current_provider} failed: {primary_error}")
                
                # Try fallback to Ollama if enabled and not already using Ollama
                if self.settings.llm_fallback_to_ollama and current_provider != "ollama":
                    logger.info("Falling back to Ollama...")
                    try:
                        # Ensure Ollama is running
                        if await ensure_ollama_running():
                            assistant_message = await self._call_ollama(messages)
                            used_provider = "ollama"
                            logger.info("Fallback to Ollama successful")
                        else:
                            raise ConnectionError("Ollama not available for fallback")
                    except Exception as fallback_error:
                        logger.error(f"Fallback to Ollama also failed: {fallback_error}")
                        raise primary_error  # Raise original error
                else:
                    raise
            
            # Update conversation history
            conversation.add_message("user", query)
            conversation.add_message("assistant", assistant_message)
            
            if used_provider != current_provider:
                assistant_message = f"[Using {used_provider} as fallback]\n\n{assistant_message}"
            
            logger.info(f"AI chat completed for session {session_id} using {used_provider}")
            return assistant_message
            
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return f"Configuration error: {str(e)}\n\n💡 Tip: Set up your AI provider in the Integrations panel, or Ollama will be used as a local fallback."
            
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return f"Connection error: {str(e)}\n\n💡 Tip: Install Ollama locally for offline AI support: https://ollama.ai"
            
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            return f"I encountered an error processing your request: {str(e)}"
    
    async def get_available_providers(self) -> dict[str, dict]:
        """
        Check which LLM providers are available.
        
        Returns:
            Dictionary with provider status and info
        """
        providers = {}
        
        # Check OpenAI
        providers["openai"] = {
            "available": bool(self.settings.openai_api_key),
            "model": self.settings.openai_model,
            "reason": "API key not configured" if not self.settings.openai_api_key else None,
        }
        
        # Check Ollama
        try:
            from src.ai.ollama_client import get_ollama_client
            client = get_ollama_client()
            ollama_available = await client.is_available()
            ollama_models = await client.list_models() if ollama_available else []
            providers["ollama"] = {
                "available": ollama_available,
                "model": self.settings.ollama_model,
                "host": self.settings.ollama_host_resolved,
                "models": [m.get("name", "") for m in ollama_models],
                "reason": None if ollama_available else "Ollama server not running",
            }
        except Exception as e:
            providers["ollama"] = {
                "available": False,
                "reason": str(e),
            }
        
        # Check Anthropic
        providers["anthropic"] = {
            "available": bool(self.settings.anthropic_api_key),
            "model": self.settings.anthropic_model,
            "reason": "API key not configured" if not self.settings.anthropic_api_key else None,
        }
        
        return providers
    
    async def get_quick_insights(self) -> list[str]:
        """
        Generate quick insights based on current system state.
        
        Returns:
            List of insight strings
        """
        try:
            context = await self.context_builder.build_context()
            insights = []
            
            # Performance insights
            if context.performance.total_pnl > 0:
                insights.append(f"📈 Portfolio is up ${context.performance.total_pnl:,.2f} overall")
            elif context.performance.total_pnl < 0:
                insights.append(f"📉 Portfolio is down ${abs(context.performance.total_pnl):,.2f} overall")
            
            if context.performance.win_rate > 0:
                if context.performance.win_rate >= 60:
                    insights.append(f"🎯 Strong win rate at {context.performance.win_rate:.1f}%")
                elif context.performance.win_rate < 40:
                    insights.append(f"⚠️ Low win rate at {context.performance.win_rate:.1f}% - review strategy parameters")
            
            # Position insights
            if context.positions.total_positions > 0:
                insights.append(
                    f"📊 {context.positions.total_positions} open positions "
                    f"(${context.positions.total_exposure:,.2f} exposure)"
                )
            
            # Bot insights
            running_bots = sum(1 for b in context.bots if b.status == "running")
            if running_bots > 0:
                insights.append(f"🤖 {running_bots} bot(s) actively trading")
            
            # LLM provider info
            insights.append(f"🧠 AI powered by {self.provider.upper()}")
            
            # Risk insights
            if context.circuit_breaker_status.get("kill_switch_active"):
                insights.append("🛑 KILL SWITCH ACTIVE - Trading halted")
            
            # Data source insights
            active_sources = sum(1 for ds in context.data_sources if ds.status == "active")
            insights.append(f"📰 {active_sources} data sources active")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return ["Unable to generate insights at this time"]
    
    async def analyze_for_optimization(self) -> dict[str, Any]:
        """
        Perform deep analysis and generate optimization recommendations.
        
        Returns:
            Dictionary with analysis and recommendations
        """
        try:
            context = await self.context_builder.build_context()
            
            recommendations = []
            warnings = []
            opportunities = []
            
            # Analyze strategy performance
            for strat in context.strategies:
                if strat.win_rate > 0 and strat.win_rate < 45:
                    recommendations.append({
                        "area": "Strategy",
                        "priority": "high",
                        "suggestion": f"Consider reducing weight for {strat.strategy_name} (win rate: {strat.win_rate:.1f}%)",
                    })
                elif strat.win_rate >= 60:
                    opportunities.append({
                        "area": "Strategy",
                        "suggestion": f"{strat.strategy_name} performing well - consider increasing allocation",
                    })
            
            # Analyze risk metrics
            if context.performance.max_drawdown > 15:
                warnings.append({
                    "level": "high",
                    "message": f"Max drawdown at {context.performance.max_drawdown:.1f}% - consider tighter stop losses",
                })
            
            if context.performance.profit_factor > 0 and context.performance.profit_factor < 1.2:
                recommendations.append({
                    "area": "Risk Management",
                    "priority": "medium",
                    "suggestion": "Profit factor is low - review entry criteria and position sizing",
                })
            
            # Analyze data sources
            error_sources = [ds for ds in context.data_sources if ds.status == "error"]
            if error_sources:
                for ds in error_sources:
                    warnings.append({
                        "level": "medium",
                        "message": f"Data source '{ds.name}' has errors - check configuration",
                    })
            
            # Analyze positions
            if context.positions.total_exposure > context.account_value * 0.8 and context.account_value > 0:
                warnings.append({
                    "level": "high",
                    "message": "Position exposure is very high (>80% of account) - consider reducing",
                })
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "llm_provider": self.provider,
                "summary": {
                    "total_recommendations": len(recommendations),
                    "warnings": len(warnings),
                    "opportunities": len(opportunities),
                },
                "recommendations": recommendations,
                "warnings": warnings,
                "opportunities": opportunities,
                "context_snapshot": {
                    "account_value": context.account_value,
                    "total_pnl": context.performance.total_pnl,
                    "win_rate": context.performance.win_rate,
                    "active_bots": len([b for b in context.bots if b.status == "running"]),
                    "open_positions": context.positions.total_positions,
                },
            }
            
        except Exception as e:
            logger.error(f"Error in optimization analysis: {e}")
            return {
                "error": str(e),
                "recommendations": [],
                "warnings": [],
                "opportunities": [],
            }
    
    def clear_conversation(self, session_id: str):
        """Clear conversation history for a session."""
        if session_id in self.conversations:
            self.conversations[session_id].clear()
    
    def get_example_questions(self) -> list[str]:
        """Get list of example questions."""
        return self.EXAMPLE_QUESTIONS


# Singleton instance
_assistant: Optional[AIAssistant] = None


def get_ai_assistant() -> AIAssistant:
    """Get or create AI assistant instance."""
    global _assistant
    if _assistant is None:
        _assistant = AIAssistant()
    return _assistant
