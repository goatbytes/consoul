"""LiteLLM model registry integration for automatic token limit updates.

This module provides automatic fetching of model context window sizes from
LiteLLM's community-maintained registry. Results are cached locally to avoid
repeated network requests.

LiteLLM Registry:
    Source: https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json
    Updates: Community-maintained (1000+ contributors)
    Coverage: OpenAI, Anthropic, Google, Cohere, Meta, Mistral, and more

Cache Strategy:
    - Location: ~/.consoul/litellm_cache.json
    - TTL: 24 hours (configurable)
    - Lazy loading: Only fetches on first unknown model lookup
    - Graceful degradation: Network failures don't break functionality

Example:
    >>> context = get_litellm_context_window("gpt-4o-2025-01-15")
    >>> if context:
    ...     print(f"Context: {context:,} tokens")
    Context: 128,000 tokens
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# LiteLLM registry URL
LITELLM_REGISTRY_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

# Cache settings
CACHE_DIR = Path.home() / ".consoul"
CACHE_FILE = CACHE_DIR / "litellm_cache.json"
CACHE_TTL_HOURS = 24

# Retry settings for failed fetches
RETRY_AFTER_FAILURE_MINUTES = 5  # Retry after 5 minutes on network failure

# In-memory cache (persists for session)
_REGISTRY_CACHE: dict[str, Any] | None = None
_CACHE_LOADED = False
_LAST_FETCH_ATTEMPT: datetime | None = None  # Track when we last tried to fetch


def _get_cache_path() -> Path:
    """Get the cache file path, creating directory if needed.

    Returns:
        Path to cache file
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_FILE


def _load_cache() -> dict[str, Any] | None:
    """Load cached LiteLLM registry from disk.

    Returns:
        Cached registry data with metadata, or None if cache invalid/missing
    """
    try:
        cache_path = _get_cache_path()
        if not cache_path.exists():
            return None

        cache_data: dict[str, Any] = json.loads(cache_path.read_text())

        # Check TTL
        fetched_at = datetime.fromisoformat(cache_data.get("fetched_at", ""))
        now = datetime.now(timezone.utc)
        age = now - fetched_at

        if age > timedelta(hours=CACHE_TTL_HOURS):
            logger.debug(
                f"LiteLLM cache expired (age: {age.total_seconds() / 3600:.1f}h, "
                f"TTL: {CACHE_TTL_HOURS}h)"
            )
            return None

        logger.debug(
            f"Loaded LiteLLM cache from disk "
            f"({len(cache_data.get('models', {}))} models, "
            f"age: {age.total_seconds() / 3600:.1f}h)"
        )
        return cache_data

    except Exception as e:
        logger.debug(f"Failed to load LiteLLM cache: {e}")
        return None


def _save_cache(registry_data: dict[str, Any]) -> None:
    """Save LiteLLM registry data to disk cache.

    Args:
        registry_data: Registry data from LiteLLM
    """
    try:
        cache_path = _get_cache_path()
        cache_data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "models": registry_data,
        }
        cache_path.write_text(json.dumps(cache_data, indent=2))
        logger.debug(
            f"Saved LiteLLM cache to {cache_path} ({len(registry_data)} models)"
        )
    except Exception as e:
        logger.warning(f"Failed to save LiteLLM cache: {e}")


def _fetch_registry() -> dict[str, Any] | None:
    """Fetch LiteLLM registry from GitHub.

    Returns:
        Registry data, or None if fetch fails
    """
    try:
        import urllib.request

        logger.info(f"Fetching LiteLLM registry from {LITELLM_REGISTRY_URL}")

        with urllib.request.urlopen(LITELLM_REGISTRY_URL, timeout=10) as response:
            if response.status != 200:
                logger.warning(
                    f"Failed to fetch LiteLLM registry: HTTP {response.status}"
                )
                return None

            data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
            logger.info(f"Fetched LiteLLM registry ({len(data)} models)")
            return data

    except Exception as e:
        logger.warning(f"Failed to fetch LiteLLM registry: {e}")
        return None


