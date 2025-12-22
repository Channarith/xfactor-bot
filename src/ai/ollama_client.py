"""
Ollama LLM Client.
Provides integration with locally running Ollama models.
"""

import httpx
from typing import Optional, AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OllamaMessage:
    """A chat message for Ollama."""
    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class OllamaResponse:
    """Response from Ollama API."""
    model: str
    message: OllamaMessage
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None


class OllamaClient:
    """
    Client for interacting with locally running Ollama LLM.
    
    Ollama provides an OpenAI-compatible API at localhost:11434.
    Supports models like llama3.1, mistral, codellama, etc.
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        settings = get_settings()
        # Use resolved host for Docker compatibility (localhost -> host.docker.internal)
        self.host = host or settings.ollama_host_resolved
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        self.keep_alive = settings.ollama_keep_alive
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.host,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            response = await self.client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    async def list_models(self) -> list[dict]:
        """List available models on the Ollama server."""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama library."""
        try:
            response = await self.client.post(
                "/api/pull",
                json={"name": model_name},
                timeout=httpx.Timeout(600),  # Models can take time to download
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled model: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
    
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """
        Send a chat completion request to Ollama.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            The assistant's response content
        """
        model = model or self.model
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
            },
            "keep_alive": self.keep_alive,
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            logger.debug(f"Sending chat request to Ollama with model {model}")
            
            response = await self.client.post(
                "/api/chat",
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            content = data.get("message", {}).get("content", "")
            
            # Log usage stats if available
            if "eval_count" in data:
                logger.debug(
                    f"Ollama response: {data.get('eval_count', 0)} tokens, "
                    f"duration: {data.get('total_duration', 0) / 1e9:.2f}s"
                )
            
            return content
            
        except httpx.TimeoutException:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            raise
            
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion response from Ollama.
        
        Yields:
            Chunks of the response content as they arrive
        """
        model = model or self.model
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
            "keep_alive": self.keep_alive,
        }
        
        try:
            async with self.client.stream(
                "POST",
                "/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        
                        if data.get("done"):
                            break
                            
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a completion (non-chat) from Ollama.
        
        Args:
            prompt: The prompt to complete
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Generated text
        """
        model = model or self.model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            response = await self.client.post(
                "/api/generate",
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("response", "")
            
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            raise
    
    async def embeddings(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> list[float]:
        """
        Generate embeddings for text using Ollama.
        
        Args:
            text: Text to embed
            model: Embedding model (e.g., 'nomic-embed-text')
            
        Returns:
            Embedding vector
        """
        model = model or "nomic-embed-text"
        
        try:
            response = await self.client.post(
                "/api/embeddings",
                json={
                    "model": model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("embedding", [])
            
        except Exception as e:
            logger.error(f"Ollama embeddings error: {e}")
            raise


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client instance."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client

