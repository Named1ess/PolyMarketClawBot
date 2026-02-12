# Polymarket CLOB Client
"""
Polymarket Central Limit Order Book (CLOB) client for trading

Based on: https://docs.polymarket.com/quickstart/first-order

Features:
- Uses static API credentials from .env
- Async-friendly methods
- Error handling
"""
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    ApiCreds, OrderArgs, MarketOrderArgs, OpenOrderParams
)
from py_clob_client.order_builder.constants import BUY, SELL
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Thread pool executor for running sync CLOB calls
_executor = ThreadPoolExecutor(max_workers=4)


def _run_sync(func, *args, **kwargs):
    """Run sync function in thread pool executor"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_in_executor(None, lambda: func(*args, **kwargs)).result()
    finally:
        loop.close()


class PolymarketClient:
    """Client for interacting with Polymarket CLOB"""
    
    def __init__(self):
        self.host = settings.CLOB_HOST
        self.chain_id = settings.CHAIN_ID
        self.private_key = settings.POLYGON_WALLET_PRIVATE_KEY
        self.wallet_address = settings.WALLET_ADDRESS
        self.signature_type = 0  # 0=EOA, 1=POLY_PROXY, 2=GNOSIS_SAFE
        
        self._init_client()
    
    def _init_client(self):
        """Initialize client with proper authentication"""
        # Get credentials from settings
        api_key = settings.CLOB_API_KEY
        api_secret = settings.CLOB_SECRET
        api_passphrase = settings.CLOB_PASS_PHRASE
        
        # Initialize with credentials if available
        if api_key and api_secret and api_passphrase:
            try:
                creds = ApiCreds(
                    api_key=api_key,
                    api_secret=api_secret,
                    api_passphrase=api_passphrase
                )
                
                # Initialize with full Level 2 auth
                self.client = ClobClient(
                    self.host,
                    key=self.private_key,
                    chain_id=self.chain_id,
                    creds=creds,
                    signature_type=self.signature_type,
                    funder=self.wallet_address
                )
                logger.info("Initialized with static API credentials (Level 2)")
                
            except Exception as e:
                logger.warning(f"Failed to initialize with static credentials: {e}")
                # Fall back to Level 1
                self.client = ClobClient(
                    self.host,
                    key=self.private_key,
                    chain_id=self.chain_id
                )
                logger.info("Initialized with private key only (Level 1)")
        else:
            # No static credentials, use private key only
            self.client = ClobClient(
                self.host,
                key=self.private_key,
                chain_id=self.chain_id
            )
            logger.info("Initialized with private key only (Level 1)")
    
    async def get_markets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of markets"""
        try:
            return _run_sync(self.client.get_sampling_markets) or []
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    async def get_market(self, market_id: str) -> Dict[str, Any]:
        """Get market details"""
        try:
            return _run_sync(self.client.get_market, market_id) or {}
        except Exception as e:
            logger.error(f"Error fetching market {market_id}: {e}")
            return {}
    
    async def get_order_book(self, token_id: str) -> Dict[str, Any]:
        """Get order book for a token"""
        try:
            return _run_sync(self.client.get_order_book, token_id) or {}
        except Exception as e:
            logger.error(f"Error fetching orderbook for {token_id}: {e}")
            return {}
    
    async def get_mid_price(self, token_id: str) -> Optional[float]:
        """Get midpoint price"""
        try:
            mid = _run_sync(self.client.get_midpoint, token_id)
            return float(mid) if mid else None
        except Exception as e:
            logger.error(f"Error fetching mid price for {token_id}: {e}")
            return None
    
    async def get_price(self, token_id: str, side: str = "BUY") -> Optional[float]:
        """Get best price"""
        try:
            price = _run_sync(self.client.get_price, token_id, side=side)
            return float(price) if price else None
        except Exception as e:
            logger.error(f"Error fetching price for {token_id}: {e}")
            return None
    
    async def get_open_orders(self, market: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open orders"""
        try:
            params = OpenOrderParams(market=market) if market else OpenOrderParams()
            result = _run_sync(self.client.get_orders, params)
            return result or []
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        try:
            return _run_sync(self.client.get_order, order_id) or {}
        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            return {}
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def place_order(
        self,
        token_id: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        order_type: str = "GTC"
    ) -> Dict[str, Any]:
        """
        Place an order on Polymarket
        Per docs: Use create_and_post_order() for proper order placement
        """
        try:
            side_enum = BUY if side.upper() == "BUY" else SELL
            
            # Get market info
            try:
                market = _run_sync(self.client.get_market, token_id)
                tick_size = market.get("tickSize", "0.01") if market else "0.01"
                neg_risk = market.get("negRisk", False) if market else False
            except:
                tick_size = "0.01"
                neg_risk = False
            
            # Build order
            if price is None:
                order_args = MarketOrderArgs(
                    token_id=token_id,
                    amount=amount,
                    side=side_enum,
                    order_type=order_type
                )
                options = {"tick_size": tick_size, "neg_risk": neg_risk}
                response = _run_sync(self.client.create_and_post_order, order_args, options)
            else:
                order_args = OrderArgs(
                    token_id=token_id,
                    price=price,
                    size=amount,
                    side=side_enum
                )
                options = {"tick_size": tick_size, "neg_risk": neg_risk}
                response = _run_sync(self.client.create_and_post_order, order_args, options, order_type)
            
            logger.info(f"Order placed: {response}")
            
            return {
                "success": True,
                "order_id": response.get("orderID") or response.get("id"),
                "status": response.get("status"),
                "response": response,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            response = _run_sync(self.client.cancel, order_id)
            return {"success": True, "order_id": order_id, "response": response}
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_all_orders(self) -> Dict[str, Any]:
        """Cancel all orders"""
        try:
            response = _run_sync(self.client.cancel_all)
            return {"success": True, "response": response}
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_trades(self) -> List[Dict[str, Any]]:
        """Get user's trades"""
        try:
            return _run_sync(self.client.get_trades) or []
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get user's positions"""
        try:
            return _run_sync(self.client.get_positions) or []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get user's balance"""
        try:
            return _run_sync(self.client.get_balance_allowance) or {}
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {}


# Singleton instance
polymarket_client = PolymarketClient()
