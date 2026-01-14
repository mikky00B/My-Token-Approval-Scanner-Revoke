"""
Django admin configuration for wallets app.
"""

from django.contrib import admin
from apps.wallets.models import Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Admin interface for Wallet model."""

    list_display = (
        "address",
        "chain_id",
        "total_scans",
        "first_scanned_at",
        "last_scanned_at",
    )
    list_filter = ("chain_id", "first_scanned_at")
    search_fields = ("address",)
    readonly_fields = ("first_scanned_at", "last_scanned_at", "total_scans")

    def has_add_permission(self, request):
        """Wallets are created automatically during scans."""
        return False
