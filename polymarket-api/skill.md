# Polymarket Trading Bot API - Agent Skill Documentation

## Overview

This API is a FastAPI-based trading bot for Polymarket prediction markets on Polygon. It provides REST endpoints for trading, portfolio management, market data, and automated trading integration with OpenClaw.

## Base Configuration

- **Base URL**: `http://{HOST}:{PORT}/api/v1`
- **Host**: Configurable via `API_HOST` (default: `0.0.0.0`)
- **Port**: Configurable via `API_PORT` (default: `8000`)
- **Health Check**: `GET /health`

---

## Authentication

### Security Features

The API supports two authentication methods:

#### 1. IP Whitelist (Recommended for server-to-server)

```bash
# Environment variables
ENABLE_IP_WHITELIST=true
ALLOWED_IPS=203.0.113.50,10.0.0.0/16  # Comma-separated IPs/CIDR
TRUSTED_PROXIES=                        # Nginx/proxy IPs if behind reverse proxy
```

#### 2. API Key Authentication

```bash
# Environment variables
ENABLE_API_KEY_AUTH=true
API_KEYS=sk_live_key1,sk_live_key2      # Comma-separated keys
```

**Usage**:
```http
GET /api/v1/orders HTTP/1.1
Host: server:8000
X-API-Key: sk_live_key1
```

---

## Endpoints Reference

### 1. Health Check

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-12T10:30:00Z"
}
```

---

### 2. Wallet Operations

#### Get Wallet Address
```http
GET /api/v1/wallet/address
```

Response:
```json
{
  "address": "0x1234..."
}
```

#### Get USDC Balance
```http
GET /api/v1/wallet/balance
```

Response:
```json
{
  "usdc_balance": 5000.50,
  "usdc_balance_raw": "5000500000",
  "wallet_address": "0x1234...",
  "last_updated": "2026-02-12T10:30:00Z"
}
```

#### Get Token Allowances
```http
GET /api/v1/wallet/allowances
```

Response:
```json
{
  "usdc_allowance_main": 1000000,
  "usdc_allowance_neg_risk": 0,
  "usdc_allowance_neg_risk_adapter": 0
}
```

#### Approve Tokens for Trading
```http
POST /api/v1/wallet/approve
```

Response:
```json
{
  "success": true,
  "transactions": {
    "usdc_main": "0xabc123...",
    "usdc_neg_risk": "0xdef456..."
  }
}
```

---

### 3. Positions & Portfolio

#### Get Positions
```http
GET /api/v1/positions
```

Response:
```json
{
  "positions": [
    {
      "token_id": "0x1234...",
      "outcome": "YES",
      "quantity": 100,
      "avg_price": 0.65,
      "current_price": 0.70,
      "current_value": 70.0,
      "unrealized_pnl": 5.0
    }
  ]
}
```

#### Get Portfolio Summary
```http
GET /api/v1/portfolio
```

Response:
```json
{
  "total_positions_value": 500.0,
  "total_realized_pnl": 150.0,
  "total_unrealized_pnl": 25.0,
  "positions_count": 3
}
```

---

### 4. Order Management

#### Create Order
```http
POST /api/v1/orders
Content-Type: application/json

