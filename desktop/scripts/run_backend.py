#!/usr/bin/env python3
"""
XFactor Bot Backend Runner
Entry point for the bundled backend executable

Supports both:
- XFactor-botMax: Full features (GitHub, localhost, desktop)
- XFactor-botMin: Restricted features (GitLab deployments)
"""

import os
import sys
import logging
import signal
import asyncio
import atexit
from typing import Optional

# Explicit imports for PyInstaller to detect
# Web framework
import uvicorn
import fastapi
import starlette
import pydantic
# HTTP/WebSocket
import httpx
import httpcore
import websockets
import aiohttp
import requests
import urllib3
import certifi
# Data
import pandas
import numpy
import orjson
# Async
import anyio
import sniffio
# Database
import sqlalchemy
# Scheduling
import apscheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('xfactor-backend')

# Global server reference for cleanup
_server: Optional[uvicorn.Server] = None
_shutdown_event = asyncio.Event() if hasattr(asyncio, 'Event') else None

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

def cleanup_resources():
    """Clean up all resources before exit."""
    global _server
    logger.info("Cleaning up resources...")
    
    # Stop all running bots
    try:
        from src.bot.bot_manager import bot_manager
        if bot_manager:
            logger.info("Stopping all bots...")
            # Use sync version if available
            if hasattr(bot_manager, 'stop_all_bots_sync'):
                bot_manager.stop_all_bots_sync()
            else:
                # Force stop without async
                for bot_id in list(bot_manager.bots.keys()):
                    try:
                        bot = bot_manager.bots.get(bot_id)
                        if bot and bot.running:
                            bot.running = False
                            logger.info(f"Stopped bot: {bot_id}")
                    except Exception as e:
                        logger.warning(f"Error stopping bot {bot_id}: {e}")
    except Exception as e:
        logger.warning(f"Error stopping bots: {e}")
    
    # Close database connections
    try:
        from src.config.database import close_db_connections
        close_db_connections()
    except Exception:
        pass
    
    # Shutdown server
    if _server:
        logger.info("Shutting down server...")
        _server.should_exit = True
    
    logger.info("Cleanup completed")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    logger.info(f"Received signal {sig_name}, initiating graceful shutdown...")
    cleanup_resources()
    sys.exit(0)


def main():
    """Start the FastAPI backend server"""
    global _server
    import uvicorn
    
    # Set environment variables
    os.environ.setdefault('XFACTOR_ENV', 'desktop')
    os.environ.setdefault('LOG_LEVEL', 'INFO')
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Windows-specific signal
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)
    
    # Register cleanup on exit
    atexit.register(cleanup_resources)
    
    # Add project root to path
    project_root = get_resource_path('')
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    logger.info("=" * 60)
    logger.info("XFactor Bot Backend Starting")
    logger.info(f"  Version: XFactor-botMax (Full Features)")
    logger.info(f"  Project Root: {project_root}")
    logger.info(f"  Python: {sys.executable}")
    logger.info(f"  PID: {os.getpid()}")
    logger.info("=" * 60)
    
    # Import and create the app
    try:
        from src.api.main import create_app
        app = create_app()
        
        # Run the server with graceful shutdown support
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=9876,
            log_level="info",
            access_log=True,
            timeout_graceful_shutdown=5,  # 5 second graceful shutdown
        )
        _server = uvicorn.Server(config)
        _server.run()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        cleanup_resources()
    except Exception as e:
        logger.error(f"Failed to start backend: {e}", exc_info=True)
        cleanup_resources()
        sys.exit(1)
    finally:
        cleanup_resources()
        logger.info("XFactor Bot Backend stopped")


if __name__ == "__main__":
    main()

