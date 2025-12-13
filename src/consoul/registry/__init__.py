"""Centralized model registry for AI models and pricing.

This module provides a single source of truth for model metadata, pricing,
and capabilities across all providers (OpenAI, Anthropic, Google, etc.).

Features:
- Static model definitions with complete metadata
- Dynamic pricing updates from Helicone API (1,114+ models)
- Hybrid approach: fast static lookups + fresh pricing data
- Automatic caching with weekly refresh

Example - Basic usage:
    >>> from consoul.registry import get_model, get_pricing, list_models
    >>> model = get_model("claude-sonnet-4-5-20250929")
    >>> pricing = get_pricing("gpt-4o", tier="flex")
    >>> all_models = list_models(provider="anthropic")

Example - External pricing:
    >>> from consoul.registry import get_helicone_pricing, sync_pricing
    >>> # Get latest pricing from Helicone API
    >>> pricing = get_helicone_pricing("gpt-4o")
    >>> # Sync all models with Helicone
    >>> updated, skipped = sync_pricing()
"""

from consoul.registry.external import (
    HeliconeClient,
    get_helicone_pricing,
    sync_pricing_from_helicone,
)
from consoul.registry.registry import (
    ModelRegistry,
    get_all_providers,
    get_model,
    get_pricing,
    list_models,
)
from consoul.registry.types import (
    Capability,
    InputModality,
    Modality,
    ModelEntry,
    ModelMetadata,
    OutputModality,
    PricingTier,
)

__all__ = [
    # Registry functions
    "get_model",
    "get_pricing",
    "list_models",
    "get_all_providers",
    "ModelRegistry",
    # External data sources
    "HeliconeClient",
    "get_helicone_pricing",
    "sync_pricing_from_helicone",
    # Types
    "ModelEntry",
    "ModelMetadata",
    "PricingTier",
    "Modality",
    "InputModality",
    "OutputModality",
    "Capability",
]


# Convenience function for syncing
def sync_pricing(update_existing: bool = True) -> tuple[int, int]:
    """Sync pricing from Helicone API into the registry.

    Args:
        update_existing: Whether to update existing model pricing

    Returns:
        Tuple of (models_updated, models_skipped)

    Example:
        >>> from consoul.registry import sync_pricing
        >>> updated, skipped = sync_pricing()
        >>> print(f"Updated {updated} models")
    """
    from consoul.registry.registry import _registry

    return sync_pricing_from_helicone(_registry, update_existing)
