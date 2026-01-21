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
        from src.bot.bot_manager import get_bot_manager
        bot_mgr = get_bot_manager()
        if bot_mgr:
            logger.info("Stopping all bots...")
            # Use stop_all method which is synchronous
            if hasattr(bot_mgr, 'stop_all'):
                bot_mgr.stop_all()
            else:
                # Fallback: stop each bot individually
                for bot in bot_mgr.get_all_bots():
                    try:
                        if bot and bot.is_running:
                            bot.stop()
                            logger.info(f"Stopped bot: {bot.id}")
                    except Exception as e:
                        logger.warning(f"Error stopping bot {bot.id}: {e}")
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


def check_port_available(host: str, port: int) -> tuple[bool, str]:
    """Check if a port is available for binding."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return False, f"Port {port} is already in use by another process"
        return True, f"Port {port} is available"
    except socket.error as e:
        return False, f"Socket error checking port {port}: {e}"


def get_system_info() -> dict:
    """Gather system information for debugging."""
    import platform
    info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "cwd": os.getcwd(),
        "pid": os.getpid(),
    }
    
    # Check network interfaces
    try:
        import socket
        info["hostname"] = socket.gethostname()
        info["local_ip"] = socket.gethostbyname(socket.gethostname())
    except Exception as e:
        info["hostname"] = f"Error: {e}"
        info["local_ip"] = "Unknown"
    
    # Check if running in container/WSL
    if platform.system() == "Linux":
        if os.path.exists("/.dockerenv"):
            info["environment"] = "Docker"
        elif "microsoft" in platform.release().lower():
            info["environment"] = "WSL"
        else:
            info["environment"] = "Native Linux"
    elif platform.system() == "Windows":
        info["environment"] = "Windows"
    elif platform.system() == "Darwin":
        info["environment"] = "macOS"
    else:
        info["environment"] = "Unknown"
    
    return info


def check_dependencies() -> list[str]:
    """Check if all required dependencies are importable."""
    errors = []
    required_modules = [
        ("uvicorn", "Web server"),
        ("fastapi", "API framework"),
        ("starlette", "ASGI toolkit"),
        ("pydantic", "Data validation"),
        ("httpx", "HTTP client"),
        ("websockets", "WebSocket support"),
        ("pandas", "Data processing"),
        ("numpy", "Numerical computing"),
        ("orjson", "JSON parsing"),
        ("sqlalchemy", "Database ORM"),
    ]
    
    for module, description in required_modules:
        try:
            __import__(module)
            logger.debug(f"  [OK] {module} ({description})")
        except ImportError as e:
            error_msg = f"  [MISSING] {module} ({description}): {e}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    return errors


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
    
    # Gather system information
    sys_info = get_system_info()
    
    logger.info("=" * 60)
    logger.info("XFactor Bot Backend Starting")
    logger.info(f"  Version: XFactor-botMax (Full Features)")
    logger.info(f"  Project Root: {project_root}")
    logger.info(f"  Python: {sys.executable}")
    logger.info(f"  PID: {os.getpid()}")
    logger.info("=" * 60)
    
    # Log system info for debugging
    logger.info("System Information:")
    logger.info(f"  Platform: {sys_info['platform']} {sys_info['platform_release']}")
    logger.info(f"  Environment: {sys_info['environment']}")
    logger.info(f"  Architecture: {sys_info['architecture']}")
    logger.info(f"  Python: {sys_info['python_version']}")
    logger.info(f"  Hostname: {sys_info['hostname']}")
    logger.info(f"  Local IP: {sys_info['local_ip']}")
    
    # Check port availability
    host = "127.0.0.1"
    port = 9876
    port_available, port_msg = check_port_available(host, port)
    if not port_available:
        logger.error(f"PORT CHECK FAILED: {port_msg}")
        logger.error(f"  Another process may be using port {port}")
        logger.error(f"  On Windows: Run 'netstat -ano | findstr :{port}' to find the process")
        logger.error(f"  On Linux: Run 'lsof -i :{port}' or 'ss -tulpn | grep {port}'")
        logger.error(f"  Kill the process or choose a different port")
        sys.exit(1)
    else:
        logger.info(f"Port check: {port_msg}")
    
    # Check dependencies
    logger.info("Checking dependencies...")
    dep_errors = check_dependencies()
    if dep_errors:
        logger.error("=" * 60)
        logger.error("DEPENDENCY ERRORS - Backend cannot start!")
        for err in dep_errors:
            logger.error(err)
        logger.error("=" * 60)
        logger.error("Please ensure all dependencies are properly bundled.")
        logger.error("If running from source, try: pip install -r requirements.txt")
        sys.exit(1)
    else:
        logger.info("All dependencies OK")
    
    # Import and create the app
    try:
        logger.info("Importing API module...")
        from src.api.main import create_app
        logger.info("API module imported successfully")
        
        logger.info("Creating FastAPI application...")
        app = create_app()
        logger.info("FastAPI application created")
        
        logger.info(f"Starting server on http://{host}:{port}")
        logger.info("=" * 60)
        
        # Run the server with graceful shutdown support
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            timeout_graceful_shutdown=5,  # 5 second graceful shutdown
        )
        _server = uvicorn.Server(config)
        _server.run()
        
    except ImportError as e:
        logger.error("=" * 60)
        logger.error(f"IMPORT ERROR: {e}")
        logger.error("=" * 60)
        logger.error("This usually means a Python module is missing or incorrectly bundled.")
        logger.error(f"Module path: {e.name if hasattr(e, 'name') else 'unknown'}")
        logger.error("Debug info:")
        logger.error(f"  sys.path: {sys.path[:5]}...")  # First 5 paths
        logger.error(f"  Project root exists: {os.path.exists(project_root)}")
        if hasattr(sys, '_MEIPASS'):
            logger.error(f"  PyInstaller temp dir: {sys._MEIPASS}")
            # List contents of src directory
            src_path = os.path.join(sys._MEIPASS, 'src')
            if os.path.exists(src_path):
                logger.error(f"  src/ contents: {os.listdir(src_path)}")
            else:
                logger.error(f"  src/ directory NOT FOUND in bundle!")
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        cleanup_resources()
        sys.exit(1)
        
    except OSError as e:
        logger.error("=" * 60)
        logger.error(f"OS ERROR: {e}")
        logger.error("=" * 60)
        if "address already in use" in str(e).lower() or e.errno == 98 or e.errno == 10048:
            logger.error(f"Port {port} is already in use!")
            logger.error("Solutions:")
            logger.error(f"  1. Kill the existing process using port {port}")
            logger.error("  2. Wait a few seconds and try again")
            logger.error("  3. Check for zombie xfactor-backend processes")
        else:
            logger.error("This may be a network or filesystem permission issue.")
            logger.error(f"  Error code: {e.errno}")
        cleanup_resources()
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        cleanup_resources()
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"UNEXPECTED ERROR: {type(e).__name__}: {e}")
        logger.error("=" * 60)
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        logger.error("Debug info:")
        logger.error(f"  Working directory: {os.getcwd()}")
        logger.error(f"  Project root: {project_root}")
        logger.error(f"  Python executable: {sys.executable}")
        cleanup_resources()
        sys.exit(1)
        
    finally:
        cleanup_resources()
        logger.info("XFactor Bot Backend stopped")


if __name__ == "__main__":
    main()