{
  "token_id": "0xabcd...",
  "side": "BUY",
  "amount": 100.0,
  "price": 0.50,
  "order_type": "FOK"
}
```

**Parameters**:
- `token_id` (string, required): Market token ID from Polymarket URL
- `side` (string, required): `BUY` or `SELL`
- `amount` (number, required): Amount in USD
- `price` (number, optional): Limit price (0.01-0.99). If not provided, uses market price
- `order_type` (string, optional): `FOK` (Fill-or-Kill), `IOC` (Immediate-or-Cancel), `LIMIT`

Response:
```json
{
  "success": true,
  "order_id": "uuid-string",
  "status": "OPEN"
}
```

#### List Orders
```http
GET /api/v1/orders?limit=20&offset=0&status=OPEN&token_id=0xabcd...
```

**Query Parameters**:
- `limit` (int): Number of orders to return (1-100, default: 20)
- `offset` (int): Pagination offset (default: 0)
- `status` (string, optional): Filter by status (`OPEN`, `FILLED`, `CANCELLED`, `FAILED`)
- `token_id` (string, optional): Filter by market

Response:
```json
{
  "orders": [...],
  "total": 50,
  "page": 1,
  "page_size": 20
}
```

#### Get Order Details
```http
GET /api/v1/orders/{order_id}
```

#### Cancel Order
```http
DELETE /api/v1/orders/{order_id}
```

#### Cancel All Orders
```http
DELETE /api/v1/orders/cancel-all
```

#### Get Order Status
```http
GET /api/v1/orders/{order_id}/status
```

---

### 5. Market Data

#### List Markets
```http
GET /api/v1/markets?limit=50&offset=0&active=true
```

**Query Parameters**:
- `limit` (int, 1-100)
- `offset` (int)
- `active` (boolean, optional)
- `archived` (boolean, optional)

#### Get Market Details
```http
GET /api/v1/markets/{token_id}
```

#### Get Order Book
```http
GET /api/v1/markets/{token_id}/orderbook
```

Response:
```json
{
  "token_id": "0xabcd...",
  "bids": [
    {"price": 0.49, "size": 500},
    {"price": 0.48, "size": 1000}
  ],
  "asks": [
    {"price": 0.51, "size": 300},
    {"price": 0.52, "size": 750}
  ]
}
```

#### Get Current Price
```http
GET /api/v1/markets/{token_id}/price?side=BUY
```

Response:
```json
{
  "token_id": "0xabcd...",
  "side": "BUY",
  "price": 0.50,
  "timestamp": "2026-02-12T10:30:00Z"
}
```

---

### 6. Trading Limits

Trading limits enforce risk management. Configure via environment variables:

```bash
ENABLE_TRADING_LIMITS=true
MAX_ORDER_AMOUNT=1000.0      # Max USD per trade
MAX_DAILY_VOLUME=10000.0     # Max daily volume USD
MAX_DAILY_TRADES=100         # Max trades per day
MAX_POSITION_PER_MARKET=5000.0 # Max position per market
```

#### Get Current Limits & Usage
```http
GET /api/v1/trading/limits
```

Response:
```json
{
  "enabled": true,
  "limits": {
    "date": "2026-02-12",
    "max_trade_usd": 1000.0,
    "max_daily_usd": 10000.0,
    "daily_volume_used": 2500.0,
    "daily_volume_remaining": 7500.0,
    "daily_trades_used": 5,
    "daily_trades_limit": 100,
    "position_limit_usd": 5000.0
  }
}
```

#### Check If Trade Is Allowed
```http
POST /api/v1/trading/can-trade?amount_usd=500&side=BUY
```

Response:
```json
{
  "allowed": true,
  "reason": "Trade allowed",
  "amount_usd": 500.0,
  "side": "BUY"
}
```

#### Get Daily Trading Statistics
```http
GET /api/v1/trading/daily-stats
```

Response:
```json
{
  "date": "2026-02-12",
  "total_trades": 5,
  "total_volume_usd": 2500.0,
  "buy_volume_usd": 1500.0,
  "sell_volume_usd": 1000.0,
  "realized_pnl": 100.0
}
```

---

### 7. Price History & Analysis

#### Get Price History
```http
GET /api/v1/markets/{token_id}/price-history?hours=24&interval_minutes=5
```

**Query Parameters**:
- `hours` (int, 1-168, default: 24)
- `interval_minutes` (int, 1-60, default: 5)

Response:
```json
{
  "token_id": "0xabcd...",
  "hours": 24,
  "data_points": 288,
  "history": [
    {
      "timestamp": "2026-02-12T10:30:00Z",
      "price_yes": 0.50,
      "price_no": 0.50
    }
  ],
  "trend": {
    "trend": "bullish",
    "change": 0.02,
    "change_percent": 4.0,
    "volatility": 0.01,
    "direction": "up"
  }
}
```

---

### 8. Market Context & Safeguards

#### Get Market Context
```http
GET /api/v1/markets/{token_id}/context
```

Response:
```json
{
  "market": {
    "question": "Will Bitcoin exceed $100k by end of 2026?",
    "active": true,
    "end_date": "2026-12-31T23:59:59Z"
  },
  "position": {},
  "slippage": {
    "spread": 0.02,
    "spread_percent": 4.0,
    "best_bid": 0.49,
    "best_ask": 0.51,
    "mid_price": 0.50,
    "liquidity_rating": "medium"
  },
  "trend": {
    "trend": "bullish",
    "change_percent": 4.0,
    "direction": "up"
  },
  "warnings": [],
  "discipline": {
    "has_position": false,
    "current_exposure": 0
  }
}
```

---

### 9. Price Alerts

#### Create Alert
```http
POST /api/v1/alerts
Content-Type: application/json

