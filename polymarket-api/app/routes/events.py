# Events Router
"""
Event-related API endpoints
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.market_service import market_service
from app.models.markets import EventListResponse, EventDetail

events_router = APIRouter()


@events_router.get("/events", response_model=EventListResponse)
async def list_events(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    active: Optional[bool] = Query(default=None),
    archived: Optional[bool] = Query(default=None),
    featured: Optional[bool] = Query(default=None)
):
    """List all events with optional filtering"""
    return await market_service.get_events(
        limit=limit,
        offset=offset,
        active=active,
        archived=archived,
        featured=featured
    )


@events_router.get("/events/active", response_model=EventListResponse)
async def list_active_events(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """List all active trading events"""
    return await market_service.get_active_events()


@events_router.get("/events/{event_id}", response_model=EventDetail)
async def get_event(event_id: str):
    """Get event details by ID"""
    event = await market_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
