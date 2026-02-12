# Orders Router
"""
Order-related API endpoints
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.order_service import order_service
from app.models.orders import (
    OrderRequest, OrderResponse, OrderListResponse,
    CancelOrderResponse, CancelAllOrdersResponse
)
from app.database import get_orders_collection

orders_router = APIRouter()


@orders_router.post("/orders", status_code=201)
async def create_order(order: OrderRequest):
    """Create a new order"""
    result = await order_service.create_order(order)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Order failed"))
    return result


@orders_router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    token_id: Optional[str] = Query(default=None)
):
    """List orders with optional filtering"""
    from app.database import get_orders_collection
    
    collection = get_orders_collection()
    
    if collection is None:
        # Return empty list if MongoDB unavailable
        return OrderListResponse(
            orders=[],
            total=0,
            page=1,
            page_size=limit
        )
    
    # Build query filter
    query = {}
    if status:
        query["status"] = status
    if token_id:
        query["token_id"] = token_id
    
    # Fetch orders
    cursor = collection.find(query).sort("created_at", -1).skip(offset).limit(limit)
    orders = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string for JSON serialization
    for order in orders:
        if "_id" in order:
            order["_id"] = str(order["_id"])
    
    # Get total count
    total = await collection.count_documents(query)
    
    return OrderListResponse(
        orders=[OrderResponse(**order) for order in orders],
        total=total,
        page=offset // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@orders_router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order details by ID"""
    order = await order_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@orders_router.delete("/orders/{order_id}", response_model=CancelOrderResponse)
async def cancel_order(order_id: str):
    """Cancel an order"""
    result = await order_service.cancel_order(order_id)
    if not result.get("success") and "not found" in result.get("error", ""):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return CancelOrderResponse(
        success=result.get("success", False),
        order_id=order_id,
        message=result.get("error", "Order cancelled") if result.get("success") else result.get("error", "Cancellation failed")
    )


@orders_router.delete("/orders/cancel-all", response_model=CancelAllOrdersResponse)
async def cancel_all_orders():
    """Cancel all open orders"""
    result = await order_service.cancel_all_orders()
    return CancelAllOrdersResponse(
        success=result.get("success", False),
        cancelled_count=0,
        message=result.get("error", "All orders cancelled") if result.get("success") else result.get("error", "Cancellation failed")
    )


@orders_router.get("/orders/{order_id}/status")
async def get_order_status(order_id: str):
    """Get order status from Polymarket"""
    status = await order_service.get_order_status(order_id)
    if not status:
        raise HTTPException(status_code=404, detail="Order status not found")
    return status
