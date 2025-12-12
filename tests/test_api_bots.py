"""Tests for Bot Management API endpoints."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class TestBotsAPI:
    """Tests for /api/bots endpoints."""

    def test_list_bots(self, client, mock_bot_manager):
        """Test GET /api/bots/ returns bot list."""
        response = client.get("/api/bots/")
        assert response.status_code == 200
        assert "bots" in response.json() or "count" in response.json()

    def test_get_bots_summary(self, client, mock_bot_manager):
        """Test GET /api/bots/summary returns lightweight summary."""
        mock_bot_manager.get_bot_summary.return_value = [
            {"id": "bot1", "name": "Test Bot", "status": "running"}
        ]
        
        response = client.get("/api/bots/summary")
        assert response.status_code == 200
        data = response.json()
        assert "bots" in data
        assert "total" in data or "max" in data

    def test_get_bot_templates(self, client):
        """Test GET /api/bots/templates returns templates."""
        response = client.get("/api/bots/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) >= 1

    def test_create_bot_requires_auth(self, client, sample_bot_config):
        """Test POST /api/bots/ requires authentication."""
        response = client.post("/api/bots/", json=sample_bot_config)
        assert response.status_code == 401 or response.status_code == 403

    def test_create_bot_with_auth(self, client, auth_headers, sample_bot_config, mock_bot_manager):
        """Test POST /api/bots/ creates bot with auth."""
        mock_bot = MagicMock()
        mock_bot.get_status.return_value = {"id": "new-bot", "name": "Test Bot", "status": "stopped"}
        mock_bot_manager.create_bot.return_value = mock_bot
        
        response = client.post("/api/bots/", json=sample_bot_config, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_create_bot_max_reached(self, client, auth_headers, sample_bot_config, mock_bot_manager):
        """Test POST /api/bots/ fails when max bots reached."""
        mock_bot_manager.can_create_bot = False
        
        response = client.post("/api/bots/", json=sample_bot_config, headers=auth_headers)
        assert response.status_code == 400
        assert "Maximum" in response.json()["detail"]

    def test_get_specific_bot(self, client, mock_bot_manager):
        """Test GET /api/bots/{bot_id} returns bot details."""
        mock_bot = MagicMock()
        mock_bot.get_status.return_value = {"id": "bot1", "name": "Test", "status": "running"}
        mock_bot_manager.get_bot.return_value = mock_bot
        
        response = client.get("/api/bots/bot1")
        assert response.status_code == 200

    def test_get_nonexistent_bot(self, client, mock_bot_manager):
        """Test GET /api/bots/{bot_id} returns 404 for unknown bot."""
        mock_bot_manager.get_bot.return_value = None
        
        response = client.get("/api/bots/unknown")
        assert response.status_code == 404

    def test_start_bot(self, client, auth_headers, mock_bot_manager):
        """Test POST /api/bots/{bot_id}/start starts bot."""
        mock_bot = MagicMock()
        mock_bot.start.return_value = True
        mock_bot.status.value = "running"
        mock_bot_manager.get_bot.return_value = mock_bot
        
        response = client.post("/api/bots/bot1/start", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_stop_bot(self, client, auth_headers, mock_bot_manager):
        """Test POST /api/bots/{bot_id}/stop stops bot."""
        mock_bot = MagicMock()
        mock_bot.stop.return_value = True
        mock_bot.status.value = "stopped"
        mock_bot_manager.get_bot.return_value = mock_bot
        
        response = client.post("/api/bots/bot1/stop", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_pause_bot(self, client, auth_headers, mock_bot_manager):
        """Test POST /api/bots/{bot_id}/pause pauses bot."""
        mock_bot = MagicMock()
        mock_bot.pause.return_value = True
        mock_bot.status.value = "paused"
        mock_bot_manager.get_bot.return_value = mock_bot
        
        response = client.post("/api/bots/bot1/pause", headers=auth_headers)
        assert response.status_code == 200

    def test_resume_bot(self, client, auth_headers, mock_bot_manager):
        """Test POST /api/bots/{bot_id}/resume resumes bot."""
        mock_bot = MagicMock()
        mock_bot.resume.return_value = True
        mock_bot.status.value = "running"
        mock_bot_manager.get_bot.return_value = mock_bot
        
        response = client.post("/api/bots/bot1/resume", headers=auth_headers)
        assert response.status_code == 200

    def test_delete_bot(self, client, auth_headers, mock_bot_manager):
        """Test DELETE /api/bots/{bot_id} deletes bot."""
        mock_bot_manager.delete_bot.return_value = True
        
        response = client.delete("/api/bots/bot1", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_nonexistent_bot(self, client, auth_headers, mock_bot_manager):
        """Test DELETE /api/bots/{bot_id} returns 404 for unknown bot."""
        mock_bot_manager.delete_bot.return_value = False
        
        response = client.delete("/api/bots/unknown", headers=auth_headers)
        assert response.status_code == 404

    def test_start_all_bots(self, client, auth_headers, mock_bot_manager):
        """Test POST /api/bots/start-all starts all bots."""
        mock_bot_manager.start_all.return_value = {"bot1": True, "bot2": True}
        
        response = client.post("/api/bots/start-all", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["started"] == 2

    def test_stop_all_bots(self, client, auth_headers, mock_bot_manager):
        """Test POST /api/bots/stop-all stops all bots."""
        mock_bot_manager.stop_all.return_value = {"bot1": True, "bot2": True}
        
        response = client.post("/api/bots/stop-all", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["stopped"] == 2

    def test_pause_all_bots(self, client, auth_headers, mock_bot_manager):
        """Test POST /api/bots/pause-all pauses all bots."""
        mock_bot_manager.pause_all.return_value = {"bot1": True}
        
        response = client.post("/api/bots/pause-all", headers=auth_headers)
        assert response.status_code == 200

    def test_update_bot_config(self, client, auth_headers, mock_bot_manager):
        """Test PATCH /api/bots/{bot_id} updates bot config."""
        mock_bot = MagicMock()
        mock_bot.get_status.return_value = {"id": "bot1", "name": "Updated Bot"}
        mock_bot_manager.get_bot.return_value = mock_bot
        
        response = client.patch(
            "/api/bots/bot1",
            json={"name": "Updated Bot", "max_position_size": 30000},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

