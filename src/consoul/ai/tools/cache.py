"""Code search caching infrastructure for AST parsing results.

Provides disk-based caching for expensive AST parsing operations using diskcache.
Implements mtime-based invalidation and LRU eviction similar to Aider's approach.

Example:
    >>> from pathlib import Path
    >>> cache = CodeSearchCache()
    >>> tags = cache.get_cached_tags(Path("src/main.py"))
    >>> if tags is None:
    ...     tags = parse_file_tags(Path("src/main.py"))
    ...     cache.cache_tags(Path("src/main.py"), tags)
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from diskcache import Cache

__all__ = ["CACHE_VERSION", "CacheStats", "CodeSearchCache"]

# Cache version for managing schema changes
# Increment when cache format changes to invalidate old caches
CACHE_VERSION = 1

# SQLite errors to handle gracefully
SQLITE_ERRORS = (sqlite3.OperationalError, sqlite3.DatabaseError, OSError)


@dataclass
class CacheStats:
    """Statistics about cache performance.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        size_bytes: Current cache size in bytes
        entry_count: Number of cached entries
        hit_rate: Cache hit rate (hits / (hits + misses))
    """

    hits: int
    misses: int
    size_bytes: int
    entry_count: int

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Hit rate as percentage (0.0 to 1.0), or 0.0 if no requests.
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


class CodeSearchCache:
    """Disk-based cache for code search AST parsing results.

    Uses diskcache (SQLite-backed) for persistent, process-safe caching.
    Implements mtime-based invalidation and configurable size limits with LRU eviction.

    The cache stores parsed AST tags keyed by file path with mtime for invalidation.
    When a file's modification time changes, the cache entry is automatically invalidated.

    Example:
        >>> cache = CodeSearchCache()
        >>> tags = cache.get_cached_tags(Path("src/utils.py"))
        >>> if tags is None:
        ...     # Cache miss - parse and cache
        ...     tags = expensive_parse_operation(Path("src/utils.py"))
        ...     cache.cache_tags(Path("src/utils.py"), tags)
        >>> # Next call will be ~10x faster from cache
        >>> cached_tags = cache.get_cached_tags(Path("src/utils.py"))

    Thread Safety:
        Thread-safe via SQLite locking. Safe for concurrent access.

    Attributes:
        cache_dir: Directory where cache is stored
        size_limit_mb: Maximum cache size in megabytes
        _cache: Underlying diskcache.Cache instance (or dict fallback)
        _hits: Number of cache hits
        _misses: Number of cache misses
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        size_limit_mb: int = 100,
    ) -> None:
        """Initialize code search cache.

        Args:
            cache_dir: Cache directory path. Defaults to ~/.consoul/cache/code-search.v{VERSION}/
            size_limit_mb: Maximum cache size in megabytes (default: 100MB)

        Note:
            If cache initialization fails (SQLite errors), falls back to in-memory dict.
        """
        if cache_dir is None:
            cache_dir = (
                Path.home() / ".consoul" / "cache" / f"code-search.v{CACHE_VERSION}"
            )

        self.cache_dir = Path(cache_dir)
        self.size_limit_mb = size_limit_mb
        self._hits = 0
        self._misses = 0

        self._cache: Cache | dict[str, Any] = self._initialize_cache()

    def _initialize_cache(self) -> Cache | dict[str, Any]:
        """Initialize diskcache.Cache with error handling.

        Returns:
            Cache instance, or dict fallback on SQLite errors.
        """
        try:
            # Create cache directory
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Initialize diskcache with size limit
            cache = Cache(
                directory=str(self.cache_dir),
                size_limit=self.size_limit_mb * 1024 * 1024,  # Convert MB to bytes
                eviction_policy="least-recently-used",
            )

            # Test that cache works
            test_key = "__test__"
            cache[test_key] = "test"
            _ = cache[test_key]
            del cache[test_key]

            return cache

        except SQLITE_ERRORS:
            # Fall back to in-memory dict
            return {}

    def _handle_sqlite_error(self, original_error: Exception | None = None) -> None:
        """Handle SQLite errors by recreating cache or falling back to dict.

        Args:
            original_error: The original exception that triggered the error handler
        """
        # Already using dict fallback
        if isinstance(self._cache, dict):
            return

        # Try to recreate cache
        try:
            # Delete existing cache
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)

            # Reinitialize
            self._cache = self._initialize_cache()

        except SQLITE_ERRORS:
            # Fall back to dict
            self._cache = {}

    def _get_cache_key(self, file_path: Path) -> str:
        """Generate cache key for file path.

        Args:
            file_path: Path to source file

        Returns:
            Cache key string (absolute path)
        """
        return str(file_path.resolve())

    def _get_mtime(self, file_path: Path) -> float | None:
        """Get file modification time.

        Args:
            file_path: Path to file

        Returns:
            Modification time as float timestamp, or None if file doesn't exist
        """
        try:
            return file_path.stat().st_mtime
        except (FileNotFoundError, OSError):
            return None

    def get_cached_tags(self, file_path: Path) -> list[Any] | None:
        """Retrieve cached tags for a file if valid.

        Args:
            file_path: Path to source file

        Returns:
            Cached tags list if cache hit and mtime matches, None otherwise

        Note:
            Automatically invalidates cache if file mtime has changed.
        """
        # Get current mtime
        current_mtime = self._get_mtime(file_path)
        if current_mtime is None:
            self._misses += 1
            return None

        cache_key = self._get_cache_key(file_path)

        try:
            # Try to get from cache
            cached_value = self._cache.get(cache_key)

            if cached_value is None:
                # Cache miss
                self._misses += 1
                return None

            # Check mtime
            cached_mtime = cached_value.get("mtime")
            if cached_mtime != current_mtime:
                # File modified - invalidate cache entry
                self._misses += 1
                return None

            # Cache hit!
            self._hits += 1
            data: list[Any] = cached_value["data"]
            return data

        except SQLITE_ERRORS as e:
            self._handle_sqlite_error(e)
            # Retry with fallback
            cached_value = self._cache.get(cache_key)
            if cached_value and cached_value.get("mtime") == current_mtime:
                self._hits += 1
                retry_data: list[Any] = cached_value["data"]
                return retry_data
            self._misses += 1
            return None

    def cache_tags(self, file_path: Path, tags: list[Any]) -> None:
        """Store parsed tags in cache with mtime.

        Args:
            file_path: Path to source file
            tags: Parsed AST tags/symbols to cache
        """
        mtime = self._get_mtime(file_path)
        if mtime is None:
            return

        cache_key = self._get_cache_key(file_path)
        cache_value = {"mtime": mtime, "data": tags}

        try:
            self._cache[cache_key] = cache_value
        except SQLITE_ERRORS as e:
            self._handle_sqlite_error(e)
            # Retry with fallback
            self._cache[cache_key] = cache_value

    def invalidate_cache(self) -> None:
        """Clear all cache entries.

        Warning:
            This deletes all cached data. Cache will need to rebuild.
        """
        try:
            if isinstance(self._cache, Cache):
                self._cache.clear()
            else:
                self._cache.clear()
        except SQLITE_ERRORS as e:
            self._handle_sqlite_error(e)
            self._cache.clear()

    def get_stats(self) -> CacheStats:
        """Get cache performance statistics.

        Returns:
            CacheStats with hit/miss counts and cache size information
        """
        try:
            if isinstance(self._cache, Cache):
                # Get cache size from diskcache
                size_bytes = self._cache.volume()
                entry_count = len(self._cache)
            else:
                # Estimate for dict fallback
                size_bytes = 0
                entry_count = len(self._cache)

            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                size_bytes=size_bytes,
                entry_count=entry_count,
            )
        except SQLITE_ERRORS as e:
            self._handle_sqlite_error(e)
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                size_bytes=0,
                entry_count=len(self._cache),
            )

    def close(self) -> None:
        """Close cache and release resources.

        Note:
            Cache can still be used after close, but will be reopened.
        """
        try:
            if isinstance(self._cache, dict):
                # Dict fallback has no close method
                return
            # If we have a Cache instance, close it
            if hasattr(self._cache, "close"):
                self._cache.close()
        except SQLITE_ERRORS:
            pass
