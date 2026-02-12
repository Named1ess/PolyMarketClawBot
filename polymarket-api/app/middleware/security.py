# Security Middleware
"""
IP Whitelist and Request Validation Middleware

Security Features:
1. Trusted Proxy List - Only accept X-Forwarded-For from configured proxies
2. Connection-based IP - Fallback to direct connection IP  
3. Spoofing Detection - Detect suspicious header patterns
"""
import ipaddress
import secrets
from typing import Optional, List, Set, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IPWhitelist:
    """IP Whitelist Manager with Trusted Proxy Support"""
    
    def __init__(self):
        self._allowed_ips: Set[str] = set()
        self._allowed_networks: List[ipaddress.IPv4Network] = []
        self._trusted_proxies: Set[str] = set()
        self._trusted_networks: List[ipaddress.IPv4Network] = []
        self._loaded = False
    
    def load_from_config(self) -> None:
        """Load allowed IPs and trusted proxies from configuration"""
        if self._loaded:
            return
        
        # Load from settings
        allowed_ips_str = getattr(settings, 'ALLOWED_IPS', '')
        allowed_networks_str = getattr(settings, 'ALLOWED_NETWORKS', '')
        trusted_proxies_str = getattr(settings, 'TRUSTED_PROXIES', '')
        
        # Parse individual IPs for whitelist
        if allowed_ips_str:
            for ip in allowed_ips_str.split(','):
                ip = ip.strip()
                if ip:
                    self._allowed_ips.add(ip)
        
        # Parse IP networks (CIDR notation) for whitelist
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
        
        # Parse trusted proxies (single IPs)
        if trusted_proxies_str:
            for proxy in trusted_proxies_str.split(','):
                proxy = proxy.strip()
                if proxy:
                    # Try as single IP first
                    try:
                        ipaddress.ip_address(proxy)
                        self._trusted_proxies.add(proxy)
                    except ValueError:
                        # Try as CIDR network
                        try:
                            net = ipaddress.ip_network(proxy, strict=False)
                            self._trusted_networks.append(net)
                            self._trusted_proxies.add(str(net))
                        except ValueError:
                            logger.warning(f"Invalid trusted proxy: {proxy}")
        
        self._loaded = True
        logger.info(
            f"IP whitelist loaded: {len(self._allowed_ips)} IPs, "
            f"{len(self._allowed_networks)} networks, "
            f"{len(self._trusted_proxies)} trusted proxies"
        )
    
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
    
    def is_trusted_proxy(self, ip: str) -> bool:
        """Check if an IP is a trusted proxy"""
        self.load_from_config()
        
        # Check exact match
        if ip in self._trusted_proxies:
            return True
        
        # Check network match
        try:
            ip_obj = ipaddress.ip_address(ip)
            for network in self._trusted_networks:
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
    
    def add_trusted_proxy(self, proxy: str) -> bool:
        """Add a trusted proxy IP or network"""
        try:
            ipaddress.ip_address(proxy)  # Validate single IP
            self._trusted_proxies.add(proxy)
            logger.info(f"Trusted proxy added: {proxy}")
            return True
        except ValueError:
            try:
                net = ipaddress.ip_network(proxy, strict=False)
                self._trusted_networks.append(net)
                self._trusted_proxies.add(str(net))
                logger.info(f"Trusted proxy network added: {proxy}")
                return True
            except ValueError:
                logger.warning(f"Invalid trusted proxy: {proxy}")
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
            "allowed_ips": list(self._allowed_ips),
            "allowed_networks": [str(n) for n in self._allowed_networks],
            "trusted_proxies": list(self._trusted_proxies),
            "total_ips": len(self._allowed_ips),
            "total_networks": len(self._allowed_networks),
        }


