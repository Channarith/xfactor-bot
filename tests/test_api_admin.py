"""Tests for Admin Panel API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestAdminAuth:
    """Tests for admin authentication."""

    def test_login_with_correct_password(self, client):
        """Test POST /api/admin/login with correct password."""
        response = client.post(
            "/api/admin/login",
            json={"password": "106431"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data
        assert "expires_at" in data

    def test_login_with_wrong_password(self, client):
        """Test POST /api/admin/login with wrong password."""
        response = client.post(
            "/api/admin/login",
            json={"password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Invalid password" in response.json()["detail"]

    def test_logout(self, client, auth_headers):
        """Test POST /api/admin/logout."""
        response = client.post("/api/admin/logout", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_verify_valid_session(self, client, auth_headers):
        """Test GET /api/admin/verify with valid token."""
        response = client.get("/api/admin/verify", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["valid"] is True

    def test_verify_invalid_session(self, client):
        """Test GET /api/admin/verify with invalid token."""
        response = client.get(
            "/api/admin/verify",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestFeatureManagement:
    """Tests for feature flag management."""

    def test_get_all_features(self, client, auth_headers):
        """Test GET /api/admin/features returns all features."""
        response = client.get("/api/admin/features", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert "grouped" in data
        assert "total" in data
        assert data["total"] > 0

    def test_get_all_features_requires_auth(self, client):
        """Test GET /api/admin/features requires authentication."""
        response = client.get("/api/admin/features")
        assert response.status_code == 401

    def test_get_specific_feature(self, client, auth_headers):
        """Test GET /api/admin/features/{feature}."""
        response = client.get(
            "/api/admin/features/strategy_technical",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["feature"] == "strategy_technical"
        assert "enabled" in data

    def test_get_nonexistent_feature(self, client, auth_headers):
        """Test GET /api/admin/features/{feature} for unknown feature."""
        response = client.get(
            "/api/admin/features/nonexistent_feature",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_toggle_feature_on(self, client, auth_headers):
        """Test PATCH /api/admin/features/{feature} to enable."""
        response = client.patch(
            "/api/admin/features/trading_options",
            json={"enabled": True},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["feature"] == "trading_options"

    def test_toggle_feature_off(self, client, auth_headers):
        """Test PATCH /api/admin/features/{feature} to disable."""
        response = client.patch(
            "/api/admin/features/strategy_momentum",
            json={"enabled": False},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    def test_bulk_toggle_features(self, client, auth_headers):
        """Test POST /api/admin/features/bulk."""
        response = client.post(
            "/api/admin/features/bulk",
            json={"features": {
                "strategy_technical": True,
                "strategy_momentum": False,
                "news_bloomberg": True,
            }},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["updated"] == 3

    def test_toggle_category(self, client, auth_headers):
        """Test POST /api/admin/features/category/{category}/toggle."""
        response = client.post(
            "/api/admin/features/category/strategies/toggle",
            json={"enabled": True},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "strategies"
        assert "updated_features" in data
        assert len(data["updated_features"]) > 0

    def test_toggle_invalid_category(self, client, auth_headers):
        """Test POST /api/admin/features/category/{category}/toggle for unknown category."""
        response = client.post(
            "/api/admin/features/category/unknown_category/toggle",
            json={"enabled": True},
            headers=auth_headers
        )
        assert response.status_code == 404


class TestEmergencyControls:
    """Tests for emergency control endpoints."""

    def test_emergency_disable_trading(self, client, auth_headers):
        """Test POST /api/admin/emergency/disable-all-trading."""
        response = client.post(
            "/api/admin/emergency/disable-all-trading",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "disabled_features" in data
        assert all(f.startswith("trading_") for f in data["disabled_features"])

    def test_emergency_disable_news(self, client, auth_headers):
        """Test POST /api/admin/emergency/disable-all-news."""
        response = client.post(
            "/api/admin/emergency/disable-all-news",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "disabled_features" in data

    def test_emergency_enable_all(self, client, auth_headers):
        """Test POST /api/admin/emergency/enable-all."""
        response = client.post(
            "/api/admin/emergency/enable-all",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_emergency_controls_require_auth(self, client):
        """Test emergency controls require authentication."""
        response = client.post("/api/admin/emergency/disable-all-trading")
        assert response.status_code == 401

