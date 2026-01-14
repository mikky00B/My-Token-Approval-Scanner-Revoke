"""
Blacklist database models for known malicious contracts.
"""

from django.db import models


class BlacklistCategory(models.TextChoices):
    """Categories of blacklisted addresses."""

    DRAINER = "DRAINER", "Token Drainer"
    SCAM = "SCAM", "Scam Contract"
    PHISHING = "PHISHING", "Phishing"
    EXPLOIT = "EXPLOIT", "Known Exploit"
    UNKNOWN = "UNKNOWN", "Unknown Malicious"


class BlacklistEntry(models.Model):
    """
    Known malicious or suspicious contract addresses.
    """

    address = models.CharField(
        max_length=42, unique=True, db_index=True, help_text="Contract address (0x...)"
    )
    category = models.CharField(
        max_length=20,
        choices=BlacklistCategory.choices,
        default=BlacklistCategory.UNKNOWN,
    )
    severity = models.IntegerField(default=50, help_text="Risk points to add (0-100)")
    name = models.CharField(
        max_length=255, blank=True, help_text="Known name of the contract/scam"
    )
    source = models.CharField(
        max_length=255,
        blank=True,
        help_text="Source of blacklist entry (e.g., ChainAbuse, manual)",
    )
    notes = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "blacklist_entries"
        verbose_name_plural = "Blacklist entries"
        ordering = ["-severity", "-added_at"]

    def __str__(self):
        return f"{self.address[:10]}... ({self.category})"