{
  "token_id": "0xabcd...",
  "side": "yes",
  "condition": "above",
  "threshold": 0.70,
  "webhook_url": "https://your-server.com/webhook"
}
```

**Parameters**:
- `token_id` (string, required): Market token ID
- `side` (string): `yes` or `no`
- `condition` (string): `above`, `below`, `crosses_above`, `crosses_below`
- `threshold` (number, required): Price threshold
- `webhook_url` (string, optional): URL to call when alert triggers

Response:
```json
{
  "alert_id": "alert_123456",
  "token_id": "0xabcd...",
  "side": "yes",
  "condition": "above",
  "threshold": 0.70,
  "active": true,
  "triggered": false,
  "created_at": "2026-02-12T10:30:00Z"
}
```

#### List Alerts
```http
GET /api/v1/alerts?include_triggered=false
```

#### Delete Alert
```http
DELETE /api/v1/alerts/{alert_id}
```

---

### 10. Market Import

Import markets for local tracking and management.

#### Get Importable Markets
```http
GET /api/v1/markets/importable?min_volume=10000&limit=50&category=Politics
```

#### Import a Market
```http
POST /api/v1/markets/import
Content-Type: application/json

{
  "polymarket_url": "https://polymarket.com/market/will-bitcoin-hit-100k"
}
```

Response:
```json
{
  "success": true,
  "market_id": "imported_123",
  "token_id": "0xabcd...",
  "name": "Will Bitcoin exceed $100k by end of 2026?"
}
```

#### Get Imported Markets
```http
GET /api/v1/markets/imported
```

#### Sync Imported Market
```http
POST /api/v1/markets/imported/{market_id}/sync
```

---

### 11. Combined Portfolio Summary

Get a complete overview in one call:
```http
GET /api/v1/portfolio/summary
```

Response:
```json
{
  "positions": {
    "count": 3,
    "total_value_usd": 500.0,
    "total_unrealized_pnl": 25.0
  },
  "daily_stats": {
    "date": "2026-02-12",
    "trades": 5,
    "volume_usd": 2500.0,
    "realized_pnl": 100.0
  },
  "trading_limits": {...},
  "imported_markets_count": 10,
  "active_alerts_count": 3
}
```

---

### 12. OpenClaw Webhook Integration

#### Trade Webhook (for OpenClaw signals)
```http
POST /api/v1/webhook/claw
X-Webhook-Signature: sha256=...  # Optional, if webhook secret configured

{
  "token_id": "0xabcd...",
  "side": "BUY",
  "amount": 100.0,
  "price": 0.50,
  "order_type": "FOK",
  "webhook_id": "signal_123",
  "metadata": {"strategy": "momentum"}
}
```

Response:
```json
{
  "success": true,
  "order_id": "uuid-string",
  "error": null,
  "timestamp": "2026-02-12T10:30:00Z"
}
```

#### Order Status Webhook
```http
POST /api/v1/webhook/order-status

