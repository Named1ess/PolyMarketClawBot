# Markets Router
"""
Market-related API endpoints
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.market_service import market_service
from app.models.markets import (
    MarketListResponse, MarketDetail, OrderBookResponse, PriceResponse
)
from app.models.orders import OrderSide

markets_router = APIRouter()


@markets_router.get("/markets", response_model=MarketListResponse)
async def list_markets(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    active: Optional[bool] = Query(default=None),
    archived: Optional[bool] = Query(default=None)
):
    """List all markets with optional filtering"""
    return await market_service.get_markets(
        limit=limit,
        offset=offset,
        active=active,
        archived=archived
    )


@markets_router.get("/markets/{token_id}", response_model=MarketDetail)
async def get_market(token_id: str):
    """Get market details by token ID"""
    market = await market_service.get_market(token_id)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    return market


@markets_router.get("/markets/{token_id}/orderbook", response_model=OrderBookResponse)
async def get_market_orderbook(token_id: str):
    """Get order book for a market"""
    orderbook = await market_service.get_orderbook(token_id)
    if not orderbook:
        raise HTTPException(status_code=404, detail="Orderbook not found")
    return orderbook


@markets_router.get("/markets/{token_id}/price")
async def get_market_price(
    token_id: str,
    side: str = Query(default="BUY", regex="^(BUY|SELL)$")
):
    """Get current best price for a market"""
    price = await market_service.get_price(token_id, side)
    if price is None:
        raise HTTPException(status_code=404, detail="Price not found")
    return {
        "token_id": token_id,
        "side": side,
        "price": price,
        "timestamp": str(__import__('datetime').datetime.utcnow())
    }
