"""
Application settings using Pydantic Settings.
Loads configuration from environment variables and .env file.

XFactor Bot - AI-Powered Automated Trading System
Supports multiple brokers, data sources, and banking integrations.
"""

from functools import lru_cache
from typing import Literal, List

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
    # IBKR Configuration (Primary Broker)
    # =========================================================================
    ibkr_host: str = Field(default="127.0.0.1", description="IBKR TWS/Gateway host")
    ibkr_port: int = Field(default=7497, description="IBKR port (7497=TWS paper, 4002=Gateway paper)")
    ibkr_client_id: int = Field(default=1, description="IBKR client ID")
    ibkr_account: str = Field(default="", description="IBKR account ID")
    ibkr_username: str = Field(default="", description="IBKR username")
    
    # =========================================================================
    # Alpaca Configuration (Commission-Free Trading)
    # =========================================================================
    alpaca_api_key: str = Field(default="", description="Alpaca API key")
    alpaca_secret_key: str = Field(default="", description="Alpaca secret key")
    alpaca_paper: bool = Field(default=True, description="Use Alpaca paper trading")
    
    # =========================================================================
    # Charles Schwab / TD Ameritrade Configuration
    # =========================================================================
    schwab_client_id: str = Field(default="", description="Schwab App Key")
    schwab_client_secret: str = Field(default="", description="Schwab App Secret")
    schwab_refresh_token: str = Field(default="", description="Schwab OAuth refresh token")
    schwab_account_id: str = Field(default="", description="Schwab account number")
    
    # =========================================================================
    # Tradier Configuration (Low-Cost Options)
    # =========================================================================
    tradier_access_token: str = Field(default="", description="Tradier access token")
    tradier_account_id: str = Field(default="", description="Tradier account ID")
    tradier_sandbox: bool = Field(default=True, description="Use Tradier sandbox")
    
    # =========================================================================
    # E*TRADE Configuration
    # =========================================================================
    etrade_consumer_key: str = Field(default="", description="E*TRADE consumer key")
    etrade_consumer_secret: str = Field(default="", description="E*TRADE consumer secret")
    etrade_sandbox: bool = Field(default=True, description="Use E*TRADE sandbox")
    
    # =========================================================================
    # Webull Configuration (Unofficial API)
    # =========================================================================
    webull_email: str = Field(default="", description="Webull email")
    webull_password: str = Field(default="", description="Webull password")
    webull_device_id: str = Field(default="", description="Webull device ID")
    webull_trading_pin: str = Field(default="", description="Webull trading PIN")
    
    # =========================================================================
    # Crypto Exchanges
    # =========================================================================
    coinbase_api_key: str = Field(default="", description="Coinbase API key")
    coinbase_api_secret: str = Field(default="", description="Coinbase API secret")
    
    binance_api_key: str = Field(default="", description="Binance API key")
    binance_api_secret: str = Field(default="", description="Binance API secret")
    
    # =========================================================================
    # Banking - Plaid Integration
    # =========================================================================
    plaid_client_id: str = Field(default="", description="Plaid client ID")
    plaid_secret: str = Field(default="", description="Plaid secret key")
    plaid_environment: str = Field(default="sandbox", description="Plaid environment (sandbox/development/production)")
    
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
    # Market Data Sources
    # =========================================================================
    # TradingView
    tradingview_webhook_secret: str = Field(default="", description="TradingView webhook secret")
    
    # Barchart OnDemand
    barchart_api_key: str = Field(default="", description="Barchart OnDemand API key")
    
    # AInvest AI
    ainvest_api_key: str = Field(default="", description="AInvest AI-powered analysis API key")
    
    # Finviz
    finviz_api_key: str = Field(default="", description="Finviz Elite API key")
    
    # OpenInsider (scraping-based, no API key needed)
    openinsider_enabled: bool = Field(default=True, description="Enable OpenInsider scraping")
    
    # Polygon.io
    polygon_api_key: str = Field(default="", description="Polygon.io API key")
    
    # Alpha Vantage
    alpha_vantage_api_key: str = Field(default="", description="Alpha Vantage API key")
    
    # IEX Cloud
    iex_cloud_api_key: str = Field(default="", description="IEX Cloud API key")
    
    # Tiingo
    tiingo_api_key: str = Field(default="", description="Tiingo API key")
    
    # Quandl/Nasdaq Data Link
    quandl_api_key: str = Field(default="", description="Quandl/Nasdaq Data Link API key")
    
    # Yahoo Finance (no key needed, but can configure)
    yahoo_finance_enabled: bool = Field(default=True, description="Enable Yahoo Finance data")
    
    # Finviz
    finviz_elite_email: str = Field(default="", description="Finviz Elite email (for premium features)")
    finviz_elite_password: str = Field(default="", description="Finviz Elite password")
    
    # OpenInsider (SEC Form 4 filings - no API key needed, web scraping)
    openinsider_enabled: bool = Field(default=True, description="Enable OpenInsider data")
    
    # =========================================================================
    # News API Keys
    # =========================================================================
    benzinga_api_key: str = Field(default="", description="Benzinga news API key")
    newsapi_api_key: str = Field(default="", description="NewsAPI.org API key")
    finnhub_api_key: str = Field(default="", description="Finnhub API key")
    marketaux_api_key: str = Field(default="", description="Marketaux news API key")
    
    # =========================================================================
    # Social Media API Keys
    # =========================================================================
    reddit_client_id: str = Field(default="", description="Reddit app client ID")
    reddit_client_secret: str = Field(default="", description="Reddit app client secret")
    reddit_user_agent: str = Field(default="XFactorBot/1.0", description="Reddit user agent")
    
    twitter_bearer_token: str = Field(default="", description="Twitter/X API bearer token")
    twitter_api_key: str = Field(default="", description="Twitter API key")
    twitter_api_secret: str = Field(default="", description="Twitter API secret")
    
    stocktwits_access_token: str = Field(default="", description="StockTwits access token")
    
    discord_bot_token: str = Field(default="", description="Discord bot token")
    discord_webhook_url: str = Field(default="", description="Discord webhook URL")
    
    telegram_bot_token: str = Field(default="", description="Telegram bot token")
    telegram_chat_id: str = Field(default="", description="Telegram chat ID")
    
    # =========================================================================
    # AI/ML Configuration
    # =========================================================================
    # LLM Provider: "anthropic" (Claude - default), "ollama" (local fallback), "openai"
    # Priority: Anthropic Claude > Ollama (local) > OpenAI
    llm_provider: str = Field(default="anthropic", description="LLM provider to use (anthropic, ollama, openai)")
    llm_fallback_to_ollama: bool = Field(default=True, description="Fallback to Ollama if primary provider fails")
    
    # Anthropic Claude Configuration (PRIMARY - Default)
    anthropic_api_key: str = Field(default="", description="Anthropic Claude API key")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514", description="Anthropic model to use")
    
    # Ollama Configuration (Local LLM - Fallback/Bundled)
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama server URL")
    ollama_model: str = Field(default="llama3.2", description="Ollama model to use")
    ollama_timeout: int = Field(default=120, description="Ollama request timeout in seconds")
    ollama_keep_alive: str = Field(default="5m", description="How long to keep model in memory")
    ollama_auto_start: bool = Field(default=True, description="Auto-start bundled Ollama if not running")
    ollama_bundled: bool = Field(default=True, description="Use bundled Ollama binary")
    
    @property
    def ollama_host_resolved(self) -> str:
        """Get Ollama host, resolving localhost to host.docker.internal when in Docker."""
        import os
        host = self.ollama_host
        
        # Check if running in Docker (/.dockerenv exists or DOCKER_CONTAINER env var)
        in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', '') == 'true'
        
        if in_docker and 'localhost' in host:
            # Replace localhost with host.docker.internal for Docker on Mac/Windows
            host = host.replace('localhost', 'host.docker.internal')
            host = host.replace('127.0.0.1', 'host.docker.internal')
        
        return host
    
    # OpenAI Configuration
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model to use")
    openai_base_url: str = Field(default="", description="OpenAI API base URL (for custom endpoints)")
    
    # HuggingFace Configuration
    huggingface_api_key: str = Field(default="", description="HuggingFace API key")
    
    # =========================================================================
    # MCP Server Configuration
    # =========================================================================
    mcp_enabled: bool = Field(default=True, description="Enable MCP server")
    mcp_port: int = Field(default=3333, description="MCP server port")
    mcp_allowed_tools: str = Field(default="*", description="Comma-separated list of allowed MCP tools")
    
    # =========================================================================
    # Trading Configuration
    # =========================================================================
    trading_mode: Literal["paper", "live"] = Field(default="paper")
    default_broker: str = Field(default="ibkr", description="Default broker (ibkr, alpaca, schwab, tradier)")
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
    slack_webhook_url: str = Field(default="", description="Slack webhook for alerts")
    pagerduty_api_key: str = Field(default="", description="PagerDuty API key")
    
    # =========================================================================
    # Application
    # =========================================================================
    log_level: str = Field(default="INFO")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    environment: Literal["development", "staging", "production"] = Field(default="development")
    admin_password_hash: str = Field(default="", description="Admin panel password hash")
    
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
    
    @property
    def enabled_brokers(self) -> List[str]:
        """Get list of brokers with configured credentials."""
        brokers = []
        if self.ibkr_account or self.ibkr_host:
            brokers.append("ibkr")
        if self.alpaca_api_key:
            brokers.append("alpaca")
        if self.schwab_client_id:
            brokers.append("schwab")
        if self.tradier_access_token:
            brokers.append("tradier")
        if self.etrade_consumer_key:
            brokers.append("etrade")
        if self.coinbase_api_key:
            brokers.append("coinbase")
        if self.binance_api_key:
            brokers.append("binance")
        return brokers
    
    @property
    def enabled_data_sources(self) -> List[str]:
        """Get list of data sources with configured API keys."""
        sources = []
        if self.polygon_api_key:
            sources.append("polygon")
        if self.alpha_vantage_api_key:
            sources.append("alpha_vantage")
        if self.iex_cloud_api_key:
            sources.append("iex_cloud")
        if self.tiingo_api_key:
            sources.append("tiingo")
        if self.barchart_api_key:
            sources.append("barchart")
        if self.finnhub_api_key:
            sources.append("finnhub")
        if self.yahoo_finance_enabled:
            sources.append("yahoo_finance")
        return sources


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
