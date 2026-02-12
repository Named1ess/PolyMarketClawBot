"""
Solana Transaction Signing Utilities

Signs Solana transactions locally for Kalshi BYOW trading.
Uses a Node.js helper script because OpenClaw Docker doesn't support pip/solana-py.

SECURITY NOTE: The private key is read from SIMMER_SOLANA_KEY environment variable
and is NEVER logged or transmitted. All signing happens locally.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Environment variable for Solana private key
SOLANA_PRIVATE_KEY_ENV_VAR = "SIMMER_SOLANA_KEY"

# Path to the Node.js signing script (inside this package)
SCRIPTS_DIR = Path(__file__).parent / "scripts"
SIGN_SOLANA_SCRIPT = SCRIPTS_DIR / "sign-solana.js"


def has_solana_key() -> bool:
    """Check if a Solana private key is configured."""
    return bool(os.environ.get(SOLANA_PRIVATE_KEY_ENV_VAR))


def get_solana_public_key() -> Optional[str]:
    """
    Get the Solana public key (wallet address) from the configured private key.

    Returns:
        Base58-encoded public key, or None if no key is configured

    Raises:
        RuntimeError: If Node.js helpers are not installed
    """
    if not has_solana_key():
        return None

    # Use Node.js to derive public key from private key
    script = """
const { Keypair } = require('@solana/web3.js');
const bs58 = require('bs58');
const secretKey = bs58.decode(process.env.SIMMER_SOLANA_KEY);
const wallet = Keypair.fromSecretKey(secretKey);
console.log(wallet.publicKey.toBase58());
"""
    try:
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            env=os.environ,
            timeout=10
        )
        if result.returncode != 0:
            logger.error("Failed to get Solana public key: %s", result.stderr)
            return None
        return result.stdout.strip()
    except FileNotFoundError:
        logger.error("Node.js not found. Required for Solana signing.")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Timed out getting Solana public key")
        return None


def sign_solana_transaction(unsigned_tx_base64: str) -> str:
    """
    Sign a Solana transaction using the Node.js helper.

    The transaction must be a VersionedTransaction serialized to base64.
    This is the format returned by DFlow for Kalshi trades.

    Args:
        unsigned_tx_base64: Base64-encoded unsigned VersionedTransaction

    Returns:
        Base64-encoded signed transaction

    Raises:
        ValueError: If SIMMER_SOLANA_KEY env var is not set
        RuntimeError: If signing fails (Node.js not found, invalid key, etc.)

    Example:
        # Get unsigned tx from Simmer API (via DFlow)
        unsigned = api.get_kalshi_quote(market_id, side, amount)

        # Sign locally
        signed = sign_solana_transaction(unsigned['transaction'])

        # Submit signed tx
        result = api.submit_kalshi_trade(signed_transaction=signed, ...)
    """
    if not os.environ.get(SOLANA_PRIVATE_KEY_ENV_VAR):
        raise ValueError(
            f"{SOLANA_PRIVATE_KEY_ENV_VAR} environment variable required for Kalshi trading. "
            "Set it to your base58-encoded Solana secret key."
        )

    # Check if script exists
    if not SIGN_SOLANA_SCRIPT.exists():
        raise RuntimeError(
            f"Solana signing script not found at {SIGN_SOLANA_SCRIPT}. "
            "Ensure the simmer-sdk package is installed correctly."
        )

    try:
        result = subprocess.run(
            ["node", str(SIGN_SOLANA_SCRIPT), unsigned_tx_base64],
            capture_output=True,
            text=True,
            env=os.environ,
            timeout=30  # 30 second timeout
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Node.js is required for Solana signing but was not found. "
            "Install Node.js or ensure it's in your PATH."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Solana signing timed out after 30 seconds")

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        raise RuntimeError(f"Solana signing failed: {error_msg}")

    signed_tx = result.stdout.strip()
    if not signed_tx:
        raise RuntimeError("Solana signing returned empty result")

    return signed_tx


def validate_solana_key() -> bool:
    """
    Validate that the configured Solana key is valid.

    Returns:
        True if the key is valid and can be used for signing

    Example:
        if not validate_solana_key():
            print("Please set a valid SIMMER_SOLANA_KEY")
    """
    if not has_solana_key():
        return False

    # Try to derive public key - this validates the key format
    try:
        pubkey = get_solana_public_key()
        return pubkey is not None and len(pubkey) > 0
    except Exception:
        return False
