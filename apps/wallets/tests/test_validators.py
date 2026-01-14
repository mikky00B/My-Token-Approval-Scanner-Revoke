"""
Tests for wallet validator service.
"""

import pytest
from apps.wallets.services.validator import WalletValidator, ValidationError


class TestWalletValidator:
    """Test wallet address validation."""

    def test_valid_address(self):
        """Test valid Ethereum address."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        result = WalletValidator.validate_address(address)
        assert result == address.lower()

    def test_valid_address_with_whitespace(self):
        """Test address with surrounding whitespace."""
        address = "  0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0  "
        result = WalletValidator.validate_address(address)
        assert result == address.strip().lower()

    def test_invalid_address_too_short(self):
        """Test address that's too short."""
        with pytest.raises(ValidationError, match="Invalid Ethereum address"):
            WalletValidator.validate_address("0x123")

    def test_invalid_address_no_0x(self):
        """Test address without 0x prefix."""
        with pytest.raises(ValidationError, match="Invalid Ethereum address"):
            WalletValidator.validate_address("742d35Cc6634C0532925a3b844Bc9e7595f0bEb")

    def test_invalid_address_non_hex(self):
        """Test address with non-hexadecimal characters."""
        with pytest.raises(ValidationError, match="Invalid Ethereum address"):
            WalletValidator.validate_address(
                "0x742d35Cc6634C0532925a3b844Bc9e7595f0bZZ"
            )

    def test_empty_address(self):
        """Test empty address."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            WalletValidator.validate_address("")

    def test_valid_chain(self):
        """Test valid chain ID."""
        WalletValidator.validate_chain(1)  # Should not raise

    def test_invalid_chain(self):
        """Test invalid chain ID."""
        with pytest.raises(ValidationError, match="Unsupported chain"):
            WalletValidator.validate_chain(999)

    def test_validate_scan_input_success(self):
        """Test complete scan input validation."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        normalized, chain = WalletValidator.validate_scan_input(address, 1)
        assert normalized == address.lower()
        assert chain == 1

    def test_validate_scan_input_invalid_address(self):
        """Test scan input with invalid address."""
        with pytest.raises(ValidationError):
            WalletValidator.validate_scan_input("invalid", 1)

    def test_validate_scan_input_invalid_chain(self):
        """Test scan input with invalid chain."""
        with pytest.raises(ValidationError):
            WalletValidator.validate_scan_input(
                "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0", 999
            )
