# Polymarket Trading Bot API

A FastAPI-based REST API for Polymarket trading with OpenClaw integration. This API provides endpoints for placing orders, monitoring markets, and tracking trading activity.

## Features

- **REST API**: Full CRUD operations for orders, markets, and positions
- **Real-time Monitoring**: WebSocket support for live trade updates
- **Market Data**: Fetch events, markets, and order books from Polymarket
- **Order Management**: Place market/limit orders, cancel orders, track order status
- **Portfolio Tracking**: Monitor positions and balances
- **OpenClaw Integration**: Webhook support for automated trading strategies
- **Async/Non-blocking**: Built with FastAPI and Motor for high performance

## Quick Start

### Prerequisites

- Python 3.9+
- MongoDB (local or Atlas)
- Polygon RPC endpoint (Infura, Alchemy, etc.)
- Polymarket API keys (from https://polymarket.com/settings/keys)

### Installation

1. Clone the repository:
```bash
cd polymarket-api
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Start MongoDB (if local):
```bash
mongod --dbpath /path/to/data/dir
```

6. Run the API:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker build -t polymarket-api .
docker run -p 8000:8000 --env-file .env polymarket-api
```

## API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /status` - System status

### Markets
- `GET /api/v1/markets` - List all markets
- `GET /api/v1/markets/{token_id}` - Get market details
- `GET /api/v1/markets/{token_id}/orderbook` - Get order book
- `GET /api/v1/markets/{token_id}/price` - Get current price

### Events
- `GET /api/v1/events` - List all events
- `GET /api/v1/events/{event_id}` - Get event details
- `GET /api/v1/events/active` - Get active trading events

### Orders
- `POST /api/v1/orders` - Place a new order
- `GET /api/v1/orders` - List orders
- `GET /api/v1/orders/{order_id}` - Get order details
- `DELETE /api/v1/orders/{order_id}` - Cancel an order
- `DELETE /api/v1/orders/cancel-all` - Cancel all orders

### Positions
- `GET /api/v1/positions` - Get all positions
- `GET /api/v1/positions/{token_id}` - Get position for specific token
- `GET /api/v1/portfolio` - Get portfolio summary

### Wallet
- `GET /api/v1/wallet/balance` - Get USDC balance
- `GET /api/v1/wallet/address` - Get wallet address
- `POST /api/v1/wallet/approve` - Set token allowances

### OpenClaw Webhooks
- `POST /api/v1/webhook/claw` - OpenClaw trade webhook
- `POST /api/v1/webhook/order-status` - Order status update webhook

### WebSocket
- `WS /ws/orders` - Real-time order updates
- `WS /ws/trades` - Real-time trade updates
- `WS /ws/positions` - Real-time position updates

## Usage Examples

### Place a Market Order

```python
import httpx

# Buy 10 USDC worth of Yes tokens
response = httpx.post(
    "http://localhost:8000/api/v1/orders",
    json={
        "token_id": "your_token_id",
        "side": "BUY",
        "amount": 10.0,
        "order_type": "FOK"  # Fill Or Kill
    }
)
print(response.json())
```

### Get Market Order Book

```python
import httpx

response = httpx.get(
    "http://localhost:8000/api/v1/markets/{token_id}/orderbook"
)
print(response.json())
```

### Subscribe to Real-time Trades (WebSocket)

```python
import asyncio
import websockets

async def handler():
    async with websockets.connect("ws://localhost:8000/ws/trades") as ws:
        while True:
            message = await ws.recv()
            print(f"New trade: {message}")

asyncio.run(handler())
```

### Using with OpenClaw

Configure OpenClaw to send webhooks to:
```
http://your-api-server:8000/api/v1/webhook/claw
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|------------|----------|
| `POLYGON_WALLET_PRIVATE_KEY` | Your Polygon wallet private key | Yes |
| `CLOB_API_KEY` | Polymarket API key | Yes |
| `CLOB_SECRET` | Polymarket API secret | Yes |
| `CLOB_PASS_PHRASE` | Polymarket API passphrase | Yes |
| `MONGO_URI` | MongoDB connection string | Yes |
| `CHAIN_ID` | Polygon chain ID (137) | No |
| `RPC_URL` | Polygon RPC endpoint | Yes |

### Token Allowances

Before trading, you need to approve token allowances for:
- USDC contract: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
- CTF contract: `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`

Approve for these exchanges:
- Main: `0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e`
- Neg Risk: `0xC5d563A36AE78145C45a50134d48A1215220f80a`
- Neg Risk Adapter: `0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296`

## Project Structure

```
polymarket-api/
├── main.py                    # FastAPI application entry point
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app factory
│   ├── config.py             # Configuration management
│   ├── models/              # Pydantic data models
│   │   ├── __init__.py
│   │   ├── orders.py        # Order-related models
│   │   ├── markets.py       # Market/Event models
│   │   └── user.py          # User/Position models
│   ├── clients/             # API clients
│   │   ├── __init__.py
│   │   ├── polymarket.py    # Polymarket CLOB client
│   │   ├── gamma.py         # Gamma API client
│   │   └── wallet.py        # Wallet/Web3 client
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── order_service.py # Order management
│   │   ├── market_service.py# Market data
│   │   └── monitor.py       # Trade monitoring
│   ├── routes/              # API routes
│   │   ├── __init__.py
│   │   ├── orders.py        # Order endpoints
│   │   ├── markets.py       # Market endpoints
│   │   ├── wallet.py        # Wallet endpoints
│   │   └── webhook.py       # Webhook endpoints
│   └── utils/               # Utilities
│       ├── __init__.py
│       ├── logger.py        # Logging setup
│       └── helpers.py       # Helper functions
├── tests/                    # Unit tests
├── .env.example              # Environment template
├── requirements.txt         # Dependencies
└── Dockerfile              # Docker configuration
```

## License

MIT License
