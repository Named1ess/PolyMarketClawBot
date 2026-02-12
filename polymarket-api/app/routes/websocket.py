# WebSocket Router
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
