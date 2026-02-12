# Order Service
"""
Business logic for order management
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.config import settings
from app.clients.polymarket import polymarket_client
from app.clients.wallet import wallet_client
from app.database import save_order, update_order, get_order
from app.models.orders import OrderStatus, OrderRequest
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OrderService:
    """Service for managing orders"""
    
    @staticmethod
    async def create_order(request: OrderRequest) -> Dict[str, Any]:
        """Create and place a new order"""
        try:
            # Generate order ID
            order_id = str(uuid.uuid4())
            
            # Place order on Polymarket
            result = await polymarket_client.place_order(
                token_id=request.token_id,
                side=request.side.value,
                amount=request.amount,
                price=request.price,
                order_type=request.order_type.value
            )
            
            # Determine order status
            if result.get("success"):
                status = OrderStatus.OPEN
            else:
                status = OrderStatus.FAILED
            
            # Create order record
            order_data = {
                "order_id": order_id,
                "transaction_hash": result.get("response", {}).get("hash"),
                "token_id": request.token_id,
                "side": request.side.value,
                "amount": request.amount,
                "price": request.price,
                "filled_amount": 0,
                "status": status.value,
                "nonce": request.nonce,
                "response": result.get("response"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Save to database
            await save_order(order_data)
            
            logger.info(f"Order created: {order_id}")
            
            return {
                "success": result.get("success", False),
                "order_id": order_id,
                "status": status.value,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def get_order(order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        return await get_order(order_id)
    
    @staticmethod
    async def cancel_order(order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            # Get order from database
            order = await get_order(order_id)
            if not order:
                return {
                    "success": False,
                    "error": "Order not found"
                }
            
            # Cancel on Polymarket
            result = await polymarket_client.cancel_order(order_id)
            
            if result.get("success"):
                # Update order status
                await update_order(order_id, {
                    "status": OrderStatus.CANCELLED.value,
                    "updated_at": datetime.utcnow()
                })
            
            logger.info(f"Order {order_id} cancellation: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def cancel_all_orders() -> Dict[str, Any]:
        """Cancel all open orders"""
        try:
            result = await polymarket_client.cancel_all_orders()
            
            if result.get("success"):
                logger.info("All orders cancelled")
            
            return result
            
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def get_open_orders() -> List[Dict[str, Any]]:
        """Get all open orders"""
        return await polymarket_client.get_open_orders()
    
    @staticmethod
    async def get_order_status(order_id: str) -> Dict[str, Any]:
        """Get order status from Polymarket"""
        return await polymarket_client.get_order_status(order_id)


# Singleton instance
order_service = OrderService()
