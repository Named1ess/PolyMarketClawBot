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
    Secure IP Whitelist Middleware
    
    Security Strategy:
    1. If no trusted proxies configured: Use direct connection IP only
    2. If trusted proxies configured: 
       - Only trust X-Forwarded-For from trusted proxies
       - Validate the chain doesn't contain suspicious patterns
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.whitelist = ip_whitelist
    
    async def dispatch(self, request: Request, call_next):
        # Skip health check endpoints
        if request.url.path in ["/health", "/status", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP with spoofing detection
        client_ip, ip_source = self._get_client_ip(request)
        
        # Log IP source for debugging
        logger.debug(f"Client IP: {client_ip} (source: {ip_source})")
        
        # Check whitelist
        if not self.whitelist.is_allowed(client_ip):
            # Log detailed info about blocked request
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
        
        # Add IP to request state for use in routes
        request.state.client_ip = client_ip
        request.state.ip_source = ip_source
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> Tuple[str, str]:
        """
        Get client IP with spoofing detection.
        
        Returns:
            Tuple of (ip_address, source_description)
        """
        self.whitelist.load_from_config()
        
        # Get direct connection IP
        direct_ip = request.client.host if request.client else "unknown"
        
        # Check X-Forwarded-For header
        forwarded = request.headers.get("X-Forwarded-For")
        real_ip_header = request.headers.get("X-Real-IP")
        
        # If no trusted proxies configured, use direct connection only
        if not self.whitelist._trusted_proxies:
            if forwarded:
                logger.debug(
                    f"X-Forwarded-For ignored (no trusted proxies configured): {forwarded}"
                )
            return direct_ip, "direct_connection"
        
        # Validate X-Forwarded-For if present
        if forwarded:
            # Get the first IP in the chain (original client)
            forwarded_ips = [ip.strip() for ip in forwarded.split(",")]
            first_ip = forwarded_ips[0]
            
            # Check if the second IP (if exists) is a trusted proxy
            # This validates the chain was set by our proxy
            if len(forwarded_ips) >= 2:
                second_ip = forwarded_ips[1]
                if self.whitelist.is_trusted_proxy(second_ip):
                    # Valid chain: client -> trusted_proxy -> our_server
                    return first_ip, "x_forwarded_for_validated"
                else:
                    # Suspicious: client says they came through untrusted proxy
                    logger.warning(
                        f"Spoofing attempt: X-Forwarded-For claims via untrusted proxy "
                        f"{second_ip}, using direct IP {direct_ip}"
                    )
                    return direct_ip, "spoofing_detected_rejected"
            else:
                # Only one IP in X-Forwarded-For, but we expect proxy chain
                # This might be spoofed
                if self.whitelist.is_trusted_proxy(direct_ip):
                    # Direct connection is from our proxy, accept X-Forwarded-For
                    return first_ip, "x_forwarded_for_from_trusted_proxy"
                else:
                    # Suspicious single IP without proxy chain
                    logger.warning(
                        f"Suspicious X-Forwarded-For (no proxy chain): {forwarded}"
                    )
                    return direct_ip, "spoofing_detected_no_chain"
        
        # Check X-Real-IP header (set by Nginx etc.)
        if real_ip_header and self.whitelist.is_trusted_proxy(direct_ip):
            return real_ip_header.strip(), "x_real_ip_validated"
        
        # Fall back to direct connection
        return direct_ip, "direct_connection"
    
    def _is_suspicious_forwarded(self, forwarded: str) -> bool:
        """Detect suspicious X-Forwarded-For patterns"""
        ips = [ip.strip() for ip in forwarded.split(",")]
        
        # Check for private IPs in the chain (possible spoofing)
        private_prefixes = ["10.", "172.16.", "172.17.", "172.18.", "172.19.", 
                           "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                           "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                           "172.30.", "172.31.", "192.168.", "127."]
        
        for ip in ips:
            for prefix in private_prefixes:
                if ip.startswith(prefix):
                    # Private IP in X-Forwarded-For - likely spoofed
                    return True
        
        # Check for multiple IPs claiming to be the client
        if len(set(ips)) < len(ips):
            # Duplicate IPs - suspicious
            return True
        
        return False


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
