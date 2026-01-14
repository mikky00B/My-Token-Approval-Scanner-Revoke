"""
Normalized data schemas used across services.
These are the contracts between pipeline stages.
"""

from dataclasses import dataclass
from typing import Optional
from apps.approvals.enums import TokenType, RiskLevel


@dataclass
class NormalizedApproval:
    """
    Standardized approval data structure.
    All approval discovery adapters must output this format.
    """

    wallet_address: str
    token_address: str
    token_type: TokenType
    spender_address: str
    approved_amount: Optional[int]  # None for NFTs
    is_unlimited: bool
    is_operator: bool  # For NFT approveForAll
    block_number: Optional[int] = None
    transaction_hash: Optional[str] = None

    def __post_init__(self):
        """Validate data consistency."""
        # NFTs should have None amount
        if self.token_type in (TokenType.ERC721, TokenType.ERC1155):
            if self.approved_amount is not None:
                self.approved_amount = None

        # Normalize addresses to checksum format
        self.wallet_address = self.wallet_address.lower()
        self.token_address = self.token_address.lower()
        self.spender_address = self.spender_address.lower()


@dataclass
class RiskEvaluation:
    """
    Risk evaluation result for a single approval.
    """

    approval: NormalizedApproval
    risk_points: int
    risk_reasons: list[str]
    risk_level: RiskLevel

    @property
    def is_high_risk(self) -> bool:
        """Check if this approval is high risk."""
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


@dataclass
class WalletRiskSummary:
    """
    Aggregated risk summary for entire wallet.
    """

    wallet_address: str
    total_approvals: int
    total_risk_score: int
    risk_level: RiskLevel
    high_risk_count: int
    critical_risk_count: int
    evaluations: list[RiskEvaluation]
