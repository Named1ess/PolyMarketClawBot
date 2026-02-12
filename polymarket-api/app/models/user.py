# User Models
"""
Pydantic models for user and position data
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PositionResponse(BaseModel):
    """Position information"""
    token_id: str
    condition_id: str
    outcome: str
    size: float
    avg_price: float
    current_value: float
    realized_pnl: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    entry_value: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PositionDetail(PositionResponse):
    """Detailed position information"""
    market_question: Optional[str] = None
    market_slug: Optional[str] = None
    status: str = "ACTIVE"
    last_trade_price: Optional[float] = None


class PortfolioSummary(BaseModel):
    """Portfolio summary"""
    total_positions_value: float
    total_realized_pnl: float
    total_unrealized_pnl: float
    positions_count: int
    positions: List[PositionDetail]


class BalanceResponse(BaseModel):
    """Balance information"""
    usdc_balance: float
    usdc_balance_raw: int
    wallet_address: str
    last_updated: datetime


class AllowancesResponse(BaseModel):
    """Token allowances information"""
    usdc_allowance_main: float
    usdc_allowance_neg_risk: float
    usdc_allowance_neg_risk_adapter: float
    ctf_allowance_main: float
    ctf_allowance_neg_risk: float
    ctf_allowance_neg_risk_adapter: float


class ApprovalResponse(BaseModel):
    """Token approval response"""
    success: bool
    transaction_hash: str
    token: str
    spender: str
    amount: str
