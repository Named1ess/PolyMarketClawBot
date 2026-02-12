# Polymarket Trading Bot API - Agent Skill Documentation

## Overview

This API is a FastAPI-based trading bot for Polymarket prediction markets on Polygon. It provides REST endpoints for trading, portfolio management, market data, and automated trading integration.

**Base URLs:**
- **API**: `http://{HOST}:{PORT}/api/v1`
- **Host**: Configurable via `HOST` (default: `0.0.0.0`)
- **Port**: Configurable via `PORT` (default: `8000`)
- **Health Check**: `GET /health`
- **API Docs**: `GET /docs` (Swagger UI)

---

## API Credentials Setup (IMPORTANT)

### Getting API Credentials

**CRITICAL**: API credentials must be derived from your private key, not manually set!

**Step 1: Ensure private key is set in `.env`**
```bash
POLYGON_WALLET_PRIVATE_KEY=0xyour_private_key_here
```

**Step 2: Start the API - credentials auto-derive on first run**
```bash
cd polymarket-api
python main.py
```

The API will automatically:
1. Use your private key to derive API credentials via `create_or_derive_api_creds()`
2. Save credentials to `.env` for future use
3. Initialize with Level 2 (trading) authentication

**Step 3: Verify credentials**
```python
# Credentials are stored in .env as:
CLOB_API_KEY=your_api_key
CLOB_SECRET=your_secret
CLOB_PASS_PHRASE=your_passphrase
```

### Required Environment Variables

```bash
# Wallet (REQUIRED for trading)
POLYGON_WALLET_PRIVATE_KEY=0x...  # Your Polygon wallet private key
WALLET_ADDRESS=0x...              # Optional: auto-derived from private key

# CLOB Credentials (auto-derived, can be manually set)
CLOB_API_KEY=                    # API key
CLOB_SECRET=                      # API secret
CLOB_PASS_PHRASE=                 # API passphrase

# Gamma API
GAMMA_API_URL=https://gamma-api.polymarket.com

# MongoDB (optional - works without it)
MONGODB_URI=mongodb://localhost:27017
```

---

## Authentication

### Security Features

The API supports two authentication methods:

#### 1. IP Whitelist (Recommended for server-to-server)

```bash
ENABLE_IP_WHITELIST=false  # Set to true to enable
ALLOWED_IPS=               # Comma-separated IPs/CIDR
```

#### 2. API Key Authentication

```bash
ENABLE_API_KEY_AUTH=false
API_KEYS=sk_live_key1,sk_live_key2
```

**Usage:**
```http
GET /api/v1/orders HTTP/1.1
Host: server:8000
X-API-Key: sk_live_key1
```

---

## Markets API - Complete Reference

### Get Markets with Advanced Filtering

```http
GET /api/v1/markets
```

**Advanced Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| **Pagination** | | |
| `limit` | int | Number of markets (1-100, default: 50) |
| `offset` | int | Pagination offset (default: 0) |
| **Sorting** | | |
| `order` | string | Fields to order by, comma-separated (e.g., `volumeNum,endDate`) |
| `ascending` | boolean | Sort order: `true`=ascending, `false`=descending |
| **ID Filters** | | |
| `ids` | string | Comma-separated market IDs |
| `slugs` | string | Comma-separated market slugs |
| `clob_token_ids` | string | Comma-separated CLOB token IDs |
| `condition_ids` | string | Comma-separated condition IDs |
| **Numeric Ranges** | | |
| `liquidity_num_min` | float | Minimum liquidity |
| `liquidity_num_max` | float | Maximum liquidity |
| `volume_num_min` | float | Minimum 24h volume |
| `volume_num_max` | float | Maximum 24h volume |
| **Date Ranges (ISO 8601)** | | |
| `start_date_min` | string | Start date minimum (e.g., `2026-01-01T00:00:00Z`) |
| `start_date_max` | string | Start date maximum |
| `end_date_min` | string | End date minimum |
| `end_date_max` | string | End date maximum (e.g., `2026-12-31T23:59:59Z`) |
| **Status Filters** | | |
| `active` | boolean | Filter by active status |
| `archived` | boolean | Filter by archived status |
| `closed` | boolean | Filter by closed status |
| `featured` | boolean | Filter by featured status |

#### Quick Filters

**Get ONLY Currently Active Markets:**
```http
GET /api/v1/markets/active?limit=50&volume_num_min=1000
```

**Get High Volume Markets:**
```http
GET /api/v1/markets?volume_num_min=10000&order=volumeNum&ascending=false
```

**Get Markets Ending Soon:**
```http
GET /api/v1/markets/ending-soon?limit=20&days_ahead=7
```

