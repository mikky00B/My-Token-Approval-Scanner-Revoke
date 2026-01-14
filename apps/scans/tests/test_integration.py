"""
Integration tests for the complete scan pipeline.
"""

import pytest
from django.test import TestCase
from apps.scans.orchestrator import scan_wallet
from apps.scans.models import WalletScan, ScanStatus
from apps.approvals.models import Approval
from apps.wallets.models import Wallet
from apps.blacklists.models import BlacklistEntry, BlacklistCategory


@pytest.mark.django_db
class TestScanPipeline(TestCase):
    """Test complete scan pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a test blacklist entry
        BlacklistEntry.objects.create(
            address="0x0000000000000000000000000000000000000001",
            category=BlacklistCategory.DRAINER,
            severity=50,
            name="Test Drainer",
            source="Test",
            is_active=True,
        )

    def test_scan_wallet_creates_records(self):
        """Test that scanning creates all necessary database records."""
        wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

        # Execute scan
        scan = scan_wallet(wallet_address)

        # Verify scan was created
        assert scan is not None
        assert scan.status == ScanStatus.COMPLETED

        # Verify wallet was created
        wallet = Wallet.objects.get(address=wallet_address.lower())
        assert wallet.total_scans == 1

        # Verify scan is linked to wallet
        assert scan.wallet == wallet

    def test_scan_with_no_approvals(self):
        """Test scanning a wallet with no approvals."""
        # Use a fresh address that likely has no approvals
        wallet_address = "0x0000000000000000000000000000000000000123"

        scan = scan_wallet(wallet_address)

        assert scan is not None
        assert scan.status == ScanStatus.COMPLETED
        assert scan.total_approvals == 0
        assert scan.total_risk_score == 0

    def test_scan_caching(self):
        """Test that scan results are cached."""
        wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

        # First scan
        scan1 = scan_wallet(wallet_address)
        scan1_id = scan1.id

        # Second scan (should use cache)
        scan2 = scan_wallet(wallet_address)
        scan2_id = scan2.id

        # Should return same scan from cache
        assert scan1_id == scan2_id

    def test_force_refresh_bypasses_cache(self):
        """Test that force_refresh bypasses cache."""
        from apps.scans.orchestrator import ScanOrchestrator

        wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        orchestrator = ScanOrchestrator()

        # First scan
        scan1 = orchestrator.execute(wallet_address)

        # Second scan with force_refresh
        scan2 = orchestrator.execute(wallet_address, force_refresh=True)

        # Should create new scan
        assert scan1.id != scan2.id

    def test_invalid_address_fails(self):
        """Test that invalid addresses are rejected."""
        from apps.wallets.services.validator import ValidationError

        with pytest.raises(ValidationError):
            scan_wallet("invalid_address")

    def test_risk_evaluation(self):
        """Test that risk is evaluated correctly."""
        # This would require mocking Etherscan responses
        # For now, just test the structure
        wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

        scan = scan_wallet(wallet_address)

        assert scan is not None
        assert hasattr(scan, "risk_level")
        assert hasattr(scan, "total_risk_score")
        assert scan.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@pytest.mark.django_db
class TestAPIEndpoints(TestCase):
    """Test API endpoints."""

    def test_health_check(self):
        """Test health check endpoint."""
        from django.test import Client

        client = Client()
        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_scan_wallet_endpoint(self):
        """Test scan wallet endpoint."""
        from django.test import Client

        client = Client()
        response = client.post(
            "/api/v1/scan-wallet/",
            data={"wallet_address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert "scan_id" in data
        assert "status" in data

    def test_scan_status_endpoint(self):
        """Test scan status endpoint."""
        from django.test import Client

        # First create a scan
        wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        scan = scan_wallet(wallet_address)

        # Then check status
        client = Client()
        response = client.get(f"/api/v1/scan-status/{scan.id}/")

        assert response.status_code == 200
        data = response.json()
        assert data["scan_id"] == scan.id
        assert "status" in data


@pytest.mark.django_db
class TestRiskEngine(TestCase):
    """Test risk evaluation rules."""

    def test_unlimited_approval_detection(self):
        """Test that unlimited approvals are flagged."""
        from shared.schemas import NormalizedApproval
        from apps.approvals.enums import TokenType
        from apps.risk_engine.evaluator import RiskEvaluator
        from apps.chains.constants import MAX_UINT256

        approval = NormalizedApproval(
            wallet_address="0xtest",
            token_address="0xtoken",
            token_type=TokenType.ERC20,
            spender_address="0xspender",
            approved_amount=MAX_UINT256,
            is_unlimited=True,
            is_operator=False,
        )

        evaluator = RiskEvaluator()
        evaluation = evaluator.evaluate_approval(approval)

        assert evaluation.risk_points > 0
        assert any("unlimited" in reason.lower() for reason in evaluation.risk_reasons)

    def test_nft_operator_detection(self):
        """Test that NFT operator approvals are flagged."""
        from shared.schemas import NormalizedApproval
        from apps.approvals.enums import TokenType
        from apps.risk_engine.evaluator import RiskEvaluator

        approval = NormalizedApproval(
            wallet_address="0xtest",
            token_address="0xtoken",
            token_type=TokenType.ERC721,
            spender_address="0xspender",
            approved_amount=None,
            is_unlimited=False,
            is_operator=True,
        )

        evaluator = RiskEvaluator()
        evaluation = evaluator.evaluate_approval(approval)

        assert evaluation.risk_points > 0
        assert any(
            "nft" in reason.lower() or "operator" in reason.lower()
            for reason in evaluation.risk_reasons
        )
