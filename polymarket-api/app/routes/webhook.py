# Webhook Router
"""
OpenClaw webhook integration endpoints
"""
import hmac
import hashlib
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from app.services.order_service import order_service
from app.models.orders import OrderRequest, OrderSide, OrderType
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

webhook_router = APIRouter()


class ClawWebhookPayload(BaseModel):
    """OpenClaw webhook payload"""
    token_id: str
    side: str  # BUY or SELL
    amount: float
    price: Optional[float] = None
    order_type: str = "FOK"
    webhook_id: Optional[str] = None
    metadata: Optional[dict] = None


class WebhookResponse(BaseModel):
    """Webhook response"""
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify webhook signature"""
    if not settings.OPENCLAW_WEBHOOK_SECRET:
        return True  # Skip verification if secret not configured
    
    expected = hmac.new(
        settings.OPENCLAW_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, f"sha256={expected}")


@webhook_router.post("/webhook/claw", response_model=WebhookResponse)
async def claw_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
):
    """
    OpenClaw trade webhook endpoint
    OpenClaw sends trade signals to this endpoint
    """
    try:
        body = await request.body()
        
        # Verify signature if configured
        if x_webhook_signature and settings.OPENCLAW_WEBHOOK_SECRET:
            if not verify_webhook_signature(body, x_webhook_signature):
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        try:
            data = await request.json()
        except:
            data = json.loads(body)
        
        # Validate required fields
        required_fields = ["token_id", "side", "amount"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")
        
        # Map side string to enum
        side_map = {"BUY": OrderSide.BUY, "SELL": OrderSide.SELL}
        side = side_map.get(data["side"].upper())
        if not side:
            raise HTTPException(status_code=400, detail="Invalid side")
        
        # Create order request
        order_request = OrderRequest(
            token_id=data["token_id"],
            side=side,
            amount=float(data["amount"]),
            price=float(data["price"]) if data.get("price") else None,
            order_type=OrderType[data.get("order_type", "FOK").upper()]
        )
        
        # Execute order
        result = await order_service.create_order(order_request)
        
        logger.info(f"Claw webhook order: {result}")
        
        return WebhookResponse(
            success=result.get("success", False),
            order_id=result.get("order_id"),
            error=result.get("error"),
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return WebhookResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow()
        )


@webhook_router.post("/webhook/order-status")
async def order_status_webhook(request: Request):
    """
    Order status webhook for receiving updates
    """
    try:
        data = await request.json()
        
        order_id = data.get("order_id")
        status = data.get("status")
        
        logger.info(f"Order status update: {order_id} -> {status}")
        
        return {"received": True, "order_id": order_id}
        
    except Exception as e:
        logger.error(f"Status webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@webhook_router.get("/webhook/health")
async def webhook_health():
    """Webhook endpoint health check"""
    return {"status": "ready"}
