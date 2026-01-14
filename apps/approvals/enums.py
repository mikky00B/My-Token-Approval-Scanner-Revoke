"""
Enums for approval-related data.
"""

from enum import Enum


class TokenType(str, Enum):
    """Token standard types."""

    ERC20 = "ERC20"
    ERC721 = "ERC721"
    ERC1155 = "ERC1155"
    UNKNOWN = "UNKNOWN"


class RiskLevel(str, Enum):
    """Risk classification levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def risk_level_from_score(score: int) -> RiskLevel:
    """Convert numeric risk score to risk level."""
    if score >= 60:
        return RiskLevel.CRITICAL
    elif score >= 40:
        return RiskLevel.HIGH
    elif score >= 20:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW
