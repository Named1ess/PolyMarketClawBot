# Market Models
"""
Pydantic models for market and event data
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Outcome(BaseModel):
    """Market outcome"""
    name: str
    price: float


class MarketResponse(BaseModel):
    """Market information response"""
    id: str
    question: str
    slug: str
    description: Optional[str] = None
    end_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    active: bool
    archived: bool
    closed: bool
    funded: bool
    outcomes: List[str]
    outcome_prices: List[float]
    volume: Optional[float] = None
    spread: Optional[float] = None
    rewards_min_size: Optional[float] = None
    rewards_max_spread: Optional[float] = None
    clob_token_ids: List[str] = []
    # Token details for trading
    tokens: List[dict] = []
    condition_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MarketDetail(MarketResponse):
    """Detailed market information"""
    tags: List[str] = []
    liquidity: Optional[float] = None
    daily_volume: Optional[float] = None
    total_liquidity: Optional[float] = None
    num_takers: Optional[int] = None
    order_min_size: Optional[float] = None
    order_price_min_tick_size: Optional[float] = None


class EventResponse(BaseModel):
    """Event information response"""
    id: str
    title: str
    slug: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    active: bool
    archived: bool
    closed: bool
    featured: bool
    new: bool
    restricted: bool
    markets: List[str]  # Market IDs
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EventDetail(EventResponse):
    """Detailed event information"""
    tags: List[str] = []
    markets_detail: List[MarketResponse] = []


class MarketListResponse(BaseModel):
    """Response for listing markets"""
    markets: List[MarketResponse]
    total: int
    page: int = 1
    page_size: int = 20


class EventListResponse(BaseModel):
    """Response for listing events"""
    events: List[EventResponse]
    total: int
    page: int = 1
    page_size: int = 20


class TradeResponse(BaseModel):
    """Trade information"""
    transaction_hash: str
    token_id: str
    side: str  # BUY/SELL
    amount: float
    price: float
    maker_address: Optional[str] = None
    taker_address: Optional[str] = None
    timestamp: datetime
    gas_fees: Optional[float] = None
    order_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class TradeListResponse(BaseModel):
    """Response for listing trades"""
    trades: List[TradeResponse]
    total: int


class OrderBookEntry(BaseModel):
    """Single order book entry"""
    price: float
    size: float
    side: str  # BUY/SELL


class OrderBookResponse(BaseModel):
    """Order book response"""
    market_id: str
    token_id: str
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]
    spread: Optional[float] = None
    mid_price: Optional[float] = None


class PriceResponse(BaseModel):
    """Price information for a market"""
    token_id: str
    outcome: str
    price: float
    change_24h: Optional[float] = None
    volume_24h: Optional[float] = None
