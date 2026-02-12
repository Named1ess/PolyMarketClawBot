# -*- coding: utf-8 -*-
"""
Monitoring service for real-time trade monitoring
"""
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.config import settings
from app.clients.polymarket import polymarket_client
from app.clients.wallet import wallet_client
from app.database import save_trade, save_position
from app.utils.logger import get_logger
from app.routes.websocket import broadcast_trade_update, broadcast_position_update

logger = get_logger(__name__)


class TradeMonitor:
    """Monitor trades and positions in real-time"""
    
    def __init__(self):
        self.running = False
        self.fetch_interval = settings.FETCH_INTERVAL
        self.too_old_timestamp = settings.TOO_OLD_TIMESTAMP
        self.last_trade_time: Optional[datetime] = None
        self.known_trades: Dict[str, bool] = {}
    
    async def start(self):
        """Start the trade monitor"""
        self.running = True
        logger.info("Starting trade monitor...")
        
        while self.running:
            try:
                await self.check_trades()
                await asyncio.sleep(self.fetch_interval)
            except Exception as e:
                logger.error(f"Error in trade monitor: {e}")
                await asyncio.sleep(self.fetch_interval)
    
    def stop(self):
        """Stop the trade monitor"""
        self.running = False
        logger.info("Trade monitor stopped")
    
    async def check_trades(self):
        """Check for new trades"""
        try:
            address = wallet_client.get_address()
            url = f"https://data-api.polymarket.com/events?user={address}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                # Process new trades
                trades = data.get("trades", [])
                for trade in trades:
                    tx_hash = trade.get("transactionHash")
                    if tx_hash and tx_hash not in self.known_trades:
                        self.known_trades[tx_hash] = True
                        
                        # Save trade to database
                        await save_trade({
                            "transaction_hash": tx_hash,
                            "token_id": trade.get("asset"),
                            "side": trade.get("side"),
                            "amount": trade.get("amount"),
                            "price": trade.get("price"),
                            "timestamp": datetime.utcnow(),
                        })
                        
                        # Broadcast to WebSocket clients
                        await broadcast_trade_update(trade)
                        
                        logger.info(f"New trade detected: {tx_hash}")
                
        except Exception as e:
            logger.error(f"Error checking trades: {e}")
    
    async def check_positions(self):
        """Check current positions"""
        try:
            positions = await polymarket_client.get_positions()
            
            for position in positions:
                token_id = position.get("asset")
                if token_id:
                    # Save position to database
                    await save_position({
                        "token_id": token_id,
                        "condition_id": position.get("conditionId"),
                        "size": position.get("size"),
                        "avg_price": position.get("avgPrice"),
                        "current_value": position.get("currentValue"),
                        "realized_pnl": position.get("realizedPnl"),
                        "unrealized_pnl": position.get("unrealizedPnl"),
                        "updated_at": datetime.utcnow(),
                    })
                    
                    # Broadcast to WebSocket clients
                    await broadcast_position_update(position)
                    
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
    
    async def get_recent_trades(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent trades for a time period"""
        try:
            address = wallet_client.get_address()
            url = f"https://data-api.polymarket.com/events?user={address}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                recent_trades = []
                
                for trade in data.get("trades", []):
                    trade_time = datetime.fromisoformat(
                        trade.get("timestamp", "").replace("Z", "+00:00")
                    )
                    if trade_time >= cutoff_time:
                        recent_trades.append(trade)
                
                return recent_trades
                
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []
    
    async def get_trade_history(self, token_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get trade history for a specific token"""
        try:
            url = f"https://data-api.polymarket.com/trades?conditionId={token_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                return data.get("trades", [])[:limit]
                
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []


# Singleton instance
trade_monitor = TradeMonitor()
