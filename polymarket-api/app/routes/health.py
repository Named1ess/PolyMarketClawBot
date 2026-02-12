# Health Router
"""
Health check and status endpoints
"""
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

health_router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str = "1.0.0"


class StatusResponse(BaseModel):
    """System status response"""
    status: str
    mongodb: str
    polymarket_api: str
    timestamp: datetime


@health_router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
    )


@health_router.get("/status", response_model=StatusResponse)
async def system_status():
    """Get system status"""
    from app.database import get_db
    
    mongo_status = "connected"
    try:
        db = get_db()
        await db.command("ping")
    except Exception:
        mongo_status = "disconnected"
    
    return StatusResponse(
        status="running",
        mongodb=mongo_status,
        polymarket_api="connected",
        timestamp=datetime.utcnow()
    )
