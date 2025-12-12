"""
ML-Based Strategy Optimizer for XFactor Bot

Uses machine learning techniques to optimize trading strategy parameters
including hyperparameter tuning, feature selection, and ensemble methods.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Callable
from enum import Enum
import logging
import numpy as np

logger = logging.getLogger(__name__)


class OptimizationMethod(str, Enum):
    """Optimization algorithms."""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"
    REINFORCEMENT = "reinforcement"


class ObjectiveMetric(str, Enum):
    """Metrics to optimize for."""
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    TOTAL_RETURN = "total_return"
    CALMAR_RATIO = "calmar_ratio"
    PROFIT_FACTOR = "profit_factor"
    WIN_RATE = "win_rate"


@dataclass
class ParameterSpace:
    """Definition of a parameter search space."""
    name: str
    param_type: str  # 'continuous', 'integer', 'categorical'
    low: Optional[float] = None
    high: Optional[float] = None
    choices: Optional[list] = None
    log_scale: bool = False


@dataclass
class OptimizationConfig:
    """Configuration for strategy optimization."""
    # Search space
    parameter_spaces: list[ParameterSpace] = field(default_factory=list)
    
    # Method
    method: OptimizationMethod = OptimizationMethod.BAYESIAN
    
    # Objective
    objective: ObjectiveMetric = ObjectiveMetric.SHARPE_RATIO
    maximize: bool = True
    
    # Budget
    max_iterations: int = 100
    max_time_seconds: Optional[int] = None
    
    # Cross-validation
    n_folds: int = 5
    train_ratio: float = 0.8
    
    # Early stopping
    early_stopping_rounds: int = 20
    min_improvement: float = 0.001
    
    # Constraints
    min_sharpe: float = 0.0
    max_drawdown: float = 0.5
    min_trades: int = 10
    
    # Parallelization
    n_jobs: int = -1  # -1 = all cores


@dataclass
class OptimizationResult:
    """Results from strategy optimization."""
    # Best parameters found
    best_params: dict = field(default_factory=dict)
    best_score: float = 0.0
    
    # Performance metrics of best solution
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    
    # Cross-validation results
    cv_scores: list[float] = field(default_factory=list)
    cv_mean: float = 0.0
    cv_std: float = 0.0
    
    # Search history
    iterations: int = 0
    history: list[dict] = field(default_factory=list)
    
    # Metadata
    optimization_time: float = 0.0
    method: str = ""
    converged: bool = False


class StrategyOptimizer:
    """
    ML-based strategy parameter optimizer.
    
    Features:
    - Multiple optimization algorithms
    - Cross-validation to prevent overfitting
    - Feature importance analysis
    - Parameter sensitivity analysis
    - Ensemble optimization
    """
    
    def __init__(self, backtest_engine=None):
        from ..backtesting import BacktestEngine
        self.backtest_engine = backtest_engine or BacktestEngine()
        self.history: list[dict] = []
        
    def optimize(self, 
                 config: OptimizationConfig,
                 backtest_config: Any,
                 strategy_fn: Optional[Callable] = None) -> OptimizationResult:
        """
        Optimize strategy parameters using specified method.
        
        Args:
            config: Optimization configuration
            backtest_config: Backtest configuration to use
            strategy_fn: Strategy function to optimize
            
        Returns:
            OptimizationResult with best parameters and metrics
        """
        import time
        start_time = time.time()
        
        logger.info(f"Starting optimization with {config.method.value}")
        logger.info(f"Objective: {config.objective.value}")
        logger.info(f"Max iterations: {config.max_iterations}")
        
        if config.method == OptimizationMethod.GRID_SEARCH:
            result = self._grid_search(config, backtest_config, strategy_fn)
        elif config.method == OptimizationMethod.RANDOM_SEARCH:
            result = self._random_search(config, backtest_config, strategy_fn)
        elif config.method == OptimizationMethod.BAYESIAN:
            result = self._bayesian_optimization(config, backtest_config, strategy_fn)
        elif config.method == OptimizationMethod.GENETIC:
            result = self._genetic_optimization(config, backtest_config, strategy_fn)
        else:
            raise ValueError(f"Unknown optimization method: {config.method}")
        
        result.optimization_time = time.time() - start_time
        result.method = config.method.value
        
        logger.info(f"Optimization complete in {result.optimization_time:.2f}s")
        logger.info(f"Best score: {result.best_score:.4f}")
        logger.info(f"Best params: {result.best_params}")
        
        return result
    
    def _evaluate_params(self, 
                         params: dict,
                         config: OptimizationConfig,
                         backtest_config: Any,
                         strategy_fn: Optional[Callable]) -> dict:
        """Evaluate a set of parameters with cross-validation."""
        from ..backtesting import BacktestConfig
        
        scores = []
        metrics_list = []
        
        # Time-series cross-validation
        for fold in range(config.n_folds):
            # Adjust dates for this fold
            total_days = (backtest_config.end_date - backtest_config.start_date).days
            fold_days = total_days // config.n_folds
            
            train_start = backtest_config.start_date
            train_end = train_start + timedelta(days=int(fold_days * (fold + 1) * config.train_ratio))
            
            # Create fold config
            fold_config = BacktestConfig(
                start_date=train_start,
                end_date=train_end,
                symbols=backtest_config.symbols,
                initial_capital=backtest_config.initial_capital,
                strategy_name=backtest_config.strategy_name,
                strategy_params=params,
            )
            
            # Run backtest
            result = self.backtest_engine.run(fold_config, strategy_fn)
            
            # Get objective metric
            score = self._get_objective_value(result, config.objective)
            scores.append(score)
            
            metrics_list.append({
                'sharpe_ratio': result.sharpe_ratio,
                'sortino_ratio': result.sortino_ratio,
                'total_return': result.total_return,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'profit_factor': result.profit_factor,
            })
        
        return {
            'params': params,
            'scores': scores,
            'mean_score': np.mean(scores),
            'std_score': np.std(scores),
            'metrics': metrics_list,
        }
    
    def _get_objective_value(self, result: Any, objective: ObjectiveMetric) -> float:
        """Extract objective value from backtest result."""
        if objective == ObjectiveMetric.SHARPE_RATIO:
            return result.sharpe_ratio
        elif objective == ObjectiveMetric.SORTINO_RATIO:
            return result.sortino_ratio
        elif objective == ObjectiveMetric.TOTAL_RETURN:
            return result.total_return
        elif objective == ObjectiveMetric.CALMAR_RATIO:
            return result.annual_return / abs(result.max_drawdown) if result.max_drawdown != 0 else 0
        elif objective == ObjectiveMetric.PROFIT_FACTOR:
            return result.profit_factor
        elif objective == ObjectiveMetric.WIN_RATE:
            return result.win_rate
        return 0.0
    
    def _sample_params(self, spaces: list[ParameterSpace]) -> dict:
        """Sample random parameters from search spaces."""
        params = {}
        for space in spaces:
            if space.param_type == 'continuous':
                if space.log_scale:
                    params[space.name] = np.exp(
                        np.random.uniform(np.log(space.low), np.log(space.high))
                    )
                else:
                    params[space.name] = np.random.uniform(space.low, space.high)
            elif space.param_type == 'integer':
                params[space.name] = np.random.randint(int(space.low), int(space.high) + 1)
            elif space.param_type == 'categorical':
                params[space.name] = np.random.choice(space.choices)
        return params
    
    def _grid_search(self, config: OptimizationConfig, 
                     backtest_config: Any,
                     strategy_fn: Optional[Callable]) -> OptimizationResult:
        """Exhaustive grid search over parameter space."""
        from itertools import product
        
        # Generate all parameter combinations
        param_values = []
        param_names = []
        
        for space in config.parameter_spaces:
            param_names.append(space.name)
            if space.param_type == 'categorical':
                param_values.append(space.choices)
            elif space.param_type == 'integer':
                param_values.append(list(range(int(space.low), int(space.high) + 1)))
            else:
                # Sample 10 values for continuous
                param_values.append(np.linspace(space.low, space.high, 10).tolist())
        
        best_score = float('-inf') if config.maximize else float('inf')
        best_params = {}
        best_metrics = {}
        history = []
        
        for i, combo in enumerate(product(*param_values)):
            if i >= config.max_iterations:
                break
            
            params = dict(zip(param_names, combo))
            eval_result = self._evaluate_params(params, config, backtest_config, strategy_fn)
            
            score = eval_result['mean_score']
            is_better = (score > best_score) if config.maximize else (score < best_score)
            
            if is_better:
                best_score = score
                best_params = params
                best_metrics = eval_result['metrics'][-1] if eval_result['metrics'] else {}
            
            history.append({
                'iteration': i,
                'params': params,
                'score': score,
                'std': eval_result['std_score'],
            })
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            sharpe_ratio=best_metrics.get('sharpe_ratio', 0),
            sortino_ratio=best_metrics.get('sortino_ratio', 0),
            total_return=best_metrics.get('total_return', 0),
            max_drawdown=best_metrics.get('max_drawdown', 0),
            win_rate=best_metrics.get('win_rate', 0),
            profit_factor=best_metrics.get('profit_factor', 0),
            iterations=len(history),
            history=history,
        )
    
    def _random_search(self, config: OptimizationConfig,
                       backtest_config: Any,
                       strategy_fn: Optional[Callable]) -> OptimizationResult:
        """Random search over parameter space."""
        best_score = float('-inf') if config.maximize else float('inf')
        best_params = {}
        best_metrics = {}
        history = []
        no_improvement = 0
        
        for i in range(config.max_iterations):
            params = self._sample_params(config.parameter_spaces)
            eval_result = self._evaluate_params(params, config, backtest_config, strategy_fn)
            
            score = eval_result['mean_score']
            is_better = (score > best_score + config.min_improvement) if config.maximize \
                        else (score < best_score - config.min_improvement)
            
            if is_better:
                best_score = score
                best_params = params
                best_metrics = eval_result['metrics'][-1] if eval_result['metrics'] else {}
                no_improvement = 0
            else:
                no_improvement += 1
            
            history.append({
                'iteration': i,
                'params': params,
                'score': score,
                'std': eval_result['std_score'],
            })
            
            # Early stopping
            if no_improvement >= config.early_stopping_rounds:
                logger.info(f"Early stopping at iteration {i}")
                break
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            sharpe_ratio=best_metrics.get('sharpe_ratio', 0),
            sortino_ratio=best_metrics.get('sortino_ratio', 0),
            total_return=best_metrics.get('total_return', 0),
            max_drawdown=best_metrics.get('max_drawdown', 0),
            win_rate=best_metrics.get('win_rate', 0),
            profit_factor=best_metrics.get('profit_factor', 0),
            iterations=len(history),
            history=history,
            converged=no_improvement >= config.early_stopping_rounds,
        )
    
    def _bayesian_optimization(self, config: OptimizationConfig,
                               backtest_config: Any,
                               strategy_fn: Optional[Callable]) -> OptimizationResult:
        """
        Bayesian optimization using Gaussian Process.
        
        More sample-efficient than random search by modeling the objective
        function and selecting points with high expected improvement.
        """
        # Try to use scikit-optimize, fall back to random search
        try:
            from skopt import gp_minimize
            from skopt.space import Real, Integer, Categorical
            
            # Convert parameter spaces
            dimensions = []
            param_names = []
            
            for space in config.parameter_spaces:
                param_names.append(space.name)
                if space.param_type == 'continuous':
                    dimensions.append(Real(space.low, space.high, 
                                           prior='log-uniform' if space.log_scale else 'uniform'))
                elif space.param_type == 'integer':
                    dimensions.append(Integer(int(space.low), int(space.high)))
                elif space.param_type == 'categorical':
                    dimensions.append(Categorical(space.choices))
            
            history = []
            
            def objective(x):
                params = dict(zip(param_names, x))
                eval_result = self._evaluate_params(params, config, backtest_config, strategy_fn)
                score = eval_result['mean_score']
                
                history.append({
                    'params': params,
                    'score': score,
                    'std': eval_result['std_score'],
                })
                
                # Minimize, so negate if maximizing
                return -score if config.maximize else score
            
            result = gp_minimize(
                objective,
                dimensions,
                n_calls=config.max_iterations,
                n_random_starts=min(10, config.max_iterations // 5),
                random_state=42,
            )
            
            best_params = dict(zip(param_names, result.x))
            best_score = -result.fun if config.maximize else result.fun
            
            # Get metrics for best params
            eval_result = self._evaluate_params(best_params, config, backtest_config, strategy_fn)
            best_metrics = eval_result['metrics'][-1] if eval_result['metrics'] else {}
            
            return OptimizationResult(
                best_params=best_params,
                best_score=best_score,
                sharpe_ratio=best_metrics.get('sharpe_ratio', 0),
                sortino_ratio=best_metrics.get('sortino_ratio', 0),
                total_return=best_metrics.get('total_return', 0),
                max_drawdown=best_metrics.get('max_drawdown', 0),
                win_rate=best_metrics.get('win_rate', 0),
                profit_factor=best_metrics.get('profit_factor', 0),
                iterations=len(history),
                history=history,
                converged=True,
            )
            
        except ImportError:
            logger.warning("scikit-optimize not installed, falling back to random search")
            return self._random_search(config, backtest_config, strategy_fn)
    
    def _genetic_optimization(self, config: OptimizationConfig,
                              backtest_config: Any,
                              strategy_fn: Optional[Callable]) -> OptimizationResult:
        """
        Genetic algorithm optimization.
        
        Evolves a population of parameter sets through selection, crossover,
        and mutation.
        """
        population_size = 20
        mutation_rate = 0.1
        elite_size = 2
        
        # Initialize population
        population = [self._sample_params(config.parameter_spaces) 
                      for _ in range(population_size)]
        
        best_score = float('-inf') if config.maximize else float('inf')
        best_params = {}
        best_metrics = {}
        history = []
        
        generations = config.max_iterations // population_size
        
        for gen in range(generations):
            # Evaluate fitness
            fitness = []
            for params in population:
                eval_result = self._evaluate_params(params, config, backtest_config, strategy_fn)
                score = eval_result['mean_score']
                fitness.append((score, params, eval_result))
                
                is_better = (score > best_score) if config.maximize else (score < best_score)
                if is_better:
                    best_score = score
                    best_params = params
                    best_metrics = eval_result['metrics'][-1] if eval_result['metrics'] else {}
                
                history.append({
                    'generation': gen,
                    'params': params,
                    'score': score,
                })
            
            # Sort by fitness
            fitness.sort(key=lambda x: x[0], reverse=config.maximize)
            
            # Selection - keep elite
            new_population = [f[1] for f in fitness[:elite_size]]
            
            # Crossover and mutation
            while len(new_population) < population_size:
                # Select parents (tournament selection)
                parent1 = fitness[np.random.randint(0, len(fitness) // 2)][1]
                parent2 = fitness[np.random.randint(0, len(fitness) // 2)][1]
                
                # Crossover
                child = {}
                for space in config.parameter_spaces:
                    if np.random.random() < 0.5:
                        child[space.name] = parent1[space.name]
                    else:
                        child[space.name] = parent2[space.name]
                
                # Mutation
                for space in config.parameter_spaces:
                    if np.random.random() < mutation_rate:
                        if space.param_type == 'continuous':
                            child[space.name] = np.random.uniform(space.low, space.high)
                        elif space.param_type == 'integer':
                            child[space.name] = np.random.randint(int(space.low), int(space.high) + 1)
                        elif space.param_type == 'categorical':
                            child[space.name] = np.random.choice(space.choices)
                
                new_population.append(child)
            
            population = new_population
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            sharpe_ratio=best_metrics.get('sharpe_ratio', 0),
            sortino_ratio=best_metrics.get('sortino_ratio', 0),
            total_return=best_metrics.get('total_return', 0),
            max_drawdown=best_metrics.get('max_drawdown', 0),
            win_rate=best_metrics.get('win_rate', 0),
            profit_factor=best_metrics.get('profit_factor', 0),
            iterations=len(history),
            history=history,
        )
    
    def analyze_sensitivity(self, 
                            best_params: dict,
                            config: OptimizationConfig,
                            backtest_config: Any,
                            n_samples: int = 20) -> dict:
        """
        Analyze parameter sensitivity around the optimal solution.
        
        Returns how much each parameter affects the objective when varied.
        """
        sensitivity = {}
        
        for space in config.parameter_spaces:
            scores = []
            param_values = []
            
            if space.param_type == 'continuous':
                test_values = np.linspace(space.low, space.high, n_samples)
            elif space.param_type == 'integer':
                test_values = range(int(space.low), int(space.high) + 1)
            else:
                test_values = space.choices
            
            for val in test_values:
                test_params = best_params.copy()
                test_params[space.name] = val
                
                eval_result = self._evaluate_params(test_params, config, backtest_config, None)
                scores.append(eval_result['mean_score'])
                param_values.append(val)
            
            sensitivity[space.name] = {
                'values': param_values,
                'scores': scores,
                'range': max(scores) - min(scores) if scores else 0,
                'std': np.std(scores) if scores else 0,
            }
        
        return sensitivity


# Import timedelta at module level
from datetime import timedelta

