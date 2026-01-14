"""
Improved Etherscan API adapter that checks ACTUAL approvals.
This replaces the placeholder implementation.
"""

import requests
import time
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from web3 import Web3

logger = logging.getLogger(__name__)


class EtherscanError(Exception):
    """Raised when Etherscan API returns an error."""

    pass


class ImprovedEtherscanAdapter:
    """
    Improved adapter that:
    1. Queries actual Approval events (not transfers)
    2. Checks current allowance via RPC
    3. Returns REAL approval data
    """

    # Approval event signature: Approval(address indexed owner, address indexed spender, uint256 value)
    APPROVAL_EVENT_TOPIC = (
        "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
    )

    # ApprovalForAll event signature: ApprovalForAll(address indexed owner, address indexed operator, bool approved)
    APPROVAL_FOR_ALL_TOPIC = (
        "0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31"
    )

    def __init__(self, api_key: Optional[str] = None, rpc_url: Optional[str] = None):
        self.api_key = api_key or settings.ETHERSCAN_API_KEY
        self.base_url = getattr(
            settings, "ETHERSCAN_API_URL", "https://api.etherscan.io/v2/api"
        )
        self.rate_limit_delay = 1.0 / getattr(settings, "ETHERSCAN_RATE_LIMIT", 5)
        self.last_request_time = 0

        # Web3 for RPC calls
        self.rpc_url = rpc_url or getattr(
            settings, "WEB3_RPC_URL", "https://eth.llamarpc.com"
        )
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        if not self.api_key:
            logger.warning("No Etherscan API key provided")

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make Etherscan API request."""
        self._rate_limit()

        params["apikey"] = self.api_key
        if "chainid" not in params:
            params["chainid"] = "1"

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "0")
            message = data.get("message", "")

            if status == "0":
                if message in ("No transactions found", "No records found"):
                    return {"status": "1", "message": "OK", "result": []}
                elif message == "NOTOK":
                    raise EtherscanError(f"API error: {data.get('result', '')}")

            return data
        except requests.RequestException as e:
            raise EtherscanError(f"Request failed: {str(e)}")

    def get_approval_events(
        self, wallet_address: str, start_block: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get ERC20 Approval events from logs.
        This finds ACTUAL approval events, not transfers.
        """
        logger.info(f"Fetching Approval events for {wallet_address}")

        # Pad address to 32 bytes for topic
        padded_address = "0x" + "0" * 24 + wallet_address[2:].lower()

        params = {
            "chainid": "1",
            "module": "logs",
            "action": "getLogs",
            "topic0": self.APPROVAL_EVENT_TOPIC,
            "topic1": padded_address,  # Owner
            "fromBlock": str(start_block),
            "toBlock": "latest",
            "page": "1",
            "offset": "1000",
        }

        try:
            data = self._make_request(params)
            events = data.get("result", [])

            if isinstance(events, str):
                return []

            logger.info(f"Found {len(events)} Approval events")
            return events

        except EtherscanError as e:
            logger.error(f"Failed to fetch Approval events: {e}")
            return []

    def get_current_allowance(
        self, token_address: str, owner: str, spender: str
    ) -> int:
        """
        Check CURRENT allowance via RPC call.
        This is the actual approval amount right now.
        """
        try:
            # ERC20 allowance ABI
            allowance_abi = [
                {
                    "constant": True,
                    "inputs": [
                        {"name": "owner", "type": "address"},
                        {"name": "spender", "type": "address"},
                    ],
                    "name": "allowance",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "type": "function",
                }
            ]

            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address), abi=allowance_abi
            )

            allowance = contract.functions.allowance(
                Web3.to_checksum_address(owner), Web3.to_checksum_address(spender)
            ).call()

            return allowance

        except Exception as e:
            logger.error(f"Failed to check allowance for {token_address}: {e}")
            return 0

    def get_erc20_approvals(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Get REAL ERC20 approvals with actual allowance amounts.
        """
        logger.info(f"Discovering real ERC20 approvals for {wallet_address}")

        # Step 1: Get approval events
        events = self.get_approval_events(wallet_address)

        # Step 2: Extract unique token-spender pairs
        approval_pairs = {}
        for event in events:
            token = event.get("address", "").lower()

            # Decode spender from topics (topic2)
            topics = event.get("topics", [])
            if len(topics) < 3:
                continue

            spender = "0x" + topics[2][-40:]  # Last 40 chars = address

            key = (token, spender)
            if key not in approval_pairs:
                approval_pairs[key] = {
                    "token_address": token,
                    "spender_address": spender,
                    "block_number": int(event.get("blockNumber", "0"), 16),
                    "transaction_hash": event.get("transactionHash", ""),
                }

        logger.info(f"Found {len(approval_pairs)} unique token-spender pairs")

        # Step 3: Check CURRENT allowance for each pair
        active_approvals = []
        for (token, spender), data in approval_pairs.items():
            try:
                # Get current allowance via RPC
                allowance = self.get_current_allowance(token, wallet_address, spender)

                # Only include if there's an active approval
                if allowance > 0:
                    data["approved_amount"] = allowance
                    data["is_active"] = True
                    active_approvals.append(data)
                    logger.debug(
                        f"Active approval: {token[:8]}... to {spender[:8]}... = {allowance}"
                    )

            except Exception as e:
                logger.error(f"Error checking allowance: {e}")
                continue

        logger.info(f"Found {len(active_approvals)} ACTIVE ERC20 approvals")
        return active_approvals

    def get_nft_approval_events(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Get NFT ApprovalForAll events.
        """
        logger.info(f"Fetching NFT ApprovalForAll events for {wallet_address}")

        padded_address = "0x" + "0" * 24 + wallet_address[2:].lower()

        params = {
            "chainid": "1",
            "module": "logs",
            "action": "getLogs",
            "topic0": self.APPROVAL_FOR_ALL_TOPIC,
            "topic1": padded_address,
            "fromBlock": "0",
            "toBlock": "latest",
            "page": "1",
            "offset": "1000",
        }

        try:
            data = self._make_request(params)
            events = data.get("result", [])

            if isinstance(events, str):
                return []

            return events

        except EtherscanError as e:
            logger.error(f"Failed to fetch NFT events: {e}")
            return []

    def check_nft_operator_status(
        self, nft_address: str, owner: str, operator: str
    ) -> bool:
        """
        Check if operator is currently approved for all NFTs.
        """
        try:
            isApprovedForAll_abi = [
                {
                    "constant": True,
                    "inputs": [
                        {"name": "owner", "type": "address"},
                        {"name": "operator", "type": "address"},
                    ],
                    "name": "isApprovedForAll",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function",
                }
            ]

            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(nft_address), abi=isApprovedForAll_abi
            )

            is_approved = contract.functions.isApprovedForAll(
                Web3.to_checksum_address(owner), Web3.to_checksum_address(operator)
            ).call()

            return is_approved

        except Exception as e:
            logger.error(f"Failed to check NFT operator: {e}")
            return False

    def get_nft_approvals(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Get REAL NFT approvals with verified operator status.
        """
        logger.info(f"Discovering real NFT approvals for {wallet_address}")

        events = self.get_nft_approval_events(wallet_address)

        # Extract unique NFT-operator pairs
        approval_pairs = {}
        for event in events:
            nft = event.get("address", "").lower()

            topics = event.get("topics", [])
            if len(topics) < 3:
                continue

            operator = "0x" + topics[2][-40:]

            # Decode approved status from data
            data_hex = event.get("data", "0x")
            is_approved_in_event = data_hex.endswith("1")

            key = (nft, operator)
            approval_pairs[key] = {
                "token_address": nft,
                "operator_address": operator,
                "block_number": int(event.get("blockNumber", "0"), 16),
                "transaction_hash": event.get("transactionHash", ""),
                "was_approved": is_approved_in_event,
            }

        # Check CURRENT operator status
        active_approvals = []
        for (nft, operator), data in approval_pairs.items():
            try:
                # Check current status via RPC
                is_approved = self.check_nft_operator_status(
                    nft, wallet_address, operator
                )

                if is_approved:
                    data["is_active"] = True
                    active_approvals.append(data)
                    logger.debug(
                        f"Active NFT approval: {nft[:8]}... to {operator[:8]}..."
                    )

            except Exception as e:
                logger.error(f"Error checking NFT operator: {e}")
                continue

        logger.info(f"Found {len(active_approvals)} ACTIVE NFT approvals")
        return active_approvals

    def get_all_approvals(self, wallet_address: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get ALL active approvals with verified amounts.
        """
        logger.info(f"Starting REAL approval scan for {wallet_address}")

        erc20_approvals = self.get_erc20_approvals(wallet_address)
        nft_approvals = self.get_nft_approvals(wallet_address)

        return {"erc20": erc20_approvals, "nft": nft_approvals}


# Export function
def get_approvals_improved(wallet_address: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get real approvals with verified amounts."""
    adapter = ImprovedEtherscanAdapter()
    return adapter.get_all_approvals(wallet_address)
