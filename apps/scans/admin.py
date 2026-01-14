"""
Django admin configuration for scans app.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.scans.models import WalletScan


@admin.register(WalletScan)
class WalletScanAdmin(admin.ModelAdmin):
    """Admin interface for WalletScan model."""

    list_display = (
        "id",
        "wallet_address",
        "status_badge",
        "risk_level_badge",
        "total_approvals",
        "total_risk_score",
        "started_at",
        "duration",
    )
    list_filter = ("status", "risk_level", "started_at")
    search_fields = ("wallet__address",)
    readonly_fields = (
        "wallet",
        "status",
        "total_approvals",
        "total_risk_score",
        "risk_level",
        "high_risk_count",
        "critical_risk_count",
        "started_at",
        "completed_at",
        "error_message",
        "duration_display",
    )

    def wallet_address(self, obj):
        """Display wallet address."""
        return obj.wallet.address

    wallet_address.short_description = "Wallet"

    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            "PENDING": "gray",
            "IN_PROGRESS": "blue",
            "COMPLETED": "green",
            "FAILED": "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.status,
        )

    status_badge.short_description = "Status"

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
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.risk_level,
        )

    risk_level_badge.short_description = "Risk Level"

    def duration(self, obj):
        """Display scan duration."""
        if obj.duration_seconds:
            return f"{obj.duration_seconds:.1f}s"
        return "-"

    duration.short_description = "Duration"

    def duration_display(self, obj):
        """Detailed duration display."""
        if obj.duration_seconds:
            return f"{obj.duration_seconds:.2f} seconds"
        return "Not completed"

    duration_display.short_description = "Scan Duration"

    def has_add_permission(self, request):
        """Scans are created via API."""
        return False
