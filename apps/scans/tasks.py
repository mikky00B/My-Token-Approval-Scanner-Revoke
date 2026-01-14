"""
Celery tasks for wallet scanning.
"""

import logging
from celery import shared_task
from apps.scans.orchestrator import ScanOrchestrator
from apps.scans.models import WalletScan, ScanStatus
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scan_wallet_async(self, wallet_address: str, chain_id: int = 1):
    """
    Asynchronously scan a wallet for approvals.

    Args:
        wallet_address: Wallet address to scan
        chain_id: Chain ID (default: 1 for Ethereum)

    Returns:
        Scan ID if successful, None if failed
    """
    try:
        logger.info(f"Starting async scan task for {wallet_address}")
        orchestrator = ScanOrchestrator()
        scan = orchestrator.execute(wallet_address, chain_id)

        if scan:
            logger.info(f"Async scan completed: {scan.id}")
            return scan.id
        else:
            logger.error(f"Async scan failed for {wallet_address}")
            return None

    except Exception as e:
        logger.error(f"Async scan error: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2**self.request.retries))
