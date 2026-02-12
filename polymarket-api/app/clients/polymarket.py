# Polymarket CLOB Client
"""
Polymarket Central Limit Order Book (CLOB) client for trading
"""
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    ApiCreds, OrderArgs, MarketOrderArgs, OrderType, OpenOrderParams
)
from py_clob_client.order_builder.constants import BUY, SELL
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.utils.logger import get_logger
from app.models.orders import OrderStatus

logger = get_logger(__name__)


class PolymarketClient:
    """Client for interacting with Polymarket CLOB"""
    
    def __init__(self):
        self.host = settings.CLOB_HOST
        self.chain_id = settings.CHAIN_ID
        self.private_key = settings.POLYGON_WALLET_PRIVATE_KEY
        
        # Initialize CLOB client
        self.client = ClobClient(
            self.host,
            key=self.private_key,
            chain_id=self.chain_id
        )
        
        # Set API credentials if available
        if settings.CLOB_API_KEY and settings.CLOB_SECRET and settings.CLOB_PASS_PHRASE:
            creds = ApiCreds(
                api_key=settings.CLOB_API_KEY,
                api_secret=settings.CLOB_SECRET,
                api_passphrase=settings.CLOB_PASS_PHRASE
            )
            self.client.set_api_creds(creds)
            logger.info("API credentials set")
        else:
            # Try to derive API credentials from private key
            try:
                api_creds = self.client.create_or_derive_api_creds()
                self.client.set_api_creds(api_creds)
                logger.info("API credentials derived from private key")
            except Exception as e:
                logger.warning(f"Could not derive API credentials: {e}")
    
    def get_address(self) -> str:
        """Get wallet address"""
        if not self.private_key:
            raise ValueError("Private key not configured")
        from web3 import Web3
        w3 = Web3()
        account = w3.eth.account.from_key(self.private_key)
        return account.address
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def get_order_book(self, token_id: str) -> Dict[str, Any]:
        """Get order book for a token"""
        try:
            orderbook = self.client.get_order_book(token_id)
            return orderbook
        except Exception as e:
            logger.error(f"Error fetching orderbook for {token_id}: {e}")
            raise
    
    async def get_mid_price(self, token_id: str) -> Optional[float]:
        """Get midpoint price for a token"""
        try:
            mid = self.client.get_midpoint(token_id)
            return float(mid) if mid else None
        except Exception as e:
            logger.error(f"Error fetching mid price for {token_id}: {e}")
            return None
    
    async def get_price(self, token_id: str, side: str = "BUY") -> Optional[float]:
        """Get best price for a side"""
        try:
            price = self.client.get_price(token_id, side=side)
            return float(price) if price else None
        except Exception as e:
            logger.error(f"Error fetching price for {token_id}: {e}")
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def place_order(
        self,
        token_id: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        order_type: str = "FOK"
    ) -> Dict[str, Any]:
        """Place an order on Polymarket"""
        try:
            nonce = str(uuid.uuid4())
            side_enum = BUY if side.upper() == "BUY" else SELL
            
            if price is None:
                # Market order
                order_args = MarketOrderArgs(
                    token_id=token_id,
                    amount=amount,
                    side=side_enum,
                    order_type=OrderType[order_type]
                )
                signed_order = self.client.create_market_order(order_args)
            else:
                # Limit order
                order_args = OrderArgs(
                    token_id=token_id,
                    price=price,
                    size=amount,
                    side=side_enum
                )
                signed_order = self.client.create_order(order_args)
            
            response = self.client.post_order(signed_order, OrderType[order_type])
            
            logger.info(f"Order placed: {response}")
            
            return {
                "success": response.get("success", False),
                "order_id": response.get("orderId") or response.get("id"),
                "response": response,
                "nonce": nonce,
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
        """Cancel a specific order"""
        try:
            response = self.client.cancel(order_id)
            logger.info(f"Order {order_id} cancelled: {response}")
            return {
                "success": True,
                "order_id": order_id,
                "response": response
            }
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return {
                "success": False,
                "order_id": order_id,
                "error": str(e)
            }
    
    async def cancel_all_orders(self) -> Dict[str, Any]:
        """Cancel all open orders"""
        try:
            response = self.client.cancel_all()
            logger.info(f"All orders cancelled: {response}")
            return {
                "success": True,
                "response": response
            }
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get all open orders"""
        try:
            params = OpenOrderParams()
            orders = self.client.get_orders(params)
            return orders if orders else []
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get the status of a specific order"""
        try:
            order = self.client.get_order(order_id)
            return order if order else {}
        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            return {}
    
    async def get_trades(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user trades"""
        try:
            # Note: This requires API credentials
            if not hasattr(self.client, 'creds') or self.client.creds is None:
                logger.warning("API credentials required to fetch trades")
                return []
            
            trades = self.client.get_trades()
            return trades if trades else []
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get user positions from data API"""
        try:
            address = self.get_address()
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://data-api.polymarket.com/positions?user={address}",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    async def get_order_history(
        self,
        limit: int = 50,
        status: Optional[OrderStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get order history"""
        try:
            # This would require polling the order status
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error fetching order history: {e}")
            return []
    
    def parse_order_status(self, order_response: Dict[str, Any]) -> OrderStatus:
        """Parse order response to determine status"""
        if not order_response:
            return OrderStatus.FAILED
        
        # Check for filled status
        if order_response.get("status") == "FILLED":
            return OrderStatus.FILLED
        elif order_response.get("status") == "PARTIALLY_FILLED":
            return OrderStatus.PARTIALLY_FILLED
        elif order_response.get("status") == "CANCELLED":
            return OrderStatus.CANCELLED
        elif order_response.get("status") == "EXPIRED":
            return OrderStatus.EXPIRED
        elif order_response.get("status") == "OPEN":
            return OrderStatus.OPEN
        else:
            return OrderStatus.PENDING


# Singleton instance
polymarket_client = PolymarketClient()
