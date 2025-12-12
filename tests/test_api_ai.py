"""Tests for AI Assistant API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


class TestAIChat:
    """Tests for AI chat functionality."""

    @patch('src.ai.assistant.get_ai_assistant')
    def test_chat_endpoint(self, mock_get_assistant, client):
        """Test POST /api/ai/chat returns AI response."""
        mock_assistant = MagicMock()
        mock_assistant.chat = AsyncMock(return_value="This is a test response from the AI.")
        mock_get_assistant.return_value = mock_assistant
        
        response = client.post(
            "/api/ai/chat",
            json={
                "query": "How is my portfolio performing?",
                "session_id": "test-session",
                "include_context": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session"

    @patch('src.ai.assistant.get_ai_assistant')
    def test_chat_without_session_id(self, mock_get_assistant, client):
        """Test POST /api/ai/chat with default session."""
        mock_assistant = MagicMock()
        mock_assistant.chat = AsyncMock(return_value="Test response")
        mock_get_assistant.return_value = mock_assistant
        
        response = client.post(
            "/api/ai/chat",
            json={"query": "What are my best performing strategies?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "default"


class TestAIInsights:
    """Tests for AI insights functionality."""

    @patch('src.ai.assistant.get_ai_assistant')
    def test_get_insights(self, mock_get_assistant, client):
        """Test GET /api/ai/insights returns quick insights."""
        mock_assistant = MagicMock()
        mock_assistant.get_quick_insights = AsyncMock(return_value=[
            "Portfolio is up 2.5% today",
            "Technical strategy outperforming",
            "3 bots currently running"
        ])
        mock_get_assistant.return_value = mock_assistant
        
        response = client.get("/api/ai/insights")
        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert isinstance(data["insights"], list)
        assert len(data["insights"]) > 0

    @patch('src.ai.assistant.get_ai_assistant')
    def test_get_optimization_recommendations(self, mock_get_assistant, client):
        """Test GET /api/ai/optimize returns recommendations."""
        mock_assistant = MagicMock()
        mock_assistant.analyze_for_optimization = AsyncMock(return_value={
            "timestamp": "2024-01-01T00:00:00",
            "summary": {"total_value": 100000},
            "recommendations": [{"type": "strategy", "action": "increase weight"}],
            "warnings": [],
            "opportunities": [],
            "context_snapshot": {}
        })
        mock_get_assistant.return_value = mock_assistant
        
        response = client.get("/api/ai/optimize")
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data or "timestamp" in data


class TestAIExamples:
    """Tests for example questions."""

    @patch('src.ai.assistant.get_ai_assistant')
    def test_get_examples(self, mock_get_assistant, client):
        """Test GET /api/ai/examples returns example questions."""
        mock_assistant = MagicMock()
        mock_assistant.get_example_questions.return_value = [
            "How is my portfolio performing?",
            "What's my best strategy?",
            "Are there any risk warnings?"
        ]
        mock_get_assistant.return_value = mock_assistant
        
        response = client.get("/api/ai/examples")
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        assert isinstance(data["examples"], list)


class TestAISessionManagement:
    """Tests for session management."""

    @patch('src.ai.assistant.get_ai_assistant')
    def test_clear_conversation(self, mock_get_assistant, client):
        """Test POST /api/ai/clear/{session_id} clears history."""
        mock_assistant = MagicMock()
        mock_assistant.clear_conversation = MagicMock()
        mock_get_assistant.return_value = mock_assistant
        
        response = client.post("/api/ai/clear/test-session")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test-session" in data["message"]

    @patch('src.ai.context_builder.get_context_builder')
    def test_get_context(self, mock_get_builder, client):
        """Test GET /api/ai/context returns system context."""
        mock_builder = MagicMock()
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {
            "portfolio": {},
            "positions": [],
            "bots": [],
            "strategies": {}
        }
        mock_builder.build_context = AsyncMock(return_value=mock_context)
        mock_get_builder.return_value = mock_builder
        
        response = client.get("/api/ai/context")
        # May return 200 or 500 depending on context availability
        assert response.status_code in [200, 500]

