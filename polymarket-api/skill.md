# Polymarket Trading Bot API - AI Agent Skill Documentation

## Why This API

This API provides a unified REST interface for AI agents to trade Polymarket prediction markets on Polygon. Instead of directly integrating with Polymarket's complex CLOB and Gamma APIs, agents can make simple HTTP calls.

**Value:**
- One-line market queries with advanced filtering
- Automatic credential management (no manual API key setup)
- Standard REST responses (JSON)
- Works without MongoDB

**Target Users:** AI agents that need to programmatically trade prediction markets.

---

## Quick Start

### Step 1: Configure Wallet

Only one environment variable is required:

```bash
POLYGON_WALLET_PRIVATE_KEY=0xyour_private_key_here
```

### Step 2: Start the API

```bash
cd polymarket-api
python main.py
```

The API will:
1. Auto-derive API credentials from your private key on first run
2. Save credentials to `.env` for future runs
3. Serve on `http://0.0.0.0:8000`
4. Swagger docs at `http://localhost:8000/docs`

### Step 3: Place an Order

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# Get active markets
markets = httpx.get(f"{BASE_URL}/markets/active", params={"limit": 1}).json()

# Extract token_id from tokens array (NOT clob_token_ids!)
market = markets["markets"][0]
token_id = market["tokens"][0]["token_id"]
price = market["tokens"][0]["price"]

# Place order ($5 minimum!)
order = httpx.post(f"{BASE_URL}/orders", json={
    "token_id": token_id,
    "side": "BUY",
    "amount": 5.0,  # MINIMUM $5!
    "price": price,
    "order_type": "GTC"
}).json()

print(f"Order placed: {order['order_id']}")
```

---

## Core Concepts

### Token ID vs Condition ID

| Field | Source | Use For |
|-------|--------|---------|
| `token_id` | `market["tokens"][i]["token_id"]` | Placing orders |
| `condition_id` | `market["condition_id"]` | Market details lookup |

**Critical:** Always use `market["tokens"][0]["token_id"]` for orders. Never use `clob_token_ids` or other fields.

### Order Amount Rules

| Rule | Value |
|------|-------|
| Minimum | $5.00 USD |
| Price Range | 0.01 - 0.99 |
| Order Types | GTC (default), FOK, MARKET, LIMIT |

### Market Status Flags

Markets have three boolean flags:
- `active`: Currently tradeable
- `archived`: Removed from main list
- `closed`: Resolved/settled

Always filter `active=true` to get tradeable markets.

---

## API Endpoints

### Markets

#### Get Active Markets
```http
GET /api/v1/markets/active
```

Parameters:
- `limit`: 1-100 (default: 50)
- `offset`: Pagination offset
- `order`: Sort field (volumeNum, liquidityNum, endDate)
- `ascending`: true/false
- `volume_num_min`: Minimum 24h volume

#### Get Markets with Filters
```http
GET /api/v1/markets
```

All filters:
| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Results count |
| `offset` | int | Pagination |
| `order` | string | Sort field |
| `ascending` | boolean | Sort direction |
| `ids` | string | Market IDs |
| `clob_token_ids` | string | CLOB token IDs |
| `condition_ids` | string | Condition IDs |
| `liquidity_num_min/max` | float | Liquidity range |
| `volume_num_min/max` | float | Volume range |
| `start_date_min/max` | string | ISO 8601 |
| `end_date_min/max` | string | ISO 8601 |
| `active` | boolean | Active only |
| `closed` | boolean | Closed only |
| `archived` | boolean | Archived only |

#### Get Trending Markets
```http
GET /api/v1/markets/trending?limit=20&volume_num_min=1000
```

#### Get Markets Ending Soon
```http
GET /api/v1/markets/ending-soon?days_ahead=7&limit=10
```

#### Get Sports Markets
```http
GET /api/v1/markets/sports?limit=50
```

#### Get Market Details
```http
GET /api/v1/markets/{token_id}
```

#### Get Current Price
```http
GET /api/v1/markets/{token_id}/price?side=BUY
```

#### Get Order Book
```http
GET /api/v1/markets/{token_id}/orderbook
```

#### Get Price History
```http
GET /api/v1/markets/{token_id}/price-history
```

#### Get Market Context
```http
GET /api/v1/markets/{token_id}/context
```

---

### Events

#### List Events
```http
GET /api/v1/events
```

Parameters:
- `limit`: 1-100
- `active`: Filter active events
- `archived`: Filter archived events
- `featured`: Filter featured events

#### Get Active Events
```http
GET /api/v1/events/active
```

#### Get Event Details
```http
GET /api/v1/events/{event_id}
```

---

### Orders

#### Create Order
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

Parameters:
| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `token_id` | Yes | string | From `market["tokens"][i]["token_id"]` |
| `side` | Yes | string | BUY or SELL |
| `amount` | Yes | float | Minimum $5.00 |
| `price` | No | float | 0.01-0.99 |
| `order_type` | No | string | GTC, FOK, MARKET, LIMIT |

Response:
```json
{
  "success": true,
  "order_id": "0xb6fd72c...",
  "status": "live"
}
```

#### Get Order Status
```http
GET /api/v1/orders/{order_id}
```

#### List Orders
```http
GET /api/v1/orders?limit=20&offset=0
```

#### Cancel Order
```http
DELETE /api/v1/orders/{order_id}
```

#### Cancel All Orders
```http
DELETE /api/v1/orders/cancel-all
```

---

### Wallet

#### Get Wallet Address
```http
GET /api/v1/wallet/address
```

#### Get USDC Balance
```http
GET /api/v1/wallet/balance
```

---

### Positions

#### Get Positions
```http
GET /api/v1/positions
```

#### Get Portfolio
```http
GET /api/v1/portfolio
```

#### Get Portfolio Summary
```http
GET /api/v1/portfolio/summary
```

---

### Trading Limits

#### Get Trading Limits
```http
GET /api/v1/trading/limits
```

#### Get Daily Stats
```http
GET /api/v1/trading/daily-stats
```

#### Check Can Trade
```http
POST /api/v1/trading/can-trade
Content-Type: application/json

