"""
Django admin configuration for blacklists app.
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.blacklists.models import BlacklistEntry


@admin.register(BlacklistEntry)
class BlacklistEntryAdmin(admin.ModelAdmin):
    """Admin interface for BlacklistEntry model."""

    list_display = (
        "address_short",
        "category_badge",
        "severity",
        "name",
        "source",
        "is_active",
        "added_at",
    )
    list_filter = ("category", "is_active", "severity", "added_at")
    search_fields = ("address", "name", "source")
    readonly_fields = ("added_at",)

    fieldsets = (
        (
            "Contract Information",
            {"fields": ("address", "name", "category", "is_active")},
        ),
        ("Risk Assessment", {"fields": ("severity", "notes")}),
        ("Metadata", {"fields": ("source", "added_at")}),
    )

    def address_short(self, obj):
        """Display shortened address."""
        return obj.address[:10] + "..."

    address_short.short_description = "Address"

    def category_badge(self, obj):
        """Display category with color badge."""
        colors = {
            "DRAINER": "#dc3545",
            "SCAM": "#fd7e14",
            "PHISHING": "#ffc107",
            "EXPLOIT": "#e83e8c",
            "UNKNOWN": "#6c757d",
        }
        color = colors.get(obj.category, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_category_display(),
        )

    category_badge.short_description = "Category"

    actions = ["mark_active", "mark_inactive"]

    def mark_active(self, request, queryset):
        """Mark selected entries as active."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} entries marked as active.")

    mark_active.short_description = "Mark selected as active"

    def mark_inactive(self, request, queryset):
        """Mark selected entries as inactive."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} entries marked as inactive.")

    mark_inactive.short_description = "Mark selected as inactive"
