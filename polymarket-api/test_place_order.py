#!/usr/bin/env python
"""Test order placement - $5 test order"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.clients.polymarket import polymarket_client, _run_sync

print("=" * 60)
print("Testing Order Placement - $5 TEST ORDER")
print("=" * 60)

# 1. Get a market with good liquidity
print("\n[1] Fetching active markets...")
markets = _run_sync(polymarket_client.client.get_sampling_markets)
data = markets.get('data', []) if isinstance(markets, dict) else markets

if not data:
    print("  ERROR: No markets found!")
    sys.exit(1)

print(f"  Found {len(data)} markets")

# Find a market with decent volume
selected_market = None
selected_token = None

for m in data:
    tokens = m.get("tokens", [])
    question = m.get("question", "Unknown")[:60]
    volume = m.get("volume", 0)
    
    if tokens and volume > 1000:
        for t in tokens:
            if t.get("outcome") == "Yes" and 0.1 < float(t.get("price", 0.5)) < 0.9:
                selected_market = m
                selected_token = t
                print(f"\n[2] Selected market: {question}")
                print(f"    Volume: ${volume:,.0f}")
                print(f"    Token: {t.get('token_id', '')[:40]}...")
                print(f"    Price: ${float(t.get('price', 0)):.2f}")
                break
        if selected_token:
            break

if not selected_token:
    # Fallback to first available
    m = data[0]
    tokens = m.get("tokens", [])
    selected_market = m
    selected_token = tokens[0] if tokens else None
    print(f"\n[2] Using fallback market: {m.get('question', 'Unknown')[:60]}")

if not selected_token:
    print("  ERROR: No token available!")
    sys.exit(1)

# Extract details
token_id = selected_token.get("token_id")
condition_id = selected_market.get("condition_id")
current_price = float(selected_token.get("price", 0.5))
order_price = round(current_price - 0.02, 2)  # Slightly below market price
if order_price < 0.01:
    order_price = 0.01

print(f"\n[3] Order Details:")
print(f"    Token ID: {token_id[:50]}...")
print(f"    Condition ID: {condition_id}")
print(f"    Side: BUY")
print(f"    Amount: $5.00")
print(f"    Price: ${order_price:.2f}")

# 3. Place the order
print(f"\n[4] Placing order...")
try:
    result = _run_sync(
        polymarket_client._create_and_post_order_sync,
        token_id=token_id,
        side="BUY",
        amount=5.0,
        price=order_price,
        tick_size="0.01",
        neg_risk=False
    )
    
    print(f"\n[5] Order Response:")
    print(f"    {result}")
    
    if result:
        order_id = result.get('orderID') or result.get('id')
        status = result.get('status', 'UNKNOWN')
        
        if order_id:
            print(f"\n" + "=" * 60)
            print(f"  ORDER SUCCESSFUL!")
            print(f"  Order ID: {order_id}")
            print(f"  Status: {status}")
            print(f"=" * 60)
        else:
            print(f"\n[FAILED] Order may have been rejected:")
            print(f"  Response: {result}")
    else:
        print(f"\n[FAILED] No response from API")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
