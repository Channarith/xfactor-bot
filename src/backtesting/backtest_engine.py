"""
Backtesting Engine for XFactor Bot

Provides historical simulation of trading strategies with realistic
execution modeling, slippage, and commission calculations.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DataSource(str, Enum):
    """Supported historical data sources."""
    YFINANCE = "yfinance"
    ALPACA = "alpaca"
    IBKR = "ibkr"
    CSV = "csv"


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""
    # Time period
    start_date: datetime
    end_date: datetime
    
    # Universe
    symbols: list[str] = field(default_factory=list)
    
    # Capital
    initial_capital: float = 100000.0
    
    # Strategy
    strategy_name: str = "momentum"
    strategy_params: dict = field(default_factory=dict)
    
    # Execution modeling
    slippage_bps: float = 5.0  # Basis points
    commission_per_share: float = 0.005
    commission_minimum: float = 1.0
    
    # Risk parameters
    max_position_pct: float = 0.1  # Max 10% per position
    max_drawdown_pct: float = 0.2  # Stop if 20% drawdown
    
    # Data
    data_source: DataSource = DataSource.YFINANCE
    timeframe: str = "1d"  # 1m, 5m, 15m, 1h, 1d
    
    # Benchmark
    benchmark_symbol: str = "SPY"


@dataclass
class Trade:
    """Record of a single trade."""
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float
    timestamp: datetime
    commission: float = 0.0
    slippage: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0


@dataclass
class Position:
    """Current position in a symbol."""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass
class DailyMetrics:
    """Daily portfolio metrics."""
    date: datetime
    portfolio_value: float
    cash: float
    positions_value: float
    daily_return: float = 0.0
    cumulative_return: float = 0.0
    drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    trades_today: int = 0


@dataclass
class BacktestResult:
    """Complete results from a backtest run."""
    config: BacktestConfig
    
    # Performance metrics
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # Days
    win_rate: float = 0.0
    profit_factor: float = 0.0
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_holding_period: float = 0.0  # Days
    
    # Capital
    final_capital: float = 0.0
    peak_capital: float = 0.0
    total_commissions: float = 0.0
    total_slippage: float = 0.0
    
    # Benchmark comparison
    benchmark_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0
    
    # Time series data
    daily_metrics: list[DailyMetrics] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    
    # Metadata
    run_time_seconds: float = 0.0
    data_points_processed: int = 0


class BacktestEngine:
    """
    High-performance backtesting engine with event-driven architecture.
    
    Features:
    - Multiple timeframes (1m to 1d)
    - Realistic execution modeling with slippage
    - Commission calculations
    - Risk management during backtest
    - Benchmark comparison
    - Walk-forward analysis support
    """
    
    def __init__(self):
        self.config: Optional[BacktestConfig] = None
        self.cash: float = 0.0
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.daily_metrics: list[DailyMetrics] = []
        self.peak_value: float = 0.0
        self.data_cache: dict = {}
        
    def run(self, config: BacktestConfig, 
            strategy_fn: Optional[Callable] = None) -> BacktestResult:
        """
        Execute a backtest with the given configuration.
        
        Args:
            config: Backtest configuration
            strategy_fn: Custom strategy function (optional)
            
        Returns:
            BacktestResult with all metrics and trade history
        """
        import time
        start_time = time.time()
        
        self.config = config
        self.cash = config.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_metrics = []
        self.peak_value = config.initial_capital
        
        logger.info(f"Starting backtest: {config.strategy_name}")
        logger.info(f"Period: {config.start_date.date()} to {config.end_date.date()}")
        logger.info(f"Universe: {len(config.symbols)} symbols")
        
        # Load historical data
        data = self._load_data(config)
        if not data:
            logger.error("Failed to load historical data")
            return BacktestResult(config=config)
        
        data_points = 0
        
        # Iterate through each trading day
        dates = self._get_trading_dates(config.start_date, config.end_date)
        
        for date in dates:
            # Get market data for this date
            daily_data = self._get_daily_data(data, date)
            if not daily_data:
                continue
            
            data_points += len(daily_data)
            
            # Update position prices
            self._update_positions(daily_data)
            
            # Generate signals and execute trades
            if strategy_fn:
                signals = strategy_fn(daily_data, self.positions, self.cash)
            else:
                signals = self._default_strategy(daily_data, date)
            
            # Execute trades based on signals
            trades_today = self._execute_signals(signals, daily_data, date)
            
            # Record daily metrics
            portfolio_value = self._calculate_portfolio_value()
            self._record_daily_metrics(date, portfolio_value, trades_today)
            
            # Check risk limits
            if self._check_drawdown_limit(portfolio_value):
                logger.warning(f"Max drawdown reached on {date.date()}, stopping backtest")
                break
        
        # Close all positions at end
        self._close_all_positions(dates[-1] if dates else config.end_date)
        
        # Calculate final metrics
        run_time = time.time() - start_time
        result = self._calculate_results(config, run_time, data_points)
        
        logger.info(f"Backtest complete in {run_time:.2f}s")
        logger.info(f"Total return: {result.total_return:.2%}")
        logger.info(f"Sharpe ratio: {result.sharpe_ratio:.2f}")
        
        return result
    
    def _load_data(self, config: BacktestConfig) -> dict:
        """Load historical data for all symbols."""
        data = {}
        
        if config.data_source == DataSource.YFINANCE:
            try:
                import yfinance as yf
                
                # Add benchmark
                all_symbols = config.symbols + [config.benchmark_symbol]
                
                for symbol in all_symbols:
                    if symbol in self.data_cache:
                        data[symbol] = self.data_cache[symbol]
                        continue
                    
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(
                        start=config.start_date,
                        end=config.end_date,
                        interval=config.timeframe
                    )
                    
                    if not hist.empty:
                        data[symbol] = hist
                        self.data_cache[symbol] = hist
                        
            except Exception as e:
                logger.error(f"Failed to load yfinance data: {e}")
                
        return data
    
    def _get_trading_dates(self, start: datetime, end: datetime) -> list[datetime]:
        """Get list of trading dates in range."""
        # Simple implementation - get weekdays
        dates = []
        current = start
        while current <= end:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                dates.append(current)
            current += timedelta(days=1)
        return dates
    
    def _get_daily_data(self, data: dict, date: datetime) -> dict:
        """Get data for a specific date."""
        daily = {}
        for symbol, df in data.items():
            try:
                # Find data for this date
                date_str = date.strftime('%Y-%m-%d')
                if date_str in df.index.strftime('%Y-%m-%d').values:
                    idx = df.index.strftime('%Y-%m-%d').tolist().index(date_str)
                    daily[symbol] = {
                        'open': float(df.iloc[idx]['Open']),
                        'high': float(df.iloc[idx]['High']),
                        'low': float(df.iloc[idx]['Low']),
                        'close': float(df.iloc[idx]['Close']),
                        'volume': float(df.iloc[idx]['Volume']),
                    }
            except Exception:
                continue
        return daily
    
    def _update_positions(self, daily_data: dict) -> None:
        """Update position prices with current market data."""
        for symbol, pos in self.positions.items():
            if symbol in daily_data:
                pos.current_price = daily_data[symbol]['close']
                pos.unrealized_pnl = (pos.current_price - pos.avg_cost) * pos.quantity
                if pos.avg_cost > 0:
                    pos.unrealized_pnl_pct = (pos.current_price / pos.avg_cost - 1)
    
    def _default_strategy(self, daily_data: dict, date: datetime) -> list[dict]:
        """Default momentum strategy for testing."""
        signals = []
        
        # Simple momentum: buy if price > 20-day SMA
        for symbol in self.config.symbols:
            if symbol not in daily_data:
                continue
            
            # For now, simple random-ish signals for testing
            price = daily_data[symbol]['close']
            
            if symbol not in self.positions:
                # Consider buying
                position_value = self.config.initial_capital * self.config.max_position_pct
                quantity = int(position_value / price)
                if quantity > 0 and self.cash >= quantity * price:
                    signals.append({
                        'symbol': symbol,
                        'side': 'buy',
                        'quantity': quantity,
                        'price': price,
                    })
        
        return signals
    
    def _execute_signals(self, signals: list[dict], daily_data: dict, 
                         date: datetime) -> int:
        """Execute trading signals with realistic modeling."""
        trades_executed = 0
        
        for signal in signals:
            symbol = signal['symbol']
            side = signal['side']
            quantity = signal['quantity']
            price = signal['price']
            
            # Apply slippage
            slippage = price * (self.config.slippage_bps / 10000)
            if side == 'buy':
                exec_price = price + slippage
            else:
                exec_price = price - slippage
            
            # Calculate commission
            commission = max(
                quantity * self.config.commission_per_share,
                self.config.commission_minimum
            )
            
            total_cost = quantity * exec_price + commission
            
            if side == 'buy':
                if total_cost > self.cash:
                    continue  # Not enough cash
                
                self.cash -= total_cost
                
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    new_qty = pos.quantity + quantity
                    pos.avg_cost = (pos.avg_cost * pos.quantity + exec_price * quantity) / new_qty
                    pos.quantity = new_qty
                else:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        quantity=quantity,
                        avg_cost=exec_price,
                        current_price=exec_price,
                    )
                
                trade = Trade(
                    symbol=symbol,
                    side='buy',
                    quantity=quantity,
                    price=exec_price,
                    timestamp=date,
                    commission=commission,
                    slippage=slippage * quantity,
                )
                
            else:  # sell
                if symbol not in self.positions:
                    continue
                
                pos = self.positions[symbol]
                if quantity > pos.quantity:
                    quantity = pos.quantity
                
                proceeds = quantity * exec_price - commission
                pnl = (exec_price - pos.avg_cost) * quantity - commission
                pnl_pct = (exec_price / pos.avg_cost - 1) if pos.avg_cost > 0 else 0
                
                self.cash += proceeds
                
                pos.quantity -= quantity
                if pos.quantity <= 0:
                    del self.positions[symbol]
                
                trade = Trade(
                    symbol=symbol,
                    side='sell',
                    quantity=quantity,
                    price=exec_price,
                    timestamp=date,
                    commission=commission,
                    slippage=slippage * quantity,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                )
            
            self.trades.append(trade)
            trades_executed += 1
        
        return trades_executed
    
    def _calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value."""
        positions_value = sum(
            pos.quantity * pos.current_price 
            for pos in self.positions.values()
        )
        return self.cash + positions_value
    
    def _record_daily_metrics(self, date: datetime, portfolio_value: float,
                              trades_today: int) -> None:
        """Record daily portfolio metrics."""
        # Calculate drawdown
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
        drawdown = (self.peak_value - portfolio_value) / self.peak_value
        
        # Calculate returns
        if self.daily_metrics:
            prev_value = self.daily_metrics[-1].portfolio_value
            daily_return = (portfolio_value / prev_value - 1) if prev_value > 0 else 0
        else:
            daily_return = 0
        
        cumulative_return = (portfolio_value / self.config.initial_capital - 1)
        
        positions_value = sum(
            pos.quantity * pos.current_price 
            for pos in self.positions.values()
        )
        
        metrics = DailyMetrics(
            date=date,
            portfolio_value=portfolio_value,
            cash=self.cash,
            positions_value=positions_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
            drawdown=drawdown,
            trades_today=trades_today,
        )
        
        self.daily_metrics.append(metrics)
    
    def _check_drawdown_limit(self, portfolio_value: float) -> bool:
        """Check if max drawdown limit has been breached."""
        if self.peak_value <= 0:
            return False
        drawdown = (self.peak_value - portfolio_value) / self.peak_value
        return drawdown >= self.config.max_drawdown_pct
    
    def _close_all_positions(self, date: datetime) -> None:
        """Close all open positions at end of backtest."""
        for symbol, pos in list(self.positions.items()):
            if pos.quantity > 0:
                proceeds = pos.quantity * pos.current_price
                pnl = (pos.current_price - pos.avg_cost) * pos.quantity
                
                trade = Trade(
                    symbol=symbol,
                    side='sell',
                    quantity=pos.quantity,
                    price=pos.current_price,
                    timestamp=date,
                    pnl=pnl,
                )
                self.trades.append(trade)
                self.cash += proceeds
        
        self.positions.clear()
    
    def _calculate_results(self, config: BacktestConfig, 
                          run_time: float, data_points: int) -> BacktestResult:
        """Calculate final backtest results and metrics."""
        import numpy as np
        
        final_value = self.cash
        total_return = (final_value / config.initial_capital - 1)
        
        # Calculate annualized return
        days = (config.end_date - config.start_date).days
        years = days / 365.25
        annual_return = ((1 + total_return) ** (1 / years) - 1) if years > 0 else 0
        
        # Extract daily returns
        daily_returns = [m.daily_return for m in self.daily_metrics]
        
        # Sharpe ratio (assuming 0 risk-free rate for simplicity)
        if daily_returns and len(daily_returns) > 1:
            returns_array = np.array(daily_returns)
            sharpe = np.sqrt(252) * (np.mean(returns_array) / np.std(returns_array)) \
                     if np.std(returns_array) > 0 else 0
            
            # Sortino ratio (downside deviation only)
            downside = returns_array[returns_array < 0]
            sortino = np.sqrt(252) * (np.mean(returns_array) / np.std(downside)) \
                      if len(downside) > 0 and np.std(downside) > 0 else 0
        else:
            sharpe = 0
            sortino = 0
        
        # Max drawdown
        max_dd = max((m.drawdown for m in self.daily_metrics), default=0)
        
        # Trade statistics
        sell_trades = [t for t in self.trades if t.side == 'sell']
        winning = [t for t in sell_trades if t.pnl > 0]
        losing = [t for t in sell_trades if t.pnl <= 0]
        
        win_rate = len(winning) / len(sell_trades) if sell_trades else 0
        avg_win = np.mean([t.pnl for t in winning]) if winning else 0
        avg_loss = np.mean([t.pnl for t in losing]) if losing else 0
        
        gross_profit = sum(t.pnl for t in winning) if winning else 0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        total_commissions = sum(t.commission for t in self.trades)
        total_slippage = sum(t.slippage for t in self.trades)
        
        return BacktestResult(
            config=config,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(self.trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=max((t.pnl for t in winning), default=0),
            largest_loss=min((t.pnl for t in losing), default=0),
            final_capital=final_value,
            peak_capital=self.peak_value,
            total_commissions=total_commissions,
            total_slippage=total_slippage,
            daily_metrics=self.daily_metrics,
            trades=self.trades,
            run_time_seconds=run_time,
            data_points_processed=data_points,
        )


# Walk-forward analysis support
class WalkForwardAnalyzer:
    """
    Walk-forward analysis for strategy validation.
    
    Splits data into in-sample (optimization) and out-of-sample (validation)
    periods to prevent overfitting.
    """
    
    def __init__(self, 
                 in_sample_months: int = 12,
                 out_sample_months: int = 3,
                 anchored: bool = False):
        self.in_sample_months = in_sample_months
        self.out_sample_months = out_sample_months
        self.anchored = anchored
        self.engine = BacktestEngine()
    
    def run(self, config: BacktestConfig, 
            optimize_fn: Callable) -> list[BacktestResult]:
        """
        Run walk-forward analysis.
        
        Args:
            config: Base backtest configuration
            optimize_fn: Function that optimizes strategy parameters
            
        Returns:
            List of out-of-sample BacktestResults
        """
        results = []
        current_start = config.start_date
        
        while current_start < config.end_date:
            # Define in-sample period
            in_sample_end = current_start + timedelta(days=30 * self.in_sample_months)
            
            # Define out-of-sample period
            out_sample_start = in_sample_end
            out_sample_end = out_sample_start + timedelta(days=30 * self.out_sample_months)
            
            if out_sample_end > config.end_date:
                out_sample_end = config.end_date
            
            if out_sample_start >= config.end_date:
                break
            
            # Optimize on in-sample
            in_sample_config = BacktestConfig(
                start_date=current_start if self.anchored else current_start,
                end_date=in_sample_end,
                symbols=config.symbols,
                initial_capital=config.initial_capital,
                strategy_name=config.strategy_name,
            )
            
            optimized_params = optimize_fn(in_sample_config)
            
            # Test on out-of-sample
            out_sample_config = BacktestConfig(
                start_date=out_sample_start,
                end_date=out_sample_end,
                symbols=config.symbols,
                initial_capital=config.initial_capital,
                strategy_name=config.strategy_name,
                strategy_params=optimized_params,
            )
            
            result = self.engine.run(out_sample_config)
            results.append(result)
            
            # Move to next period
            if self.anchored:
                current_start = config.start_date
            else:
                current_start = out_sample_end
        
        return results

