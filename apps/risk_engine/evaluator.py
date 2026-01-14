"""
Risk evaluation engine.
Stage 4 of the scan pipeline.
"""

import logging
from typing import List
from shared.schemas import NormalizedApproval, RiskEvaluation
from apps.approvals.enums import risk_level_from_score
from apps.risk_engine.rules import get_active_rules

logger = logging.getLogger(__name__)


class RiskEvaluator:
    """
    Evaluates risk for approvals using a rule-based system.
    """

    def __init__(self):
        self.rules = get_active_rules()
        logger.info(f"Initialized RiskEvaluator with {len(self.rules)} rules")

    def evaluate_approval(self, approval: NormalizedApproval) -> RiskEvaluation:
        """
        Evaluate risk for a single approval.

        Args:
            approval: NormalizedApproval to evaluate

        Returns:
            RiskEvaluation with points and reasons
        """
        total_points = 0
        reasons = []

        # Run all rules
        for rule in self.rules:
            try:
                if rule.evaluate(approval):
                    total_points += rule.get_points()
                    reasons.append(rule.get_reason())
            except Exception as e:
                logger.error(f"Rule evaluation failed: {e}")
                continue

        # Determine risk level from score
        risk_level = risk_level_from_score(total_points)

        return RiskEvaluation(
            approval=approval,
            risk_points=total_points,
            risk_reasons=reasons,
            risk_level=risk_level,
        )

    def evaluate_all(self, approvals: List[NormalizedApproval]) -> List[RiskEvaluation]:
        """
        Evaluate risk for multiple approvals.

        Args:
            approvals: List of NormalizedApproval objects

        Returns:
            List of RiskEvaluation objects
        """
        logger.info(f"Evaluating {len(approvals)} approvals")

        evaluations = []
        for approval in approvals:
            try:
                evaluation = self.evaluate_approval(approval)
                evaluations.append(evaluation)
            except Exception as e:
                logger.error(f"Failed to evaluate approval: {e}")
                continue

        logger.info(f"Completed evaluation for {len(evaluations)} approvals")
        return evaluations


# Convenience function
def evaluate_approvals(approvals: List[NormalizedApproval]) -> List[RiskEvaluation]:
    """Evaluate risk for a list of approvals."""
    evaluator = RiskEvaluator()
    return evaluator.evaluate_all(approvals)
