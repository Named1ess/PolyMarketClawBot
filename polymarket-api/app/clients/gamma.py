# Gamma API Client
"""
Client for Polymarket Gamma API - Market and Event data

API Documentation: https://docs.polymarket.com/api-reference/markets/list-markets

Supported Parameters:
- Pagination: limit, offset
- Sorting: order, ascending
- Filters: id, slug, clob_token_ids, condition_ids, market_maker_address
- Numeric ranges: liquidity_num_min/max, volume_num_min/max, rewards_min_size
- Date ranges: start_date_min/max, end_date_min/max (ISO 8601 format)
- Status: closed, active, archived, featured
- Tags: tag_id, related_tags, include_tag
- Special: cyom, uma_resolution_status, game_id, sports_market_types, question_ids
"""
import ast
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

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
    ) -> List[Dict[str, Any]]:
        """
        Fetch markets from Gamma API with comprehensive filtering options.

        Args:
            limit: Maximum number of markets to return (default: 50)
            offset: Number of markets to skip for pagination (default: 0)
            order: Comma-separated list of fields to order by (e.g., "volumeNum,endDate")
            ascending: Sort order (true for ascending, false for descending)
            ids: Filter by market IDs
            slugs: Filter by market slugs
            clob_token_ids: Filter by CLOB token IDs
            condition_ids: Filter by condition IDs
            question_ids: Filter by question IDs
            market_maker_address: Filter by market maker wallet address
            liquidity_num_min/max: Filter by liquidity number range
            volume_num_min/max: Filter by volume number range
            rewards_min_size: Minimum reward size
            start_date_min/max: Filter by market start date range (ISO 8601 format)
            end_date_min/max: Filter by market end date range (ISO 8601 format)
            active: Filter by active status
            archived: Filter by archived status
            closed: Filter by closed status
            featured: Filter by featured status
            tag_id: Filter by tag ID
            related_tags: Include related tags
            include_tag: Include tag information
            cyom: "Create Your Own Market" filter
            uma_resolution_status: UMA resolution status filter
            game_id: Filter by game ID (for sports markets)
            sports_market_types: Filter by sports market types

        Returns:
            List of market dictionaries from Gamma API
        """
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        # Sorting parameters
        if order is not None:
            params["order"] = order
        if ascending is not None:
            params["ascending"] = ascending

        # ID filters - convert lists to comma-separated strings
        if ids is not None:
            params["id"] = ",".join(str(i) for i in ids) if isinstance(ids, list) else ids
        if slugs is not None:
            params["slug"] = ",".join(slugs) if isinstance(slugs, list) else slugs
        if clob_token_ids is not None:
            params["clob_token_ids"] = ",".join(clob_token_ids) if isinstance(clob_token_ids, list) else clob_token_ids
        if condition_ids is not None:
            params["condition_ids"] = ",".join(condition_ids) if isinstance(condition_ids, list) else condition_ids
        if question_ids is not None:
            params["question_ids"] = ",".join(question_ids) if isinstance(question_ids, list) else question_ids

        # Address filters
        if market_maker_address is not None:
            params["market_maker_address"] = market_maker_address

        # Numeric range filters
        if liquidity_num_min is not None:
            params["liquidity_num_min"] = liquidity_num_min
        if liquidity_num_max is not None:
            params["liquidity_num_max"] = liquidity_num_max
        if volume_num_min is not None:
            params["volume_num_min"] = volume_num_min
        if volume_num_max is not None:
            params["volume_num_max"] = volume_num_max
        if rewards_min_size is not None:
            params["rewards_min_size"] = rewards_min_size

        # Date range filters (ISO 8601 format)
        if start_date_min is not None:
            params["start_date_min"] = start_date_min
        if start_date_max is not None:
            params["start_date_max"] = start_date_max
        if end_date_min is not None:
            params["end_date_min"] = end_date_min
        if end_date_max is not None:
            params["end_date_max"] = end_date_max

        # Status filters
        if active is not None:
            params["active"] = active
        if archived is not None:
            params["archived"] = archived
        if closed is not None:
            params["closed"] = closed
        if featured is not None:
            params["featured"] = featured

        # Tag filters
        if tag_id is not None:
            params["tag_id"] = tag_id
        if related_tags is not None:
            params["related_tags"] = related_tags
        if include_tag is not None:
            params["include_tag"] = include_tag

        # Special filters
        if cyom is not None:
            params["cyom"] = cyom
        if uma_resolution_status is not None:
            params["uma_resolution_status"] = uma_resolution_status
        if game_id is not None:
            params["game_id"] = game_id
        if sports_market_types is not None:
            params["sports_market_types"] = ",".join(sports_market_types) if isinstance(sports_market_types, list) else sports_market_types

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
    
    def _safe_float(self, value, default=None):
        """Safely convert value to float, handling string arrays and other edge cases"""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Handle edge cases like '[' or '[]'
            if value in ('[', ']', '', 'nan', 'inf', '-inf'):
                return default
            try:
                return float(value)
            except ValueError:
                return default
        # Handle lists (take first element if numeric)
        if isinstance(value, list):
            if len(value) > 0:
                return self._safe_float(value[0], default)
            return default
        return default

    def _safe_parse_json_list(self, value, default=None):
        """Safely parse a JSON string or list into a Python list"""
        if value is None:
            return default if default is not None else []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            if not value:
                return default if default is not None else []
            # Try to parse as JSON
            try:
                import json
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            # Try to parse with ast.literal_eval
            try:
                parsed = ast.literal_eval(value)
                if isinstance(parsed, list):
                    return parsed
            except (ValueError, SyntaxError):
                pass
            # Return as single element list if it's a non-empty string
            return [value] if value else []
        return default if default is not None else []

    def map_api_to_market(self, market_data: Dict[str, Any], token_id: str = "") -> MarketDetail:
        """Map API response to MarketDetail model"""
        try:
            outcome_prices = self._safe_parse_json_list(market_data.get("outcomePrices", []))
            clob_token_ids = self._safe_parse_json_list(market_data.get("clobTokenIds", []))
            outcomes = self._safe_parse_json_list(market_data.get("outcomes", []))

            # Get first token_id if not provided
            if not token_id and clob_token_ids:
                token_id = str(clob_token_ids[0])

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
                outcomes=outcomes,
                outcome_prices=[float(p) for p in outcome_prices if p],
                volume=self._safe_float(market_data.get("volume")),
                spread=self._safe_float(market_data.get("spread")),
                rewards_min_size=self._safe_float(market_data.get("rewardsMinSize")),
                rewards_max_spread=self._safe_float(market_data.get("rewardsMaxSpread")),
                clob_token_ids=[str(tid) for tid in clob_token_ids],
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
    
    def _safe_parse_tags(self, tags):
        """Safely parse tags - they can be strings or dicts with 'label' field"""
        if tags is None:
            return []
        if isinstance(tags, list):
            result = []
            for tag in tags:
                if isinstance(tag, str):
                    result.append(tag)
                elif isinstance(tag, dict) and tag.get('label'):
                    result.append(tag['label'])
            return result
        return []

    def map_api_to_event(self, event_data: Dict[str, Any]) -> EventDetail:
        """Map API response to EventDetail model"""
        try:
            markets = event_data.get("markets", [])
            market_ids = [str(m["id"]) for m in markets] if markets else []

            # Safely parse tags
            tags = self._safe_parse_tags(event_data.get("tags", []))

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
                tags=tags,
            )
        except Exception as e:
            logger.error(f"Error mapping event data: {e}")
            raise


# Singleton instance
gamma_client = GammaClient()
