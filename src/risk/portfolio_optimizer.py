"""
Portfolio Optimizer for optimal capital allocation.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class PortfolioAllocation:
    """Optimal portfolio allocation."""
    weights: dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    method: str


class PortfolioOptimizer:
    """
    Optimize portfolio allocation using various methods.
    
    Methods:
    - Equal weight
    - Risk parity
    - Mean-variance optimization
    - Maximum Sharpe ratio
    """
    
    def __init__(self):
        """Initialize portfolio optimizer."""
        self.risk_free_rate = 0.05  # 5% risk-free rate
        self.min_weight = 0.0
        self.max_weight = 0.25  # Max 25% in single position
    
    def equal_weight(self, symbols: list[str]) -> PortfolioAllocation:
        """
        Calculate equal-weight allocation.
        
        Args:
            symbols: List of symbols
            
        Returns:
            PortfolioAllocation
        """
        n = len(symbols)
        if n == 0:
            return PortfolioAllocation({}, 0, 0, 0, "equal_weight")
        
        weight = 1.0 / n
        weights = {s: weight for s in symbols}
        
        return PortfolioAllocation(
            weights=weights,
            expected_return=0,
            expected_volatility=0,
            sharpe_ratio=0,
            method="equal_weight",
        )
    
    def risk_parity(
        self,
        symbols: list[str],
        volatilities: dict[str, float],
    ) -> PortfolioAllocation:
        """
        Calculate risk parity allocation (equal risk contribution).
        
        Args:
            symbols: List of symbols
            volatilities: Symbol -> annualized volatility
            
        Returns:
            PortfolioAllocation
        """
        if not symbols or not volatilities:
            return PortfolioAllocation({}, 0, 0, 0, "risk_parity")
        
        # Inverse volatility weighting
        inv_vols = {s: 1.0 / max(volatilities.get(s, 0.2), 0.01) for s in symbols}
        total_inv_vol = sum(inv_vols.values())
        
        weights = {s: inv_vols[s] / total_inv_vol for s in symbols}
        
        # Apply weight constraints
        weights = self._apply_constraints(weights)
        
        # Calculate portfolio volatility
        avg_vol = sum(volatilities.get(s, 0.2) * w for s, w in weights.items())
        
        return PortfolioAllocation(
            weights=weights,
            expected_return=0,
            expected_volatility=avg_vol,
            sharpe_ratio=0,
            method="risk_parity",
        )
    
    def mean_variance(
        self,
        returns: pd.DataFrame,
        target_return: float = None,
    ) -> PortfolioAllocation:
        """
        Mean-variance optimization.
        
        Args:
            returns: DataFrame with daily returns (columns = symbols)
            target_return: Target annual return (optional)
            
        Returns:
            PortfolioAllocation
        """
        if returns.empty:
            return PortfolioAllocation({}, 0, 0, 0, "mean_variance")
        
        symbols = returns.columns.tolist()
        n = len(symbols)
        
        # Calculate expected returns and covariance
        mean_returns = returns.mean() * 252  # Annualized
        cov_matrix = returns.cov() * 252  # Annualized
        
        if target_return is None:
            # Maximize Sharpe ratio
            return self._max_sharpe(symbols, mean_returns, cov_matrix)
        else:
            # Target return optimization
            return self._target_return_opt(symbols, mean_returns, cov_matrix, target_return)
    
    def _max_sharpe(
        self,
        symbols: list[str],
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
    ) -> PortfolioAllocation:
        """Find maximum Sharpe ratio portfolio."""
        try:
            from scipy.optimize import minimize
            
            n = len(symbols)
            
            def neg_sharpe(weights):
                port_return = np.dot(weights, mean_returns)
                port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                return -(port_return - self.risk_free_rate) / port_vol
            
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # Weights sum to 1
            ]
            
            bounds = [(self.min_weight, self.max_weight) for _ in range(n)]
            
            initial = np.array([1.0/n] * n)
            
            result = minimize(
                neg_sharpe,
                initial,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
            )
            
            if result.success:
                weights = dict(zip(symbols, result.x))
                weights = self._apply_constraints(weights)
                
                w = np.array(list(weights.values()))
                port_return = np.dot(w, mean_returns)
                port_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
                sharpe = (port_return - self.risk_free_rate) / port_vol
                
                return PortfolioAllocation(
                    weights=weights,
                    expected_return=port_return,
                    expected_volatility=port_vol,
                    sharpe_ratio=sharpe,
                    method="max_sharpe",
                )
            
        except ImportError:
            logger.warning("scipy not available, falling back to equal weight")
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
        
        return self.equal_weight(symbols)
    
    def _target_return_opt(
        self,
        symbols: list[str],
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        target_return: float,
    ) -> PortfolioAllocation:
        """Find minimum variance portfolio for target return."""
        try:
            from scipy.optimize import minimize
            
            n = len(symbols)
            
            def portfolio_vol(weights):
                return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'eq', 'fun': lambda x: np.dot(x, mean_returns) - target_return},
            ]
            
            bounds = [(self.min_weight, self.max_weight) for _ in range(n)]
            initial = np.array([1.0/n] * n)
            
            result = minimize(
                portfolio_vol,
                initial,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
            )
            
            if result.success:
                weights = dict(zip(symbols, result.x))
                weights = self._apply_constraints(weights)
                
                w = np.array(list(weights.values()))
                port_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
                sharpe = (target_return - self.risk_free_rate) / port_vol
                
                return PortfolioAllocation(
                    weights=weights,
                    expected_return=target_return,
                    expected_volatility=port_vol,
                    sharpe_ratio=sharpe,
                    method="target_return",
                )
                
        except Exception as e:
            logger.error(f"Target return optimization failed: {e}")
        
        return self.equal_weight(symbols)
    
    def _apply_constraints(self, weights: dict[str, float]) -> dict[str, float]:
        """Apply min/max weight constraints and renormalize."""
        # Apply constraints
        constrained = {}
        for symbol, weight in weights.items():
            constrained[symbol] = max(self.min_weight, min(self.max_weight, weight))
        
        # Renormalize
        total = sum(constrained.values())
        if total > 0:
            constrained = {s: w / total for s, w in constrained.items()}
        
        return constrained

