# FastAPI Application Factory
"""
Polymarket Trading Bot API
FastAPI-based REST API for Polymarket trading with OpenClaw integration
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logger import setup_logging, get_logger
from app.database import connect_to_mongo, close_mongo_connection
from app.routes import health_router, markets_router, events_router, orders_router, wallet_router, webhook_router, websocket_router

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting Polymarket Trading Bot API...")
    
    # Connect to MongoDB
    try:
        await connect_to_mongo()
        logger.info("Connected to MongoDB successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        # Continue without MongoDB for read-only operations
    
    yield
    
    # Shutdown
    logger.info("Shutting down Polymarket Trading Bot API...")
    await close_mongo_connection()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Polymarket Trading Bot API",
        description="REST API for Polymarket trading with OpenClaw integration",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        debug=settings.DEBUG
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health_router, prefix="")
    app.include_router(markets_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(orders_router, prefix="/api/v1")
    app.include_router(wallet_router, prefix="/api/v1")
    app.include_router(webhook_router, prefix="/api/v1")
    app.include_router(websocket_router)
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
