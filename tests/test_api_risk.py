"""Tests for Risk Management API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestRiskStatus:
    """Tests for risk status endpoints."""

    def test_get_risk_status(self, client):
        """Test GET /api/risk/status returns current risk status."""
        response = client.get("/api/risk/status")
        assert response.status_code == 200
        data = response.json()
        assert "trading_allowed" in data
        assert "paused" in data
        assert "killed" in data
        assert "daily_pnl" in data
        assert "current_drawdown_pct" in data
        assert "vix" in data

    def test_get_risk_limits(self, client):
        """Test GET /api/risk/limits returns risk limits."""
        response = client.get("/api/risk/limits")
        assert response.status_code == 200
        data = response.json()
        assert "max_position_size" in data
        assert "max_portfolio_pct" in data
        assert "daily_loss_limit_pct" in data
        assert "weekly_loss_limit_pct" in data
        assert "max_drawdown_pct" in data
        assert "vix_pause_threshold" in data
        assert "max_open_positions" in data


class TestTradingControl:
    """Tests for trading control endpoints."""

    def test_pause_trading(self, client):
        """Test POST /api/risk/pause pauses trading."""
        response = client.post("/api/risk/pause")
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    def test_resume_trading_with_confirmation(self, client):
        """Test POST /api/risk/resume with correct confirmation."""
        response = client.post(
            "/api/risk/resume",
            json={"confirmation": "CONFIRM"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "resumed"

    def test_resume_trading_without_confirmation(self, client):
        """Test POST /api/risk/resume without confirmation fails."""
        response = client.post(
            "/api/risk/resume",
            json={"confirmation": "wrong"}
        )
        assert response.status_code == 400
        assert "Invalid confirmation" in response.json()["detail"]


class TestKillSwitch:
    """Tests for kill switch functionality."""

    def test_activate_kill_switch(self, client):
        """Test POST /api/risk/kill-switch activates kill switch."""
        response = client.post(
            "/api/risk/kill-switch",
            json={
                "reason": "Test activation",
                "close_positions": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "activated"
        assert data["reason"] == "Test activation"
        assert data["positions_closed"] is False

    def test_activate_kill_switch_with_position_close(self, client):
        """Test POST /api/risk/kill-switch with position closing."""
        response = client.post(
            "/api/risk/kill-switch",
            json={
                "reason": "Emergency stop",
                "close_positions": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["positions_closed"] is True

    def test_reset_kill_switch_with_confirmation(self, client):
        """Test POST /api/risk/kill-switch/reset with correct confirmation."""
        response = client.post(
            "/api/risk/kill-switch/reset",
            json={"confirmation": "CONFIRM_DEACTIVATE"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "reset"

    def test_reset_kill_switch_without_confirmation(self, client):
        """Test POST /api/risk/kill-switch/reset without confirmation fails."""
        response = client.post(
            "/api/risk/kill-switch/reset",
            json={"confirmation": "wrong"}
        )
        assert response.status_code == 400
        assert "Invalid confirmation" in response.json()["detail"]


class TestRiskLimitsValidation:
    """Tests for risk limit values."""

    def test_risk_limits_values_reasonable(self, client):
        """Test risk limits have reasonable default values."""
        response = client.get("/api/risk/limits")
        data = response.json()
        
        # Max position size should be positive
        assert data["max_position_size"] > 0
        
        # Percentages should be between 0 and 100
        assert 0 < data["daily_loss_limit_pct"] <= 100
        assert 0 < data["weekly_loss_limit_pct"] <= 100
        assert 0 < data["max_drawdown_pct"] <= 100
        
        # VIX threshold should be reasonable
        assert 10 <= data["vix_pause_threshold"] <= 100
        
        # Max positions should be positive
        assert data["max_open_positions"] > 0

