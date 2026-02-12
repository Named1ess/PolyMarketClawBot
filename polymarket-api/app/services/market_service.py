# Market Service
"""
Business logic for market data
"""
from typing import Dict, Any, List, Optional
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
    """Service for market data operations"""
    
    @staticmethod
    async def get_markets(
        limit: int = 50,
        offset: int = 0,
        active: Optional[bool] = None,
        archived: Optional[bool] = None
    ) -> MarketListResponse:
        """Get list of markets"""
        try:
            markets_data = await gamma_client.get_markets(
                limit=limit,
                offset=offset,
                active=active,
                archived=archived
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
    async def get_market(token_id: str) -> Optional[MarketDetail]:
        """Get market details by token ID"""
        try:
            # Check cache first
            cached = await get_cached_market(token_id)
            if cached:
                return MarketDetail(**cached)
            
            # Fetch from API
            market_data = await gamma_client.get_market_by_token_id(token_id)
            if market_data:
                market = gamma_client.map_api_to_market(market_data, token_id)
                
                # Cache the result
                await cache_market(market.model_dump())
                
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
