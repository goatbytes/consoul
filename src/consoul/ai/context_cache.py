"""Context size cache for Ollama models.

Caches context sizes locally to avoid expensive /api/show calls.
Cache is refreshed in background threads for fast UI loading.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["OllamaContextCache"]


class OllamaContextCache:
    """Cache for Ollama model context sizes.

    Features:
    - Persistent cache file (~/.consoul/cache/ollama_context_sizes.json)
    - 7-day TTL for cached entries
    - Background refresh for stale entries
    - Thread-safe operations
    """

    DEFAULT_TTL_DAYS = 7
    CACHE_FILE = "ollama_context_sizes.json"

    def __init__(self, cache_dir: Path | None = None):
        """Initialize context cache.

        Args:
            cache_dir: Custom cache directory (default: ~/.consoul/cache)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".consoul" / "cache"

        self.cache_dir = cache_dir
        self.cache_file = cache_dir / self.CACHE_FILE
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                self._cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            # Invalid cache, start fresh
            self._cache = {}

    def _save_cache(self) -> None:
        """Save cache to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except OSError:
            # Failed to save, ignore
            pass

    def get(self, model_id: str) -> int | None:
        """Get cached context size for a model.

        Args:
            model_id: Ollama model ID (e.g., "llama3.2:latest")

        Returns:
            Context size in tokens, or None if not cached or stale
        """
        with self._lock:
            entry = self._cache.get(model_id)
            if not entry:
                return None

            # Check if stale (7 days old)
            try:
                cached_at = datetime.fromisoformat(entry.get("cached_at", ""))
                age_days = (
                    datetime.now(timezone.utc) - cached_at.replace(tzinfo=timezone.utc)
                ).days
            except (ValueError, TypeError):
                return None  # Invalid timestamp, treat as stale

            if age_days > self.DEFAULT_TTL_DAYS:
                return None  # Stale, needs refresh

            return entry.get("context_size")

    def set(self, model_id: str, context_size: int) -> None:
        """Cache context size for a model.

        Args:
            model_id: Ollama model ID (e.g., "llama3.2:latest")
            context_size: Context size in tokens
        """
        with self._lock:
            self._cache[model_id] = {
                "context_size": context_size,
                "cached_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_cache()

    def set_bulk(self, context_sizes: dict[str, int]) -> None:
        """Cache multiple context sizes at once.

        Args:
            context_sizes: Dict mapping model IDs to context sizes
        """
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            for model_id, size in context_sizes.items():
                self._cache[model_id] = {
                    "context_size": size,
                    "cached_at": now,
                }
            self._save_cache()

    def get_all(self) -> dict[str, int]:
        """Get all cached context sizes.

        Returns:
            Dict mapping model IDs to context sizes (only non-stale entries)
        """
        with self._lock:
            result = {}
            now = datetime.now(timezone.utc)

            for model_id, entry in self._cache.items():
                try:
                    cached_at = datetime.fromisoformat(entry.get("cached_at", ""))
                    age_days = (now - cached_at.replace(tzinfo=timezone.utc)).days

                    if age_days <= self.DEFAULT_TTL_DAYS:
                        context_size = entry.get("context_size")
                        if context_size is not None:
                            result[model_id] = context_size
                except (ValueError, TypeError):
                    continue

            return result

    def clear(self) -> None:
        """Clear all cached context sizes."""
        with self._lock:
            self._cache = {}
            self._save_cache()

    def refresh_in_background(
        self,
        model_ids: list[str],
        fetch_func: Callable[[str], int | None],
        on_complete: Callable[[dict[str, int]], None] | None = None,
    ) -> threading.Thread:
        """Refresh context sizes in background thread.

        Args:
            model_ids: List of model IDs to refresh
            fetch_func: Function to fetch context size for a model
            on_complete: Optional callback when refresh completes

        Returns:
            Background thread (already started)
        """

        def refresh_worker() -> None:
            """Worker function for background refresh."""
            new_sizes = {}

            for model_id in model_ids:
                try:
                    size = fetch_func(model_id)
                    if size is not None:
                        new_sizes[model_id] = size
                except Exception:
                    # Failed to fetch, skip
                    continue

                # Small delay to avoid hammering API
                time.sleep(0.05)  # 50ms between requests

            # Save all at once
            if new_sizes:
                self.set_bulk(new_sizes)

            # Notify completion
            if on_complete:
                on_complete(new_sizes)

        thread = threading.Thread(target=refresh_worker, daemon=True)
        thread.start()
        return thread


# Global cache instance
_global_cache: OllamaContextCache | None = None


def get_global_cache() -> OllamaContextCache:
    """Get or create global context cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = OllamaContextCache()
    return _global_cache
