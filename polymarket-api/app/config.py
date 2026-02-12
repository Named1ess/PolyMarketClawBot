# Configuration Management
"""
Environment-based configuration with Pydantic settings
"""
import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True
    )
    
    # Server Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Wallet Configuration
    POLYGON_WALLET_PRIVATE_KEY: Optional[str] = None
    WALLET_ADDRESS: Optional[str] = None
    
    # Polymarket CLOB Configuration
    CLOB_HOST: str = "https://clob.polymarket.com"
    CLOB_WS_URL: str = "wss://ws-subscriptions-clob.polymarket.com/ws"
    CHAIN_ID: int = 137
    
    # Polymarket API Keys
    CLOB_API_KEY: Optional[str] = None
    CLOB_SECRET: Optional[str] = None
    CLOB_PASS_PHRASE: Optional[str] = None
    
    # Gamma API
    GAMMA_API_URL: str = "https://gamma-api.polymarket.com"
    
    # MongoDB Configuration
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "polymarket_trading"
    
    # Polygon RPC
    POLYGON_RPC_URL: str = "https://polygon-rpc.com"
    
    # Token Addresses
    USDC_CONTRACT_ADDRESS: str = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    CTF_CONTRACT_ADDRESS: str = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
    EXCHANGE_ADDRESS: str = "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
    NEG_RISK_EXCHANGE_ADDRESS: str = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
    NEG_RISK_ADAPTER_ADDRESS: str = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
    
    # Trading Configuration
    DEFAULT_FEE_RATE_BPS: int = 1
    DEFAULT_ORDER_EXPIRATION: str = "0"
    MIN_ORDER_SIZE_USD: float = 1.0
    MIN_ORDER_SIZE_TOKENS: float = 1.0
    FETCH_INTERVAL: int = 1
    TOO_OLD_TIMESTAMP: int = 24
    
    # Retry Settings
    RETRY_LIMIT: int = 3
    NETWORK_RETRY_LIMIT: int = 3
    REQUEST_TIMEOUT_MS: int = 10000
    
    # OpenClaw Integration
    OPENCLAW_API_KEY: Optional[str] = None
    OPENCLAW_WEBHOOK_SECRET: Optional[str] = None
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    
    @field_validator("WALLET_ADDRESS", mode="before")
    @classmethod
    def derive_wallet_address(cls, v, info):
        """Derive wallet address from private key if not provided"""
        if v:
            return v
        private_key = info.data.get("POLYGON_WALLET_PRIVATE_KEY")
        if private_key and private_key.startswith("0x"):
            try:
                from web3 import Web3
                w3 = Web3()
                account = w3.eth.account.from_key(private_key)
                return account.address
            except Exception:
                pass
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
