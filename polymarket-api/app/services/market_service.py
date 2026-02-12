# Market Service
"""
Business logic for market data

Features:
- Advanced filtering with date ranges, volume, liquidity
- Support for Polymarket Gamma API full parameter set
- Helper methods for common queries (active markets, trending, etc.)
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.clients.gamma import gamma_client
from app.clients.polymarket import polymarket_client
from app.database import cache_market, get_cached_market
from app.models.markets import (
    MarketResponse, MarketDetail, EventResponse, EventDetail,
    MarketListResponse, EventListResponse, OrderBookResponse, OrderBookEntry
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketService:
    """Service for market data operations with comprehensive filtering"""

    @staticmethod
    async def get_markets(
        limit: int = 50,
        offset: int = 0,
        # Sorting
        order: Optional[str] = None,
        ascending: Optional[bool] = None,
        # ID filters
        ids: Optional[List[str]] = None,
        slugs: Optional[List[str]] = None,
        clob_token_ids: Optional[List[str]] = None,
        condition_ids: Optional[List[str]] = None,
        question_ids: Optional[List[str]] = None,
        # Address filters
        market_maker_address: Optional[str] = None,
        # Numeric range filters
        liquidity_num_min: Optional[float] = None,
        liquidity_num_max: Optional[float] = None,
        volume_num_min: Optional[float] = None,
        volume_num_max: Optional[float] = None,
        rewards_min_size: Optional[float] = None,
        # Date range filters (ISO 8601 format)
        start_date_min: Optional[str] = None,
        start_date_max: Optional[str] = None,
        end_date_min: Optional[str] = None,
        end_date_max: Optional[str] = None,
        # Status filters
        active: Optional[bool] = None,
        archived: Optional[bool] = None,
        closed: Optional[bool] = None,
        featured: Optional[bool] = None,
        # Tag filters
        tag_id: Optional[int] = None,
        related_tags: Optional[bool] = None,
        include_tag: Optional[bool] = None,
        # Special filters
        cyom: Optional[bool] = None,
        uma_resolution_status: Optional[str] = None,
        game_id: Optional[str] = None,
        sports_market_types: Optional[List[str]] = None,
    ) -> MarketListResponse:
        """
        Get list of markets with comprehensive filtering options.

        Advanced Filtering:
        - Date ranges: end_date_min/max to filter by market end date
        - Volume filters: volume_num_min/max to find high-volume markets
        - Liquidity filters: liquidity_num_min/max for liquidity screening
        - Status filters: active, archived, closed for market state
        - Sorting: order by volumeNum, endDate, liquidityNum, etc.
        """
        try:
            markets_data = await gamma_client.get_markets(
                limit=limit,
                offset=offset,
                order=order,
                ascending=ascending,
                ids=ids,
                slugs=slugs,
                clob_token_ids=clob_token_ids,
                condition_ids=condition_ids,
                question_ids=question_ids,
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
                sports_market_types=sports_market_types,
            )

            markets = []
            for market_data in markets_data:
                try:
                    # Try to get token IDs
                    token_ids = market_data.get("clobTokenIds", [])
                    if token_ids and len(token_ids) > 0:
                        token_id = str(token_ids[0])
                    else:
                        token_id = ""

                    market = gamma_client.map_api_to_market(market_data, token_id)
                    markets.append(market)
                except Exception as e:
                    logger.warning(f"Error mapping market: {e}")
                    continue

            return MarketListResponse(
                markets=markets,
                total=len(markets),
                page=offset // limit + 1 if limit > 0 else 1,
                page_size=limit
            )

        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return MarketListResponse(markets=[], total=0)

    @staticmethod
    async def get_active_markets(
        limit: int = 50,
        offset: int = 0,
        order: str = "volumeNum",
        ascending: bool = False,
        volume_num_min: Optional[float] = None,
        liquidity_num_min: Optional[float] = None,
    ) -> MarketListResponse:
        """
        Get currently active markets (not closed, not archived).

        Args:
            limit: Maximum number of markets
            offset: Pagination offset
            order: Sort field (default: volumeNum for trending)
            ascending: Sort order (default: False = descending)
            volume_num_min: Minimum volume filter
            liquidity_num_min: Minimum liquidity filter

        Returns:
            MarketListResponse with active markets
        """
        return await MarketService.get_markets(
            limit=limit,
            offset=offset,
            active=True,
            archived=False,
            closed=False,
            order=order,
            ascending=ascending,
            volume_num_min=volume_num_min,
            liquidity_num_min=liquidity_num_min,
        )

    @staticmethod
    async def get_trending_markets(
        limit: int = 20,
        offset: int = 0,
        volume_num_min: float = 1000,
    ) -> MarketListResponse:
        """
        Get trending markets by volume.

        Args:
            limit: Maximum number of markets (default: 20)
            offset: Pagination offset
            volume_num_min: Minimum 24h volume (default: $1000)

        Returns:
            MarketListResponse with trending markets
        """
        return await MarketService.get_active_markets(
            limit=limit,
            offset=offset,
            order="volumeNum",
            ascending=False,
            volume_num_min=volume_num_min,
        )

    @staticmethod
    async def get_markets_ending_soon(
        limit: int = 20,
        days_ahead: int = 7,
        volume_num_min: Optional[float] = None,
    ) -> MarketListResponse:
        """
        Get markets ending within specified days.

        Args:
            limit: Maximum number of markets
            days_ahead: Filter markets ending within this many days
            volume_num_min: Optional minimum volume filter

        Returns:
            MarketListResponse with soon-to-expire markets
        """
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        end_date_max = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%dT%H:%M:%SZ")

        return await MarketService.get_markets(
            limit=limit,
            offset=0,
            active=True,
            archived=False,
            closed=False,
            end_date_max=end_date_max,
            order="endDate",
            ascending=True,  # Soonest first
            volume_num_min=volume_num_min,
        )

    @staticmethod
    async def get_sports_markets(
        limit: int = 50,
        offset: int = 0,
        game_id: Optional[str] = None,
        sports_market_types: Optional[List[str]] = None,
    ) -> MarketListResponse:
        """
        Get sports-related markets.

        Args:
            limit: Maximum number of markets
            offset: Pagination offset
            game_id: Specific game ID to filter
            sports_market_types: Types like "spread", "total", "moneyline"

        Returns:
            MarketListResponse with sports markets
        """
        return await MarketService.get_markets(
            limit=limit,
            offset=offset,
            active=True,
            archived=False,
            game_id=game_id,
            sports_market_types=sports_market_types,
            order="endDate",
            ascending=True,
        )
    
    @staticmethod
    async def get_market(token_id: str) -> Optional[MarketDetail]:
        """Get market details by token ID"""
        try:
            # Check cache first (if MongoDB is connected)
            try:
                cached = await get_cached_market(token_id)
                if cached:
                    return MarketDetail(**cached)
            except RuntimeError:
                # MongoDB not connected, skip cache
                pass
            
            # Fetch from API
            market_data = await gamma_client.get_market_by_token_id(token_id)
            if market_data:
                market = gamma_client.map_api_to_market(market_data, token_id)
                
                # Try to cache the result (if MongoDB is connected)
                try:
                    await cache_market(market.model_dump())
                except RuntimeError:
                    # MongoDB not connected, skip cache
                    pass
                
                return market
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching market {token_id}: {e}")
            return None
    
    @staticmethod
    async def get_orderbook(token_id: str) -> Optional[OrderBookResponse]:
        """Get order book for a market"""
        try:
            orderbook = await polymarket_client.get_order_book(token_id)
            
            if not orderbook:
                return None
            
            # Parse bids and asks
            bids = [
                OrderBookEntry(
                    price=float(b["price"]),
                    size=float(b["size"])
                )
                for b in orderbook.get("bids", [])
            ]
            
            asks = [
                OrderBookEntry(
                    price=float(a["price"]),
                    size=float(a["size"])
                )
                for a in orderbook.get("asks", [])
            ]
            
            # Calculate mid price and spread
            mid_price = None
            spread = None
            if bids and asks:
                best_bid = max(b.price for b in bids)
                best_ask = min(a.price for a in asks)
                mid_price = (best_bid + best_ask) / 2
                spread = best_ask - best_bid
            
            return OrderBookResponse(
                market=orderbook.get("market", ""),
                token_id=token_id,
                bids=bids,
                asks=asks,
                mid_price=mid_price,
                spread=spread
            )
            
        except Exception as e:
            logger.error(f"Error fetching orderbook for {token_id}: {e}")
            return None
    
    @staticmethod
    async def get_price(token_id: str, side: str = "BUY") -> Optional[float]:
        """Get best price for a market"""
        try:
            return await polymarket_client.get_price(token_id, side)
        except Exception as e:
            logger.error(f"Error fetching price for {token_id}: {e}")
            return None
    
    @staticmethod
    async def get_events(
        limit: int = 50,
        offset: int = 0,
        active: Optional[bool] = None,
        archived: Optional[bool] = None,
        featured: Optional[bool] = None
    ) -> EventListResponse:
        """Get list of events"""
        try:
            events_data = await gamma_client.get_events(
                limit=limit,
                offset=offset,
                active=active,
                archived=archived,
                featured=featured
            )
            
            events = []
            for event_data in events_data:
                try:
                    event = gamma_client.map_api_to_event(event_data)
                    events.append(event)
                except Exception as e:
                    logger.warning(f"Error mapping event: {e}")
                    continue
            
            return EventListResponse(
                events=events,
                total=len(events),
                page=offset // limit + 1 if limit > 0 else 1,
                page_size=limit
            )
            
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return EventListResponse(events=[], total=0)
    
    @staticmethod
    async def get_active_events() -> EventListResponse:
        """Get all active trading events"""
        return await MarketService.get_events(active=True, archived=False)
    
    @staticmethod
    async def get_event(event_id: str) -> Optional[EventDetail]:
        """Get event details by ID"""
        try:
            event_data = await gamma_client.get_event_by_id(event_id)
            if event_data:
                return gamma_client.map_api_to_event(event_data)
            return None
        except Exception as e:
            logger.error(f"Error fetching event {event_id}: {e}")
            return None


# Singleton instance
market_service = MarketService()
