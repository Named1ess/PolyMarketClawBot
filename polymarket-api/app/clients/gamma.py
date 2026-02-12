# Gamma API Client
"""
Client for Polymarket Gamma API - Market and Event data
"""
import ast
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.config import settings
from app.utils.logger import get_logger
from app.models.markets import MarketResponse, EventResponse, MarketDetail, EventDetail

logger = get_logger(__name__)


class GammaClient:
    """Client for interacting with Polymarket Gamma API"""
    
    def __init__(self):
        self.base_url = settings.GAMMA_API_URL
        self.markets_endpoint = f"{self.base_url}/markets"
        self.events_endpoint = f"{self.base_url}/events"
    
    async def get_markets(
        self,
        limit: int = 50,
        offset: int = 0,
        active: Optional[bool] = None,
        archived: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch markets from Gamma API"""
        params = {
            "limit": limit,
            "offset": offset,
        }
        if active is not None:
            params["active"] = active
        if archived is not None:
            params["archived"] = archived
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.markets_endpoint, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Error fetching markets: {e}")
                raise
    
    async def get_market_by_token_id(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific market by token ID"""
        params = {"clob_token_ids": token_id}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.markets_endpoint, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data[0] if data else None
            except httpx.HTTPError as e:
                logger.error(f"Error fetching market {token_id}: {e}")
                return None
    
    async def get_events(
        self,
        limit: int = 50,
        offset: int = 0,
        active: Optional[bool] = None,
        archived: Optional[bool] = None,
        featured: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch events from Gamma API"""
        params = {
            "limit": limit,
            "offset": offset,
        }
        if active is not None:
            params["active"] = active
        if archived is not None:
            params["archived"] = archived
        if featured is not None:
            params["featured"] = featured
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.events_endpoint, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Error fetching events: {e}")
                raise
    
    async def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific event by ID"""
        endpoint = f"{self.events_endpoint}/{event_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Error fetching event {event_id}: {e}")
                return None
    
    def map_api_to_market(self, market_data: Dict[str, Any], token_id: str = "") -> MarketDetail:
        """Map API response to MarketDetail model"""
        try:
            outcome_prices = market_data.get("outcomePrices", [])
            clob_token_ids = market_data.get("clobTokenIds", [])
            
            return MarketDetail(
                id=str(market_data.get("id", "")),
                question=market_data.get("question", ""),
                slug=market_data.get("slug", ""),
                description=market_data.get("description"),
                end_date=market_data.get("endDate"),
                start_date=market_data.get("startDate"),
                active=market_data.get("active", False),
                archived=market_data.get("archived", False),
                closed=market_data.get("closed", False),
                funded=market_data.get("funded", False),
                outcomes=market_data.get("outcomes", []),
                outcome_prices=[float(p) for p in outcome_prices] if outcome_prices else [],
                volume=float(market_data.get("volume", 0)) if market_data.get("volume") else None,
                spread=float(market_data.get("spread", 0)) if market_data.get("spread") else None,
                rewards_min_size=float(market_data.get("rewardsMinSize", 0)) if market_data.get("rewardsMinSize") else None,
                rewards_max_spread=float(market_data.get("rewardsMaxSpread", 0)) if market_data.get("rewardsMaxSpread") else None,
                clob_token_ids=[str(tid) for tid in clob_token_ids] if clob_token_ids else [],
                tags=market_data.get("tags", []),
                liquidity=market_data.get("liquidity"),
                daily_volume=market_data.get("dailyVolume"),
                total_liquidity=market_data.get("totalLiquidity"),
                num_takers=market_data.get("numTakers"),
                order_min_size=market_data.get("orderMinSize"),
                order_price_min_tick_size=market_data.get("orderPriceMinTickSize"),
            )
        except Exception as e:
            logger.error(f"Error mapping market data: {e}")
            raise
    
    def map_api_to_event(self, event_data: Dict[str, Any]) -> EventDetail:
        """Map API response to EventDetail model"""
        try:
            markets = event_data.get("markets", [])
            market_ids = [str(m["id"]) for m in markets] if markets else []
            
            return EventDetail(
                id=str(event_data.get("id", "")),
                title=event_data.get("title", ""),
                slug=event_data.get("slug", ""),
                description=event_data.get("description"),
                start_date=event_data.get("startDate"),
                end_date=event_data.get("endDate"),
                active=event_data.get("active", False),
                archived=event_data.get("archived", False),
                closed=event_data.get("closed", False),
                featured=event_data.get("featured", False),
                new=event_data.get("new", False),
                restricted=event_data.get("restricted", False),
                markets=market_ids,
                tags=event_data.get("tags", []),
            )
        except Exception as e:
            logger.error(f"Error mapping event data: {e}")
            raise


# Singleton instance
gamma_client = GammaClient()
