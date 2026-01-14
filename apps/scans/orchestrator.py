"""
Scan orchestration service.
Coordinates the complete scan pipeline.
"""

import logging
from datetime import datetime
from typing import Optional
from django.db import transaction
from django.utils import timezone

from apps.wallets.models import Wallet
from apps.wallets.services.validator import validate_scan_input, ValidationError
from apps.approvals.services.adapters.indexer import get_approvals_improved
from apps.approvals.services.normalizer import normalize_approvals_improved
from apps.risk_engine.evaluator import evaluate_approvals
from apps.risk_engine.aggregator import aggregate_risk
from apps.scans.models import WalletScan, ScanStatus
from apps.approvals.models import Approval
from apps.scans.cache import ScanCache
from shared.schemas import WalletRiskSummary

logger = logging.getLogger(__name__)


class ScanOrchestrator:
    """
    Orchestrates the complete wallet scan pipeline.

    Pipeline stages:
    1. Validate input
    2. Discover approvals (Etherscan)
    3. Normalize data
    4. Evaluate risk
    5. Aggregate results
    6. Persist to database
    """

    def execute(
        self, wallet_address: str, chain_id: int = 1, force_refresh: bool = False
    ) -> Optional[WalletScan]:
        """
        Execute complete scan pipeline.

        Args:
            wallet_address: Wallet address to scan
            chain_id: Chain ID (default: 1 for Ethereum)
            force_refresh: If True, bypass cache

        Returns:
            WalletScan object if successful, None if failed
        """
        scan = None

        try:
            # Stage 1: Validate
            logger.info(f"Starting scan for {wallet_address}")
            normalized_address, chain_id = validate_scan_input(wallet_address, chain_id)

            # Check cache unless force refresh
            if not force_refresh:
                cached_scan_id = ScanCache.get_recent_scan(normalized_address, chain_id)
                if cached_scan_id:
                    try:
                        cached_scan = WalletScan.objects.get(id=cached_scan_id)
                        logger.info(f"Returning cached scan {cached_scan_id}")
                        return cached_scan
                    except WalletScan.DoesNotExist:
                        # Cache stale, continue with new scan
                        ScanCache.invalidate_wallet(normalized_address, chain_id)

            # Get or create wallet
            wallet, _ = Wallet.objects.get_or_create(
                address=normalized_address,
                chain_id=chain_id,
                defaults={"total_scans": 0},
            )

            # Create scan record
            scan = WalletScan.objects.create(
                wallet=wallet, status=ScanStatus.IN_PROGRESS
            )

            # Stage 2: Discover approvals
            logger.info(f"[Scan {scan.id}] Discovering approvals")
            raw_approvals = get_approvals_improved(normalized_address)

            # Stage 3: Normalize
            logger.info(f"[Scan {scan.id}] Normalizing approvals")
            normalized_approvals = normalize_approvals_improved(
                normalized_address, raw_approvals
            )

            if not normalized_approvals:
                logger.info(f"[Scan {scan.id}] No approvals found")
                scan.status = ScanStatus.COMPLETED
                scan.completed_at = timezone.now()
                scan.save()

                # Cache the result
                ScanCache.set_recent_scan(normalized_address, scan.id, chain_id)

                return scan

            # Stage 4: Evaluate risk
            logger.info(
                f"[Scan {scan.id}] Evaluating risk for {len(normalized_approvals)} approvals"
            )
            evaluations = evaluate_approvals(normalized_approvals)

            # Stage 5: Aggregate
            logger.info(f"[Scan {scan.id}] Aggregating risk")
            summary = aggregate_risk(normalized_address, evaluations)

            # Stage 6: Persist
            logger.info(f"[Scan {scan.id}] Persisting results")
            self._persist_results(scan, summary)

            # Update wallet stats
            wallet.total_scans += 1
            wallet.save()

            # Cache the scan
            ScanCache.set_recent_scan(normalized_address, scan.id, chain_id)

            logger.info(
                f"[Scan {scan.id}] Completed: {summary.total_approvals} approvals, "
                f"risk={summary.risk_level.value}"
            )

            return scan

        except ValidationError as e:
            logger.error(f"Validation failed: {e}")
            if scan:
                scan.status = ScanStatus.FAILED
                scan.error_message = str(e)
                scan.save()
            raise

        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            if scan:
                scan.status = ScanStatus.FAILED
                scan.error_message = str(e)
                scan.completed_at = timezone.now()
                scan.save()
            return None

    @transaction.atomic
    def _persist_results(self, scan: WalletScan, summary: WalletRiskSummary) -> None:
        """
        Persist scan results to database.

        Args:
            scan: WalletScan instance
            summary: WalletRiskSummary with evaluations
        """
        # Update scan summary
        scan.total_approvals = summary.total_approvals
        scan.total_risk_score = summary.total_risk_score
        scan.risk_level = summary.risk_level.value
        scan.high_risk_count = summary.high_risk_count
        scan.critical_risk_count = summary.critical_risk_count
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = timezone.now()
        scan.save()

        # Create approval records
        approval_objs = []
        for evaluation in summary.evaluations:
            approval_obj = Approval(
                wallet_scan=scan,
                token_address=evaluation.approval.token_address,
                token_type=evaluation.approval.token_type.value,
                spender_address=evaluation.approval.spender_address,
                approved_amount=evaluation.approval.approved_amount,
                is_unlimited=evaluation.approval.is_unlimited,
                is_operator=evaluation.approval.is_operator,
                risk_points=evaluation.risk_points,
                risk_level=evaluation.risk_level.value,
                risk_reasons=evaluation.risk_reasons,
                block_number=evaluation.approval.block_number,
                transaction_hash=evaluation.approval.transaction_hash or "",
            )
            approval_objs.append(approval_obj)

        # Bulk create for performance
        Approval.objects.bulk_create(approval_objs)

        logger.info(f"Persisted {len(approval_objs)} approvals for scan {scan.id}")


# Convenience function
def scan_wallet(wallet_address: str, chain_id: int = 1) -> Optional[WalletScan]:
    """Execute a wallet scan."""
    orchestrator = ScanOrchestrator()
    return orchestrator.execute(wallet_address, chain_id)
