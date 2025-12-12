"""
FastAPI application for the Trading Bot Control Panel.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from loguru import logger

from src.config.settings import get_settings
from src.monitoring.metrics import MetricsCollector


# Global instances (initialized in lifespan)
metrics = MetricsCollector()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    logger.info("Starting Trading Bot API...")
    
    # Startup
    # TODO: Initialize connections here
    
    yield
    
    # Shutdown
    logger.info("Shutting down Trading Bot API...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Trading Bot API",
        description="Control panel API for the IBKR Trading Bot",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    from src.api.routes import config, positions, orders, risk, news
    
    app.include_router(config.router, prefix="/api/config", tags=["Config"])
    app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
    app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
    app.include_router(risk.router, prefix="/api/risk", tags=["Risk"])
    app.include_router(news.router, prefix="/api/news", tags=["News"])
    
    @app.get("/")
    async def root():
        return {"status": "ok", "name": "Trading Bot API", "version": "0.1.0"}
    
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
        logger.info("WebSocket client connected")
        
        try:
            while True:
                # Receive messages from client
                data = await websocket.receive_json()
                
                # Handle subscription requests
                if data.get("type") == "subscribe":
                    channel = data.get("channel")
                    logger.debug(f"Client subscribed to {channel}")
                    await websocket.send_json({"type": "subscribed", "channel": channel})
                
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
    
    return app


# Create app instance
app = create_app()

