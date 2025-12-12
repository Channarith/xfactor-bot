"""Tests for risk management."""

import pytest
from src.risk.risk_manager import RiskManager, RiskCheckResult
from src.risk.position_sizer import PositionSizer


class TestRiskManager:
    """Tests for Risk Manager."""
    
    @pytest.fixture
    def risk_manager(self):
        rm = RiskManager()
        rm.update_portfolio_value(1000000)
        return rm
    
    def test_initialization(self, risk_manager):
        assert risk_manager.is_trading_allowed
        assert not risk_manager._paused
        assert not risk_manager._killed
    
    def test_check_order_approved(self, risk_manager):
        decision = risk_manager.check_order(
            symbol="AAPL",
            quantity=100,
            price=150,
            side="BUY",
        )
        
        assert decision.result == RiskCheckResult.APPROVED
        assert decision.approved_quantity == 100
    
    def test_check_order_exceeds_max_position(self, risk_manager):
        decision = risk_manager.check_order(
            symbol="AAPL",
            quantity=1000,
            price=150,
            side="BUY",
        )
        
        # 1000 * 150 = $150,000 > $50,000 max
        assert decision.result == RiskCheckResult.REDUCED
        assert decision.approved_quantity < 1000
    
    def test_check_order_when_paused(self, risk_manager):
        risk_manager._paused = True
        
        decision = risk_manager.check_order(
            symbol="AAPL",
            quantity=100,
            price=150,
            side="BUY",
        )
        
        assert decision.result == RiskCheckResult.REJECTED
    
    def test_vix_reduction(self, risk_manager):
        risk_manager.update_vix(40)  # Above pause threshold of 35
        
        decision = risk_manager.check_order(
            symbol="AAPL",
            quantity=100,
            price=150,
            side="BUY",
        )
        
        assert decision.result == RiskCheckResult.REDUCED
        assert decision.approved_quantity == 50  # 50% reduction
    
    def test_vix_extreme_rejection(self, risk_manager):
        risk_manager.update_vix(55)  # Above extreme threshold of 50
        
        decision = risk_manager.check_order(
            symbol="AAPL",
            quantity=100,
            price=150,
            side="BUY",
        )
        
        assert decision.result == RiskCheckResult.REJECTED
    
    def test_daily_loss_limit(self, risk_manager):
        # Simulate 4% daily loss (above 3% limit)
        risk_manager.update_pnl(-40000, -40000, -40000)
        
        assert risk_manager._paused
    
    def test_resume_trading(self, risk_manager):
        risk_manager._paused = True
        
        result = risk_manager.resume_trading()
        
        assert result
        assert not risk_manager._paused
    
    def test_cannot_resume_after_kill(self, risk_manager):
        risk_manager._killed = True
        
        result = risk_manager.resume_trading()
        
        assert not result
        assert risk_manager._killed


class TestPositionSizer:
    """Tests for Position Sizer."""
    
    @pytest.fixture
    def sizer(self):
        return PositionSizer()
    
    def test_fixed_fractional(self, sizer):
        result = sizer.calculate_fixed_fractional(
            portfolio_value=100000,
            entry_price=100,
            stop_loss=95,
            risk_per_trade=0.02,
        )
        
        # Risk $2000 (2%), risk per share = $5, shares = 400
        assert result.shares == 400
        assert result.method == "fixed_fractional"
    
    def test_fixed_fractional_capped_by_max(self, sizer):
        result = sizer.calculate_fixed_fractional(
            portfolio_value=10000000,
            entry_price=10,
            stop_loss=9,
            risk_per_trade=0.02,
        )
        
        # Would be 200,000 shares but capped by max position
        assert result.shares <= 50000 / 10  # $50k max / $10 price
    
    def test_equal_weight(self, sizer):
        result = sizer.calculate_equal_weight(
            portfolio_value=100000,
            entry_price=100,
            num_positions=10,
        )
        
        # $10,000 per position
        assert result.shares == 100
        assert result.method == "equal_weight"
    
    def test_signal_weighted(self, sizer):
        result = sizer.calculate_signal_weighted(
            portfolio_value=100000,
            entry_price=100,
            stop_loss=95,
            signal_strength=0.5,
            base_risk_per_trade=0.02,
        )
        
        # Half the normal size due to 0.5 signal strength
        assert result.shares == 200  # Half of 400

