"""
Wallet address validation service.
Stage 1 of the scan pipeline.
"""

import re
from typing import Tuple
from apps.chains.constants import ChainId, CHAIN_NAMES


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


class WalletValidator:
    """
    Validates and normalizes wallet addresses.
    """

    # Ethereum address pattern (0x followed by 40 hex chars)
    ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")

    @classmethod
    def validate_address(cls, address: str) -> str:
        """
        Validate Ethereum address format.

        Args:
            address: Raw address string

        Returns:
            Normalized lowercase address

        Raises:
            ValidationError: If address is invalid
        """
        if not address:
            raise ValidationError("Address cannot be empty")

        address = address.strip()

        if not cls.ADDRESS_PATTERN.match(address):
            raise ValidationError(
                f"Invalid Ethereum address format: {address}. "
                "Expected 0x followed by 40 hexadecimal characters."
            )

        # Return lowercase for consistent storage
        return address.lower()

    @classmethod
    def validate_chain(cls, chain_id: int) -> None:
        """
        Validate that chain is supported.

        Args:
            chain_id: Blockchain network ID

        Raises:
            ValidationError: If chain is not supported
        """
        try:
            ChainId(chain_id)
        except ValueError:
            supported = ", ".join(f"{c.value} ({CHAIN_NAMES[c]})" for c in ChainId)
            raise ValidationError(
                f"Unsupported chain ID: {chain_id}. " f"Supported chains: {supported}"
            )

    @classmethod
    def validate_scan_input(cls, address: str, chain_id: int) -> Tuple[str, int]:
        """
        Validate complete scan input.

        Args:
            address: Wallet address
            chain_id: Chain ID

        Returns:
            Tuple of (normalized_address, chain_id)

        Raises:
            ValidationError: If validation fails
        """
        normalized_address = cls.validate_address(address)
        cls.validate_chain(chain_id)
        return normalized_address, chain_id


# Convenience function for direct import
def validate_scan_input(address: str, chain_id: int = 1) -> Tuple[str, int]:
    """Validate wallet scan input."""
    return WalletValidator.validate_scan_input(address, chain_id)
