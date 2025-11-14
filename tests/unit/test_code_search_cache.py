"""Test code search cache implementation."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from consoul.ai.tools.cache import CACHE_VERSION, CacheStats, CodeSearchCache


class TestCodeSearchCacheInitialization:
    """Test cache initialization and configuration."""

    def test_default_initialization(self) -> None:
        """Test cache initializes with default settings."""
        cache = CodeSearchCache()

        assert cache.cache_dir == (
            Path.home() / ".consoul" / "cache" / f"code-search.v{CACHE_VERSION}"
        )
        assert cache.size_limit_mb == 100
        assert cache._hits == 0
        assert cache._misses == 0

    def test_custom_directory(self) -> None:
        """Test cache initializes with custom directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir) / "custom-cache"
            cache = CodeSearchCache(cache_dir=custom_dir)

            assert cache.cache_dir == custom_dir
            assert custom_dir.exists()

    def test_custom_size_limit(self) -> None:
        """Test cache initializes with custom size limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir), size_limit_mb=50)

            assert cache.size_limit_mb == 50

    def test_cache_directory_created(self) -> None:
        """Test cache directory is automatically created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "new" / "nested" / "cache"
            cache = CodeSearchCache(cache_dir=cache_dir)

            assert cache_dir.exists()
            cache.close()


class TestCacheHitMiss:
    """Test cache hit and miss logic."""

    def test_cache_miss_on_new_file(self) -> None:
        """Test cache miss for file not in cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            # Create a test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def foo(): pass")

            # First access should be cache miss
            result = cache.get_cached_tags(test_file)

            assert result is None
            stats = cache.get_stats()
            assert stats.misses == 1
            assert stats.hits == 0
            cache.close()

    def test_cache_hit_on_cached_file(self) -> None:
        """Test cache hit for file in cache with matching mtime."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            # Create and cache a file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def foo(): pass")

            tags = [{"name": "foo", "type": "function", "line": 1}]
            cache.cache_tags(test_file, tags)

            # Second access should be cache hit
            result = cache.get_cached_tags(test_file)

            assert result == tags
            stats = cache.get_stats()
            assert stats.hits == 1
            assert stats.misses == 0
            cache.close()

    def test_cache_miss_on_nonexistent_file(self) -> None:
        """Test cache miss for file that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            nonexistent = Path(tmpdir) / "nonexistent.py"
            result = cache.get_cached_tags(nonexistent)

            assert result is None
            stats = cache.get_stats()
            assert stats.misses == 1
            cache.close()


class TestMtimeInvalidation:
    """Test mtime-based cache invalidation."""

    def test_cache_invalidated_on_file_modification(self) -> None:
        """Test cache invalidated when file mtime changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            # Create and cache a file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def foo(): pass")

            tags_v1 = [{"name": "foo", "type": "function", "line": 1}]
            cache.cache_tags(test_file, tags_v1)

            # Verify cache hit
            assert cache.get_cached_tags(test_file) == tags_v1

            # Modify file (change mtime)
            time.sleep(0.01)  # Ensure mtime difference
            test_file.write_text("def bar(): pass")

            # Should be cache miss now
            result = cache.get_cached_tags(test_file)

            assert result is None
            stats = cache.get_stats()
            assert stats.misses == 1  # One miss after modification
            assert stats.hits == 1  # One hit before modification
            cache.close()

    def test_cache_valid_with_unchanged_file(self) -> None:
        """Test cache remains valid when file unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            # Create and cache a file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def foo(): pass")

            tags = [{"name": "foo", "type": "function", "line": 1}]
            cache.cache_tags(test_file, tags)

            # Multiple accesses without modification
            for _ in range(5):
                result = cache.get_cached_tags(test_file)
                assert result == tags

            stats = cache.get_stats()
            assert stats.hits == 5
            assert stats.misses == 0
            cache.close()


class TestCacheOperations:
    """Test cache operations and management."""

    def test_cache_tags_stores_data(self) -> None:
        """Test cache_tags stores data correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def foo(): pass")

            tags = [
                {"name": "foo", "type": "function", "line": 1},
                {"name": "MyClass", "type": "class", "line": 3},
            ]

            cache.cache_tags(test_file, tags)
            result = cache.get_cached_tags(test_file)

            assert result == tags
            cache.close()

    def test_invalidate_cache_clears_all_entries(self) -> None:
        """Test invalidate_cache removes all cached entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            # Cache multiple files
            for i in range(3):
                test_file = Path(tmpdir) / f"test{i}.py"
                test_file.write_text(f"def foo{i}(): pass")
                cache.cache_tags(test_file, [{"name": f"foo{i}"}])

            # Verify all cached
            stats_before = cache.get_stats()
            assert stats_before.entry_count == 3

            # Invalidate cache
            cache.invalidate_cache()

            # Verify all cleared
            stats_after = cache.get_stats()
            assert stats_after.entry_count == 0
            cache.close()

    def test_close_releases_resources(self) -> None:
        """Test close releases cache resources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def foo(): pass")
            cache.cache_tags(test_file, [{"name": "foo"}])

            # Close should not raise
            cache.close()


