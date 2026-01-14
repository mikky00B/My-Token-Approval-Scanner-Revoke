"""
Approval-related database models.
"""

from django.db import models
from apps.scans.models import WalletScan
from apps.approvals.enums import TokenType, RiskLevel


class Approval(models.Model):
    """
    Represents a single token approval discovered during a scan.
    """

    wallet_scan = models.ForeignKey(
        WalletScan, on_delete=models.CASCADE, related_name="approvals"
    )

    # Approval details
    token_address = models.CharField(max_length=42, db_index=True)
    token_type = models.CharField(
        max_length=10, choices=[(t.value, t.name) for t in TokenType]
    )
    spender_address = models.CharField(max_length=42, db_index=True)

    # Approval amounts
    approved_amount = models.DecimalField(
        max_digits=78,  # Supports uint256
        decimal_places=0,
        null=True,
        blank=True,
        help_text="Approved amount (null for NFTs)",
    )
    is_unlimited = models.BooleanField(default=False)
    is_operator = models.BooleanField(default=False, help_text="For NFT approveForAll")

    # Risk evaluation
    risk_points = models.IntegerField(default=0)
    risk_level = models.CharField(
        max_length=20,
        choices=[(level.value, level.name) for level in RiskLevel],
        default=RiskLevel.LOW.value,
    )
    risk_reasons = models.JSONField(
        default=list, help_text="List of risk reason strings"
    )

    # Blockchain metadata
    block_number = models.BigIntegerField(null=True, blank=True)
    transaction_hash = models.CharField(max_length=66, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "approvals"
        indexes = [
            models.Index(fields=["wallet_scan", "risk_level"]),
            models.Index(fields=["spender_address"]),
            models.Index(fields=["token_address"]),
        ]

    def __str__(self):
        return f"{self.token_type} approval to {self.spender_address[:8]}..."

    @property
    def is_high_risk(self):
        """Check if this is a high-risk approval."""
        return self.risk_level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)
