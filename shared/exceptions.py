"""
Custom exceptions for wallet scanner.
"""


class WalletScannerException(Exception):
    """Base exception for all wallet scanner errors."""

    pass


class ValidationError(WalletScannerException):
    """Raised when validation fails."""

    pass


class ScanError(WalletScannerException):
    """Raised when scan execution fails."""

    pass


class APIError(WalletScannerException):
    """Raised when external API calls fail."""

    pass


class ContractError(WalletScannerException):
    """Raised when smart contract interaction fails."""

    pass


class CacheError(WalletScannerException):
    """Raised when cache operations fail."""

    pass
