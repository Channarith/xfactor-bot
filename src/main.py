"""
Main entry point for the IBKR Trading Bot.
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from loguru import logger

from src.config.settings import get_settings
from src.utils.logger import setup_logging


async def shutdown(signal_name: str) -> None:
    """Handle graceful shutdown."""
    logger.warning(f"Received {signal_name}, initiating graceful shutdown...")
    
    # TODO: Close all positions if configured
    # TODO: Disconnect from IBKR
    # TODO: Close database connections
    # TODO: Stop all scheduled tasks
    
    logger.info("Shutdown complete")


@asynccontextmanager
async def lifespan():
    """Application lifespan manager."""
    settings = get_settings()
    
    logger.info("=" * 60)
    logger.info("IBKR Trading Bot Starting")
    logger.info(f"Mode: {settings.trading_mode.upper()}")
    logger.info(f"Environment: {settings.environment}")
    logger.info("=" * 60)
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s.name))
        )
    
    try:
        yield
    finally:
        logger.info("Trading Bot stopped")


async def run_trading_bot() -> None:
    """Main trading bot execution loop."""
    settings = get_settings()
    
    async with lifespan():
        logger.info("Initializing components...")
        
        # TODO: Initialize IBKR connection
        # TODO: Initialize database connections
        # TODO: Initialize Redis cache
        # TODO: Initialize news aggregator
        # TODO: Initialize strategies
        # TODO: Initialize risk manager
        # TODO: Start scheduled tasks
        # TODO: Start API server
        
        logger.info("All components initialized")
        logger.info("Trading bot is running. Press Ctrl+C to stop.")
        
        # Keep the bot running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Trading loop cancelled")


def main() -> None:
    """Entry point for the trading bot."""
    # Setup logging first
    setup_logging()
    
    try:
        asyncio.run(run_trading_bot())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

