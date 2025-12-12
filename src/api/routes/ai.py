"""
API routes for AI assistant functionality.
Supports multiple LLM providers: OpenAI, Ollama (local), Anthropic.
"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.ai.assistant import get_ai_assistant
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

LLMProvider = Literal["openai", "ollama", "anthropic"]


# =========================================================================
# Request/Response Models
# =========================================================================

class ChatRequest(BaseModel):
    """Chat request payload."""
    
    query: str
    session_id: Optional[str] = "default"
    include_context: bool = True
    provider: Optional[LLMProvider] = None  # Override default provider


class SetProviderRequest(BaseModel):
    """Request to change LLM provider."""
    
    provider: LLMProvider


class ChatResponse(BaseModel):
    """Chat response payload."""
    
    response: str
    session_id: str


class InsightsResponse(BaseModel):
    """Quick insights response."""
    
    insights: list[str]


class OptimizationResponse(BaseModel):
    """Optimization analysis response."""
    
    timestamp: str
    summary: dict
    recommendations: list[dict]
    warnings: list[dict]
    opportunities: list[dict]
    context_snapshot: dict


# =========================================================================
# Routes
# =========================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """
    Send a message to the AI assistant.
    
    The assistant has access to real-time system context including:
    - Portfolio positions and P&L
    - Strategy performance
    - Data source status
    - Bot activity
    - Risk metrics
    
    Supports multiple LLM providers (set via 'provider' field):
    - openai: GPT-4, GPT-3.5 (requires OPENAI_API_KEY)
    - ollama: Local LLMs like Llama, Mistral (requires Ollama running)
    - anthropic: Claude (requires ANTHROPIC_API_KEY)
    
    Example queries:
    - "How is my portfolio performing today?"
    - "Which strategy is generating the best returns?"
    - "What optimizations would you recommend?"
    """
    try:
        assistant = get_ai_assistant()
        
        response = await assistant.chat(
            query=request.query,
            session_id=request.session_id,
            include_context=request.include_context,
            provider=request.provider,  # Can override provider per request
        )
        
        return ChatResponse(
            response=response,
            session_id=request.session_id,
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights", response_model=InsightsResponse)
async def get_quick_insights():
    """
    Get quick insights about current system state.
    
    Returns a list of key observations about:
    - Portfolio performance
    - Position status
    - Bot activity
    - Risk alerts
    - Data source status
    """
    try:
        assistant = get_ai_assistant()
        insights = await assistant.get_quick_insights()
        
        return InsightsResponse(insights=insights)
        
    except Exception as e:
        logger.error(f"Insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimize")
async def get_optimization_recommendations():
    """
    Get AI-powered optimization recommendations.
    
    Analyzes current system state and provides:
    - Strategy optimization suggestions
    - Risk management recommendations
    - Data source improvements
    - Position sizing adjustments
    """
    try:
        assistant = get_ai_assistant()
        analysis = await assistant.analyze_for_optimization()
        
        return analysis
        
    except Exception as e:
        logger.error(f"Optimization analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples")
async def get_example_questions():
    """
    Get list of example questions to ask the AI assistant.
    """
    assistant = get_ai_assistant()
    return {"examples": assistant.get_example_questions()}


@router.post("/clear/{session_id}")
async def clear_conversation(session_id: str):
    """
    Clear conversation history for a session.
    """
    try:
        assistant = get_ai_assistant()
        assistant.clear_conversation(session_id)
        
        return {"message": f"Conversation history cleared for session: {session_id}"}
        
    except Exception as e:
        logger.error(f"Clear conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context")
async def get_system_context():
    """
    Get current system context used by the AI assistant.
    
    Returns the full context object that the AI uses to answer questions.
    Useful for debugging and understanding what data the AI sees.
    """
    try:
        from src.ai.context_builder import get_context_builder
        
        builder = get_context_builder()
        context = await builder.build_context()
        
        return context.model_dump()
        
    except Exception as e:
        logger.error(f"Context retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# LLM Provider Management
# =========================================================================

@router.get("/providers")
async def get_available_providers():
    """
    Get available LLM providers and their status.
    
    Returns information about each provider:
    - available: Whether the provider is configured and accessible
    - model: The model configured for this provider
    - reason: Why the provider is not available (if applicable)
    
    Providers:
    - openai: Requires OPENAI_API_KEY in environment
    - ollama: Requires Ollama running locally (http://localhost:11434)
    - anthropic: Requires ANTHROPIC_API_KEY in environment
    """
    try:
        assistant = get_ai_assistant()
        providers = await assistant.get_available_providers()
        
        return {
            "current_provider": assistant.provider,
            "providers": providers,
        }
        
    except Exception as e:
        logger.error(f"Provider check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/set")
async def set_llm_provider(request: SetProviderRequest):
    """
    Set the default LLM provider for the AI assistant.
    
    Available providers:
    - openai: GPT-4, GPT-3.5-turbo
    - ollama: Local models (llama3.1, mistral, codellama, etc.)
    - anthropic: Claude 3
    """
    try:
        assistant = get_ai_assistant()
        
        # Verify provider is available
        providers = await assistant.get_available_providers()
        provider_info = providers.get(request.provider)
        
        if not provider_info or not provider_info.get("available"):
            reason = provider_info.get("reason", "Unknown error") if provider_info else "Provider not found"
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{request.provider}' is not available: {reason}"
            )
        
        assistant.set_provider(request.provider)
        
        return {
            "success": True,
            "provider": request.provider,
            "model": provider_info.get("model"),
            "message": f"Switched to {request.provider} provider",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Set provider error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ollama/models")
async def list_ollama_models():
    """
    List available models on the Ollama server.
    
    Returns a list of models that can be used with the 'ollama' provider.
    Requires Ollama to be running at the configured host.
    """
    try:
        from src.ai.ollama_client import get_ollama_client
        
        client = get_ollama_client()
        
        if not await client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Ollama server is not available. Please ensure Ollama is running."
            )
        
        models = await client.list_models()
        
        return {
            "host": client.host,
            "models": [
                {
                    "name": m.get("name", ""),
                    "size": m.get("size", 0),
                    "modified_at": m.get("modified_at", ""),
                    "digest": m.get("digest", "")[:12] + "...",
                }
                for m in models
            ],
            "count": len(models),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List Ollama models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/pull/{model_name}")
async def pull_ollama_model(model_name: str):
    """
    Pull a model from the Ollama library.
    
    This will download the specified model to the Ollama server.
    Popular models: llama3.1, mistral, codellama, phi, gemma
    
    Note: This can take several minutes for large models.
    """
    try:
        from src.ai.ollama_client import get_ollama_client
        
        client = get_ollama_client()
        
        if not await client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Ollama server is not available."
            )
        
        success = await client.pull_model(model_name)
        
        if success:
            return {
                "success": True,
                "model": model_name,
                "message": f"Successfully pulled model: {model_name}",
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to pull model: {model_name}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pull Ollama model error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ollama/status")
async def get_ollama_status():
    """
    Check Ollama server status and configuration.
    """
    try:
        from src.ai.ollama_client import get_ollama_client
        from src.config.settings import get_settings
        
        settings = get_settings()
        client = get_ollama_client()
        
        available = await client.is_available()
        models = await client.list_models() if available else []
        
        return {
            "available": available,
            "host": settings.ollama_host,
            "configured_model": settings.ollama_model,
            "timeout": settings.ollama_timeout,
            "installed_models": [m.get("name", "") for m in models],
            "model_installed": any(
                m.get("name", "").startswith(settings.ollama_model) 
                for m in models
            ) if available else False,
        }
        
    except Exception as e:
        logger.error(f"Ollama status error: {e}")
        return {
            "available": False,
            "error": str(e),
        }

