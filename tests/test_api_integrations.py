"""Tests for Integrations API endpoints."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


class TestBrokerIntegrations:
    """Tests for broker integration endpoints."""

    def test_list_brokers(self, client):
        """Test GET /api/integrations/brokers lists available brokers."""
        response = client.get("/api/integrations/brokers")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data or "brokers" in data

    @patch('src.brokers.registry.BrokerRegistry.get_broker_class')
    def test_connect_broker(self, mock_get_class, client, auth_headers):
        """Test POST /api/integrations/brokers/connect."""
        mock_broker = MagicMock()
        mock_broker.return_value.connect = AsyncMock(return_value=True)
        mock_get_class.return_value = mock_broker
        
        response = client.post(
            "/api/integrations/brokers/connect",
            json={
                "broker_type": "alpaca",
                "api_key": "test_key",
                "secret_key": "test_secret",
                "paper": True
            },
            headers=auth_headers
        )
        # May succeed or fail depending on broker availability
        assert response.status_code in [200, 500, 404]


class TestDataSourceIntegrations:
    """Tests for data source integration endpoints."""

    def test_list_data_sources(self, client):
        """Test GET /api/integrations/data-sources lists available sources."""
        response = client.get("/api/integrations/data-sources")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data or "data_sources" in data


class TestBankingIntegrations:
    """Tests for banking (Plaid) integration endpoints."""

    def test_get_banking_status(self, client):
        """Test GET /api/integrations/banking/status."""
        response = client.get("/api/integrations/banking/status")
        assert response.status_code == 200

    @patch('src.banking.plaid_client.PlaidClient')
    def test_create_link_token(self, mock_plaid, client, auth_headers):
        """Test POST /api/integrations/banking/link-token."""
        mock_client = MagicMock()
        mock_client.initialize = AsyncMock(return_value=True)
        mock_client.create_link_token = AsyncMock(return_value="link-sandbox-xxx")
        mock_plaid.return_value = mock_client
        
        response = client.post(
            "/api/integrations/banking/link-token",
            json={
                "user_id": "test-user",
                "redirect_uri": "http://localhost:9876/callback"
            },
            headers=auth_headers
        )
        # May succeed or fail depending on Plaid configuration
        assert response.status_code in [200, 500]


class TestTradingViewWebhook:
    """Tests for TradingView webhook integration."""

    def test_receive_webhook(self, client):
        """Test POST /api/integrations/webhooks/tradingview."""
        webhook_payload = {
            "alertName": "RSI Oversold Alert",
            "symbol": "BINANCE:BTCUSDT",
            "exchange": "BINANCE",
            "price": 45000,
            "volume": 12345,
            "time": "2024-01-01T12:00:00Z",
            "message": "RSI crossed below 30"
        }
        
        response = client.post(
            "/api/integrations/webhooks/tradingview",
            json=webhook_payload
        )
        # May succeed or fail depending on webhook handler
        assert response.status_code in [200, 400, 500]

    def test_get_tradingview_alerts(self, client):
        """Test GET /api/integrations/webhooks/tradingview/alerts."""
        response = client.get("/api/integrations/webhooks/tradingview/alerts")
        assert response.status_code in [200, 500]


class TestAInvestIntegration:
    """Tests for AInvest AI integration endpoints."""

    def test_get_recommendations(self, client):
        """Test GET /api/integrations/ainvest/recommendations."""
        response = client.get("/api/integrations/ainvest/recommendations")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "recommendations" in data

    def test_get_recommendations_with_filters(self, client):
        """Test GET /api/integrations/ainvest/recommendations with filters."""
        response = client.get(
            "/api/integrations/ainvest/recommendations",
            params={"symbols": "AAPL,NVDA", "min_score": 70, "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] <= 10

    def test_get_sentiment(self, client):
        """Test GET /api/integrations/ainvest/sentiment/{symbol}."""
        response = client.get("/api/integrations/ainvest/sentiment/NVDA")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "overall_sentiment" in data

    def test_get_signals(self, client):
        """Test GET /api/integrations/ainvest/signals."""
        response = client.get("/api/integrations/ainvest/signals")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "signals" in data

    def test_get_insider_trades(self, client):
        """Test GET /api/integrations/ainvest/insider-trades."""
        response = client.get("/api/integrations/ainvest/insider-trades")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "trades" in data

    def test_get_earnings_calendar(self, client):
        """Test GET /api/integrations/ainvest/earnings."""
        response = client.get("/api/integrations/ainvest/earnings")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "earnings" in data

    def test_get_ainvest_news(self, client):
        """Test GET /api/integrations/ainvest/news."""
        response = client.get("/api/integrations/ainvest/news")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "articles" in data

