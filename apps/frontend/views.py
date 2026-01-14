"""
Frontend views for Wallet Scanner UI.
"""

from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from apps.scans.orchestrator import scan_wallet
from apps.scans.models import WalletScan
from apps.wallets.services.validator import ValidationError


@require_http_methods(["GET"])
def home(request):
    """Home page with scanner form."""
    return render(request, "frontend/home.html")


@require_http_methods(["POST"])
def scan(request):
    """Handle wallet scan request via HTMX."""
    wallet_address = request.POST.get("wallet_address", "").strip()
    async_scan = request.POST.get("async_scan") == "on"

    if not wallet_address:
        return render(
            request,
            "frontend/partials/error.html",
            {"error": "Please enter a wallet address"},
        )

    try:
        # Execute scan
        scan_result = scan_wallet(wallet_address)

        if not scan_result:
            return render(
                request,
                "frontend/partials/error.html",
                {"error": "Scan failed. Please try again."},
            )

        # Get approvals
        approvals = scan_result.approvals.all().order_by("-risk_points")

        return render(
            request,
            "frontend/partials/scan_results.html",
            {"scan": scan_result, "approvals": approvals},
        )

    except ValidationError as e:
        return render(request, "frontend/partials/error.html", {"error": str(e)})
    except Exception as e:
        return render(
            request,
            "frontend/partials/error.html",
            {"error": f"An error occurred: {str(e)}"},
        )


@require_http_methods(["GET"])
def scan_detail(request, scan_id):
    """Detailed view of a specific scan."""
    scan = get_object_or_404(WalletScan, id=scan_id)
    approvals = scan.approvals.all().order_by("-risk_points")

    return render(
        request, "frontend/scan_detail.html", {"scan": scan, "approvals": approvals}
    )


@require_http_methods(["GET"])
def history(request):
    """View recent scan history."""
    recent_scans = (
        WalletScan.objects.filter(status="COMPLETED")
        .select_related("wallet")
        .order_by("-started_at")[:50]
    )

    return render(request, "frontend/history.html", {"scans": recent_scans})
