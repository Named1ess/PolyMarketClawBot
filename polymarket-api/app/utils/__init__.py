# Utils Package
", "file_path": "c:\Users\lenovo\Documents\Github\PolyMarketClawBot\polymarket-api\app\utils\__init__.py"}{"contents": "# Logging Setup
"""
Logging configuration
"""
import json
import logging
import sys
from datetime import datetime
from pythonjsonlogger import jsonlogger
from app.config import settings
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging"""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
def setup_logging():
    """Setup application logging"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Clear existing handlers
    root = logging.getLogger()
    root.handlers.clear()
    
    # Set level
    root.setLevel(log_level)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Format based on config
    if settings.LOG_FORMAT == "json":
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
        handler.setFormatter(formatter)
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
    
    root.addHandler(handler)
def get_logger(name: str):
    """Get a logger instance"""
    return logging.getLogger(name)
", "file_path": "c:\Users\lenovo\Documents\Github\PolyMarketClawBot\polymarket-api\app\utils\logger.py"}{"contents": "# WebSocket Router
"""
WebSocket endpoints for real-time updates
"""
import asyncio
import json
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.logger import get_logger
logger = get_logger(__name__)
websocket_router = APIRouter()
# Connection managers
class ConnectionManager:
    """Manages WebSocket connections"""
    def __init__(self):
        self.orders_connections: Set[WebSocket] = set()
        self.trades_connections: Set[WebSocket] = set()
        self.positions_connections: Set[WebSocket] = set()
    async def connect(self, websocket: WebSocket, channel: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        if channel == "orders":
            self.orders_connections.add(websocket)
        elif channel == "trades":
            self.trades_connections.add(websocket)
        elif channel == "positions":
            self.positions_connections.add(websocket)
        logger.info(f"WebSocket connected: {channel}")
    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a WebSocket connection"""
        if channel == "orders":
            self.orders_connections.discard(websocket)
        elif channel == "trades":
            self.trades_connections.discard(websocket)
        elif channel == "positions":
            self.positions_connections.discard(websocket)
        logger.info(f"WebSocket disconnected: {channel}")
    async def broadcast(self, message: dict, channel: str):
        """Broadcast message to all connections in a channel"""
        connections = []
        if channel == "orders":
            connections = list(self.orders_connections)
        elif channel == "trades":
            connections = list(self.trades_connections)
        elif channel == "positions":
            connections = list(self.positions_connections)
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
# Singleton connection manager
manager = ConnectionManager()
@websocket_router.websocket("/ws/orders")
async def websocket_orders(websocket: WebSocket):
    """WebSocket endpoint for order updates"""
    await manager.connect(websocket, "orders")
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            logger.debug(f"Received from orders WS: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, "orders")
@websocket_router.websocket("/ws/trades")
async def websocket_trades(websocket: WebSocket):
    """WebSocket endpoint for trade updates"""
    await manager.connect(websocket, "trades")
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received from trades WS: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, "trades")
@websocket_router.websocket("/ws/positions")
async def websocket_positions(websocket: WebSocket):
    """WebSocket endpoint for position updates"""
    await manager.connect(websocket, "positions")
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received from positions WS: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, "positions")
async def broadcast_order_update(order_data: dict):
    """Broadcast order update to connected clients"""
    await manager.broadcast({
        "type": "order_update",
        "data": order_data
    }, "orders")
async def broadcast_trade_update(trade_data: dict):
    """Broadcast trade update to connected clients"""
    await manager.broadcast({
        "type": "trade_update",
        "data": trade_data
    }, "trades")
async def broadcast_position_update(position_data: dict):
    """Broadcast position update to connected clients"""
    await manager.broadcast({
        "type": "position_update",
        "data": position_data
    }, "positions")
", "file_path": "c:\Users\lenovo\Documents\Github\PolyMarketClawBot\polymarket-api\app\routes\websocket.py"}{"contents"># Docker Container
FROM python:3.11-slim
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy application code
COPY . .
# Expose port
EXPOSE 8000
# Run the application
CMD ["python", "main.py"]
", "file_path": "c:\Users\lenovo\Documents\Github\PolyMarketClawBot\polymarket-api\Dockerfile"}{"contents"># -*- coding: utf-8 -*-
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
", "file_path": "c:\Users\lenovo\Documents\Github\PolyMarketClawBot\polymarket-api\app\services\monitor.py"}{"contents">{
    "polymarket_api",
    "polymarket_api/__pycache__",
    "polymarket_api/tests",
    ".env",
    "*.pyc",
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    ".gitignore",
    ".dockerignore",
    "Dockerfile",
    "docker-compose.yml"
}
", "file_path": "c:\Users\lenovo\Documents\Github\PolyMarketClawBot\polymarket-api\.gitignore"}{"contents"># Polymarket Trading Bot API
# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
", "file_path": "c:\Users\lenovo\Documents\Github\PolyMarketClawBot\polymarket-api\main.py"}
</think>


<minimax:tool_call>
<invoke name="write">
<parameter name="contents"># Utils Package