**Response:**
```json
{
  "markets": [
    {
      "id": "123",
      "question": "Will Bitcoin exceed $100k by end of 2026?",
      "slug": "will-bitcoin-exceed-100k-by-end-of-2026",
      "end_date": "2026-12-31T23:59:59Z",
      "start_date": "2026-01-01T00:00:00Z",
      "active": true,
      "archived": false,
      "closed": false,
      "outcomes": ["Yes", "No"],
      "outcome_prices": [0.45, 0.55],
      "volume": 125000.50,
      "volume_num": 125000.50,
      "liquidity": 50000.00,
      "liquidity_num": 50000.00,
      "tokens": [
        {"token_id": "0x123...", "outcome": "Yes", "price": 0.45},
        {"token_id": "0x456...", "outcome": "No", "price": 0.55}
      ],
      "tags": ["Crypto", "Bitcoin"]
    }
  ],
  "total": 50
}
```

### Pre-built Market Endpoints

#### Get Active Markets
```http
GET /api/v1/markets/active?limit=50&order=volumeNum&ascending=false&volume_num_min=1000
```

#### Get Trending Markets
```http
GET /api/v1/markets/trending?limit=20&volume_num_min=1000
```

#### Get Markets Ending Soon
```http
GET /api/v1/markets/ending-soon?limit=20&days_ahead=7
```

#### Get Sports Markets
```http
GET /api/v1/markets/sports?limit=50&game_id=some_game_id
```

---

### Get Market Details
```http
GET /api/v1/markets/{token_id}
```

### Get Order Book
```http
GET /api/v1/markets/{token_id}/orderbook
```

### Get Current Price
```http
GET /api/v1/markets/{token_id}/price?side=BUY
```

---

## Order Placement (CRITICAL - Read This!)

### Correct Order Flow

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# 1. GET markets with active=true to get valid markets
response = httpx.get(f"{BASE_URL}/markets/active", params={
    "limit": 10,
    "order": "volumeNum",
    "ascending": False
}).json()

# 2. Extract token_id from 'tokens' array (NOT 'clob_token_ids'!)
for market in response["markets"]:
    for token in market.get("tokens", []):
        if token.get("outcome") == "Yes":
            token_id = token["token_id"]
            price = token["price"]
            break

# 3. Get market details (requires condition_id!)
condition_id = market["condition_id"]
market_detail = httpx.get(f"{BASE_URL}/markets/{token_id}").json()

# 4. Place order (minimum amount: $5!)
order = httpx.post(f"{BASE_URL}/orders", json={
    "token_id": token_id,
    "side": "BUY",        # or "SELL"
    "amount": 5.0,       # MINIMUM $5!
    "price": price,       # Price between 0.01 and 0.99
    "order_type": "GTC"   # Good-Til-Cancelled
}).json()
```

### Key Order Rules

| Rule | Value |
|------|-------|
| **Minimum Order Amount** | $5.00 USD |
| **Price Range** | 0.01 - 0.99 |
| **Token ID Source** | `market["tokens"][i]["token_id"]` |
| **Market ID for Details** | `market["condition_id"]` |
| **Order Type** | `GTC` (Good-Til-Cancelled) |

### Create Order Endpoint

```http
POST /api/v1/orders
Content-Type: application/json

{
  "token_id": "0xabc123...",
  "side": "BUY",
  "amount": 5.0,
  "price": 0.50,
  "order_type": "GTC"
}
```

**Parameters:**
- `token_id` (required): Market token ID from `market["tokens"][0]["token_id"]`
- `side` (required): `BUY` or `SELL`
- `amount` (required): Amount in USD (minimum: $5)
- `price` (optional): Limit price (0.01 - 0.99)
- `order_type` (optional): `GTC` (default)

**Response:**
```json
{
  "success": true,
  "order_id": "0xb6fd72c3207d3035baa5311fb9d5ec1bec098a36e1e02ef4ff81c3cfbbf11c2e",
  "status": "live"
}
```

### Order Status Check

```http
GET /api/v1/orders/{order_id}
```

**Response:**
```json
{
  "id": "0xb6fd72c...",
  "status": "LIVE",
  "side": "BUY",
  "price": 0.88,
  "original_size": "5",
  "size_matched": "0",
  "filled_size": "0"
}
```

### Cancel Order
```http
DELETE /api/v1/orders/{order_id}
```

### Get Open Orders
```http
GET /api/v1/orders
```

---

## Wallet Operations

### Get Wallet Address
```http
GET /api/v1/wallet/address
```

### Get USDC Balance
```http
GET /api/v1/wallet/balance
```

### Approve Tokens
```http
POST /api/v1/wallet/approve
```

---

## Positions & Portfolio

### Get Positions
```http
GET /api/v1/positions
```

### Get Portfolio Summary
```http
GET /api/v1/portfolio
```

---

## Complete Workflow Examples

### Example 1: Find and Trade Active Markets

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# 1. Get active markets sorted by volume
response = httpx.get(f"{BASE_URL}/markets/active", params={
    "limit": 10,
    "order": "volumeNum",
    "ascending": False,
    "volume_num_min": 5000  # Minimum $5k volume
}).json()

print(f"Found {response['total']} active markets")

# 2. Select first high-volume market
for market in response["markets"][:3]:
    print(f"\n{market['question'][:60]}...")
    print(f"  Volume: ${market.get('volume_num', 0):,.2f}")
    print(f"  Ends: {market.get('end_date', 'N/A')}")
    
    # 3. Extract YES token
    for token in market.get("tokens", []):
        if token.get("outcome") == "Yes":
            token_id = token["token_id"]
            current_price = token["price"]
            print(f"  YES Price: ${current_price:.2f}")
            break
    
    if token_id:
        # 4. Place order ($5 minimum)
        order = httpx.post(f"{BASE_URL}/orders", json={
            "token_id": token_id,
            "side": "BUY",
            "amount": 5.0,  # Minimum!
            "price": current_price,
            "order_type": "GTC"
        }).json()
        
        if order.get("success"):
            print(f"  [ORDER PLACED] {order['order_id']}")
        else:
            print(f"  [ORDER FAILED] {order.get('error')}")
```