def _get_registry() -> dict[str, Any]:
    """Get LiteLLM registry data (from cache or fetch).

    Uses lazy loading strategy with retry logic:
    1. Check in-memory cache (fastest)
    2. Load from disk cache if valid
    3. Fetch from GitHub if cache expired/missing
    4. On fetch failure, retry after RETRY_AFTER_FAILURE_MINUTES
    5. Return empty dict if all sources fail (graceful degradation)

    The key difference from naive caching: we DON'T cache empty results
    permanently. Instead, we track _LAST_FETCH_ATTEMPT and retry after
    the configured interval. This allows recovery from transient failures.

    Returns:
        Registry data dictionary (may be empty if fetch fails)
    """
    global _REGISTRY_CACHE, _CACHE_LOADED, _LAST_FETCH_ATTEMPT

    # Return in-memory cache if available and still valid
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE

    # Load from disk cache
    if not _CACHE_LOADED:
        cache_data = _load_cache()
        if cache_data:
            _REGISTRY_CACHE = cache_data.get("models", {})
            _CACHE_LOADED = True
            return _REGISTRY_CACHE

        _CACHE_LOADED = True

    # Check if we should retry fetching after a previous failure
    now = datetime.now(timezone.utc)
    should_retry = True

    if _LAST_FETCH_ATTEMPT is not None:
        time_since_attempt = now - _LAST_FETCH_ATTEMPT
        should_retry = time_since_attempt > timedelta(
            minutes=RETRY_AFTER_FAILURE_MINUTES
        )

        if not should_retry:
            # Too soon to retry, return empty dict without caching
            logger.debug(
                f"LiteLLM registry fetch attempted recently "
                f"({time_since_attempt.total_seconds() / 60:.1f}m ago), "
                f"will retry in {RETRY_AFTER_FAILURE_MINUTES - time_since_attempt.total_seconds() / 60:.1f}m"
            )
            return {}

    # Fetch from network (or retry after failure interval)
    _LAST_FETCH_ATTEMPT = now
    registry_data = _fetch_registry()

    if registry_data:
        _REGISTRY_CACHE = registry_data
        _save_cache(registry_data)
        # Reset failure tracking on success
        _LAST_FETCH_ATTEMPT = None
        return _REGISTRY_CACHE

    # Fetch failed - DO NOT cache the empty result
    # This allows retry on next call after RETRY_AFTER_FAILURE_MINUTES
    logger.debug(
        f"LiteLLM registry fetch failed, will retry in {RETRY_AFTER_FAILURE_MINUTES}m"
    )
    return {}


def get_litellm_context_window(model_id: str) -> int | None:
    """Get context window size for a model from LiteLLM registry.

    Args:
        model_id: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet")

    Returns:
        Context window in tokens, or None if not found

    Example:
        >>> context = get_litellm_context_window("gpt-4o-2025-01-15")
        >>> if context:
        ...     print(f"Found context: {context:,}")
        Found context: 128,000
    """
    registry = _get_registry()

    # Try exact match
    if model_id in registry:
        model_data = registry[model_id]
        # LiteLLM uses "max_input_tokens" for context window
        max_input: int | None = model_data.get("max_input_tokens")
        if max_input and max_input > 0:
            logger.debug(
                f"Found context window for {model_id} in LiteLLM registry: "
                f"{max_input:,} tokens"
            )
            return max_input

    # Try with normalized separators (- → /, : → /)
    # LiteLLM sometimes uses provider prefixes like "openai/gpt-4o"
    for separator in ["/", ":"]:
        for provider in ["openai", "anthropic", "google", "cohere", "meta"]:
            prefixed_id = f"{provider}{separator}{model_id}"
            if prefixed_id in registry:
                model_data = registry[prefixed_id]
                max_input = model_data.get("max_input_tokens")
                if max_input and max_input > 0:
                    logger.debug(
                        f"Found context window for {model_id} (as {prefixed_id}) "
                        f"in LiteLLM registry: {max_input:,} tokens"
                    )
                    return max_input

    return None


def refresh_cache() -> bool:
    """Force-refresh the LiteLLM cache from network.

    Clears all caches and retry timers, then attempts a fresh fetch.
    This bypasses the retry delay for manual refreshes.

    Returns:
        True if refresh succeeded, False otherwise

    Example:
        >>> success = refresh_cache()
        >>> print(f"Refresh {'succeeded' if success else 'failed'}")
    """
    global _REGISTRY_CACHE, _CACHE_LOADED, _LAST_FETCH_ATTEMPT

    # Clear in-memory cache and failure tracking
    _REGISTRY_CACHE = None
    _CACHE_LOADED = False
    _LAST_FETCH_ATTEMPT = None

    # Fetch fresh data
    registry_data = _fetch_registry()
    if registry_data:
        _REGISTRY_CACHE = registry_data
        _save_cache(registry_data)
        logger.info(
            f"Successfully refreshed LiteLLM cache ({len(registry_data)} models)"
        )
        return True

    logger.warning("Failed to refresh LiteLLM cache")
    # Don't set _LAST_FETCH_ATTEMPT here - let it remain None
    # so next automatic attempt will try immediately
    return False


def get_cache_info() -> dict[str, Any]:
    """Get information about the current cache state.

    Returns:
        Dictionary with cache metadata

    Example:
        >>> info = get_cache_info()
        >>> print(f"Cache loaded: {info['loaded']}, Age: {info.get('age_hours', 'N/A')}h")
    """
    info: dict[str, Any] = {
        "loaded": _CACHE_LOADED,
        "cache_file": str(CACHE_FILE),
        "ttl_hours": CACHE_TTL_HOURS,
    }

    if _REGISTRY_CACHE is not None:
        info["model_count"] = len(_REGISTRY_CACHE)

    try:
        if CACHE_FILE.exists():
            cache_data = json.loads(CACHE_FILE.read_text())
            fetched_at = datetime.fromisoformat(cache_data.get("fetched_at", ""))
            age = datetime.now(timezone.utc) - fetched_at
            info["age_hours"] = age.total_seconds() / 3600
            info["fetched_at"] = cache_data.get("fetched_at")
            info["expired"] = age > timedelta(hours=CACHE_TTL_HOURS)
    except Exception:
        pass

    return info
