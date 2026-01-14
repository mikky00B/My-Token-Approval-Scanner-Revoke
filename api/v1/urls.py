"""
API v1 URL configuration.
"""

from django.urls import path
from .views import (
    ScanWalletView,
    ScanStatusView,
    ScanDetailView,
    ScanApprovalsView,
    ApprovalDetailView,
    WalletHistoryView,
    HealthCheckView,
    MetricsView,
)

app_name = "api_v1"

urlpatterns = [
    # Health & metrics
    path("health/", HealthCheckView.as_view(), name="health"),
    path("metrics/", MetricsView.as_view(), name="metrics"),
    # Scan endpoints
    path("scan-wallet/", ScanWalletView.as_view(), name="scan-wallet"),
    path("scan-status/<int:scan_id>/", ScanStatusView.as_view(), name="scan-status"),
    # RESTful scan endpoints
    path("scans/<int:scan_id>/", ScanDetailView.as_view(), name="scan-detail"),
    path(
        "scans/<int:scan_id>/approvals/",
        ScanApprovalsView.as_view(),
        name="scan-approvals",
    ),
    # Approval endpoints
    path(
        "approvals/<int:approval_id>/",
        ApprovalDetailView.as_view(),
        name="approval-detail",
    ),
    # Wallet endpoints
    path(
        "wallets/<str:wallet_address>/scans/",
        WalletHistoryView.as_view(),
        name="wallet-history",
    ),
]