{
  "order_id": "uuid-string",
  "status": "FILLED"
}
```

#### Webhook Health Check
```http
GET /api/v1/webhook/health
```

---

### 13. Security Management

#### Get IP Whitelist
```http
GET /api/v1/security/whitelist
```

#### Add IP to Whitelist
```http
POST /api/v1/security/whitelist/ip

{
  "ip": "203.0.113.50",
  "description": "OpenClaw Server A"
}
```

#### Add Network to Whitelist
```http
POST /api/v1/security/whitelist/network

{
  "network": "10.0.0.0/16",
  "description": "Internal network"
}
```

#### Check IP Allowed
```http
GET /api/v1/security/whitelist/check/203.0.113.50
```

#### Add Trusted Proxy
```http
POST /api/v1/security/trusted-proxies

{
  "proxy": "10.0.0.5",
  "description": "Nginx load balancer"
}
```

#### Manage API Keys
```http
POST /api/v1/security/api-keys

{
  "api_key": "sk_live_new_key..."
}

DELETE /api/v1/security/api-keys

{
  "api_key": "sk_live_old_key..."
}
```

#### Get My IP Info
```http
GET /api/v1/security/my-ip
```

---

## Complete Workflow Examples

### Example 1: Basic Trading Flow

```python
import httpx

BASE_URL = "http://server:8000/api/v1"

# 1. Check balance
balance = httpx.get(f"{BASE_URL}/wallet/balance").json()
print(f"USDC Balance: {balance['usdc_balance']}")

# 2. Get market info
market = httpx.get(f"{BASE_URL}/markets/0xabcd...").json()
print(f"Current Price: {market['outcome_prices']}")

# 3. Check trading limits
limits = httpx.get(f"{BASE_URL}/trading/limits").json()
print(f"Daily remaining: {limits['limits']['daily_volume_remaining']}")

# 4. Create order
order = httpx.post(f"{BASE_URL}/orders", json={
    "token_id": "0xabcd...",
    "side": "BUY",
    "amount": 100.0,
    "price": 0.50,
    "order_type": "FOK"
}).json()
print(f"Order ID: {order['order_id']}")

# 5. Check order status
status = httpx.get(f"{BASE_URL}/orders/{order['order_id']}/status").json()
print(f"Status: {status}")
```

### Example 2: Automated Trading with Alerts

```python
import httpx

BASE_URL = "http://server:8000/api/v1"

# 1. Set up price alert
alert = httpx.post(f"{BASE_URL}/alerts", json={
    "token_id": "0xabcd...",
    "side": "yes",
    "condition": "above",
    "threshold": 0.75,
    "webhook_url": "https://your-server.com/alert-callback"
}).json()
print(f"Alert created: {alert['alert_id']}")

# 2. Get market context before trading
context = httpx.get(f"{BASE_URL}/markets/0xabcd/context").json()
print(f"Liquidity Rating: {context['slippage']['liquidity_rating']}")
print(f"Trend: {context['trend']['direction']}")

# 3. Check daily limits
daily = httpx.get(f"{BASE_URL}/trading/daily-stats").json()
print(f"Today's trades: {daily['total_trades']}")
print(f"Volume used: ${daily['total_volume_usd']}")

# 4. Get portfolio summary
portfolio = httpx.get(f"{BASE_URL}/portfolio/summary").json()
print(f"Total positions: {portfolio['positions']['count']}")
```

### Example 3: Market Import and Tracking

```python
import httpx

BASE_URL = "http://server:8000/api/v1"

# 1. Find importable markets
markets = httpx.get(f"{BASE_URL}/markets/importable", params={
    "min_volume": 50000,
    "limit": 20,
    "category": "Politics"
}).json()
print(f"Found {markets['count']} markets")

# 2. Import a market
result = httpx.post(f"{BASE_URL}/markets/import", json={
    "polymarket_url": "https://polymarket.com/market/will-some-event-happen"
}).json()
print(f"Imported: {result['market_id']}")

# 3. Get imported markets
imported = httpx.get(f"{BASE_URL}/markets/imported").json()
print(f"Total imported: {imported['count']}")

