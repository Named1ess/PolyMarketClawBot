# Markets Router
"""
Market-related API endpoints with advanced filtering

API Documentation: https://docs.polymarket.com/api-reference/markets/list-markets

Features:
- Advanced filtering by date ranges, volume, liquidity
- Pre-built queries: active markets, trending, ending soon, sports
- Support for all Gamma API parameters
"""
from typing import Optional, List
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
    # Sorting
    order: Optional[str] = Query(default=None, description="Comma-separated fields to order by (e.g., 'volumeNum,endDate')"),
    ascending: Optional[bool] = Query(default=None, description="Sort order (true=ascending, false=descending)"),
    # ID filters
    ids: Optional[str] = Query(default=None, description="Comma-separated market IDs"),
    slugs: Optional[str] = Query(default=None, description="Comma-separated market slugs"),
    clob_token_ids: Optional[str] = Query(default=None, description="Comma-separated CLOB token IDs"),
    condition_ids: Optional[str] = Query(default=None, description="Comma-separated condition IDs"),
    question_ids: Optional[str] = Query(default=None, description="Comma-separated question IDs"),
    # Address filters
    market_maker_address: Optional[str] = Query(default=None, description="Market maker wallet address"),
    # Numeric range filters
    liquidity_num_min: Optional[float] = Query(default=None, ge=0, description="Minimum liquidity"),
    liquidity_num_max: Optional[float] = Query(default=None, ge=0, description="Maximum liquidity"),
    volume_num_min: Optional[float] = Query(default=None, ge=0, description="Minimum 24h volume"),
    volume_num_max: Optional[float] = Query(default=None, ge=0, description="Maximum 24h volume"),
    rewards_min_size: Optional[float] = Query(default=None, ge=0, description="Minimum reward size"),
    # Date range filters (ISO 8601 format)
    start_date_min: Optional[str] = Query(default=None, description="Start date minimum (ISO 8601)"),
    start_date_max: Optional[str] = Query(default=None, description="Start date maximum (ISO 8601)"),
    end_date_min: Optional[str] = Query(default=None, description="End date minimum (ISO 8601)"),
    end_date_max: Optional[str] = Query(default=None, description="End date maximum (ISO 8601)"),
    # Status filters
    active: Optional[bool] = Query(default=None, description="Filter by active status"),
    archived: Optional[bool] = Query(default=None, description="Filter by archived status"),
    closed: Optional[bool] = Query(default=None, description="Filter by closed status"),
    featured: Optional[bool] = Query(default=None, description="Filter by featured status"),
    # Tag filters
    tag_id: Optional[int] = Query(default=None, description="Filter by tag ID"),
    related_tags: Optional[bool] = Query(default=None, description="Include related tags"),
    include_tag: Optional[bool] = Query(default=None, description="Include tag information"),
    # Special filters
    cyom: Optional[bool] = Query(default=None, description="Create Your Own Market filter"),
    uma_resolution_status: Optional[str] = Query(default=None, description="UMA resolution status"),
    game_id: Optional[str] = Query(default=None, description="Game ID for sports markets"),
    sports_market_types: Optional[str] = Query(default=None, description="Comma-separated sports market types"),
):
    """
    List all markets with comprehensive filtering options.

    ## Filtering Examples

    **Active Markets Only:**
    - `active=true&archived=false&closed=false`

    **High Volume Markets:**
    - `volume_num_min=10000&order=volumeNum&ascending=false`

    **Markets Ending Soon (next 7 days):**
    - `end_date_max=2026-02-19T00:00:00Z&order=endDate&ascending=true`

    **Sports Markets:**
    - `game_id=some_game_id` or `sports_market_types=spread,total`

    **Date Range:**
    - `start_date_min=2026-01-01T00:00:00Z&start_date_max=2026-12-31T23:59:59Z`
    """
    # Parse comma-separated lists
    ids_list = ids.split(",") if ids else None
    slugs_list = slugs.split(",") if slugs else None
    clob_token_ids_list = clob_token_ids.split(",") if clob_token_ids else None
    condition_ids_list = condition_ids.split(",") if condition_ids else None
    question_ids_list = question_ids.split(",") if question_ids else None
    sports_market_types_list = sports_market_types.split(",") if sports_market_types else None

    return await market_service.get_markets(
        limit=limit,
        offset=offset,
        order=order,
        ascending=ascending,
        ids=ids_list,
        slugs=slugs_list,
        clob_token_ids=clob_token_ids_list,
        condition_ids=condition_ids_list,
        question_ids=question_ids_list,
        market_maker_address=market_maker_address,
        liquidity_num_min=liquidity_num_min,
        liquidity_num_max=liquidity_num_max,
        volume_num_min=volume_num_min,
        volume_num_max=volume_num_max,
        rewards_min_size=rewards_min_size,
        start_date_min=start_date_min,
        start_date_max=start_date_max,
        end_date_min=end_date_min,
        end_date_max=end_date_max,
        active=active,
        archived=archived,
        closed=closed,
        featured=featured,
        tag_id=tag_id,
        related_tags=related_tags,
        include_tag=include_tag,
        cyom=cyom,
        uma_resolution_status=uma_resolution_status,
        game_id=game_id,
        sports_market_types=sports_market_types_list,
    )


@markets_router.get("/markets/active", response_model=MarketListResponse)
async def list_active_markets(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="volumeNum", description="Sort field"),
    ascending: bool = Query(default=False, description="Sort order"),
    volume_num_min: Optional[float] = Query(default=None, ge=0, description="Minimum volume"),
    liquidity_num_min: Optional[float] = Query(default=None, ge=0, description="Minimum liquidity"),
):
    """
    Get currently active markets (not closed, not archived).

    These are markets that are currently trading and can be bet on.
    """
    return await market_service.get_active_markets(
        limit=limit,
        offset=offset,
        order=order,
        ascending=ascending,
        volume_num_min=volume_num_min,
        liquidity_num_min=liquidity_num_min,
    )


@markets_router.get("/markets/trending", response_model=MarketListResponse)
async def list_trending_markets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    volume_num_min: float = Query(default=1000, ge=0, description="Minimum 24h volume"),
):
    """
    Get trending markets by 24h volume.

    These are the most active markets in the last 24 hours.
    Great for finding popular markets to trade.
    """
    return await market_service.get_trending_markets(
        limit=limit,
        offset=offset,
        volume_num_min=volume_num_min,
    )


@markets_router.get("/markets/ending-soon", response_model=MarketListResponse)
async def list_ending_soon_markets(
    limit: int = Query(default=20, ge=1, le=100),
    days_ahead: int = Query(default=7, ge=1, le=365, description="Markets ending within this many days"),
    volume_num_min: Optional[float] = Query(default=None, ge=0, description="Minimum volume filter"),
):
    """
    Get markets that are ending within the specified number of days.

    Great for finding markets about to resolve where you can take a position.
    """
    return await market_service.get_markets_ending_soon(
        limit=limit,
        days_ahead=days_ahead,
        volume_num_min=volume_num_min,
    )


@markets_router.get("/markets/sports", response_model=MarketListResponse)
async def list_sports_markets(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    game_id: Optional[str] = Query(default=None, description="Filter by specific game ID"),
    sports_market_types: Optional[str] = Query(default=None, description="Comma-separated types (spread,total,moneyline)"),
):
    """
    Get sports-related markets.

    Filter by game ID or market types like spread, total, moneyline.
    """
    sports_types_list = sports_market_types.split(",") if sports_market_types else None

    return await market_service.get_sports_markets(
        limit=limit,
        offset=offset,
        game_id=game_id,
        sports_market_types=sports_types_list,
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
