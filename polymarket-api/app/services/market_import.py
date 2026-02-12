# Market Import Service
"""
Service for importing Polymarket markets for tracking and trading
"""
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx
from app.config import settings
from app.database import cache_market
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketImportService:
    """Service for importing and tracking Polymarket markets"""
    
    # URL patterns for Polymarket
    POLYMARKET_URL_PATTERN = re.compile(
        r"https?://(www\.)?polymarket\.com/(event|market)/([a-zA-Z0-9-]+)"
    )
    
    # Common categories
    CATEGORIES = [
        "politics", "crypto", "economics", "sports", 
        "science", "entertainment", "technology", "news"
    ]
    
    def __init__(self):
        self.imported_markets: Dict[str, Dict] = {}
    
    def extract_condition_id(self, polymarket_url: str) -> Optional[str]:
        """
        Extract condition ID from Polymarket URL.
        
        Example: 
            https://polymarket.com/event/btc-updown-15m-1739902800
            -> condition_id or slug
        """
        match = self.POLYMARKET_URL_PATTERN.search(polymarket_url)
        if match:
            return match.group(3)
        return None
    
    def parse_url(self, url: str) -> Dict[str, Any]:
        """
        Parse a Polymarket URL to extract information.
        
        Returns:
            Dict with url, slug, type (event/market)
        """
        match = self.POLYMARKET_URL_PATTERN.search(url)
        if not match:
            raise ValueError(f"Invalid Polymarket URL: {url}")
        
        return {
            "original_url": url,
            "slug": match.group(3),
            "type": match.group(2),  # event or market
        }
    
    async def get_importable_markets(
        self,
        min_volume: float = 10000,
        limit: int = 50,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of importable Polymarket markets.
        
        These are markets that can be imported for tracking.
        
        Args:
            min_volume: Minimum 24h volume in USD
            limit: Maximum number of markets to return
            category: Filter by category (e.g., "politics", "crypto")
            
        Returns:
            List of market dicts with question, url, condition_id, volume_24h
        """
        try:
            params = {
                "limit": limit,
                "active": True,
            }
            
            if min_volume > 0:
                params["min_volume"] = min_volume
            
            if category:
                params["category"] = category
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.GAMMA_API_URL}/markets",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                markets = []
                for m in data:
                    url = f"https://polymarket.com/event/{m.get('slug', '')}"
                    markets.append({
                        "question": m.get("question", ""),
                        "slug": m.get("slug", ""),
                        "url": url,
                        "condition_id": m.get("conditionId"),
                        "volume_24h": m.get("volume24h", 0),
                        "current_price": m.get("outcomePrices", [0.5, 0.5]),
                        "active": m.get("active", True),
                        "end_date": m.get("endDate"),
                    })
                
                return markets
                
        except Exception as e:
            logger.error(f"Error fetching importable markets: {e}")
            return []
    
    async def import_market(self, polymarket_url: str) -> Dict[str, Any]:
        """
        Import a Polymarket market for tracking.
        
        This fetches full market data and caches it locally.
        
        Args:
            polymarket_url: Full Polymarket event URL
            
        Returns:
            Dict with market_id, question, token_ids, and import details
        """
        try:
            # Parse URL
            parsed = self.parse_url(polymarket_url)
            slug = parsed["slug"]
            
            # Fetch market data from Gamma API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.GAMMA_API_URL}/markets",
                    params={"slug": slug},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    raise ValueError(f"Market not found: {polymarket_url}")
                
                market_data = data[0]
                
                # Extract key information
                token_ids = market_data.get("clobTokenIds", [])
                outcome_prices = market_data.get("outcomePrices", [])
                outcomes = market_data.get("outcomes", [])
                
                import_result = {
                    "market_id": f"poly_{market_data.get('id', slug)}",
                    "slug": slug,
                    "question": market_data.get("question", ""),
                    "description": market_data.get("description", ""),
                    "imported_at": datetime.utcnow().isoformat(),
                    "import_url": polymarket_url,
                    "token_ids": [str(tid) for tid in token_ids] if token_ids else [],
                    "outcomes": outcomes,
                    "outcome_prices": [float(p) for p in outcome_prices] if outcome_prices else [],
                    "active": market_data.get("active", True),
                    "end_date": market_data.get("endDate"),
                    "volume": market_data.get("volume", 0),
                    "spread": market_data.get("spread", 0),
                }
                
                # Cache the market data
                await cache_market({
                    **import_result,
                    "token_id": token_ids[0] if token_ids else None,
                })
                
                # Store in imported markets
                self.imported_markets[import_result["market_id"]] = import_result
                
                logger.info(f"Market imported: {import_result['market_id']}")
                
                return import_result
                
        except Exception as e:
            logger.error(f"Error importing market {polymarket_url}: {e}")
            raise
    
    def get_imported_markets(self) -> List[Dict[str, Any]]:
        """Get all imported markets"""
        return list(self.imported_markets.values())
    
    def get_imported_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific imported market"""
        return self.imported_markets.get(market_id)
    
    def categorize_market(self, question: str) -> List[str]:
        """
        Auto-categorize a market based on keywords in the question.
        
        Returns:
            List of matching categories
        """
        question_lower = question.lower()
        matched = []
        
        keywords = {
            "politics": ["election", "president", "government", "policy", "vote", "congress", "senate"],
            "crypto": ["bitcoin", "ethereum", "crypto", "btc", "eth", "token", "blockchain"],
            "economics": ["gdp", "inflation", "interest", "recession", "unemployment", "economy"],
            "sports": ["game", "championship", "season", "team", "player", "match", "win"],
            "science": ["research", "study", "discover", "climate", "space", "temperature"],
            "entertainment": ["award", "movie", "music", "oscar", "grammy", "release"],
            "technology": ["ai", "tech", "software", "device", "launch", "apple", "google", "microsoft"],
            "news": ["breaking", "report", "announcement", "update", "latest"],
        }
        
        for category, words in keywords.items():
            for word in words:
                if word in question_lower:
                    matched.append(category)
                    break
        
        return matched if matched else ["other"]
    
    async def sync_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        Sync an imported market with latest data from Polymarket.
        
        Args:
            market_id: The imported market ID
            
        Returns:
            Updated market data or None if not found
        """
        import_info = self.imported_markets.get(market_id)
        if not import_info:
            return None
        
        try:
            # Re-import to get fresh data
            return await self.import_market(import_info["import_url"])
        except Exception as e:
            logger.error(f"Error syncing market {market_id}: {e}")
            return None


# Singleton instance
market_import_service = MarketImportService()