# 4. Sync market data
synced = httpx.post(f"{BASE_URL}/markets/imported/{result['market_id']}/sync").json()
print(f"Synced: {synced}")
```

### Example 4: OpenClaw Integration

```python
import httpx
import hmac
import hashlib
import json

BASE_URL = "http://server:8000/api/v1"
WEBHOOK_SECRET = "your_webhook_secret"

def send_webhook(token_id, side, amount, price=None):
    """Send trade signal to the bot"""
    payload = {
        "token_id": token_id,
        "side": side,
        "amount": amount,
        "price": price,
        "order_type": "FOK"
    }
    
    # Sign the payload
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        json.dumps(payload).encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {"X-Webhook-Signature": f"sha256={signature}"}
    
    response = httpx.post(
        f"{BASE_URL}/webhook/claw",
        json=payload,
        headers=headers
    )
    
    return response.json()

# Send a buy signal
result = send_webhook(
    token_id="0xabcd...",
    side="BUY",
    amount=50.0,
    price=0.45
)
print(f"Order placed: {result['order_id']}")
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (missing/invalid API key) |
| 403 | Forbidden (IP not whitelisted) |
| 404 | Not Found |
| 500 | Internal Server Error |

### Error Response Format

```json
{
  "error": "Forbidden",
  "message": "Access denied. Your IP is not whitelisted.",
  "client_ip": "203.0.113.50"
}
```

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Server bind address |
| `API_PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |

### Wallet

| Variable | Description |
|----------|-------------|
| `POLYGON_WALLET_PRIVATE_KEY` | Wallet private key (0x prefix) |
| `WALLET_ADDRESS` | Wallet address (auto-derived if not set) |

### Polymarket API

| Variable | Default | Description |
|----------|---------|-------------|
| `CLOB_HOST` | `https://clob.polymarket.com` | CLOB API URL |
| `CLOB_API_KEY` | - | API key from Polymarket |
| `CLOB_SECRET` | - | API secret |
| `CLOB_PASS_PHRASE` | - | API passphrase |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB_NAME` | `polymarket_trading` | Database name |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_IP_WHITELIST` | `false` | Enable IP filtering |
| `ALLOWED_IPS` | - | Comma-separated IPs |
| `ALLOWED_NETWORKS` | - | Comma-separated CIDR |
| `TRUSTED_PROXIES` | - | Proxy IPs for X-Forwarded-For |
| `ENABLE_API_KEY_AUTH` | `false` | Enable API key auth |
| `API_KEYS` | - | Comma-separated API keys |

### Trading Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_TRADING_LIMITS` | `false` | Enable trading limits |
| `MAX_ORDER_AMOUNT` | `1000.0` | Max USD per trade |
| `MAX_DAILY_VOLUME` | `10000.0` | Max daily volume USD |
| `MAX_DAILY_TRADES` | `100` | Max trades per day |
| `MAX_POSITION_PER_MARKET` | `5000.0` | Max position per market |

---

## WebSocket (Future)

Real-time updates are available via WebSocket:

```http
WS /ws
```

Subscribe to:
- `orders` - Order updates
- `trades` - Trade notifications
- `positions` - Position changes

---

## Notes

1. **Token ID Extraction**: Get token ID from Polymarket URL: `https://polymarket.com/market/question?token_id=0xabcd...`

2. **Price Precision**: Prices are between 0.01 and 0.99 (representing percentage)

3. **Amount Units**: All USD amounts are in USDC decimals (e.g., $100 = `100000000` raw)

4. **Rate Limiting**: Configurable via `RATE_LIMIT_REQUESTS_PER_MINUTE` and `RATE_LIMIT_BURST`

5. **Database**: MongoDB is used for persistence. Requires `orders`, `trades`, `positions` collections

6. **Order Types**:
   - `FOK` (Fill-or-Kill): Order must fill completely or cancel
   - `IOC` (Immediate-or-Cancel): Fill what you can, cancel rest
   - `LIMIT`: Standard limit order
