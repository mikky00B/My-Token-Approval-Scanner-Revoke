"""
Web3 service for on-chain approval verification.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from web3 import Web3
from web3.exceptions import ContractLogicError
from django.conf import settings

logger = logging.getLogger(__name__)


class Web3Service:
    """
    Service for interacting with Ethereum via Web3.
    """

    def __init__(self, rpc_url: Optional[str] = None):
        """Initialize Web3 connection."""
        self.rpc_url = rpc_url or getattr(
            settings, "WEB3_RPC_URL", "https://eth.llamarpc.com"
        )
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        # Load ApprovalInspector contract if available
        self.inspector_contract = None
        self._load_inspector_contract()

        if not self.w3.is_connected():
            logger.warning(f"Failed to connect to RPC: {self.rpc_url}")

    def _load_inspector_contract(self):
        """Load ApprovalInspector contract ABI."""
        try:
            # Try to load from vyper_contracts/abi
            base_dir = Path(__file__).parent.parent.parent.parent
            abi_path = base_dir / "vyper_contracts" / "abi" / "ApprovalInspector.json"

            if abi_path.exists():
                with open(abi_path, "r") as f:
                    abi = json.load(f)

                # Get deployed address from settings
                inspector_address = getattr(
                    settings, "INSPECTOR_CONTRACT_ADDRESS", None
                )

                if inspector_address:
                    self.inspector_contract = self.w3.eth.contract(
                        address=Web3.to_checksum_address(inspector_address), abi=abi
                    )
                    logger.info(f"Loaded ApprovalInspector at {inspector_address}")
                else:
                    logger.info(
                        "ApprovalInspector ABI loaded but no deployment address configured"
                    )

        except Exception as e:
            logger.warning(f"Could not load ApprovalInspector contract: {e}")

    def check_erc20_allowance(
        self, token_address: str, owner_address: str, spender_address: str
    ) -> int:
        """
        Check ERC20 allowance on-chain.

        Args:
            token_address: ERC20 token contract address
            owner_address: Token owner address
            spender_address: Spender address

        Returns:
            Allowance amount (0 if check fails)
        """
        try:
            # ERC20 allowance function signature
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
                Web3.to_checksum_address(owner_address),
                Web3.to_checksum_address(spender_address),
            ).call()

            return allowance

        except Exception as e:
            logger.error(f"Failed to check ERC20 allowance: {e}")
            return 0

    def check_nft_approval(
        self, token_address: str, owner_address: str, operator_address: str
    ) -> bool:
        """
        Check NFT operator approval on-chain.

        Args:
            token_address: NFT contract address
            owner_address: Token owner address
            operator_address: Operator address

        Returns:
            True if approved, False otherwise
        """
        try:
            # isApprovedForAll function signature
            approval_abi = [
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
                address=Web3.to_checksum_address(token_address), abi=approval_abi
            )

            is_approved = contract.functions.isApprovedForAll(
                Web3.to_checksum_address(owner_address),
                Web3.to_checksum_address(operator_address),
            ).call()

            return is_approved

        except Exception as e:
            logger.error(f"Failed to check NFT approval: {e}")
            return False

    def batch_check_erc20_approvals(
        self, owner_address: str, token_spender_pairs: List[tuple]
    ) -> List[Dict[str, Any]]:
        """
        Batch check multiple ERC20 approvals using ApprovalInspector contract.

        Args:
            owner_address: Wallet address
            token_spender_pairs: List of (token_address, spender_address) tuples

        Returns:
            List of approval data dicts
        """
        if not self.inspector_contract:
            # Fallback to individual calls
            logger.info("No inspector contract, falling back to individual calls")
            results = []
            for token, spender in token_spender_pairs:
                allowance = self.check_erc20_allowance(token, owner_address, spender)
                results.append(
                    {
                        "token": token,
                        "spender": spender,
                        "amount": allowance,
                        "is_unlimited": allowance >= (2**256 - 1) * 0.9,
                    }
                )
            return results

        try:
            tokens = [pair[0] for pair in token_spender_pairs]
            spenders = [pair[1] for pair in token_spender_pairs]

            # Call contract
            approvals = self.inspector_contract.functions.checkERC20Approvals(
                Web3.to_checksum_address(owner_address),
                [Web3.to_checksum_address(t) for t in tokens],
                [Web3.to_checksum_address(s) for s in spenders],
            ).call()

            return [
                {
                    "token": approval[0],
                    "spender": approval[1],
                    "amount": approval[2],
                    "is_unlimited": approval[3],
                }
                for approval in approvals
            ]

        except Exception as e:
            logger.error(f"Batch check failed: {e}")
            return []


# Singleton instance
_web3_service = None


def get_web3_service() -> Web3Service:
    """Get or create Web3Service singleton."""
    global _web3_service
    if _web3_service is None:
        _web3_service = Web3Service()
    return _web3_service
