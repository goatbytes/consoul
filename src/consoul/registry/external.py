"""External data source integration for model pricing.

This module provides integration with external APIs (like Helicone) to fetch
up-to-date model pricing information. Works alongside static model definitions
to provide a hybrid approach.

Features:
- Fetch pricing from Helicone API (1,114+ models)
- Cache responses locally with TTL
- Fallback to static definitions
- Automatic refresh on stale data
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

__all__ = [
    "HeliconeClient",
    "get_helicone_pricing",
    "sync_pricing_from_helicone",
]

# Helicone API endpoint
HELICONE_API_URL = "https://www.helicone.ai/api/llm-costs"

# Cache settings
CACHE_DIR = Path.home() / ".cache" / "consoul" / "pricing"
CACHE_FILE = CACHE_DIR / "helicone_pricing.json"
CACHE_TTL = timedelta(days=7)  # Refresh weekly


class HeliconeClient:
    """Client for fetching pricing data from Helicone API.

    Helicone maintains a comprehensive database of 1,114+ AI models across
    all major providers (OpenAI, Anthropic, Google, etc.) with up-to-date pricing.

    Features:
    - Automatic caching with configurable TTL
    - Provider filtering
    - Model name pattern matching (equals, startsWith, includes)
    - Fallback handling for network errors

    Example:
        >>> client = HeliconeClient()
        >>> pricing = client.get_pricing("claude-sonnet-4-5-20250929")
        >>> if pricing:
        ...     print(f"Input: ${pricing['input_cost_per_1m']}/MTok")
    """

    def __init__(
        self, cache_dir: Path | None = None, cache_ttl: timedelta | None = None
    ) -> None:
        """Initialize Helicone client.

        Args:
            cache_dir: Directory for caching responses (default: ~/.cache/consoul/pricing)
            cache_ttl: Cache time-to-live (default: 7 days)
        """
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_file = self.cache_dir / "helicone_pricing.json"
        self.cache_ttl = cache_ttl or CACHE_TTL
        self._data: dict[str, Any] | None = None

    def fetch(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch pricing data from Helicone API with caching.

        Args:
            force_refresh: Bypass cache and fetch fresh data

        Returns:
            Dictionary with 'metadata' and 'data' keys

        Raises:
            httpx.HTTPError: If API request fails
        """
        # Check cache first
        if not force_refresh and self._is_cache_valid():
            logger.debug("Loading Helicone pricing from cache")
            return self._load_cache()

        # Fetch from API
        logger.info("Fetching fresh pricing data from Helicone API")
        try:
            response = httpx.get(HELICONE_API_URL, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            # Cache response
            self._save_cache(data)

            logger.info(
                f"Fetched {data.get('metadata', {}).get('total_models', 0)} "
                f"models from Helicone"
            )
            return data

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch from Helicone API: {e}")
            # Try cache as fallback
            if self.cache_file.exists():
                logger.warning("Using stale cache as fallback")
                return self._load_cache()
            raise

    def get_pricing(
        self, model_id: str, provider: str | None = None
    ) -> dict[str, Any] | None:
        """Get pricing for a specific model.

        Args:
            model_id: Model identifier
            provider: Optional provider filter (ANTHROPIC, OPENAI, GOOGLE, etc.)

        Returns:
            Pricing dictionary if found, None otherwise

        Example:
            >>> client = HeliconeClient()
            >>> pricing = client.get_pricing("gpt-4o", provider="OPENAI")
            >>> print(pricing)
            {
                'provider': 'OPENAI',
                'model': 'gpt-4o',
                'input_cost_per_1m': 2.5,
                'output_cost_per_1m': 10.0,
                ...
            }
        """
        data = self.fetch()

        # Search for exact match first
        for entry in data.get("data", []):
            # Filter by provider if specified
            if provider and entry.get("provider") != provider.upper():
                continue

            # Check operator type
            model_name = entry.get("model", "")
            operator = entry.get("operator", "equals")

            if (
                (operator == "equals" and model_name == model_id)
                or (operator == "startsWith" and model_id.startswith(model_name))
                or (operator == "includes" and model_name in model_id)
            ):
                return entry

        return None

    def list_models(
        self, provider: str | None = None, show_in_playground_only: bool = False
    ) -> list[dict[str, Any]]:
        """List all models with optional filtering.

        Args:
            provider: Filter by provider (ANTHROPIC, OPENAI, GOOGLE, etc.)
            show_in_playground_only: Only return models shown in playground

        Returns:
            List of model pricing dictionaries
        """
        data = self.fetch()
        models = data.get("data", [])

        if provider:
            models = [m for m in models if m.get("provider") == provider.upper()]

        if show_in_playground_only:
            models = [m for m in models if m.get("show_in_playground")]

        return models

    def _is_cache_valid(self) -> bool:
        """Check if cache exists and is not stale."""
        if not self.cache_file.exists():
            return False

        # Check age
        mtime = datetime.fromtimestamp(self.cache_file.stat().st_mtime)
        age = datetime.now() - mtime

        return age < self.cache_ttl

    def _load_cache(self) -> dict[str, Any]:
        """Load pricing data from cache file."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file) as f:
            return json.load(f)

    def _save_cache(self, data: dict[str, Any]) -> None:
        """Save pricing data to cache file."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(data, f, indent=2)


# Global client instance
_client = HeliconeClient()


def get_helicone_pricing(
    model_id: str, provider: str | None = None
) -> dict[str, Any] | None:
    """Get pricing from Helicone API (convenience function).

    Args:
        model_id: Model identifier
        provider: Optional provider filter

    Returns:
        Pricing dictionary if found, None otherwise

    Example:
        >>> pricing = get_helicone_pricing("claude-sonnet-4-5-20250929")
        >>> if pricing:
        ...     print(f"Input: ${pricing['input_cost_per_1m']}/MTok")
    """
    return _client.get_pricing(model_id, provider)


def sync_pricing_from_helicone(
    registry: Any, update_existing: bool = False
) -> tuple[int, int]:
    """Sync pricing from Helicone into the registry.

    Updates pricing tiers for models that exist in both the registry and Helicone.
    Optionally adds new models found in Helicone.

    Args:
        registry: ModelRegistry instance to update
        update_existing: Whether to update existing model pricing

    Returns:
        Tuple of (models_updated, models_skipped)

    Example:
        >>> from consoul.registry.registry import _registry
        >>> updated, skipped = sync_pricing_from_helicone(_registry)
        >>> print(f"Updated {updated} models, skipped {skipped}")
    """
    from datetime import date

    updated = 0
    skipped = 0

    helicone_data = _client.fetch()

    for entry in helicone_data.get("data", []):
        model_id = entry.get("model")
        if not model_id:
            continue

        # Get model from registry
        model = registry.get(model_id)
        if not model:
            skipped += 1
            continue

        # Update pricing if enabled
        if update_existing:
            # Convert Helicone pricing to PricingTier format
            from consoul.registry.types import PricingTier

            pricing_tier = PricingTier(
                tier="standard",
                input_price=entry.get("input_cost_per_1m", 0.0),
                output_price=entry.get("output_cost_per_1m", 0.0),
                cache_read=entry.get("prompt_cache_read_per_1m"),
                cache_write_5m=entry.get("prompt_cache_write_per_1m"),
                effective_date=date.today(),
                notes=f"Synced from Helicone API ({model_id})",
            )

            model.pricing["standard"] = pricing_tier
            updated += 1

    logger.info(f"Helicone sync: {updated} updated, {skipped} skipped")
    return updated, skipped
