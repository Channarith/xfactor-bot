"""Tests for Positions API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestPositionsAPI:
    """Tests for /api/positions endpoints."""

    def test_get_all_positions(self, client):
        """Test GET /api/positions/ returns positions."""
        response = client.get("/api/positions/")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        assert "count" in data
        assert "total_value" in data

    def test_get_portfolio_summary(self, client):
        """Test GET /api/positions/summary returns summary."""
        response = client.get("/api/positions/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "cash" in data
        assert "positions_value" in data
        assert "unrealized_pnl" in data
        assert "realized_pnl" in data
        assert "daily_pnl" in data
        assert "position_count" in data

    def test_get_exposure(self, client):
        """Test GET /api/positions/exposure returns exposure breakdown."""
        response = client.get("/api/positions/exposure")
        assert response.status_code == 200
        data = response.json()
        assert "by_sector" in data
        assert "by_strategy" in data
        assert "gross_exposure" in data
        assert "net_exposure" in data

    def test_get_specific_position(self, client):
        """Test GET /api/positions/{symbol} returns position."""
        response = client.get("/api/positions/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "quantity" in data
        assert "avg_cost" in data
        assert "current_price" in data
        assert "market_value" in data
        assert "unrealized_pnl" in data


class TestPositionDataTypes:
    """Tests for position data types and values."""

    def test_summary_values_numeric(self, client):
        """Test that summary values are numeric."""
        response = client.get("/api/positions/summary")
        data = response.json()
        
        assert isinstance(data["total_value"], (int, float))
        assert isinstance(data["cash"], (int, float))
        assert isinstance(data["unrealized_pnl"], (int, float))
        assert isinstance(data["position_count"], int)

    def test_positions_list_format(self, client):
        """Test that positions list has correct format."""
        response = client.get("/api/positions/")
        data = response.json()
        
        assert isinstance(data["positions"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["positions"])