### Example 2: Quick Trade - Single Script

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# Get one active market
market = httpx.get(f"{BASE_URL}/markets/active", params={
    "limit": 1,
    "volume_num_min": 10000
}).json()["markets"][0]

# Get YES token
token_id = market["tokens"][0]["token_id"]
price = market["tokens"][0]["price"]

# Place $5 order
order = httpx.post(f"{BASE_URL}/orders", json={
    "token_id": token_id,
    "side": "BUY",
    "amount": 5.0,
    "price": price,
    "order_type": "GTC"
}).json()

print(f"Order: {order}")
```

### Example 3: Check Order Status

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"
ORDER_ID = "0xb6fd72c3207d3035baa5311fb9d5ec1bec098a36e1e02ef4ff81c3cfbbf11c2e"

# Check specific order
status = httpx.get(f"{BASE_URL}/orders/{ORDER_ID}").json()
print(f"Order Status: {status['status']}")
print(f"Price: {status['price']}")
print(f"Filled: {status.get('filled_size', '0')}")

# Get all open orders
orders = httpx.get(f"{BASE_URL}/orders").json()
print(f"\nOpen Orders: {len(orders['orders'])}")
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (invalid parameters, amount too small) |
| 401 | Unauthorized (invalid API credentials) |
| 403 | Forbidden (IP not whitelisted) |
| 404 | Not Found |
| 500 | Internal Server Error |

### Common Errors

**"Size (X) lower than the minimum: 5"**
→ Increase order amount to at least $5

**"market not found"**
→ Using wrong ID - use `condition_id` for market details, `token_id` for orders

**"Unauthorized/Invalid api key"**
→ Credentials not properly derived - restart API to regenerate

**"order is invalid"**
→ Check price is between 0.01 and 0.99

---

## Configuration Reference

### Environment Variables

```bash
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Wallet (REQUIRED)
POLYGON_WALLET_PRIVATE_KEY=0x...

# CLOB Credentials (auto-derived)
CLOB_API_KEY=
CLOB_SECRET=
CLOB_PASS_PHRASE=

# Gamma API
GAMMA_API_URL=https://gamma-api.polymarket.com
CLOB_HOST=https://clob.polymarket.com

# MongoDB (optional)
MONGODB_URI=mongodb://localhost:27017

# Security
ENABLE_IP_WHITELIST=false
ENABLE_API_KEY_AUTH=false
```

---

## Quick Reference Card

```python
# Get active markets
markets = httpx.get("/api/v1/markets/active").json()

# Get token_id (from tokens array!)
token_id = market["tokens"][0]["token_id"]

# Get market details (uses condition_id)
detail = httpx.get(f"/api/v1/markets/{token_id}").json()

# Place order ($5 minimum!)
order = httpx.post("/api/v1/orders", json={
    "token_id": token_id,
    "side": "BUY",
    "amount": 5.0,  # MINIMUM!
    "price": 0.50,
    "order_type": "GTC"
}).json()

# Check status
status = httpx.get(f"/api/v1/orders/{order_id}").json()

# Cancel order
httpx.delete(f"/api/v1/orders/{order_id}")
```

---

## Notes

1. **Token ID Location**: Token IDs are in `market["tokens"][i]["token_id"]`, NOT `market["clob_token_ids"]`

2. **Minimum Order**: All orders must be at least $5.00 USD

3. **Price Format**: Prices are 0.01 to 0.99 (representing 1-99%)

4. **API Credentials**: Automatically derived from private key on first run

5. **Market ID**: Use `condition_id` for market details endpoint

6. **Date Format**: ISO 8601 UTC (e.g., `2026-12-31T23:59:59Z`)

7. **Restart Required**: After changing `.env`, restart the API

8. **MongoDB Optional**: API works without MongoDB (some caching features disabled)
