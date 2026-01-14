"""
Risk evaluation rules.
Stage 4 of the scan pipeline.
"""

from abc import ABC, abstractmethod
from typing import List
from shared.schemas import NormalizedApproval
from apps.approvals.enums import TokenType
from apps.blacklists.models import BlacklistEntry
import logging

logger = logging.getLogger(__name__)


class RiskRule(ABC):
    """
    Abstract base class for risk rules.
    Each rule evaluates an approval and returns points + reason.
    """

    points: int = 0
    reason: str = ""

    @abstractmethod
    def evaluate(self, approval: NormalizedApproval) -> bool:
        """
        Check if this rule applies to the approval.

        Args:
            approval: NormalizedApproval to evaluate

        Returns:
            True if rule applies, False otherwise
        """
        pass

    def get_points(self) -> int:
        """Get risk points for this rule."""
        return self.points

    def get_reason(self) -> str:
        """Get human-readable reason."""
        return self.reason


class UnlimitedERC20ApprovalRule(RiskRule):
    """
    Detects unlimited ERC20 approvals.
    High risk because spender can drain all tokens.
    """

    points = 25
    reason = "Unlimited ERC20 approval - spender can transfer any amount"

    def evaluate(self, approval: NormalizedApproval) -> bool:
        return approval.token_type == TokenType.ERC20 and approval.is_unlimited


class NFTOperatorApprovalRule(RiskRule):
    """
    Detects NFT operator approvals (approveForAll).
    High risk because operator can transfer all NFTs.
    """

    points = 30
    reason = "NFT operator approval - spender can transfer all your NFTs from this collection"

    def evaluate(self, approval: NormalizedApproval) -> bool:
        return (
            approval.token_type in (TokenType.ERC721, TokenType.ERC1155)
            and approval.is_operator
        )


class BlacklistedSpenderRule(RiskRule):
    """
    Detects approvals to known malicious contracts.
    Critical risk.
    """

    points = 50
    reason = "Approval to known malicious contract"

    def __init__(self):
        super().__init__()
        # Cache blacklist in memory for performance
        self._blacklist_cache = set(
            BlacklistEntry.objects.filter(is_active=True).values_list(
                "address", flat=True
            )
        )

    def evaluate(self, approval: NormalizedApproval) -> bool:
        spender = approval.spender_address.lower()
        if spender in self._blacklist_cache:
            # Update reason with specific blacklist info
            try:
                entry = BlacklistEntry.objects.get(address=spender)
                self.reason = f"Approval to known {entry.get_category_display()}: {entry.name or 'malicious contract'}"
                self.points = entry.severity
            except BlacklistEntry.DoesNotExist:
                pass
            return True
        return False


class UnknownSpenderRule(RiskRule):
    """
    Detects approvals to contracts we don't recognize.
    Medium risk - needs investigation.
    """

    points = 10
    reason = "Approval to unverified contract"

    # Well-known spenders (DEXs, marketplaces, etc.)
    KNOWN_SPENDERS = {
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap V2 Router
        "0xe592427a0aece92de3edee1f18e0157c05861564",  # Uniswap V3 Router
        "0x1111111254fb6c44baaac2c91e80f689c7e4a0cf",  # 1inch
        "0xdef1c0ded9bec7f1a1670819833240f027b25eff",  # 0x Exchange
        "0x00000000006c3852cbef3e08e8df289169ede581",  # OpenSea Seaport
        "0x7f268357a8c2552623316e2562d90e642bb538e5",  # OpenSea Legacy
    }

    def evaluate(self, approval: NormalizedApproval) -> bool:
        spender = approval.spender_address.lower()
        # Skip if it's a known good spender
        if spender in self.KNOWN_SPENDERS:
            return False
        # Skip if it's a zero address (placeholder)
        if spender == "0x" + "0" * 40:
            return False
        return True


class OldApprovalRule(RiskRule):
    """
    Detects very old approvals that might be forgotten.
    Low risk but worth reviewing.
    """

    points = 5
    reason = "Old approval (1+ years) - consider revoking if no longer needed"

    # Approximate blocks per year (Ethereum ~13s block time)
    BLOCKS_PER_YEAR = 2_400_000

    def evaluate(self, approval: NormalizedApproval) -> bool:
        if not approval.block_number:
            return False

        # TODO: Get current block number dynamically
        # For MVP, we'll skip this rule
        return False


# Registry of all active rules
ACTIVE_RULES: List[RiskRule] = [
    UnlimitedERC20ApprovalRule(),
    NFTOperatorApprovalRule(),
    BlacklistedSpenderRule(),
    UnknownSpenderRule(),
]


def get_active_rules() -> List[RiskRule]:
    """Get list of all active risk rules."""
    return ACTIVE_RULES
