"""
API views for wallet scanning.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .serializers import ScanRequestSerializer
from apps.scans.orchestrator import scan_wallet
from apps.scans.models import WalletScan, ScanStatus
from apps.approvals.models import Approval
from apps.wallets.services.validator import ValidationError

logger = logging.getLogger(__name__)


class ScanWalletView(APIView):
    """
    POST /api/v1/scan-wallet/

    Initiates a wallet scan.
    """

    def post(self, request):
        """Handle scan request."""
        serializer = ScanRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet_address = serializer.validated_data["wallet_address"]
        chain_id = serializer.validated_data["chain_id"]
        async_scan = request.data.get("async", False)  # NEW: support async parameter

        try:
            if async_scan:
                # Async mode: Queue task and return immediately
                from apps.scans.tasks import scan_wallet_async
                from apps.wallets.models import Wallet
                from apps.scans.models import WalletScan, ScanStatus

                # Create wallet and pending scan
                wallet, _ = Wallet.objects.get_or_create(
                    address=wallet_address.lower(),
                    chain_id=chain_id,
                    defaults={"total_scans": 0},
                )

                scan = WalletScan.objects.create(
                    wallet=wallet, status=ScanStatus.PENDING
                )

                # Queue the task
                scan_wallet_async.delay(wallet_address, chain_id)

                return Response(
                    {
                        "scan_id": scan.id,
                        "wallet_address": wallet_address,
                        "chain_id": chain_id,
                        "status": "PENDING",
                        "message": "Scan queued successfully. Check status endpoint for results.",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            else:
                # Sync mode: Execute immediately (original behavior)
                scan = scan_wallet(wallet_address, chain_id)

                if not scan:
                    return Response(
                        {
                            "error": "Scan failed",
                            "message": "Unable to complete scan. Please try again.",
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                # Return complete results immediately
                return Response(
                    {
                        "scan_id": scan.id,
                        "wallet_address": wallet_address,
                        "chain_id": chain_id,
                        "status": scan.status,
                        "total_approvals": scan.total_approvals,
                        "total_risk_score": scan.total_risk_score,
                        "risk_level": scan.risk_level,
                        "high_risk_count": scan.high_risk_count,
                        "critical_risk_count": scan.critical_risk_count,
                        "message": "Scan completed successfully",
                    },
                    status=status.HTTP_200_OK,
                )

        except ValidationError as e:
            return Response(
                {"error": "Validation failed", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Scan error: {e}", exc_info=True)
            return Response(
                {"error": "Internal error", "message": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ScanStatusView(APIView):
    """
    GET /api/v1/scan-status/{scan_id}/

    Retrieves scan results.
    """

    def get(self, request, scan_id):
        """Get scan status and results."""
        scan = get_object_or_404(WalletScan, id=scan_id)

        # Build response
        response_data = {
            "scan_id": scan.id,
            "wallet_address": scan.wallet.address,
            "chain_id": scan.wallet.chain_id,
            "status": scan.status,
            "started_at": scan.started_at,
            "completed_at": scan.completed_at,
        }

        # Add results if completed
        if scan.status == ScanStatus.COMPLETED:
            # Get approvals with ordering
            approvals = scan.approvals.all().order_by("-risk_points")

            response_data.update(
                {
                    "total_approvals": scan.total_approvals,
                    "total_risk_score": scan.total_risk_score,
                    "risk_level": scan.risk_level,
                    "high_risk_count": scan.high_risk_count,
                    "critical_risk_count": scan.critical_risk_count,
                    "approvals": [
                        {
                            "id": a.id,
                            "token_address": a.token_address,
                            "token_type": a.token_type,
                            "spender_address": a.spender_address,
                            "approved_amount": (
                                str(a.approved_amount) if a.approved_amount else None
                            ),
                            "is_unlimited": a.is_unlimited,
                            "is_operator": a.is_operator,
                            "risk_points": a.risk_points,
                            "risk_level": a.risk_level,
                            "risk_reasons": a.risk_reasons,
                        }
                        for a in approvals
                    ],
                }
            )
        elif scan.status == ScanStatus.FAILED:
            response_data["error_message"] = scan.error_message

        return Response(response_data)


class ScanDetailView(APIView):
    """
    GET /api/v1/scans/{scan_id}/

    Retrieves detailed scan information.
    """

    def get(self, request, scan_id):
        """Get detailed scan information."""
        scan = get_object_or_404(WalletScan, id=scan_id)

        return Response(
            {
                "scan_id": scan.id,
                "wallet_address": scan.wallet.address,
                "chain_id": scan.wallet.chain_id,
                "status": scan.status,
                "total_approvals": scan.total_approvals,
                "total_risk_score": scan.total_risk_score,
                "risk_level": scan.risk_level,
                "high_risk_count": scan.high_risk_count,
                "critical_risk_count": scan.critical_risk_count,
                "started_at": scan.started_at,
                "completed_at": scan.completed_at,
                "error_message": (
                    scan.error_message if scan.status == ScanStatus.FAILED else None
                ),
            }
        )


class ScanApprovalsView(APIView):
    """
    GET /api/v1/scans/{scan_id}/approvals/

    Lists all approvals for a specific scan with filtering.
    """

    def get(self, request, scan_id):
        """Get all approvals for a scan."""
        scan = get_object_or_404(WalletScan, id=scan_id)

        if scan.status != ScanStatus.COMPLETED:
            return Response(
                {"error": "Scan not completed", "status": scan.status},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get query parameters for filtering
        risk_level = request.query_params.get("risk_level")
        token_type = request.query_params.get("token_type")

        approvals = scan.approvals.all().order_by("-risk_points")

        # Apply filters
        if risk_level:
            approvals = approvals.filter(risk_level=risk_level.upper())
        if token_type:
            approvals = approvals.filter(token_type=token_type.upper())

        return Response(
            {
                "scan_id": scan_id,
                "total_count": approvals.count(),
                "approvals": [
                    {
                        "id": a.id,
                        "token_address": a.token_address,
                        "token_type": a.token_type,
                        "spender_address": a.spender_address,
                        "approved_amount": (
                            str(a.approved_amount) if a.approved_amount else None
                        ),
                        "is_unlimited": a.is_unlimited,
                        "is_operator": a.is_operator,
                        "risk_points": a.risk_points,
                        "risk_level": a.risk_level,
                        "risk_reasons": a.risk_reasons,
                        "block_number": a.block_number,
                        "transaction_hash": a.transaction_hash,
                    }
                    for a in approvals
                ],
            }
        )


class ApprovalDetailView(APIView):
    """
    GET /api/v1/approvals/{approval_id}/

    Gets detailed information about a specific approval.
    """

    def get(self, request, approval_id):
        """Get approval details."""
        approval = get_object_or_404(Approval, id=approval_id)

        return Response(
            {
                "id": approval.id,
                "scan_id": approval.wallet_scan.id,
                "wallet_address": approval.wallet_scan.wallet.address,
                "token_address": approval.token_address,
                "token_type": approval.token_type,
                "spender_address": approval.spender_address,
                "approved_amount": (
                    str(approval.approved_amount) if approval.approved_amount else None
                ),
                "is_unlimited": approval.is_unlimited,
                "is_operator": approval.is_operator,
                "risk_points": approval.risk_points,
                "risk_level": approval.risk_level,
                "risk_reasons": approval.risk_reasons,
                "block_number": approval.block_number,
                "transaction_hash": approval.transaction_hash,
                "created_at": approval.created_at,
            }
        )


class WalletHistoryView(APIView):
    """
    GET /api/v1/wallets/{wallet_address}/scans/

    Lists all scans for a specific wallet.
    """

    def get(self, request, wallet_address):
        """Get scan history for a wallet."""
        # Normalize address
        wallet_address = wallet_address.lower()

        scans = WalletScan.objects.filter(wallet__address=wallet_address).order_by(
            "-started_at"
        )[
            :10
        ]  # Last 10 scans

        if not scans.exists():
            return Response(
                {
                    "wallet_address": wallet_address,
                    "scans": [],
                    "message": "No scans found for this wallet",
                }
            )

        return Response(
            {
                "wallet_address": wallet_address,
                "total_scans": scans.count(),
                "scans": [
                    {
                        "scan_id": scan.id,
                        "status": scan.status,
                        "total_approvals": scan.total_approvals,
                        "risk_level": scan.risk_level,
                        "risk_score": scan.total_risk_score,
                        "started_at": scan.started_at,
                        "completed_at": scan.completed_at,
                    }
                    for scan in scans
                ],
            }
        )


class HealthCheckView(APIView):
    """
    GET /api/v1/health/

    Health check endpoint.
    """

    def get(self, request):
        """Health check."""
        return Response({"status": "healthy", "version": "0.1.0"})


class MetricsView(APIView):
    """
    GET /api/v1/metrics/

    Application metrics endpoint.
    """

    def get(self, request):
        """Get application metrics."""
        from shared.metrics import Metrics
        from apps.scans.models import WalletScan
        from apps.wallets.models import Wallet
        from django.utils import timezone
        from datetime import timedelta

        # Get counts
        total_scans = WalletScan.objects.count()
        total_wallets = Wallet.objects.count()

        # Recent scans (last 24h)
        yesterday = timezone.now() - timedelta(days=1)
        recent_scans = WalletScan.objects.filter(started_at__gte=yesterday).count()

        # Scan stats
        completed_scans = WalletScan.objects.filter(status="COMPLETED").count()
        failed_scans = WalletScan.objects.filter(status="FAILED").count()

        # Timing metrics
        avg_scan_time = Metrics.get_avg_timing("scan.execution")

        return Response(
            {
                "scans": {
                    "total": total_scans,
                    "completed": completed_scans,
                    "failed": failed_scans,
                    "last_24h": recent_scans,
                    "avg_duration_seconds": round(avg_scan_time, 2),
                },
                "wallets": {"total": total_wallets},
                "cache": {"enabled": True},
            }
        )
