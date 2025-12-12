"""
Prometheus metrics collection.
"""

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from loguru import logger


class MetricsCollector:
    """
    Collect and expose Prometheus metrics.
    """
    
    def __init__(self):
        """Initialize metrics."""
        # Trading metrics
        self.orders_total = Counter(
            'trading_orders_total',
            'Total number of orders',
            ['side', 'status', 'strategy']
        )
        
        self.order_value = Counter(
            'trading_order_value_total',
            'Total order value in USD',
            ['side']
        )
        
        self.positions_count = Gauge(
            'trading_positions_count',
            'Number of open positions'
        )
        
        self.portfolio_value = Gauge(
            'trading_portfolio_value_usd',
            'Total portfolio value in USD'
        )
        
        self.daily_pnl = Gauge(
            'trading_daily_pnl_usd',
            'Daily P&L in USD'
        )
        
        self.unrealized_pnl = Gauge(
            'trading_unrealized_pnl_usd',
            'Unrealized P&L in USD'
        )
        
        self.drawdown_pct = Gauge(
            'trading_drawdown_pct',
            'Current drawdown percentage'
        )
        
        # Latency metrics
        self.order_latency = Histogram(
            'trading_order_latency_seconds',
            'Order execution latency',
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        )
        
        self.data_latency = Histogram(
            'trading_data_latency_seconds',
            'Market data latency',
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25]
        )
        
        # News & sentiment metrics
        self.news_articles_total = Counter(
            'trading_news_articles_total',
            'Total news articles processed',
            ['source']
        )
        
        self.sentiment_score = Gauge(
            'trading_sentiment_score',
            'Current sentiment score',
            ['symbol']
        )
        
        # Strategy metrics
        self.signals_total = Counter(
            'trading_signals_total',
            'Total signals generated',
            ['strategy', 'signal_type']
        )
        
        self.strategy_pnl = Gauge(
            'trading_strategy_pnl_usd',
            'P&L by strategy',
            ['strategy']
        )
        
        # System metrics
        self.ibkr_connected = Gauge(
            'trading_ibkr_connected',
            'IBKR connection status (1=connected, 0=disconnected)'
        )
        
        self.kill_switch_active = Gauge(
            'trading_kill_switch_active',
            'Kill switch status (1=active, 0=inactive)'
        )
        
        self.trading_paused = Gauge(
            'trading_paused',
            'Trading pause status (1=paused, 0=running)'
        )
        
        self.vix_value = Gauge(
            'trading_vix_value',
            'Current VIX value'
        )
        
        # Info
        self.bot_info = Info(
            'trading_bot',
            'Trading bot information'
        )
        self.bot_info.info({
            'version': '0.1.0',
            'mode': 'paper',
        })
        
        logger.info("Metrics collector initialized")
    
    def record_order(
        self,
        side: str,
        status: str,
        strategy: str,
        value: float,
        latency: float = None,
    ) -> None:
        """Record an order."""
        self.orders_total.labels(side=side, status=status, strategy=strategy).inc()
        self.order_value.labels(side=side).inc(value)
        
        if latency:
            self.order_latency.observe(latency)
    
    def record_signal(self, strategy: str, signal_type: str) -> None:
        """Record a strategy signal."""
        self.signals_total.labels(strategy=strategy, signal_type=signal_type).inc()
    
    def record_news(self, source: str) -> None:
        """Record a news article."""
        self.news_articles_total.labels(source=source).inc()
    
    def update_portfolio(
        self,
        value: float,
        positions: int,
        daily_pnl: float,
        unrealized_pnl: float,
        drawdown: float,
    ) -> None:
        """Update portfolio metrics."""
        self.portfolio_value.set(value)
        self.positions_count.set(positions)
        self.daily_pnl.set(daily_pnl)
        self.unrealized_pnl.set(unrealized_pnl)
        self.drawdown_pct.set(drawdown)
    
    def update_connection_status(self, connected: bool) -> None:
        """Update IBKR connection status."""
        self.ibkr_connected.set(1 if connected else 0)
    
    def update_trading_status(self, paused: bool, killed: bool) -> None:
        """Update trading status."""
        self.trading_paused.set(1 if paused else 0)
        self.kill_switch_active.set(1 if killed else 0)
    
    def update_vix(self, value: float) -> None:
        """Update VIX value."""
        self.vix_value.set(value)
    
    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest()
    
    def get_content_type(self) -> str:
        """Get content type for metrics endpoint."""
        return CONTENT_TYPE_LATEST

