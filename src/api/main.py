"""
FastAPI application for XFactor Bot Control Panel.
XFactor Bot - AI-Powered Automated Trading System

Versions:
- XFactor-botMax: Full features (GitHub, localhost, desktop)
- XFactor-botMin: Restricted features (GitLab deployments)
"""

# Application version - keep in sync with frontend/package.json
APP_VERSION = "2.1.13"

import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from src.config.settings import get_settings
from src.monitoring.metrics import MetricsCollector


# Global instances (initialized in lifespan)
metrics = MetricsCollector()

# Track active WebSocket connections for cleanup
active_websockets: Set[WebSocket] = set()


async def cleanup_all_resources():
    """Clean up all resources on shutdown."""
    logger.info("Cleaning up all resources...")
    
    # Save bot state and agentic tuning BEFORE stopping (to preserve running state)
    try:
        from src.bot.bot_manager import get_bot_manager
        bot_mgr = get_bot_manager()
        if bot_mgr:
            logger.info("Saving bot configurations and state...")
            bot_mgr.save_all_bots()
            bot_mgr.save_position_tracking()
            logger.info("Bot state saved successfully")
    except Exception as e:
        logger.warning(f"Error saving bot state: {e}")
    try:
        from src.bot.agentic_tuner import get_agentic_tuner
        tuner = get_agentic_tuner()
        if getattr(tuner, "_bot_scores", None):
            tuner._save_persisted_scores()
            logger.info("Agentic tuning rankings saved")
    except Exception as e:
        logger.warning(f"Error saving agentic tuning state: {e}")
    
    # Stop all bots
    try:
        from src.bot.bot_manager import get_bot_manager
        bot_mgr = get_bot_manager()
        if bot_mgr:
            logger.info("Stopping all trading bots...")
            bot_mgr.stop_all()  # stop_all() is synchronous
            logger.info("All bots stopped")
    except Exception as e:
        logger.warning(f"Error stopping bots: {e}")
    
    # Close all WebSocket connections
    logger.info(f"Closing {len(active_websockets)} WebSocket connections...")
    for ws in list(active_websockets):
        try:
            await ws.close(code=1001, reason="Server shutting down")
        except Exception:
            pass
    active_websockets.clear()
    
    # Close database connections
    try:
        from src.config.database import close_db_connections
        await close_db_connections()
    except Exception as e:
        logger.warning(f"Error closing database: {e}")
    
    # Close any broker connections
    try:
        from src.brokers.ibkr_client import ibkr_client
        if ibkr_client and ibkr_client.connected:
            await ibkr_client.disconnect()
            logger.info("Broker connection closed")
    except Exception as e:
        logger.warning(f"Error closing broker: {e}")
    
    logger.info("All resources cleaned up")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    logger.info("=" * 60)
    logger.info("🚀 Starting XFactor Bot API...")
    logger.info(f"   Version: XFactor-botMax")
    logger.info(f"   PID: {os.getpid()}")
    logger.info("=" * 60)
    
    # Startup
    # Initialize bot manager
    try:
        from src.bot.bot_manager import get_bot_manager
        _bot_mgr = get_bot_manager()  # Initialize the singleton
        logger.info("Bot manager initialized")
    except Exception as e:
        logger.warning(f"Bot manager initialization: {e}")
    
    # Auto-fetch forecasting data on startup (in background)
    try:
        import asyncio
        from src.api.routes import forecasting as fc_routes
        logger.info("Starting background forecasting data fetch...")
        asyncio.create_task(fc_routes._fetch_and_populate_data(fc_routes.POPULAR_SYMBOLS))
    except Exception as e:
        logger.warning(f"Auto-fetch initialization: {e}")
    
    # Auto-connect to saved broker connections
    try:
        from src.brokers.registry import get_broker_registry
        registry = get_broker_registry()
        
        async def auto_connect_brokers():
            await asyncio.sleep(2)  # Wait for other services to initialize
            results = await registry.auto_connect_all()
            if results:
                successful = sum(1 for v in results.values() if v)
                logger.info(f"Auto-connected to {successful}/{len(results)} saved brokers")
        
        asyncio.create_task(auto_connect_brokers())
        logger.info("Broker auto-connect scheduled")
    except Exception as e:
        logger.warning(f"Broker auto-connect initialization: {e}")
    
    # Start background equity tracking
    try:
        from src.utils.equity_tracker import get_equity_tracker
        from src.brokers.registry import get_broker_registry
        
        async def track_equity_continuously():
            """Background task to track equity every 5 minutes."""
            tracker = get_equity_tracker()
            registry = get_broker_registry()
            
            await asyncio.sleep(10)  # Initial delay
            
            while True:
                try:
                    total_equity = 0.0
                    
                    # Get equity from all connected brokers
                    for broker_type in registry.connected_brokers:
                        broker = registry.get_broker(broker_type)
                        if broker and broker.is_connected:
                            try:
                                accounts = await broker.get_accounts()
                                for account in accounts:
                                    total_equity += account.equity
                            except Exception as e:
                                logger.debug(f"Error fetching equity from {broker_type.value}: {e}")
                    
                    # Record equity if we have any
                    if total_equity > 0:
                        tracker.record_equity(total_equity)
                        logger.debug(f"Background equity tracked: ${total_equity:,.2f}")
                    
                except Exception as e:
                    logger.error(f"Error in equity tracking background task: {e}")
                
                # Wait 5 minutes before next check
                await asyncio.sleep(300)
        
        asyncio.create_task(track_equity_continuously())
        logger.info("Background equity tracking started (5min intervals)")
    except Exception as e:
        logger.warning(f"Equity tracking initialization: {e}")
    
    yield
    
    # Shutdown - clean up all resources
    logger.info("👋 Shutting down XFactor Bot API...")
    
    # Save equity tracker before shutdown
    try:
        from src.utils.equity_tracker import get_equity_tracker
        tracker = get_equity_tracker()
        tracker.save()
        logger.info("Equity history saved")
    except Exception as e:
        logger.warning(f"Error saving equity history: {e}")
    
    await cleanup_all_resources()
    logger.info("XFactor Bot API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="XFactor Bot API",
        description="AI-Powered Automated Trading System - Control Panel API",
        version=APP_VERSION,
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:9876",
            "http://localhost:9877",
            "http://127.0.0.1:9876",
            "http://foresight.nvidia.com:9876",
            "https://foresight.nvidia.com:9876",
            "*",  # Allow all origins for easier development
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    from src.api.routes import config, positions, orders, risk, news, admin, bots, ai, integrations, commodities, crypto, fees, symbols, seasonal, optimizer, performance, agentic_tuning, tradingview, strategies, forex, forecasting, bot_risk, video_sentiment, stock_analysis, compliance, market, screener, momentum, manual_trading
    
    app.include_router(config.router, prefix="/api/config", tags=["Config"])
    app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
    app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
    app.include_router(risk.router, prefix="/api/risk", tags=["Risk"])
    app.include_router(news.router, prefix="/api/news", tags=["News"])
    app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
    app.include_router(bots.router, prefix="/api/bots", tags=["Bots"])
    app.include_router(ai.router, prefix="/api", tags=["AI Assistant"])
    app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
    app.include_router(commodities.router, prefix="/api/commodities", tags=["Commodities"])
    app.include_router(crypto.router, prefix="/api/crypto", tags=["Crypto"])
    app.include_router(fees.router, prefix="/api/fees", tags=["Fees"])
    app.include_router(symbols.router, prefix="/api", tags=["Symbols"])  # Global symbol search
    app.include_router(seasonal.router, tags=["Seasonal"])  # Seasonal events calendar
    app.include_router(optimizer.router, tags=["Auto-Optimizer"])  # Bot auto-optimization
    app.include_router(performance.router, tags=["Performance"])  # Performance charts & metrics
    app.include_router(agentic_tuning.router, tags=["Agentic Tuning"])  # ATRWAC - Bot pruning & optimization
    app.include_router(tradingview.router, tags=["TradingView"])  # TradingView webhook integration
    app.include_router(strategies.router, tags=["Strategies"])  # Strategy templates, visual builder, social trading
    app.include_router(forex.router, tags=["Forex"])  # Comprehensive Forex trading
    app.include_router(forecasting.router, tags=["Forecasting"])  # AI-powered market forecasting & speculation
    app.include_router(bot_risk.router, tags=["Bot Risk Management"])  # Risk scoring and alerts for bots
    app.include_router(video_sentiment.router, tags=["Video Platforms"])  # YouTube, TikTok, Instagram analysis
    app.include_router(stock_analysis.router, prefix="/api", tags=["Stock Analysis"])  # Comprehensive stock analysis with overlays
    app.include_router(market.router, prefix="/api/market", tags=["Market Data"])  # Insider trades, earnings, screener signals
    app.include_router(compliance.router, prefix="/api", tags=["Compliance"])  # Trading compliance (PDT, Good Faith, etc.)
    app.include_router(screener.router, prefix="/api/screener", tags=["Screener"])  # Symbol universe & growth screener
    app.include_router(momentum.router, prefix="/api/momentum", tags=["Momentum"])  # Momentum scanning, sectors, social, news
    app.include_router(manual_trading.router, prefix="/api/trading", tags=["Manual Trading"])  # Manual trading with performance comparison
    
    @app.get("/api")
    async def api_root():
        # Check for MIN mode based on request origin
        return {
            "status": "ok", 
            "name": "XFactor Bot", 
            "version": APP_VERSION, 
            "description": "AI-Powered Automated Trading System",
            "edition": "MAX",  # Backend always serves MAX - frontend determines MIN based on hostname
            "note": "Edition determined by frontend based on deployment hostname"
        }
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    @app.get("/metrics")
    async def prometheus_metrics():
        return Response(
            content=metrics.get_metrics(),
            media_type=metrics.get_content_type(),
        )
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time updates."""
        await websocket.accept()
        active_websockets.add(websocket)
        logger.info(f"WebSocket client connected (total: {len(active_websockets)})")
        
        try:
            while True:
                # Receive messages from client
                data = await websocket.receive_json()
                
                # Handle subscription requests
                if data.get("type") == "subscribe":
                    channel = data.get("channel")
                    logger.debug(f"Client subscribed to {channel}")
                    await websocket.send_json({"type": "subscribed", "channel": channel})
                
                # Handle cleanup request from frontend
                elif data.get("type") == "cleanup":
                    logger.info("Cleanup request received from frontend")
                    await websocket.send_json({"type": "cleanup_ack", "status": "received"})
                
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            active_websockets.discard(websocket)
            logger.info(f"WebSocket removed (remaining: {len(active_websockets)})")
    
    # Serve static frontend files
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        # Mount static assets
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
        
        # Serve index.html for root (no caching to ensure latest version)
        @app.get("/")
        async def serve_root():
            index_file = frontend_dist / "index.html"
            if index_file.exists():
                response = FileResponse(str(index_file), media_type="text/html")
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
            return {"error": "Frontend not built"}
        
        # Serve index.html for all non-API routes (SPA fallback)
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # Don't intercept API, health, metrics, or ws routes
            if full_path.startswith(("api", "health", "metrics", "ws", "docs", "openapi.json", "redoc")):
                return {"error": "Not found", "path": full_path}
            
            index_file = frontend_dist / "index.html"
            if index_file.exists():
                response = FileResponse(str(index_file), media_type="text/html")
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
            return {"error": "Frontend not built"}
        
        logger.info(f"📁 Serving frontend from {frontend_dist}")
    else:
        logger.warning(f"⚠️ Frontend dist not found at {frontend_dist}")
        
        @app.get("/")
        async def root_no_frontend():
            return {"status": "ok", "name": "XFactor Bot", "version": APP_VERSION, "description": "AI-Powered Automated Trading System", "note": "Frontend not deployed"}
    
    return app


# Create app instance
app = create_app()

