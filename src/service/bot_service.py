"""
XFactor Bot Background Service.

Standalone service that runs trading bots independently of the desktop application.
Can be started as a system service or run manually.

Usage:
    python -m src.service.bot_service [--port 8765] [--config-dir ~/.xfactor]

Features:
- Loads saved bot configurations from disk
- Runs bots on schedule or continuously
- Exposes REST API for status/control
- Auto-reconnects to brokers
- Graceful shutdown handling
"""

import argparse
import asyncio
import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from loguru import logger

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Service configuration
DEFAULT_PORT = 8765
DEFAULT_CONFIG_DIR = Path.home() / ".xfactor"
BOT_CONFIG_FILE = "bot_configs.json"
SERVICE_STATE_FILE = "service_state.json"


class BotService:
    """
    Background service for running trading bots.
    
    Runs independently of the desktop application and can be
    configured to start automatically on system boot.
    """
    
    def __init__(
        self,
        port: int = DEFAULT_PORT,
        config_dir: Path = DEFAULT_CONFIG_DIR,
    ):
        self.port = port
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._running = False
        self._app = None
        self._bots: Dict[str, Any] = {}  # bot_id -> BotInstance
        self._scheduler = None
        self._broker_registry = None
        
        # State tracking
        self._started_at: Optional[datetime] = None
        self._last_health_check: Optional[datetime] = None
        
        logger.info(f"BotService initialized: port={port}, config_dir={config_dir}")
    
    async def start(self) -> None:
        """Start the background service."""
        from fastapi import FastAPI
        import uvicorn
        
        logger.info("Starting XFactor Bot Background Service...")
        
        self._running = True
        self._started_at = datetime.now()
        
        # Initialize components
        await self._init_components()
        
        # Load saved bot configurations
        await self._load_bot_configs()
        
        # Connect to saved brokers
        await self._connect_saved_brokers()
        
        # Start scheduler
        if self._scheduler:
            self._scheduler.start()
        
        # Create FastAPI app for status/control
        self._app = await self._create_api()
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Run the API server
        config = uvicorn.Config(
            self._app,
            host="127.0.0.1",
            port=self.port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        
        logger.info(f"Service API running on http://127.0.0.1:{self.port}")
        
        try:
            await server.serve()
        except asyncio.CancelledError:
            logger.info("Service shutdown requested")
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop the background service gracefully."""
        logger.info("Stopping XFactor Bot Background Service...")
        
        self._running = False
        
        # Stop all bots
        for bot_id, bot in self._bots.items():
            try:
                bot.stop()
                logger.info(f"Stopped bot: {bot_id}")
            except Exception as e:
                logger.error(f"Error stopping bot {bot_id}: {e}")
        
        # Stop scheduler
        if self._scheduler:
            self._scheduler.stop()
        
        # Disconnect brokers
        if self._broker_registry:
            await self._broker_registry.disconnect_all()
        
        # Save state
        self._save_state()
        
        logger.info("Service stopped")
    
    async def _init_components(self) -> None:
        """Initialize service components."""
        from src.brokers.registry import get_broker_registry
        from src.service.scheduler import TradingScheduler
        
        # Get broker registry
        self._broker_registry = get_broker_registry()
        
        # Create scheduler
        self._scheduler = TradingScheduler(
            on_schedule_trigger=self._on_schedule_trigger
        )
        
        logger.info("Service components initialized")
    
    async def _load_bot_configs(self) -> None:
        """Load saved bot configurations from disk."""
        from src.bot.bot_instance import BotConfig, BotInstance
        
        config_path = self.config_dir / BOT_CONFIG_FILE
        
        if not config_path.exists():
            logger.info("No saved bot configurations found")
            return
        
        try:
            with open(config_path, "r") as f:
                configs = json.load(f)
            
            for config_data in configs:
                try:
                    bot_id = config_data.pop("id", None)
                    auto_start = config_data.pop("auto_start", False)
                    schedule = config_data.pop("schedule", None)
                    
                    # Create bot config
                    config = BotConfig.from_dict(config_data)
                    
                    # Create bot instance
                    bot = BotInstance(config, bot_id)
                    self._bots[bot.id] = bot
                    
                    # Register with scheduler if has schedule
                    if schedule and self._scheduler:
                        self._scheduler.add_bot_schedule(bot.id, schedule)
                    
                    # Auto-start if configured
                    if auto_start:
                        bot.start()
                        logger.info(f"Auto-started bot: {bot.id} ({config.name})")
                    
                except Exception as e:
                    logger.error(f"Error loading bot config: {e}")
            
            logger.info(f"Loaded {len(self._bots)} bot configurations")
            
        except Exception as e:
            logger.error(f"Error loading bot configs: {e}")
    
    async def _connect_saved_brokers(self) -> None:
        """Connect to saved broker configurations."""
        from src.brokers.saved_connections import get_saved_connections
        
        saved_conns = get_saved_connections()
        auto_connect_conns = saved_conns.get_auto_connect_connections()
        
        for conn in auto_connect_conns:
            try:
                success, error = await self._broker_registry.connect_saved(conn.id)
                if success:
                    logger.info(f"Connected to saved broker: {conn.broker_type}")
                else:
                    logger.warning(f"Failed to connect to {conn.broker_type}: {error}")
            except Exception as e:
                logger.error(f"Error connecting to saved broker: {e}")
    
    async def _on_schedule_trigger(self, bot_id: str, action: str) -> None:
        """Handle scheduled bot actions."""
        bot = self._bots.get(bot_id)
        if not bot:
            logger.warning(f"Scheduled action for unknown bot: {bot_id}")
            return
        
        if action == "start":
            if not bot.is_running:
                bot.start()
                logger.info(f"Scheduler started bot: {bot_id}")
        elif action == "stop":
            if bot.is_running:
                bot.stop()
                logger.info(f"Scheduler stopped bot: {bot_id}")
        elif action == "cycle":
            # Trigger a single trading cycle
            if bot.is_running:
                # Bot will run its cycle automatically
                logger.debug(f"Scheduler triggered cycle for bot: {bot_id}")
    
    async def _create_api(self):
        """Create the FastAPI app for status/control."""
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
        
        app = FastAPI(
            title="XFactor Bot Service",
            description="Background trading bot service API",
            version="1.0.0",
            lifespan=lifespan,
        )
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @app.get("/")
        async def root():
            return {
                "service": "XFactor Bot Service",
                "status": "running" if self._running else "stopped",
                "started_at": self._started_at.isoformat() if self._started_at else None,
                "uptime_seconds": (datetime.now() - self._started_at).total_seconds() if self._started_at else 0,
                "bots_count": len(self._bots),
                "bots_running": sum(1 for b in self._bots.values() if b.is_running),
            }
        
        @app.get("/health")
        async def health():
            self._last_health_check = datetime.now()
            return {
                "status": "healthy" if self._running else "unhealthy",
                "timestamp": datetime.now().isoformat(),
            }
        
        @app.get("/bots")
        async def list_bots():
            return {
                "bots": [
                    {
                        "id": bot.id,
                        "name": bot.config.name,
                        "status": bot.status.value,
                        "is_running": bot.is_running,
                        "symbols": bot.config.symbols[:5],  # First 5
                        "trades_today": bot.stats.trades_today,
                        "errors": bot.stats.errors_count,
                    }
                    for bot in self._bots.values()
                ]
            }
        
        @app.post("/bots/{bot_id}/start")
        async def start_bot(bot_id: str):
            bot = self._bots.get(bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            bot.start()
            return {"status": "started", "bot_id": bot_id}
        
        @app.post("/bots/{bot_id}/stop")
        async def stop_bot(bot_id: str):
            bot = self._bots.get(bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            bot.stop()
            return {"status": "stopped", "bot_id": bot_id}
        
        @app.post("/bots/start-all")
        async def start_all_bots():
            started = 0
            for bot in self._bots.values():
                if not bot.is_running:
                    bot.start()
                    started += 1
            return {"started": started}
        
        @app.post("/bots/stop-all")
        async def stop_all_bots():
            stopped = 0
            for bot in self._bots.values():
                if bot.is_running:
                    bot.stop()
                    stopped += 1
            return {"stopped": stopped}
        
        @app.get("/brokers")
        async def list_brokers():
            if not self._broker_registry:
                return {"brokers": []}
            return {
                "brokers": [
                    {
                        "type": bt.value,
                        "connected": bt in self._broker_registry.connected_brokers,
                    }
                    for bt in self._broker_registry._broker_classes.keys()
                ]
            }
        
        @app.post("/shutdown")
        async def shutdown():
            """Gracefully shutdown the service."""
            asyncio.create_task(self._delayed_shutdown())
            return {"status": "shutting_down"}
        
        return app
    
    async def _delayed_shutdown(self):
        """Delayed shutdown to allow response to be sent."""
        await asyncio.sleep(0.5)
        await self.stop()
        os._exit(0)
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            asyncio.create_task(self.stop())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _save_state(self) -> None:
        """Save service state to disk."""
        state = {
            "stopped_at": datetime.now().isoformat(),
            "bots": [
                {
                    "id": bot.id,
                    "name": bot.config.name,
                    "was_running": bot.is_running,
                    "trades_today": bot.stats.trades_today,
                }
                for bot in self._bots.values()
            ]
        }
        
        state_path = self.config_dir / SERVICE_STATE_FILE
        try:
            with open(state_path, "w") as f:
                json.dump(state, f, indent=2)
            logger.info(f"Service state saved to {state_path}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def save_bot_configs(self) -> None:
        """Save current bot configurations to disk."""
        configs = []
        for bot in self._bots.values():
            config_dict = bot.config.to_dict()
            config_dict["id"] = bot.id
            config_dict["auto_start"] = bot.is_running
            configs.append(config_dict)
        
        config_path = self.config_dir / BOT_CONFIG_FILE
        try:
            with open(config_path, "w") as f:
                json.dump(configs, f, indent=2)
            logger.info(f"Bot configs saved to {config_path}")
        except Exception as e:
            logger.error(f"Error saving bot configs: {e}")


# Global service instance
_service: Optional[BotService] = None


def get_bot_service() -> Optional[BotService]:
    """Get the global bot service instance."""
    return _service


async def main():
    """Main entry point for the background service."""
    global _service
    
    parser = argparse.ArgumentParser(description="XFactor Bot Background Service")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="API port")
    parser.add_argument("--config-dir", type=str, default=str(DEFAULT_CONFIG_DIR), help="Config directory")
    args = parser.parse_args()
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    
    # Add file logging
    log_dir = Path(args.config_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "bot_service_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
    )
    
    logger.info("=" * 60)
    logger.info("XFactor Bot Background Service Starting")
    logger.info("=" * 60)
    
    _service = BotService(
        port=args.port,
        config_dir=Path(args.config_dir),
    )
    
    await _service.start()


if __name__ == "__main__":
    asyncio.run(main())