# Singleton instance
ip_whitelist = IPWhitelist()


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Secure IP Whitelist Middleware - Anti-Spoofing Mode
    
    Security Strategy (User's Choice):
    1. If TRUSTED_PROXIES is EMPTY: Use direct connection IP ONLY (safest)
       - Ignores X-Forwarded-For and X-Real-IP completely
       - Cannot be spoofed by client headers
    
    2. If TRUSTED_PROXIES is configured:
       - Only trust X-Forwarded-For from trusted proxies
       - Validates proxy chain to prevent spoofing
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.whitelist = ip_whitelist
    
    async def dispatch(self, request: Request, call_next):
        # Skip health check endpoints
        if request.url.path in ["/health", "/status", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP with strict anti-spoofing
        client_ip, ip_source = self._get_client_ip(request)
        
        # Log for debugging
        logger.debug(f"Client IP: {client_ip} (source: {ip_source})")
        
        # Check whitelist
        if not self.whitelist.is_allowed(client_ip):
            logger.warning(
                f"Blocked request from unauthorized IP: {client_ip} "
                f"(source: {ip_source}, path: {request.url.path})"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "message": "Access denied. Your IP is not whitelisted.",
                    "client_ip": client_ip,
                }
            )
        
        # Add IP to request state
        request.state.client_ip = client_ip
        request.state.ip_source = ip_source
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> Tuple[str, str]:
        """
        Get client IP with anti-spoofing protection.
        
        Returns:
            Tuple of (ip_address, source_description)
        """
        self.whitelist.load_from_config()
        
        # Get direct connection IP (from the TCP connection itself)
        direct_ip = request.client.host if request.client else "unknown"
        
        # Check if any trusted proxies are configured
        has_trusted_proxies = bool(
            self.whitelist._trusted_proxies or self.whitelist._trusted_networks
        )
        
        if not has_trusted_proxies:
            # === NO TRUSTED PROXIES: Use direct connection ONLY ===
            # This is the safest mode - ignores all X-* headers
            # Client CANNOT spoof their IP
            
            # Log and ignore any X-Forwarded-For attempts
            forwarded = request.headers.get("X-Forwarded-For")
            real_ip = request.headers.get("X-Real-IP")
            
            if forwarded or real_ip:
                logger.debug(
                    f"Ignoring client headers (no trusted proxies): "
                    f"X-Forwarded-For='{forwarded}', X-Real-IP='{real_ip}'"
                )
            
            return direct_ip, "direct_connection_no_proxy"
        
        # === TRUSTED PROXIES CONFIGURED ===
        # Only trust X-Forwarded-For if it comes through a trusted proxy
        
        # Check X-Forwarded-For header
        forwarded = request.headers.get("X-Forwarded-For")
        real_ip_header = request.headers.get("X-Real-IP")
        
        if forwarded:
            # Parse all IPs in the chain
            forwarded_ips = [ip.strip() for ip in forwarded.split(",")]
            first_ip = forwarded_ips[0]  # Original client
            
            if len(forwarded_ips) >= 2:
                # Client -> Proxy1 -> Proxy2 -> ... -> Our Server
                second_ip = forwarded_ips[1]
                
                if self.whitelist.is_trusted_proxy(second_ip):
                    # Valid chain through trusted proxy
                    return first_ip, "x_forwarded_for_chain_valid"
                else:
                    # Suspicious: claims to come through untrusted proxy
                    logger.warning(
                        f"Spoofing detected: X-Forwarded-For chain contains "
                        f"untrusted proxy {second_ip}, falling back to direct IP"
                    )
                    return direct_ip, "spoofing_rejected_using_direct"
            else:
                # Only one IP in chain, but we expect proxy
                if self.whitelist.is_trusted_proxy(direct_ip):
                    # Our server is directly connected from trusted proxy
                    return first_ip, "x_forwarded_for_from_trusted_proxy"
                else:
                    # Suspicious - single IP without proxy chain
                    logger.warning(
                        f"Suspicious X-Forwarded-For (no proxy chain): {forwarded}"
                    )
                    return direct_ip, "spoofing_rejected_using_direct"
        
        # Check X-Real-IP (set by Nginx real_ip_header)
        if real_ip_header and self.whitelist.is_trusted_proxy(direct_ip):
            return real_ip_header.strip(), "x_real_ip_validated"
        
        # Fall back to direct connection
        return direct_ip, "direct_connection_fallback"


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


# Helper functions
def get_client_ip(request: Request) -> str:
    """Helper to get client IP from request state"""
    return getattr(request.state, 'client_ip', 'unknown')


def get_ip_source(request: Request) -> str:
    """Helper to get IP source from request state"""
    return getattr(request.state, 'ip_source', 'unknown')


def require_ip(ip: str) -> bool:
    """Check if IP is allowed"""
    return ip_whitelist.is_allowed(ip)


def add_allowed_ip(ip: str) -> bool:
    """Add an IP to the whitelist at runtime"""
    return ip_whitelist.add_ip(ip)


def add_allowed_network(network: str) -> bool:
    """Add a network to the whitelist at runtime"""
    return ip_whitelist.add_network(network)


def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_hex(32)
