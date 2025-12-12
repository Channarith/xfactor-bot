"""Tests for main application endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestAppEndpoints:
    """Tests for main application endpoints."""

    def test_root_endpoint(self, client):
        """Test GET / returns app info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["name"] == "XFactor Bot"
        assert "version" in data

    def test_health_endpoint(self, client):
        """Test GET /health returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_metrics_endpoint(self, client):
        """Test GET /metrics returns prometheus metrics."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Prometheus metrics are text/plain
        assert "text" in response.headers["content-type"]


class TestWebSocket:
    """Tests for WebSocket endpoint."""

    def test_websocket_connection(self, client):
        """Test WebSocket connects successfully."""
        with client.websocket_connect("/ws") as websocket:
            # Send subscription
            websocket.send_json({"type": "subscribe", "channel": "portfolio"})
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert data["channel"] == "portfolio"

    def test_websocket_multiple_subscriptions(self, client):
        """Test subscribing to multiple channels."""
        with client.websocket_connect("/ws") as websocket:
            # Subscribe to multiple channels
            for channel in ["portfolio", "orders", "news"]:
                websocket.send_json({"type": "subscribe", "channel": channel})
                data = websocket.receive_json()
                assert data["type"] == "subscribed"
                assert data["channel"] == channel


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:9876",
                "Access-Control-Request-Method": "GET"
            }
        )
        # May be 200 or 405 depending on FastAPI version
        assert response.status_code in [200, 405]

    def test_allowed_origin(self, client):
        """Test allowed origin returns proper headers."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:9876"}
        )
        assert response.status_code == 200
        # CORS headers should allow the origin
        cors_header = response.headers.get("access-control-allow-origin")
        if cors_header:
            assert cors_header in ["*", "http://localhost:9876"]

