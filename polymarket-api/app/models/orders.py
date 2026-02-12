# Order Models
"""
Pydantic models for order-related data
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    FOK = "FOK"  # Fill Or Kill
    GTC = "GTC"  # Good Till Cancel


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class OrderRequest(BaseModel):
    """Request model for creating an order"""
    token_id: str = Field(..., description="Market token ID (from market['tokens'][i]['token_id'])")
    condition_id: Optional[str] = Field(None, description="Market condition ID (from market['condition_id'])")
    side: OrderSide = Field(..., description="Order side (BUY/SELL)")
    amount: float = Field(..., gt=0, description="Amount in USDC (minimum $5)")
    price: Optional[float] = Field(None, ge=0, le=1, description="Limit price (0-1). Required for LIMIT/GTC orders.")
    order_type: OrderType = Field(default=OrderType.GTC, description="Order type (GTC, FOK, LIMIT)")
    nonce: Optional[str] = Field(None, description="Custom nonce for order identification")


class OrderResponse(BaseModel):
    """Response model for order data"""
    order_id: str
    transaction_hash: Optional[str] = None
    token_id: str
    side: OrderSide
    amount: float
    price: Optional[float]
    filled_amount: float = 0
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrderDetails(OrderResponse):
    """Detailed order information"""
    maker_address: Optional[str] = None
    fee_rate_bps: Optional[int] = None
    nonce: Optional[str] = None
    expiration: Optional[str] = None
    signature: Optional[str] = None
    avg_price: Optional[float] = None


class OrderListResponse(BaseModel):
    """Response for listing orders"""
    orders: List[OrderResponse]
    total: int
    page: int = 1
    page_size: int = 20


class CancelOrderResponse(BaseModel):
    """Response for order cancellation"""
    success: bool
    order_id: str
    message: str


class CancelAllOrdersResponse(BaseModel):
    """Response for cancel all orders"""
    success: bool
    cancelled_count: int
    message: str


class OrderBookEntry(BaseModel):
    """Order book entry"""
    price: float
    size: float


class OrderBookResponse(BaseModel):
    """Order book response"""
    market: str
    token_id: str
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]
    mid_price: Optional[float] = None
    spread: Optional[float] = None


class PriceResponse(BaseModel):
    """Price response"""
    token_id: str
    side: OrderSide
    price: float
    timestamp: datetime
