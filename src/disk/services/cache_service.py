from django.core.cache import cache
from typing import List
from .disk_service import YandexDiskFile


class CacheService:
    """Service for caching Yandex.Disk resources."""

    @staticmethod
    def get_cache_key(public_key: str, path: str = "") -> str:
        """Generate cache key for resources."""
        return f"yandex_disk_resources:{public_key}:{path}"

    @staticmethod
    def cache_resources(
        public_key: str, path: str, resources: List[YandexDiskFile]
    ) -> None:
        """Cache resources for 5 minutes."""
        cache_key = CacheService.get_cache_key(public_key, path)
        cache.set(cache_key, resources, timeout=300)  # 5 minutes cache

    @staticmethod
    def get_cached_resources(public_key: str, path: str = "") -> List[YandexDiskFile]:
        """Get cached resources if available."""
        cache_key = CacheService.get_cache_key(public_key, path)
        return cache.get(cache_key)
