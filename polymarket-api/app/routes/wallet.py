# Wallet Router
"""
Wallet-related API endpoints
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.clients.wallet import wallet_client
from app.clients.polymarket import polymarket_client
from app.models.user import (
    BalanceResponse, AllowancesResponse, ApprovalResponse, PortfolioSummary
)

wallet_router = APIRouter()


@wallet_router.get("/wallet/address")
async def get_wallet_address():
    """Get wallet address"""
    try:
        address = wallet_client.get_address()
        return {"address": address}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@wallet_router.get("/wallet/balance", response_model=BalanceResponse)
async def get_wallet_balance():
    """Get USDC balance"""
    try:
        balance = wallet_client.get_usdc_balance()
        return BalanceResponse(
            usdc_balance=balance,
            usdc_balance_raw=wallet_client.get_usdc_balance_raw(),
            wallet_address=wallet_client.get_address(),
            last_updated=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@wallet_router.get("/wallet/allowances", response_model=AllowancesResponse)
async def get_token_allowances():
    """Get token allowances for exchanges"""
    try:
        allowances = wallet_client.get_all_allowances()
        return AllowancesResponse(
            usdc_allowance_main=allowances.get("usdc_main", 0),
            usdc_allowance_neg_risk=allowances.get("usdc_neg_risk", 0),
            usdc_allowance_neg_risk_adapter=allowances.get("usdc_neg_risk_adapter", 0),
            ctf_allowance_main=0,
            ctf_allowance_neg_risk=0,
            ctf_allowance_neg_risk_adapter=0
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@wallet_router.post("/wallet/approve")
async def approve_tokens():
    """Approve tokens for all exchanges"""
    try:
        results = wallet_client.approve_all_tokens()
        return {
            "success": any(isinstance(v, str) and v.startswith("0x") for v in results.values()),
            "transactions": results
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@wallet_router.get("/positions")
async def get_positions():
    """Get user positions"""
    try:
        positions = await polymarket_client.get_positions()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@wallet_router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio():
    """Get portfolio summary"""
    try:
        positions = await polymarket_client.get_positions()
        
        total_value = sum(
            float(p.get("currentValue", 0) or 0) 
            for p in positions
        )
        
        realized_pnl = sum(
            float(p.get("realizedPnl", 0) or 0) 
            for p in positions
        )
        
        unrealized_pnl = sum(
            float(p.get("unrealizedPnl", 0) or 0) 
            for p in positions
        )
        
        return PortfolioSummary(
            total_positions_value=total_value,
            total_realized_pnl=realized_pnl,
            total_unrealized_pnl=unrealized_pnl,
            positions_count=len(positions),
            positions=[]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
