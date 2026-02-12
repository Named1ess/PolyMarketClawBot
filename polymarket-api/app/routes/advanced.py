# Advanced Features Router
"""
Advanced features API endpoints: trading limits, price history, alerts, etc.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.advanced import (
    trading_limits_service,
    price_history_service,
    market_context_service,
    price_alert_service,
)
from app.services.market_import import market_import_service

advanced_router = APIRouter()


# Pydantic models for requests
class CreateAlertRequest(BaseModel):
    """Request for creating a price alert"""
    token_id: str
    side: str = "yes"  # "yes" or "no"
    condition: str  # "above", "below", "crosses_above", "crosses_below"
    threshold: float
    webhook_url: Optional[str] = None


class UpdateLimitsRequest(BaseModel):
    """Request for updating trading limits"""
    max_trade_usd: Optional[float] = None
    max_daily_usd: Optional[float] = None
    max_position_usd: Optional[float] = None
    max_daily_trades: Optional[int] = None


# Trading Limits Endpoints
@advanced_router.get("/trading/limits")
async def get_trading_limits():
    """Get current trading limits and usage"""
    return {
        "enabled": trading_limits_service.is_enabled,
        "limits": trading_limits_service.get_remaining_limits(),
        "config": {
            "max_trade_usd": trading_limits_service.limits.max_trade_usd,
            "max_daily_usd": trading_limits_service.limits.max_daily_usd,
            "max_position_usd": trading_limits_service.limits.max_position_usd,
            "max_daily_trades": trading_limits_service.limits.max_daily_trades,
        }
    }


@advanced_router.get("/trading/daily-stats")
async def get_daily_stats():
    """Get today's trading statistics"""
    stats = trading_limits_service.get_daily_stats()
    return {
        "date": stats.date,
        "total_trades": stats.total_trades,
        "total_volume_usd": stats.total_volume_usd,
        "buy_volume_usd": stats.buy_volume_usd,
        "sell_volume_usd": stats.sell_volume_usd,
        "realized_pnl": stats.realized_pnl,
    }


@advanced_router.post("/trading/can-trade")
async def check_trade_allowed(amount_usd: float = Query(..., gt=0), side: str = "BUY"):
    """Check if a trade is allowed based on limits"""
    allowed, reason = trading_limits_service.can_trade(amount_usd, side)
    return {
        "allowed": allowed,
        "reason": reason,
        "amount_usd": amount_usd,
        "side": side,
    }


# Price History Endpoints
@advanced_router.get("/markets/{token_id}/price-history")
async def get_price_history(
    token_id: str,
    hours: int = Query(default=24, ge=1, le=168),
    interval_minutes: int = Query(default=5, ge=1, le=60)
):
    """Get price history for a market"""
    history = await price_history_service.get_price_history(
        token_id=token_id,
        hours=hours,
        interval_minutes=interval_minutes
    )
    trend = price_history_service.analyze_trend(history)
    return {
        "token_id": token_id,
        "hours": hours,
        "data_points": len(history),
        "history": history,
        "trend": trend,
    }


# Market Context Endpoints
@advanced_router.get("/markets/{token_id}/context")
async def get_market_context(token_id: str):
    """Get market context with trading safeguards"""
    context = await market_context_service.get_market_context(token_id)
    return context


# Price Alerts Endpoints
@advanced_router.post("/alerts")
async def create_alert(request: CreateAlertRequest):
    """Create a price alert"""
    try:
        alert = price_alert_service.create_alert(
            token_id=request.token_id,
            side=request.side,
            condition=request.condition,
            threshold=request.threshold,
            webhook_url=request.webhook_url
        )
        return alert
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@advanced_router.get("/alerts")
async def get_alerts(include_triggered: bool = False):
    """Get all price alerts"""
    alerts = price_alert_service.get_alerts(include_triggered=include_triggered)
    return {
        "alerts": alerts,
        "count": len(alerts),
    }


@advanced_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete a price alert"""
    success = price_alert_service.delete_alert(alert_id)
    if success:
        return {"success": True, "alert_id": alert_id}
    raise HTTPException(status_code=404, detail="Alert not found")


# Market Import Endpoints
@advanced_router.get("/markets/importable")
async def get_importable_markets(
    min_volume: float = Query(default=10000, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    category: Optional[str] = Query(default=None)
):
    """Get list of importable Polymarket markets"""
    markets = await market_import_service.get_importable_markets(
        min_volume=min_volume,
        limit=limit,
        category=category
    )
    return {
        "markets": markets,
        "count": len(markets),
    }


@advanced_router.post("/markets/import")
async def import_market(polymarket_url: str):
    """Import a Polymarket market for tracking"""
    try:
        result = await market_import_service.import_market(polymarket_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@advanced_router.get("/markets/imported")
async def get_imported_markets():
    """Get all imported markets"""
    markets = market_import_service.get_imported_markets()
    return {
        "markets": markets,
        "count": len(markets),
    }


@advanced_router.get("/markets/imported/{market_id}")
async def get_imported_market(market_id: str):
    """Get a specific imported market"""
    market = market_import_service.get_imported_market(market_id)
    if market:
        return market
    raise HTTPException(status_code=404, detail="Imported market not found")


@advanced_router.post("/markets/imported/{market_id}/sync")
async def sync_imported_market(market_id: str):
    """Sync an imported market with latest data"""
    try:
        result = await market_import_service.sync_market(market_id)
        if result:
            return result
        raise HTTPException(status_code=404, detail="Imported market not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Combined Portfolio Summary
@advanced_router.get("/portfolio/summary")
async def get_portfolio_summary():
    """Get complete portfolio summary including positions, stats, and limits"""
    from app.clients.polymarket import polymarket_client
    
    # Get positions
    positions = await polymarket_client.get_positions()
    
    # Get daily stats
    stats = trading_limits_service.get_daily_stats()
    
    # Get remaining limits
    limits = trading_limits_service.get_remaining_limits()
    
    # Calculate totals
    total_value = sum(float(p.get("currentValue", 0) or 0) for p in positions)
    total_pnl = sum(float(p.get("unrealizedPnl", 0) or 0) for p in positions)
    
    return {
        "positions": {
            "count": len(positions),
            "total_value_usd": total_value,
            "total_unrealized_pnl": total_pnl,
        },
        "daily_stats": {
            "date": stats.date,
            "trades": stats.total_trades,
            "volume_usd": stats.total_volume_usd,
            "realized_pnl": stats.realized_pnl,
        },
        "trading_limits": limits,
        "imported_markets_count": len(market_import_service.get_imported_markets()),
        "active_alerts_count": len(price_alert_service.get_alerts()),
    }
