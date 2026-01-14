"""
Wallet-related database models.
"""

from django.db import models


class Wallet(models.Model):
    """
    Represents a scanned wallet address.
    """

    address = models.CharField(
        max_length=42,
        unique=True,
        db_index=True,
        help_text="Ethereum wallet address (0x...)",
    )
    chain_id = models.IntegerField(default=1, help_text="Blockchain network ID")
    first_scanned_at = models.DateTimeField(auto_now_add=True)
    last_scanned_at = models.DateTimeField(auto_now=True)
    total_scans = models.IntegerField(default=0)

    class Meta:
        db_table = "wallets"
        indexes = [
            models.Index(fields=["address", "chain_id"]),
        ]

    def __str__(self):
        return f"{self.address[:8]}... (Chain {self.chain_id})"
