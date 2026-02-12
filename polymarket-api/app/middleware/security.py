# Security Middleware
"""
IP Whitelist and Request Validation Middleware
"""
import ipaddress
from typing import Optional, List, Set
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IPWhitelist:
    """IP Whitelist Manager"""
    
    def __init__(self):
        self._allowed_ips: Set[str] = set()
        self._allowed_networks: List[ipaddress.IPv4Network] = []
        self._loaded = False
    
    def load_from_config(self) -> None:
        """Load allowed IPs from configuration"""
        if self._loaded:
            return
        
        # Load from settings
        allowed_ips_str = getattr(settings, 'ALLOWED_IPS', '')
        allowed_networks_str = getattr(settings, 'ALLOWED_NETWORKS', '')
        
        # Parse individual IPs
        if allowed_ips_str:
            for ip in allowed_ips_str.split(','):
                ip = ip.strip()
                if ip:
                    self._allowed_ips.add(ip)
        
        # Parse IP networks (CIDR notation)
        if allowed_networks_str:
            for network in allowed_networks_str.split(','):
                network = network.strip()
                if network:
                    try:
                        self._allowed_networks.append(
                            ipaddress.ip_network(network, strict=False)
                        )
                    except ValueError as e:
                        logger.warning(f"Invalid network {network}: {e}")
        
        self._loaded = True
        logger.info(f"IP whitelist loaded: {len(self._allowed_ips)} IPs, {len(self._allowed_networks)} networks")
    
    def is_allowed(self, ip: str) -> bool:
        """Check if an IP is in the whitelist"""
        self.load_from_config()
        
        # Check exact IP match
        if ip in self._allowed_ips:
            return True
        
        # Check network match
        try:
            ip_obj = ipaddress.ip_address(ip)
            for network in self._allowed_networks:
                if ip_obj in network:
                    return True
        except ValueError:
            pass
        
        return False
    
    def add_ip(self, ip: str) -> bool:
        """Add an IP to the whitelist"""
        try:
            ipaddress.ip_address(ip)  # Validate
            self._allowed_ips.add(ip)
            logger.info(f"IP added to whitelist: {ip}")
            return True
        except ValueError:
            logger.warning(f"Invalid IP: {ip}")
            return False
    
    def add_network(self, network: str) -> bool:
        """Add a network (CIDR) to the whitelist"""
        try:
            net = ipaddress.ip_network(network, strict=False)
            self._allowed_networks.append(net)
            logger.info(f"Network added to whitelist: {network}")
            return True
        except ValueError:
            logger.warning(f"Invalid network: {network}")
            return False
    
    def remove_ip(self, ip: str) -> bool:
        """Remove an IP from the whitelist"""
        if ip in self._allowed_ips:
            self._allowed_ips.remove(ip)
            logger.info(f"IP removed from whitelist: {ip}")
            return True
        return False
    
    def get_whitelist(self) -> dict:
        """Get current whitelist configuration"""
        self.load_from_config()
        return {
            "ips": list(self._allowed_ips),
            "networks": [str(n) for n in self._allowed_networks],
            "total_ips": len(self._allowed_ips),
            "total_networks": len(self._allowed_networks),
        }


# Singleton instance
ip_whitelist = IPWhitelist()


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce IP whitelist"""
    
    def __init__(self, app):
        super().__init__(app)
        self.whitelist = ip_whitelist
    
    async def dispatch(self, request: Request, call_next):
        # Skip health check endpoints
        if request.url.path in ["/health", "/status", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check whitelist
        if not self.whitelist.is_allowed(client_ip):
            logger.warning(f"Blocked request from unauthorized IP: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "message": "Access denied. Your IP is not whitelisted.",
                    "client_ip": client_ip,
                }
            )
        
        # Add IP to request state for use in routes
        request.state.client_ip = client_ip
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check X-Forwarded-For header (for reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get the first IP in the chain
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct connection IP
        if request.client:
            return request.client.host
        
        return "unknown"


class APIKeyAuth:
    """API Key Authentication"""
    
    def __init__(self):
        self._api_keys: Set[str] = set()
        self._loaded = False
    
    def load_from_config(self) -> None:
        """Load API keys from configuration"""
        if self._loaded:
            return
        
        api_keys_str = getattr(settings, 'API_KEYS', '')
        
        if api_keys_str:
            for key in api_keys_str.split(','):
                key = key.strip()
                if key:
                    self._api_keys.add(key)
        
        self._loaded = True
        logger.info(f"API keys loaded: {len(self._api_keys)} keys")
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate an API key"""
        self.load_from_config()
        return api_key in self._api_keys
    
    def add_api_key(self, key: str) -> bool:
        """Add an API key"""
        if len(key) >= 32:  # Minimum key length
            self._api_keys.add(key)
            logger.info(f"API key added")
            return True
        return False
    
    def remove_api_key(self, key: str) -> bool:
        """Remove an API key"""
        if key in self._api_keys:
            self._api_keys.remove(key)
            logger.info(f"API key removed")
            return True
        return False


# Singleton instance
api_key_auth = APIKeyAuth()


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce API key authentication"""
    
    def __init__(self, app):
        super().__init__(app)
        self.auth = api_key_auth
    
    async def dispatch(self, request: Request, call_next):
        # Skip health check endpoints
        if request.url.path in ["/health", "/status", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "API key required. Add 'X-API-Key' header.",
                }
            )
        
        if not self.auth.validate_api_key(api_key):
            logger.warning(f"Invalid API key from {request.client.host}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Invalid API key.",
                }
            )
        
        return await call_next(request)


def get_client_ip(request: Request) -> str:
    """Helper to get client IP from request state"""
    return getattr(request.state, 'client_ip', 'unknown')


def require_ip(ip: str) -> bool:
    """Decorator/function to check if IP is allowed"""
    return ip_whitelist.is_allowed(ip)


def add_allowed_ip(ip: str) -> bool:
    """Add an IP to the whitelist at runtime"""
    return ip_whitelist.add_ip(ip)


def add_allowed_network(network: str) -> bool:
    """Add a network to the whitelist at runtime"""
    return ip_whitelist.add_network(network)
