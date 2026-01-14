"""
Improved normalizer that handles REAL approval data.
"""

import logging
from typing import List, Dict, Any
from shared.schemas import NormalizedApproval
from apps.approvals.enums import TokenType
from apps.chains.constants import is_unlimited_approval

logger = logging.getLogger(__name__)


class ImprovedApprovalNormalizer:
    """
    Normalizes REAL approval data with actual amounts.
    """

    @staticmethod
    def normalize_erc20_approval(
        wallet_address: str, raw_data: Dict[str, Any]
    ) -> NormalizedApproval:
        """
        Normalize ERC20 approval with REAL allowance amount.

        Args:
            wallet_address: Owner wallet address
            raw_data: Raw approval data with 'approved_amount' field

        Returns:
            NormalizedApproval object
        """
        token_address = raw_data.get("token_address", "").lower()
        spender_address = raw_data.get("spender_address", "").lower()

        # Use ACTUAL approved amount from RPC call
        approved_amount = raw_data.get("approved_amount", 0)

        # Check if unlimited (>90% of max uint256)
        is_unlimited = is_unlimited_approval(approved_amount)

        return NormalizedApproval(
            wallet_address=wallet_address.lower(),
            token_address=token_address,
            token_type=TokenType.ERC20,
            spender_address=spender_address,
            approved_amount=approved_amount,
            is_unlimited=is_unlimited,
            is_operator=False,
            block_number=raw_data.get("block_number"),
            transaction_hash=raw_data.get("transaction_hash", ""),
        )

    @staticmethod
    def normalize_nft_approval(
        wallet_address: str, raw_data: Dict[str, Any]
    ) -> NormalizedApproval:
        """
        Normalize NFT approval with VERIFIED operator status.

        Args:
            wallet_address: Owner wallet address
            raw_data: Raw approval data with 'is_active' field

        Returns:
            NormalizedApproval object
        """
        token_address = raw_data.get("token_address", "").lower()
        operator_address = raw_data.get("operator_address", "").lower()

        # Use VERIFIED operator status from RPC call
        is_active = raw_data.get("is_active", False)

        return NormalizedApproval(
            wallet_address=wallet_address.lower(),
            token_address=token_address,
            token_type=TokenType.ERC721,
            spender_address=operator_address,
            approved_amount=None,
            is_unlimited=False,
            is_operator=is_active,
            block_number=raw_data.get("block_number"),
            transaction_hash=raw_data.get("transaction_hash", ""),
        )

    @classmethod
    def normalize_all(
        cls, wallet_address: str, raw_approvals: Dict[str, List[Dict[str, Any]]]
    ) -> List[NormalizedApproval]:
        """
        Normalize all approvals from discovery stage.

        Args:
            wallet_address: Wallet address
            raw_approvals: Dict with 'erc20' and 'nft' lists

        Returns:
            List of NormalizedApproval objects
        """
        normalized = []

        # Normalize ERC20 approvals
        for raw_erc20 in raw_approvals.get("erc20", []):
            try:
                approval = cls.normalize_erc20_approval(wallet_address, raw_erc20)
                normalized.append(approval)
                logger.debug(
                    f"Normalized ERC20: {approval.token_address[:8]}... "
                    f"amount={approval.approved_amount}, unlimited={approval.is_unlimited}"
                )
            except Exception as e:
                logger.error(f"Failed to normalize ERC20 approval: {e}")
                continue

        # Normalize NFT approvals
        for raw_nft in raw_approvals.get("nft", []):
            try:
                approval = cls.normalize_nft_approval(wallet_address, raw_nft)
                normalized.append(approval)
                logger.debug(
                    f"Normalized NFT: {approval.token_address[:8]}... "
                    f"operator={approval.is_operator}"
                )
            except Exception as e:
                logger.error(f"Failed to normalize NFT approval: {e}")
                continue

        logger.info(f"Normalized {len(normalized)} REAL approvals for {wallet_address}")
        return normalized


# Export function
def normalize_approvals_improved(
    wallet_address: str, raw_approvals: Dict[str, List[Dict[str, Any]]]
) -> List[NormalizedApproval]:
    """Normalize raw approval data with real amounts."""
    return ImprovedApprovalNormalizer.normalize_all(wallet_address, raw_approvals)
