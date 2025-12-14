#!/usr/bin/env python3
"""
XFactor Bot Backend Runner
Entry point for the bundled backend executable
"""

import os
import sys
import logging

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

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

def main():
    """Start the FastAPI backend server"""
    import uvicorn
    
    # Set environment variables
    os.environ.setdefault('XFACTOR_ENV', 'desktop')
    os.environ.setdefault('LOG_LEVEL', 'INFO')
    
    # Add project root to path
    project_root = get_resource_path('')
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    logger.info(f"Starting XFactor Backend from: {project_root}")
    logger.info(f"Python: {sys.executable}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Import and create the app
    try:
        from src.api.main import create_app
        app = create_app()
        
        # Run the server
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=9876,
            log_level="info",
            access_log=True,
        )
        server = uvicorn.Server(config)
        server.run()
        
    except Exception as e:
        logger.error(f"Failed to start backend: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

