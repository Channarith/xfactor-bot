"""
Structured logging setup using Loguru.
"""

import sys
from pathlib import Path

from loguru import logger

from src.config.settings import get_settings


def setup_logging() -> None:
    """Configure structured logging with Loguru."""
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Console handler with color
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )
    
    # File handler - general logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "trading_bot_{time:YYYY-MM-DD}.log",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="00:00",
        retention="30 days",
        compression="gz",
    )
    
    # File handler - errors only
    logger.add(
        log_dir / "errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="00:00",
        retention="90 days",
        compression="gz",
    )
    
    # File handler - trades (structured JSON)
    logger.add(
        log_dir / "trades_{time:YYYY-MM-DD}.json",
        level="INFO",
        format="{message}",
        filter=lambda record: record["extra"].get("trade", False),
        rotation="00:00",
        retention="365 days",
        serialize=True,
    )
    
    logger.info(f"Logging initialized at level {settings.log_level}")


def get_logger(name: str) -> "logger":
    """Get a logger instance with a specific name."""
    return logger.bind(name=name)


def log_trade(
    action: str,
    symbol: str,
    quantity: float,
    price: float,
    strategy: str,
    order_id: str = "",
    **kwargs
) -> None:
    """Log a trade execution with structured data."""
    logger.bind(trade=True).info(
        "",
        action=action,
        symbol=symbol,
        quantity=quantity,
        price=price,
        strategy=strategy,
        order_id=order_id,
        **kwargs,
    )

