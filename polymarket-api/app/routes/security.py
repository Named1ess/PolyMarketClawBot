# Security Admin Router
"""
Security administration endpoints for IP whitelist and API keys
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from app.middleware.security import ip_whitelist, api_key_auth, get_client_ip
from app.utils.logger import get_logger

logger = get_logger(__name__)

security_router = APIRouter()


class AddIPRequest(BaseModel):
    """Request to add an IP to whitelist"""
    ip: str
    description: Optional[str] = None


class AddNetworkRequest(BaseModel):
    """Request to add a network to whitelist"""
    network: str  # CIDR notation, e.g., "10.0.0.0/16"
    description: Optional[str] = None


class AddAPIKeyRequest(BaseModel):
    """Request to add an API key"""
    api_key: str


class RemoveIPRequest(BaseModel):
    """Request to remove an IP from whitelist"""
    ip: str


class RemoveAPIKeyRequest(BaseModel):
    """Request to remove an API key"""
    api_key: str


@security_router.get("/security/whitelist")
async def get_whitelist():
    """Get current IP whitelist configuration"""
    return ip_whitelist.get_whitelist()


@security_router.post("/security/whitelist/ip")
async def add_ip(request: AddIPRequest):
    """Add an IP to the whitelist"""
    success = ip_whitelist.add_ip(request.ip)
    if success:
        return {
            "success": True,
            "message": f"IP {request.ip} added to whitelist",
            "description": request.description
        }
    raise HTTPException(status_code=400, detail="Invalid IP address")


@security_router.post("/security/whitelist/network")
async def add_network(request: AddNetworkRequest):
    """Add a network (CIDR) to the whitelist"""
    success = ip_whitelist.add_network(request.network)
    if success:
        return {
            "success": True,
            "message": f"Network {request.network} added to whitelist",
            "description": request.description
        }
    raise HTTPException(status_code=400, detail="Invalid network format")


@security_router.delete("/security/whitelist/ip")
async def remove_ip(request: RemoveIPRequest):
    """Remove an IP from the whitelist"""
    success = ip_whitelist.remove_ip(request.ip)
    if success:
        return {
            "success": True,
            "message": f"IP {request.ip} removed from whitelist"
        }
    raise HTTPException(status_code=404, detail="IP not found in whitelist")


@security_router.get("/security/whitelist/check/{ip}")
async def check_ip_allowed(ip: str):
    """Check if an IP is allowed"""
    is_allowed = ip_whitelist.is_allowed(ip)
    return {
        "ip": ip,
        "allowed": is_allowed
    }


@security_router.post("/security/api-keys")
async def add_api_key(request: AddAPIKeyRequest):
    """Add an API key"""
    success = api_key_auth.add_api_key(request.api_key)
    if success:
        return {
            "success": True,
            "message": "API key added"
        }
    raise HTTPException(status_code=400, detail="Invalid API key (minimum 32 characters)")


@security_router.delete("/security/api-keys")
async def remove_api_key(request: RemoveAPIKeyRequest):
    """Remove an API key"""
    success = api_key_auth.remove_api_key(request.api_key)
    if success:
        return {
            "success": True,
            "message": "API key removed"
        }
    raise HTTPException(status_code=404, detail="API key not found")


@security_router.get("/security/api-keys/count")
async def get_api_key_count():
    """Get number of configured API keys"""
    api_key_auth.load_from_config()
    return {
        "count": len(api_key_auth._api_keys)
    }


@security_router.get("/security/my-ip")
async def get_my_ip():
    """Get the IP of the current request"""
    # This will be available from middleware
    return {
        "message": "Use X-API-Key header with valid key to access"
    }
