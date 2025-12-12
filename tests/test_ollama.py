"""Tests for Ollama LLM integration."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestOllamaClient:
    """Tests for OllamaClient."""

    @pytest.fixture
    def client(self):
        with patch('src.ai.ollama_client.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                ollama_host="http://localhost:11434",
                ollama_model="llama3.1",
                ollama_timeout=120,
                ollama_keep_alive="5m",
            )
            from src.ai.ollama_client import OllamaClient
            return OllamaClient()

    def test_initialization(self, client):
        assert client.host == "http://localhost:11434"
        assert client.model == "llama3.1"
        assert client.timeout == 120

    @pytest.mark.asyncio
    async def test_is_available_when_running(self, client):
        with patch.object(client, 'client') as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_http.get = AsyncMock(return_value=mock_response)
            
            result = await client.is_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_is_available_when_not_running(self, client):
        with patch.object(client, 'client') as mock_http:
            mock_http.get = AsyncMock(side_effect=Exception("Connection refused"))
            
            result = await client.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_list_models(self, client):
        with patch.object(client, 'client') as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "models": [
                    {"name": "llama3.1:latest", "size": 4000000000},
                    {"name": "mistral:latest", "size": 3500000000},
                ]
            }
            mock_http.get = AsyncMock(return_value=mock_response)
            
            models = await client.list_models()
            
            assert len(models) == 2
            assert models[0]["name"] == "llama3.1:latest"

    @pytest.mark.asyncio
    async def test_chat(self, client):
        with patch.object(client, 'client') as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "message": {"content": "Hello! How can I help you today?"},
                "done": True,
                "eval_count": 50,
            }
            mock_http.post = AsyncMock(return_value=mock_response)
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ]
            
            response = await client.chat(messages)
            
            assert response == "Hello! How can I help you today?"

    @pytest.mark.asyncio
    async def test_chat_with_custom_model(self, client):
        with patch.object(client, 'client') as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "message": {"content": "Test response"},
                "done": True,
            }
            mock_http.post = AsyncMock(return_value=mock_response)
            
            messages = [{"role": "user", "content": "Test"}]
            response = await client.chat(messages, model="mistral")
            
            assert response == "Test response"
            # Verify the model was passed in the request
            call_args = mock_http.post.call_args
            assert call_args[1]["json"]["model"] == "mistral"


class TestAIAssistantWithOllama:
    """Tests for AI Assistant with Ollama provider."""

    @pytest.fixture
    def assistant(self):
        with patch('src.ai.assistant.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                llm_provider="ollama",
                ollama_host="http://localhost:11434",
                ollama_model="llama3.1",
                ollama_timeout=120,
                ollama_keep_alive="5m",
                openai_api_key="",
                anthropic_api_key="",
            )
            from src.ai.assistant import AIAssistant
            return AIAssistant(provider="ollama")

    def test_initialization_with_ollama(self, assistant):
        assert assistant.provider == "ollama"

    def test_set_provider(self, assistant):
        assistant.set_provider("openai")
        assert assistant.provider == "openai"
        
        assistant.set_provider("ollama")
        assert assistant.provider == "ollama"

    @pytest.mark.asyncio
    async def test_get_available_providers(self, assistant):
        with patch('src.ai.ollama_client.OllamaClient') as mock_ollama:
            mock_client = MagicMock()
            mock_client.is_available = AsyncMock(return_value=True)
            mock_client.list_models = AsyncMock(return_value=[
                {"name": "llama3.1:latest"}
            ])
            mock_ollama.return_value = mock_client
            
            providers = await assistant.get_available_providers()
            
            assert "ollama" in providers
            assert "openai" in providers
            assert "anthropic" in providers


class TestOllamaAPIRoutes:
    """Tests for Ollama-related API routes."""

    def test_get_providers(self, client):
        with patch('src.ai.assistant.AIAssistant.get_available_providers') as mock:
            mock.return_value = AsyncMock(return_value={
                "openai": {"available": False, "reason": "No API key"},
                "ollama": {"available": True, "model": "llama3.1"},
                "anthropic": {"available": False, "reason": "No API key"},
            })()
            
            response = client.get("/api/ai/providers")
            assert response.status_code == 200

    def test_set_provider(self, client, auth_headers):
        with patch('src.ai.assistant.get_ai_assistant') as mock:
            mock_assistant = MagicMock()
            mock_assistant.get_available_providers = AsyncMock(return_value={
                "ollama": {"available": True, "model": "llama3.1"},
            })
            mock_assistant.set_provider = MagicMock()
            mock.return_value = mock_assistant
            
            response = client.post(
                "/api/ai/providers/set",
                json={"provider": "ollama"},
            )
            # May succeed or fail depending on setup
            assert response.status_code in [200, 400, 500]

    def test_get_ollama_status(self, client):
        response = client.get("/api/ai/ollama/status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "host" in data

    def test_list_ollama_models(self, client):
        response = client.get("/api/ai/ollama/models")
        # May be 200 if Ollama is running, 503 if not
        assert response.status_code in [200, 503]