class TestCacheStats:
    """Test cache statistics and metrics."""

    def test_stats_track_hits_and_misses(self) -> None:
        """Test stats correctly track cache hits and misses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def foo(): pass")

            # Cache miss
            cache.get_cached_tags(test_file)

            # Cache entry
            cache.cache_tags(test_file, [{"name": "foo"}])

            # Cache hits
            cache.get_cached_tags(test_file)
            cache.get_cached_tags(test_file)

            stats = cache.get_stats()

            assert stats.hits == 2
            assert stats.misses == 1
            assert stats.entry_count == 1
            cache.close()

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate is calculated correctly."""
        stats_empty = CacheStats(hits=0, misses=0, size_bytes=0, entry_count=0)
        assert stats_empty.hit_rate == 0.0

        stats_perfect = CacheStats(hits=10, misses=0, size_bytes=1000, entry_count=5)
        assert stats_perfect.hit_rate == 1.0

        stats_half = CacheStats(hits=5, misses=5, size_bytes=1000, entry_count=5)
        assert stats_half.hit_rate == 0.5

        stats_low = CacheStats(hits=1, misses=9, size_bytes=1000, entry_count=5)
        assert stats_low.hit_rate == 0.1

    def test_stats_report_entry_count(self) -> None:
        """Test stats report correct entry count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            # Add multiple entries
            for i in range(5):
                test_file = Path(tmpdir) / f"test{i}.py"
                test_file.write_text(f"def foo{i}(): pass")
                cache.cache_tags(test_file, [{"name": f"foo{i}"}])

            stats = cache.get_stats()
            assert stats.entry_count == 5
            cache.close()


class TestSQLiteErrorHandling:
    """Test handling of SQLite errors."""

    def test_fallback_to_dict_on_sqlite_error(self) -> None:
        """Test cache falls back to dict on SQLite errors."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("consoul.ai.tools.cache.Cache") as mock_cache_class,
        ):
            # Create cache with invalid path to trigger error
            mock_cache_class.side_effect = OSError("SQLite error")

            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            # Should fallback to dict
            assert isinstance(cache._cache, dict)

    def test_cache_operations_work_with_dict_fallback(self) -> None:
        """Test cache operations work with dict fallback."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("consoul.ai.tools.cache.Cache") as mock_cache_class,
        ):
            mock_cache_class.side_effect = OSError("SQLite error")

            cache = CodeSearchCache(cache_dir=Path(tmpdir))

            # Create test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def foo(): pass")

            # Cache and retrieve should work with dict
            tags = [{"name": "foo"}]
            cache.cache_tags(test_file, tags)
            result = cache.get_cached_tags(test_file)

            assert result == tags
            cache.close()


class TestCacheVersioning:
    """Test cache versioning behavior."""

    def test_cache_version_in_directory_name(self) -> None:
        """Test cache version is part of directory name."""
        cache = CodeSearchCache()

        assert f"v{CACHE_VERSION}" in str(cache.cache_dir)

    def test_different_versions_use_different_directories(self) -> None:
        """Test that different cache versions use separate directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Simulate version 1
            cache_v1_dir = Path(tmpdir) / "code-search.v1"
            cache_v1 = CodeSearchCache(cache_dir=cache_v1_dir)

            # Simulate version 2
            cache_v2_dir = Path(tmpdir) / "code-search.v2"
            cache_v2 = CodeSearchCache(cache_dir=cache_v2_dir)

            assert cache_v1.cache_dir != cache_v2.cache_dir
            assert cache_v1_dir.exists()
            assert cache_v2_dir.exists()

            cache_v1.close()
            cache_v2.close()


class TestConcurrentAccess:
    """Test thread safety and concurrent access."""

    def test_multiple_cache_instances_same_directory(self) -> None:
        """Test multiple cache instances can share same directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "shared"

            cache1 = CodeSearchCache(cache_dir=cache_dir)
            cache2 = CodeSearchCache(cache_dir=cache_dir)

            # Create test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def foo(): pass")

            # Cache with instance 1
            tags = [{"name": "foo"}]
            cache1.cache_tags(test_file, tags)

            # Retrieve with instance 2
            result = cache2.get_cached_tags(test_file)

            assert result == tags

            cache1.close()
            cache2.close()
