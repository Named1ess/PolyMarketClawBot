#!/usr/bin/env python
"""Test order placement locally"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.clients.polymarket import polymarket_client, _run_sync

print("=" * 60)
print("Testing Polymarket Order Placement")
print("=" * 60)

# Check client initialization
print("\n[1] Checking client initialization...")
print(f"  Client host: {polymarket_client.host}")
print(f"  Wallet address: {polymarket_client.wallet_address}")

# Get markets
print("\n[2] Fetching active markets...")
try:
    markets = _run_sync(polymarket_client.client.get_sampling_markets)
    if isinstance(markets, dict):
        data = markets.get('data', [])
    else:
        data = markets or []
    
    print(f"  Found {len(data)} markets")
    
    if data:
        # Find a market with tokens
        for m in data[:5]:
            tokens = m.get("tokens", [])
            question = m.get("question", "Unknown")[:50]
            if tokens:
                print(f"\n  Selected market: {question}...")
                print(f"  Tokens: {len(tokens)}")
                for t in tokens[:2]:
                    print(f"    - {t.get('outcome')}: {t.get('token_id', '')[:30]}... @ ${t.get('price', 0):.2f}")
                break
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Try to get order book for a token
if data:
    for m in data:
        tokens = m.get("tokens", [])
        if tokens:
            token_id = tokens[0].get("token_id")
            if token_id:
                print(f"\n[3] Getting order book for {token_id[:30]}...")
                try:
                    ob = _run_sync(polymarket_client.client.get_order_book, token_id)
                    print(f"  Order book: {ob}")
                except Exception as e:
                    print(f"  Order book error: {e}")

# Try to get API credentials
print("\n[4] Checking API credentials...")
try:
    creds = _run_sync(polymarket_client.client.create_or_derive_api_creds)
    if creds:
        print(f"  API Key: {creds.api_key[:20]}...")
        print(f"  API Secret: {creds.api_secret[:20]}...")
        print(f"  API Passphrase: {creds.api_passphrase[:20]}...")
    else:
        print("  WARNING: create_or_derive_api_creds returned None!")
except Exception as e:
    print(f"  ERROR deriving credentials: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
