"""Tests for Configuration API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestConfigParameters:
    """Tests for configuration parameter endpoints."""

    def test_get_all_parameters(self, client):
        """Test GET /api/config/parameters returns all parameters."""
        response = client.get("/api/config/parameters")
        assert response.status_code == 200
        data = response.json()
        
        # Check required parameter categories
        assert "trading" in data
        assert "risk" in data
        assert "strategies" in data
        assert "technical" in data
        assert "news" in data

    def test_trading_parameters(self, client):
        """Test trading parameters have required fields."""
        response = client.get("/api/config/parameters")
        trading = response.json()["trading"]
        
        assert "mode" in trading
        assert "max_position_size" in trading
        assert "max_portfolio_pct" in trading
        assert "max_open_positions" in trading

    def test_risk_parameters(self, client):
        """Test risk parameters have required fields."""
        response = client.get("/api/config/parameters")
        risk = response.json()["risk"]
        
        assert "daily_loss_limit_pct" in risk
        assert "weekly_loss_limit_pct" in risk
        assert "max_drawdown_pct" in risk
        assert "vix_pause_threshold" in risk

    def test_strategy_parameters(self, client):
        """Test strategy parameters have required fields."""
        response = client.get("/api/config/parameters")
        strategies = response.json()["strategies"]
        
        assert "technical_weight" in strategies
        assert "momentum_weight" in strategies
        assert "news_sentiment_weight" in strategies

    def test_technical_parameters(self, client):
        """Test technical parameters have required fields."""
        response = client.get("/api/config/parameters")
        technical = response.json()["technical"]
        
        assert "rsi_oversold" in technical
        assert "rsi_overbought" in technical
        assert "ma_fast_period" in technical
        assert "ma_slow_period" in technical

    def test_news_parameters(self, client):
        """Test news parameters have required fields."""
        response = client.get("/api/config/parameters")
        news = response.json()["news"]
        
        assert "min_confidence" in news
        assert "min_urgency" in news
        assert "sentiment_threshold" in news
        assert "llm_enabled" in news

    def test_update_parameter(self, client):
        """Test PATCH /api/config/parameters/{category}/{parameter}."""
        response = client.patch(
            "/api/config/parameters/risk/daily_loss_limit_pct",
            json={"value": 5.0}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert data["category"] == "risk"
        assert data["parameter"] == "daily_loss_limit_pct"
        assert data["value"] == 5.0


class TestSystemStatus:
    """Tests for system status endpoint."""

    def test_get_system_status(self, client):
        """Test GET /api/config/status returns system status."""
        response = client.get("/api/config/status")
        assert response.status_code == 200
        data = response.json()
        
        assert "trading_enabled" in data
        assert "mode" in data
        assert "ibkr_connected" in data
        assert "database_connected" in data
        assert "redis_connected" in data
        assert "uptime_seconds" in data

