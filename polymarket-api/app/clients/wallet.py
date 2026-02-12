# Wallet/Web3 Client
"""
Web3 client for blockchain interactions
"""
import time
from typing import Optional
from web3 import Web3

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WalletClient:
    """Client for wallet and blockchain operations"""

    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.POLYGON_RPC_URL))

        self.private_key = settings.POLYGON_WALLET_PRIVATE_KEY
        self.chain_id = settings.CHAIN_ID

        # Token addresses
        self.usdc_address = settings.USDC_CONTRACT_ADDRESS
        self.ctf_address = settings.CTF_CONTRACT_ADDRESS

        # Exchange addresses
        self.exchange_address = settings.EXCHANGE_ADDRESS
        self.neg_risk_exchange_address = settings.NEG_RISK_EXCHANGE_ADDRESS
        self.neg_risk_adapter_address = settings.NEG_RISK_ADAPTER_ADDRESS

        # ERC20 ABI (simplified for approval)
        self.erc20_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "spender", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "owner", "type": "address"},
                    {"internalType": "address", "name": "spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

        # ERC1155 ABI (simplified for approval)
        self.erc1155_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "operator", "type": "address"},
                    {"internalType": "bool", "name": "approved", "type": "bool"}
                ],
                "name": "setApprovalForAll",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

        # Initialize contracts
        self.usdc_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.usdc_address),
            abi=self.erc20_abi
        )
        self.ctf_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.ctf_address),
            abi=self.erc1155_abi
        )

    def get_address(self) -> str:
        """Get wallet address from private key"""
        if not self.private_key:
            raise ValueError("Private key not configured")
        account = self.w3.eth.account.from_key(self.private_key)
        return account.address

    def get_usdc_balance(self) -> float:
        """Get USDC balance"""
        address = self.get_address()
        balance_raw = self.usdc_contract.functions.balanceOf(address).call()
        return float(balance_raw / 10**6)  # USDC has 6 decimals

    def get_usdc_balance_raw(self) -> int:
        """Get USDC balance in raw format"""
        address = self.get_address()
        return self.usdc_contract.functions.balanceOf(address).call()

    def get_usdc_allowance(self, spender_address: str) -> float:
        """Get USDC allowance for a spender"""
        address = self.get_address()
        spender = Web3.to_checksum_address(spender_address)
        allowance_raw = self.usdc_contract.functions.allowance(
            address, spender
        ).call()
        return float(allowance_raw / 10**6)

    def _send_transaction(self, tx: dict) -> str:
        """Send a raw transaction and return tx hash"""
        if not self.private_key:
            raise ValueError("Private key not configured")

        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return tx_hash.hex()

    def approve_usdc(self, spender_address: str, amount: float = None) -> str:
        """Approve USDC spending for an exchange"""
        if amount is None:
            amount_raw = 2**256 - 1  # max uint256
        else:
            amount_raw = int(amount * 10**6)

        address = self.get_address()
        spender = Web3.to_checksum_address(spender_address)
        nonce = self.w3.eth.get_transaction_count(address)

        tx = self.usdc_contract.functions.approve(
            spender, amount_raw
        ).build_transaction({
            "chainId": self.chain_id,
            "from": address,
            "nonce": nonce,
            "gas": 100000,
            "gasPrice": self.w3.eth.gas_price
        })

        tx_hash = self._send_transaction(tx)
        logger.info(f"USDC approval tx: {tx_hash}")
        return tx_hash

    def approve_ctf(self, spender_address: str) -> str:
        """Approve CTF (conditional tokens) for an exchange"""
        address = self.get_address()
        spender = Web3.to_checksum_address(spender_address)
        nonce = self.w3.eth.get_transaction_count(address)

        tx = self.ctf_contract.functions.setApprovalForAll(
            spender, True
        ).build_transaction({
            "chainId": self.chain_id,
            "from": address,
            "nonce": nonce,
            "gas": 100000,
            "gasPrice": self.w3.eth.gas_price
        })

        tx_hash = self._send_transaction(tx)
        logger.info(f"CTF approval tx: {tx_hash}")
        return tx_hash

    def approve_all_tokens(self) -> dict:
        """Approve tokens for all exchanges"""
        results = {}

        # Approve USDC for main exchange
        try:
            tx_hash = self.approve_usdc(self.exchange_address)
            results["usdc_main"] = tx_hash
        except Exception as e:
            logger.error(f"Failed to approve USDC for main exchange: {e}")
            results["usdc_main"] = str(e)

        # Approve USDC for neg risk exchange
        try:
            tx_hash = self.approve_usdc(self.neg_risk_exchange_address)
            results["usdc_neg_risk"] = tx_hash
        except Exception as e:
            logger.error(f"Failed to approve USDC for neg risk exchange: {e}")
            results["usdc_neg_risk"] = str(e)

        # Approve USDC for neg risk adapter
        try:
            tx_hash = self.approve_usdc(self.neg_risk_adapter_address)
            results["usdc_neg_risk_adapter"] = tx_hash
        except Exception as e:
            logger.error(f"Failed to approve USDC for neg risk adapter: {e}")
            results["usdc_neg_risk_adapter"] = str(e)

        # Approve CTF for main exchange
        try:
            tx_hash = self.approve_ctf(self.exchange_address)
            results["ctf_main"] = tx_hash
        except Exception as e:
            logger.error(f"Failed to approve CTF for main exchange: {e}")
            results["ctf_main"] = str(e)

        # Approve CTF for neg risk exchange
        try:
            tx_hash = self.approve_ctf(self.neg_risk_exchange_address)
            results["ctf_neg_risk"] = tx_hash
        except Exception as e:
            logger.error(f"Failed to approve CTF for neg risk exchange: {e}")
            results["ctf_neg_risk"] = str(e)

        # Approve CTF for neg risk adapter
        try:
            tx_hash = self.approve_ctf(self.neg_risk_adapter_address)
            results["ctf_neg_risk_adapter"] = tx_hash
        except Exception as e:
            logger.error(f"Failed to approve CTF for neg risk adapter: {e}")
            results["ctf_neg_risk_adapter"] = str(e)

        return results

    def get_all_allowances(self) -> dict:
        """Get all token allowances"""
        return {
            "usdc_main": self.get_usdc_allowance(self.exchange_address),
            "usdc_neg_risk": self.get_usdc_allowance(self.neg_risk_exchange_address),
            "usdc_neg_risk_adapter": self.get_usdc_allowance(self.neg_risk_adapter_address),
        }


# Singleton instance
wallet_client = WalletClient()
