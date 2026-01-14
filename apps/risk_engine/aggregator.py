"""
Risk aggregation service.
Stage 5 of the scan pipeline.
"""

import logging
from typing import List
from shared.schemas import RiskEvaluation, WalletRiskSummary
from apps.approvals.enums import RiskLevel, risk_level_from_score

logger = logging.getLogger(__name__)


class RiskAggregator:
    """
    Aggregates individual approval risks into wallet-level risk.
    """

    @staticmethod
    def aggregate(
        wallet_address: str, evaluations: List[RiskEvaluation]
    ) -> WalletRiskSummary:
        """
        Aggregate risk evaluations into wallet summary.

        Args:
            wallet_address: Wallet address
            evaluations: List of RiskEvaluation objects

        Returns:
            WalletRiskSummary
        """
        if not evaluations:
            return WalletRiskSummary(
                wallet_address=wallet_address,
                total_approvals=0,
                total_risk_score=0,
                risk_level=RiskLevel.LOW,
                high_risk_count=0,
                critical_risk_count=0,
                evaluations=[],
            )

        # Sum risk points
        total_risk_score = sum(e.risk_points for e in evaluations)

        # Count high-risk approvals
        high_risk_count = sum(1 for e in evaluations if e.risk_level == RiskLevel.HIGH)

        critical_risk_count = sum(
            1 for e in evaluations if e.risk_level == RiskLevel.CRITICAL
        )

        # Determine wallet-level risk
        # Use max of: average risk per approval, or critical/high count thresholds
        avg_risk = total_risk_score / len(evaluations) if evaluations else 0

        # Boost wallet risk if multiple critical issues
        if critical_risk_count >= 3:
            wallet_risk_level = RiskLevel.CRITICAL
        elif critical_risk_count >= 1 or high_risk_count >= 5:
            wallet_risk_level = RiskLevel.HIGH
        elif high_risk_count >= 2:
            wallet_risk_level = RiskLevel.MEDIUM
        else:
            wallet_risk_level = risk_level_from_score(int(avg_risk))

        logger.info(
            f"Wallet {wallet_address}: {len(evaluations)} approvals, "
            f"score={total_risk_score}, level={wallet_risk_level.value}"
        )

        return WalletRiskSummary(
            wallet_address=wallet_address,
            total_approvals=len(evaluations),
            total_risk_score=total_risk_score,
            risk_level=wallet_risk_level,
            high_risk_count=high_risk_count,
            critical_risk_count=critical_risk_count,
            evaluations=evaluations,
        )


# Convenience function
def aggregate_risk(
    wallet_address: str, evaluations: List[RiskEvaluation]
) -> WalletRiskSummary:
    """Aggregate risk evaluations into wallet summary."""
    return RiskAggregator.aggregate(wallet_address, evaluations)
