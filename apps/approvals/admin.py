"""
Django admin configuration for approvals app.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.approvals.models import Approval


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    """Admin interface for Approval model."""

    list_display = (
        "id",
        "wallet_address",
        "token_type",
        "token_address_short",
        "spender_address_short",
        "risk_level_badge",
        "risk_points",
        "is_unlimited",
        "is_operator",
    )
    list_filter = ("token_type", "risk_level", "is_unlimited", "is_operator")
    search_fields = ("token_address", "spender_address", "wallet_scan__wallet__address")
    readonly_fields = (
        "wallet_scan",
        "token_address",
        "token_type",
        "spender_address",
        "approved_amount",
        "is_unlimited",
        "is_operator",
        "risk_points",
        "risk_level",
        "risk_reasons",
        "block_number",
        "transaction_hash",
        "created_at",
    )

    def wallet_address(self, obj):
        """Display wallet address."""
        return obj.wallet_scan.wallet.address[:10] + "..."

    wallet_address.short_description = "Wallet"

    def token_address_short(self, obj):
        """Display shortened token address."""
        return obj.token_address[:10] + "..."

    token_address_short.short_description = "Token"

    def spender_address_short(self, obj):
        """Display shortened spender address."""
        return obj.spender_address[:10] + "..."

    spender_address_short.short_description = "Spender"

    def risk_level_badge(self, obj):
        """Display risk level with color badge."""
        colors = {
            "LOW": "#28a745",
            "MEDIUM": "#ffc107",
            "HIGH": "#fd7e14",
            "CRITICAL": "#dc3545",
        }
        color = colors.get(obj.risk_level, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.risk_level,
        )

    risk_level_badge.short_description = "Risk"

    def has_add_permission(self, request):
        """Approvals are created during scans."""
        return False
