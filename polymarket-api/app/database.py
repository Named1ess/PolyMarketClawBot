# Database Connection Management
"""
MongoDB connection management with Motor async driver

Features:
- Automatic connection handling
- Fallback mode when MongoDB is unavailable
- All operations work without MongoDB (for testing)
"""
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# MongoDB client instance
_mongo_client: Optional[AsyncIOMotorClient] = None
_mongo_db: Optional[AsyncIOMotorDatabase] = None
_mongo_available: bool = False


async def connect_to_mongo() -> bool:
    """Connect to MongoDB. Returns True if successful, False otherwise."""
    global _mongo_client, _mongo_db, _mongo_available
    
    try:
        _mongo_client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        # Test connection
        await _mongo_client.admin.command('ping')
        _mongo_db = _mongo_client[settings.MONGO_DB_NAME]
        
        # Create indexes
        await create_indexes()
        
        _mongo_available = True
        logger.info(f"Connected to MongoDB: {settings.MONGO_DB_NAME}")
        return True
    except ConnectionFailure as e:
        logger.warning(f"MongoDB not available: {e}")
        _mongo_available = False
        return False


async def close_mongo_connection() -> None:
    """Close MongoDB connection"""
    global _mongo_client, _mongo_db, _mongo_available
    
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
        _mongo_available = False
        logger.info("MongoDB connection closed")


def is_mongo_available() -> bool:
    """Check if MongoDB is available"""
    return _mongo_available


async def create_indexes() -> None:
    """Create database indexes for better query performance"""
    if _mongo_db is None:
        return
    
    try:
        # Orders collection indexes
        orders_collection = _mongo_db.orders
        await orders_collection.create_index([("order_id", ASCENDING)], unique=True)
        await orders_collection.create_index([("status", ASCENDING)])
        await orders_collection.create_index([("created_at", DESCENDING)])
        await orders_collection.create_index([("token_id", ASCENDING)])
        
        # Trades collection indexes
        trades_collection = _mongo_db.trades
        await trades_collection.create_index([("transaction_hash", ASCENDING)], unique=True)
        await trades_collection.create_index([("created_at", DESCENDING)])
        await trades_collection.create_index([("token_id", ASCENDING)])
        await trades_collection.create_index([("side", ASCENDING)])
        
        # Positions collection indexes
        positions_collection = _mongo_db.positions
        await positions_collection.create_index([("token_id", ASCENDING)], unique=True)
        await positions_collection.create_index([("updated_at", DESCENDING)])
        
        # Markets cache indexes
        markets_collection = _mongo_db.markets
        await markets_collection.create_index([("token_id", ASCENDING)], unique=True)
        await markets_collection.create_index([("updated_at", DESCENDING)])
        
        logger.info("MongoDB indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")


def get_db() -> Optional[AsyncIOMotorDatabase]:
    """Get MongoDB database instance. Returns None if not connected."""
    return _mongo_db


def get_collection(collection_name: str):
    """Get a collection by name. Returns None if not connected."""
    db = get_db()
    if db is None:
        return None
    return db[collection_name]


# Convenience functions for common collections
def get_orders_collection():
    """Get the orders collection"""
    return get_collection("orders")


def get_trades_collection():
    """Get the trades collection"""
    return get_collection("trades")


def get_positions_collection():
    """Get the positions collection"""
    return get_collection("positions")


def get_markets_collection():
    """Get the markets cache collection"""
    return get_collection("markets")


async def save_order(order_data: dict) -> str:
    """Save an order to the database. Returns a mock ID if MongoDB unavailable."""
    collection = get_orders_collection()
    if collection is None:
        # Return mock ID for testing without MongoDB
        return "mock_order_" + order_data.get("order_id", "unknown")
    result = await collection.insert_one(order_data)
    return str(result.inserted_id)


async def update_order(order_id: str, update_data: dict) -> bool:
    """Update an order in the database. Returns False if MongoDB unavailable."""
    collection = get_orders_collection()
    if collection is None:
        return False
    result = await collection.update_one(
        {"order_id": order_id},
        {"$set": update_data}
    )
    return result.modified_count > 0


async def get_order(order_id: str) -> dict:
    """Get an order by ID. Returns empty dict if MongoDB unavailable."""
    collection = get_orders_collection()
    if collection is None:
        return {}
    order = await collection.find_one({"order_id": order_id})
    return order or {}


async def save_trade(trade_data: dict) -> str:
    """Save a trade to the database. Returns a mock ID if MongoDB unavailable."""
    collection = get_trades_collection()
    if collection is None:
        return "mock_trade_" + trade_data.get("transaction_hash", "unknown")
    result = await collection.insert_one(trade_data)
    return str(result.inserted_id)


async def save_position(position_data: dict) -> None:
    """Save or update a position. Silent fail if MongoDB unavailable."""
    collection = get_positions_collection()
    if collection is None:
        return
    await collection.update_one(
        {"token_id": position_data["token_id"]},
        {"$set": position_data},
        upsert=True
    )


async def get_position(token_id: str) -> dict:
    """Get a position by token ID. Returns empty dict if MongoDB unavailable."""
    collection = get_positions_collection()
    if collection is None:
        return {}
    return await collection.find_one({"token_id": token_id}) or {}


async def cache_market(market_data: dict) -> None:
    """Cache market data. Silent fail if MongoDB unavailable."""
    collection = get_markets_collection()
    if collection is None:
        return
    await collection.update_one(
        {"token_id": market_data["token_id"]},
        {"$set": market_data},
        upsert=True
    )


async def get_cached_market(token_id: str) -> dict:
    """Get cached market data. Returns empty dict if MongoDB unavailable."""
    collection = get_markets_collection()
    if collection is None:
        return {}
    return await collection.find_one({"token_id": token_id}) or {}
