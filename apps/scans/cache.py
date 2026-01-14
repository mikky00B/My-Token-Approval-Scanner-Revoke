"""
Cache service with fallback for missing Redis.
apps/scans/cache.py
"""

import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class ScanCache:
    """
    Manages caching of scan results.
    Gracefully falls back if Redis is unavailable.
    """

    CACHE_PREFIX = "wallet_scan"
    DEFAULT_TIMEOUT = 3600  # 1 hour

    @classmethod
    def _get_cache_key(cls, wallet_address: str, chain_id: int) -> str:
        """Generate cache key for a wallet scan."""
        return f"{cls.CACHE_PREFIX}:{chain_id}:{wallet_address.lower()}"

    @classmethod
    def get_recent_scan(cls, wallet_address: str, chain_id: int = 1):
        """
        Get cached scan ID if available.

        Returns:
            int: Scan ID if cached
            None: If not cached or cache unavailable
        """
        try:
            key = cls._get_cache_key(wallet_address, chain_id)
            scan_id = cache.get(key)

            if scan_id:
                logger.info(f"Cache hit for {wallet_address[:8]}...")
                return scan_id

            logger.debug(f"Cache miss for {wallet_address[:8]}...")
            return None

        except Exception as e:
            # Don't crash if cache is unavailable
            logger.warning(f"Cache unavailable: {e}")
            return None

    @classmethod
    def set_recent_scan(
        cls, wallet_address: str, scan_id: int, chain_id: int = 1, timeout: int = None
    ):
        """
        Cache a scan ID.

        Args:
            wallet_address: Wallet address
            scan_id: ID of completed scan
            chain_id: Blockchain network ID
            timeout: Cache timeout in seconds
        """
        try:
            key = cls._get_cache_key(wallet_address, chain_id)
            timeout = timeout or cls.DEFAULT_TIMEOUT

            cache.set(key, scan_id, timeout)
            logger.info(f"Cached scan {scan_id} for {wallet_address[:8]}...")

        except Exception as e:
            # Don't crash if cache is unavailable
            logger.warning(f"Failed to cache scan: {e}")

    @classmethod
    def invalidate_scan(cls, wallet_address: str, chain_id: int = 1):
        """
        Invalidate cached scan for a wallet.

        Args:
            wallet_address: Wallet address
            chain_id: Blockchain network ID
        """
        try:
            key = cls._get_cache_key(wallet_address, chain_id)
            cache.delete(key)
            logger.info(f"Invalidated cache for {wallet_address[:8]}...")

        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")

    @classmethod
    def clear_all(cls):
        """Clear all scan caches. Use with caution."""
        try:
            cache.clear()
            logger.info("Cleared all scan caches")
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")
