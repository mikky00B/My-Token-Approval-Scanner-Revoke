"""
Scan execution and results models.
"""

from django.db import models
from apps.wallets.models import Wallet
from apps.approvals.enums import RiskLevel


class ScanStatus(models.TextChoices):
    """Scan execution status."""

    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class WalletScan(models.Model):
    """
    Represents a single wallet scan execution.
    """

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="scans")
    status = models.CharField(
        max_length=20, choices=ScanStatus.choices, default=ScanStatus.PENDING
    )
    total_approvals = models.IntegerField(default=0)
    total_risk_score = models.IntegerField(default=0)
    risk_level = models.CharField(
        max_length=20,
        choices=[(level.value, level.name) for level in RiskLevel],
        default=RiskLevel.LOW.value,
    )
    high_risk_count = models.IntegerField(default=0)
    critical_risk_count = models.IntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "wallet_scans"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["wallet", "-started_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Scan {self.id} - {self.wallet.address[:8]}... ({self.status})"

    @property
    def duration_seconds(self):
        """Calculate scan duration if completed."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