{
  "amount": 10.0,
  "token_id": "0xabc123..."
}
```

---

### Alerts

#### Create Alert
```http
POST /api/v1/alerts
Content-Type: application/json

{
  "token_id": "0xabc123...",
  "side": "yes",
  "condition": "above",
  "threshold": 0.75
}
```

Parameters:
- `token_id`: Market token
- `side`: yes/no
- `condition`: above, below, crosses
- `threshold`: Price threshold (0-1)
- `webhook_url`: Optional callback URL

#### List Alerts
```http
GET /api/v1/alerts
```

#### Delete Alert
```http
DELETE /api/v1/alerts/{alert_id}
```

---

### Market Import

#### Get Importable Markets
```http
GET /api/v1/markets/importable
```

#### Import Market
```http
POST /api/v1/markets/import
Content-Type: application/json

{
  "polymarket_url": "https://polymarket.com/market/will-bitcoin-hit-100k"
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

### Webhooks

#### OpenClaw Trade Signal
```http
POST /api/v1/webhook/claw
Content-Type: application/json

{
  "token_id": "0xabc123...",
  "side": "BUY",
  "amount": 10.0,
  "price": 0.55,
  "order_type": "FOK"
}
```

#### Webhook Health
```http
GET /api/v1/webhook/health
```

---

### Security

#### Get IP Whitelist
```http
GET /api/v1/security/whitelist
```

#### Add IP to Whitelist
```http
POST /api/v1/security/whitelist/ip
Content-Type: application/json

{
  "ip": "203.0.113.50"
}
```

#### Check IP
```http
GET /api/v1/security/whitelist/check/{ip}
```

#### Get My IP
```http
GET /api/v1/security/my-ip
```

#### Add API Key
```http
POST /api/v1/security/api-keys
Content-Type: application/json

{
  "name": "my-key",
  "key": "sk_live_..."
}
```

#### Delete API Key
```http
DELETE /api/v1/security/api-keys?key=sk_live_...
```

---

### Health

#### Health Check
```http
GET /api/v1/health
```

#### Status
```http
GET /api/v1/status
```

---

## Complete Examples

### Find and Trade a Market

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# Step 1: Get active markets sorted by volume
response = httpx.get(f"{BASE_URL}/markets/active", params={
    "limit": 10,
    "volume_num_min": 5000,
    "order": "volumeNum",
    "ascending": False
}).json()

# Step 2: Select a market
market = response["markets"][0]
print(f"Trading: {market['question']}")

# Step 3: Get YES token
for token in market["tokens"]:
    if token["outcome"] == "Yes":
        token_id = token["token_id"]
        price = token["price"]
        break

# Step 4: Place order ($5 minimum)
order = httpx.post(f"{BASE_URL}/orders", json={
    "token_id": token_id,
    "side": "BUY",
    "amount": 5.0,
    "price": price,
    "order_type": "GTC"
}).json()

if order.get("success"):
    print(f"Order placed: {order['order_id']}")
else:
    print(f"Error: {order.get('error')}")
```

### Quick Trade Script

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# Get one high-volume active market
market = httpx.get(f"{BASE_URL}/markets/active", params={
    "limit": 1,
    "volume_num_min": 10000
}).json()["markets"][0]

# Place $5 order on YES
order = httpx.post(f"{BASE_URL}/orders", json={
    "token_id": market["tokens"][0]["token_id"],
    "side": "BUY",
    "amount": 5.0,
    "price": market["tokens"][0]["price"],
    "order_type": "GTC"
}).json()

print(order)
```

### Check Trading Limits

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# Get current limits and usage
limits = httpx.get(f"{BASE_URL}/trading/limits").json()
print(f"Daily limit: ${limits['daily_limit']}")
print(f"Used: ${limits['daily_used']}")
print(f"Remaining: ${limits['daily_remaining']}")

# Check daily stats
stats = httpx.get(f"{BASE_URL}/trading/daily-stats").json()
print(f"Today's trades: {stats['total_trades']}")
print(f"Volume: ${stats['volume_usd']}")
```

### Create Price Alert

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# Create alert for price above 0.75
alert = httpx.post(f"{BASE_URL}/alerts", json={
    "token_id": "0xabc123...",
    "side": "yes",
    "condition": "above",
    "threshold": 0.75,
    "webhook_url": "https://your-server.com/callback"
}).json()

print(f"Alert created: {alert['alert_id']}")
```

### OpenClaw Integration

```python
import httpx
import hmac
import hashlib
import json

BASE_URL = "http://localhost:8000/api/v1"
WEBHOOK_SECRET = "your_webhook_secret"

def send_trade_signal(token_id, side, amount, price=None):
    """Send trade signal to API (for OpenClaw integration)"""
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

# Send buy signal
result = send_trade_signal(
    token_id="0xabc123...",
    side="BUY",
    amount=50.0,
    price=0.45
)
print(f"Order created: {result['order_id']}")
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created (order placed) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Server Error |

### Common Errors

**"Size (X) lower than the minimum: 5"**
→ Increase order amount to at least $5

**"market not found" (404)**
→ Wrong ID. Use `condition_id` for market details, `token_id` for orders

**"Access restricted. Regional restrictions"**
→ Polymarket blocked your IP. Use a VPN

**"Unauthorized/Invalid api key" (401)**
→ Credentials not derived. Restart API to regenerate

**"Result is not set"**
→ Async/sync conflict. Restart API

---

## Environment Variables

```bash
# Required
POLYGON_WALLET_PRIVATE_KEY=0x...

# Auto-generated (do not manually set)
CLOB_API_KEY=
CLOB_SECRET=
CLOB_PASS_PHRASE=

# Optional
HOST=0.0.0.0
PORT=8000
MONGODB_URI=mongodb://localhost:27017
ENABLE_IP_WHITELIST=false
```

---

## Quick Reference

```python
# Get active markets
markets = httpx.get("/api/v1/markets/active").json()

# Get token_id
token_id = market["tokens"][0]["token_id"]

# Place order
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

1. **Token Location:** Always use `market["tokens"][i]["token_id"]`
2. **Minimum Amount:** $5.00 minimum
3. **Price Format:** 0.01 to 0.99
4. **Credentials:** Auto-derived from private key
5. **MongoDB:** Optional - API works without it
6. **Restart Required:** After changing `.env`
