"""
Chain-related constants and configurations.
"""

from enum import IntEnum


class ChainId(IntEnum):
    """Supported blockchain networks."""

    ETHEREUM = 1
    # Future: POLYGON = 137, BSC = 56, etc.


CHAIN_NAMES = {
    ChainId.ETHEREUM: "Ethereum Mainnet",
}

CHAIN_RPC_URLS = {
    ChainId.ETHEREUM: "https://eth.llamarpc.com",  # Public RPC
}

CHAIN_EXPLORERS = {
    ChainId.ETHEREUM: "https://etherscan.io",
}

# Max uint256 value for unlimited approvals
MAX_UINT256 = 2**256 - 1


def is_unlimited_approval(amount: int) -> bool:
    """Check if approval amount is effectively unlimited."""
    # Consider approvals > 90% of max as unlimited
    threshold = int(MAX_UINT256 * 0.9)
    return amount >= threshold
