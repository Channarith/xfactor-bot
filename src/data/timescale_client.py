"""
TimescaleDB client for time-series data storage.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Any

import asyncpg
from loguru import logger

from src.config.settings import get_settings


class TimescaleClient:
    """
    TimescaleDB client for storing and querying time-series data.
    
    Handles:
    - Market data (ticks, bars)
    - News articles and sentiment
    - Trade history and audit trail
    - Portfolio snapshots
    """
    
    def __init__(self):
        """Initialize TimescaleDB client."""
        self.settings = get_settings()
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> bool:
        """Create connection pool to TimescaleDB."""
        try:
            self._pool = await asyncpg.create_pool(
                self.settings.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
            )
            logger.info("Connected to TimescaleDB")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to TimescaleDB: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Disconnected from TimescaleDB")
    
    async def initialize_schema(self) -> None:
        """Create tables and hypertables if they don't exist."""
        if not self._pool:
            raise RuntimeError("Not connected to database")
        
        async with self._pool.acquire() as conn:
            # Market data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    time        TIMESTAMPTZ NOT NULL,
                    symbol      TEXT NOT NULL,
                    bid         DECIMAL(18,6),
                    ask         DECIMAL(18,6),
                    last        DECIMAL(18,6),
                    volume      BIGINT,
                    exchange    TEXT
                );
            """)
            
            # OHLCV bars table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_bars (
                    time        TIMESTAMPTZ NOT NULL,
                    symbol      TEXT NOT NULL,
                    timeframe   TEXT NOT NULL,
                    open        DECIMAL(18,6),
                    high        DECIMAL(18,6),
                    low         DECIMAL(18,6),
                    close       DECIMAL(18,6),
                    volume      BIGINT
                );
            """)
            
            # News articles table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS news_articles (
                    time            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    article_id      TEXT NOT NULL,
                    source          TEXT NOT NULL,
                    headline        TEXT NOT NULL,
                    summary         TEXT,
                    url             TEXT,
                    raw_sentiment   DECIMAL(4,3),
                    llm_sentiment   DECIMAL(4,3),
                    urgency         DECIMAL(4,3),
                    confidence      DECIMAL(4,3),
                    is_breaking     BOOLEAN DEFAULT FALSE,
                    processed       BOOLEAN DEFAULT FALSE,
                    UNIQUE(article_id)
                );
            """)
            
            # News-ticker impact table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS news_ticker_impact (
                    time            TIMESTAMPTZ NOT NULL,
                    article_id      TEXT NOT NULL,
                    symbol          TEXT NOT NULL,
                    impact_type     TEXT NOT NULL,
                    sentiment_score DECIMAL(4,3),
                    expected_impact DECIMAL(6,2),
                    signal          TEXT,
                    acted_upon      BOOLEAN DEFAULT FALSE,
                    source_file     TEXT
                );
            """)
            
            # Trade audit table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_audit (
                    time            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    order_id        TEXT NOT NULL,
                    symbol          TEXT NOT NULL,
                    side            TEXT NOT NULL,
                    quantity        DECIMAL(18,6),
                    price           DECIMAL(18,6),
                    strategy        TEXT,
                    signal_strength DECIMAL(5,4),
                    risk_score      DECIMAL(5,4),
                    execution_ms    INTEGER,
                    pnl             DECIMAL(18,2)
                );
            """)
            
            # Portfolio snapshots
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    time            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    total_value     DECIMAL(18,2),
                    cash            DECIMAL(18,2),
                    positions_value DECIMAL(18,2),
                    daily_pnl       DECIMAL(18,2),
                    total_pnl       DECIMAL(18,2),
                    position_count  INTEGER
                );
            """)
            
            # Local documents tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS local_documents (
                    time            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    file_name       TEXT NOT NULL,
                    file_type       TEXT NOT NULL,
                    file_size       BIGINT,
                    page_count      INTEGER,
                    chunk_count     INTEGER,
                    processed       BOOLEAN DEFAULT FALSE,
                    error_message   TEXT,
                    processing_ms   INTEGER
                );
            """)
            
            # Create hypertables (only if TimescaleDB extension is available)
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                
                # Convert to hypertables
                for table in ['market_data', 'ohlcv_bars', 'news_articles', 
                              'news_ticker_impact', 'trade_audit', 
                              'portfolio_snapshots', 'local_documents']:
                    try:
                        await conn.execute(f"""
                            SELECT create_hypertable('{table}', 'time', 
                                if_not_exists => TRUE);
                        """)
                    except Exception:
                        pass  # Table might already be a hypertable
                
                logger.info("TimescaleDB schema initialized with hypertables")
            except Exception as e:
                logger.warning(f"TimescaleDB extension not available, using regular tables: {e}")
            
            logger.info("Database schema initialized")
    
    # =========================================================================
    # Market Data Operations
    # =========================================================================
    
    async def insert_market_data(
        self,
        symbol: str,
        bid: float,
        ask: float,
        last: float,
        volume: int,
        exchange: str = "",
        time: datetime = None,
    ) -> None:
        """Insert market data tick."""
        if not self._pool:
            return
        
        if time is None:
            time = datetime.utcnow()
        
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO market_data (time, symbol, bid, ask, last, volume, exchange)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, time, symbol, bid, ask, last, volume, exchange)
    
    async def insert_ohlcv_bar(
        self,
        symbol: str,
        timeframe: str,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        time: datetime = None,
    ) -> None:
        """Insert OHLCV bar."""
        if not self._pool:
            return
        
        if time is None:
            time = datetime.utcnow()
        
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO ohlcv_bars (time, symbol, timeframe, open, high, low, close, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, time, symbol, timeframe, open_price, high, low, close, volume)
    
    async def get_ohlcv_bars(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime = None,
    ) -> list[dict]:
        """Get OHLCV bars for a symbol and timeframe."""
        if not self._pool:
            return []
        
        if end_time is None:
            end_time = datetime.utcnow()
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, open, high, low, close, volume
                FROM ohlcv_bars
                WHERE symbol = $1 AND timeframe = $2 AND time >= $3 AND time <= $4
                ORDER BY time ASC
            """, symbol, timeframe, start_time, end_time)
            
            return [dict(row) for row in rows]
    
    # =========================================================================
    # News Operations
    # =========================================================================
    
    async def insert_news_article(
        self,
        article_id: str,
        source: str,
        headline: str,
        summary: str = "",
        url: str = "",
        raw_sentiment: float = None,
        llm_sentiment: float = None,
        urgency: float = None,
        confidence: float = None,
        is_breaking: bool = False,
    ) -> bool:
        """Insert a news article."""
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO news_articles 
                    (article_id, source, headline, summary, url, 
                     raw_sentiment, llm_sentiment, urgency, confidence, is_breaking)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (article_id) DO UPDATE SET
                        raw_sentiment = COALESCE(EXCLUDED.raw_sentiment, news_articles.raw_sentiment),
                        llm_sentiment = COALESCE(EXCLUDED.llm_sentiment, news_articles.llm_sentiment),
                        processed = TRUE
                """, article_id, source, headline, summary, url,
                     raw_sentiment, llm_sentiment, urgency, confidence, is_breaking)
            return True
        except Exception as e:
            logger.error(f"Failed to insert news article: {e}")
            return False
    
    async def insert_news_ticker_impact(
        self,
        article_id: str,
        symbol: str,
        impact_type: str,
        sentiment_score: float,
        expected_impact: float = None,
        signal: str = None,
        source_file: str = None,
    ) -> None:
        """Insert news impact for a ticker."""
        if not self._pool:
            return
        
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO news_ticker_impact 
                (time, article_id, symbol, impact_type, sentiment_score, 
                 expected_impact, signal, source_file)
                VALUES (NOW(), $1, $2, $3, $4, $5, $6, $7)
            """, article_id, symbol, impact_type, sentiment_score, 
                 expected_impact, signal, source_file)
    
    # =========================================================================
    # Trade Operations
    # =========================================================================
    
    async def insert_trade(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        strategy: str = "",
        signal_strength: float = None,
        risk_score: float = None,
        execution_ms: int = None,
        pnl: float = None,
    ) -> None:
        """Insert a trade record."""
        if not self._pool:
            return
        
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO trade_audit 
                (order_id, symbol, side, quantity, price, strategy,
                 signal_strength, risk_score, execution_ms, pnl)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, order_id, symbol, side, quantity, price, strategy,
                 signal_strength, risk_score, execution_ms, pnl)
    
    async def get_daily_pnl(self, date: datetime = None) -> float:
        """Get daily P&L."""
        if not self._pool:
            return 0.0
        
        if date is None:
            date = datetime.utcnow().date()
        
        async with self._pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT COALESCE(SUM(pnl), 0)
                FROM trade_audit
                WHERE DATE(time) = $1
            """, date)
            return float(result) if result else 0.0
    
    async def insert_portfolio_snapshot(
        self,
        total_value: float,
        cash: float,
        positions_value: float,
        daily_pnl: float,
        total_pnl: float,
        position_count: int,
    ) -> None:
        """Insert a portfolio snapshot."""
        if not self._pool:
            return
        
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO portfolio_snapshots 
                (total_value, cash, positions_value, daily_pnl, total_pnl, position_count)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, total_value, cash, positions_value, daily_pnl, total_pnl, position_count)

