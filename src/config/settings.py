"""
Application settings using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # =========================================================================
    # IBKR Configuration
    # =========================================================================
    ibkr_host: str = Field(default="127.0.0.1", description="IBKR TWS/Gateway host")
    ibkr_port: int = Field(default=7497, description="IBKR port (7497=TWS paper, 4002=Gateway paper)")
    ibkr_client_id: int = Field(default=1, description="IBKR client ID")
    ibkr_account: str = Field(default="", description="IBKR account ID")
    ibkr_username: str = Field(default="newtrader925", description="IBKR username")
    
    # =========================================================================
    # Database Configuration
    # =========================================================================
    timescale_host: str = Field(default="localhost")
    timescale_port: int = Field(default=5432)
    timescale_db: str = Field(default="trading_bot")
    timescale_user: str = Field(default="postgres")
    timescale_password: str = Field(default="")
    timescale_url: str = Field(default="")
    
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # =========================================================================
    # News API Keys
    # =========================================================================
    benzinga_api_key: str = Field(default="")
    newsapi_api_key: str = Field(default="")
    finnhub_api_key: str = Field(default="")
    alpha_vantage_api_key: str = Field(default="")
    polygon_api_key: str = Field(default="")
    iex_cloud_api_key: str = Field(default="")
    tiingo_api_key: str = Field(default="")
    
    # =========================================================================
    # Social Media API Keys
    # =========================================================================
    reddit_client_id: str = Field(default="")
    reddit_client_secret: str = Field(default="")
    reddit_user_agent: str = Field(default="TradingBot/1.0")
    
    twitter_bearer_token: str = Field(default="")
    
    stocktwits_access_token: str = Field(default="")
    
    # =========================================================================
    # AI/ML API Keys
    # =========================================================================
    openai_api_key: str = Field(default="")
    
    # =========================================================================
    # Trading Configuration
    # =========================================================================
    trading_mode: Literal["paper", "live"] = Field(default="paper")
    max_position_size: float = Field(default=50000.0)
    max_portfolio_pct: float = Field(default=5.0)
    daily_loss_limit_pct: float = Field(default=3.0)
    weekly_loss_limit_pct: float = Field(default=7.0)
    max_drawdown_pct: float = Field(default=10.0)
    vix_pause_threshold: float = Field(default=35.0)
    max_open_positions: int = Field(default=50)
    
    # =========================================================================
    # Strategy Configuration
    # =========================================================================
    technical_strategy_weight: int = Field(default=60, ge=0, le=100)
    momentum_strategy_weight: int = Field(default=50, ge=0, le=100)
    news_sentiment_weight: int = Field(default=40, ge=0, le=100)
    
    # Technical Strategy Parameters
    rsi_oversold: int = Field(default=30, ge=10, le=40)
    rsi_overbought: int = Field(default=70, ge=60, le=90)
    ma_fast_period: int = Field(default=10, ge=5, le=50)
    ma_slow_period: int = Field(default=50, ge=20, le=200)
    macd_fast: int = Field(default=12)
    macd_slow: int = Field(default=26)
    macd_signal: int = Field(default=9)
    
    # News Sentiment Parameters
    news_min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    news_min_urgency: float = Field(default=0.5, ge=0.0, le=1.0)
    news_sentiment_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    llm_analysis_enabled: bool = Field(default=True)
    
    # =========================================================================
    # Monitoring & Alerting
    # =========================================================================
    slack_webhook_url: str = Field(default="")
    
    # =========================================================================
    # Application
    # =========================================================================
    log_level: str = Field(default="INFO")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    environment: Literal["development", "staging", "production"] = Field(default="development")
    
    @field_validator("trading_mode")
    @classmethod
    def validate_trading_mode(cls, v: str) -> str:
        """Ensure trading mode is always lowercase."""
        return v.lower()
    
    @property
    def database_url(self) -> str:
        """Construct database URL if not provided."""
        if self.timescale_url:
            return self.timescale_url
        return (
            f"postgresql://{self.timescale_user}:{self.timescale_password}"
            f"@{self.timescale_host}:{self.timescale_port}/{self.timescale_db}"
        )
    
    @property
    def is_paper_trading(self) -> bool:
        """Check if running in paper trading mode."""
        return self.trading_mode == "paper"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

