"""Model registry implementation with O(1) lookups.

This module provides the central registry for all AI models with efficient
indexed access patterns inspired by Helicone's registry design.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.registry.types import ModelEntry, PricingTier

logger = logging.getLogger(__name__)

__all__ = [
    "ModelRegistry",
    "get_all_providers",
    "get_model",
    "get_pricing",
    "list_models",
]


class ModelRegistry:
    """Centralized registry for AI models with O(1) lookups.

    Provides efficient indexed access to model metadata and pricing.
    Inspired by Helicone's registry design with runtime index building.

    Attributes:
        _models: Dictionary of all registered models (id -> ModelEntry)
        _by_provider: Index of models by provider
        _by_author: Index of models by author
        _aliases: Index of model aliases to canonical IDs
    """

    def __init__(self) -> None:
        """Initialize empty registry.

        Models are registered via register() or bulk loaded via load_all().
        """
        self._models: dict[str, ModelEntry] = {}
        self._by_provider: dict[str, list[str]] = {}
        self._by_author: dict[str, list[str]] = {}
        self._aliases: dict[str, str] = {}

    def register(self, entry: ModelEntry) -> None:
        """Register a model in the registry.

        Args:
            entry: ModelEntry to register

        Raises:
            ValueError: If model ID already registered
        """
        model_id = entry.metadata.id

        if model_id in self._models:
            logger.warning(f"Model {model_id} already registered, overwriting")

        # Store model
        self._models[model_id] = entry

        # Update provider index
        provider = entry.metadata.provider
        if provider not in self._by_provider:
            self._by_provider[provider] = []
        if model_id not in self._by_provider[provider]:
            self._by_provider[provider].append(model_id)

        # Update author index
        author = entry.metadata.author
        if author not in self._by_author:
            self._by_author[author] = []
        if model_id not in self._by_author[author]:
            self._by_author[author].append(model_id)

        # Register aliases
        for alias in entry.metadata.aliases:
            if alias in self._aliases:
                logger.warning(
                    f"Alias {alias} already points to {self._aliases[alias]}, "
                    f"overwriting with {model_id}"
                )
            self._aliases[alias] = model_id

    def get(self, model_id: str) -> ModelEntry | None:
        """Get model by ID or alias.

        Args:
            model_id: Model identifier or alias

        Returns:
            ModelEntry if found, None otherwise
        """
        # Direct lookup
        if model_id in self._models:
            return self._models[model_id]

        # Alias lookup
        if model_id in self._aliases:
            canonical_id = self._aliases[model_id]
            return self._models.get(canonical_id)

        return None

    def get_pricing(self, model_id: str, tier: str = "standard") -> PricingTier | None:
        """Get pricing for a model.

        Args:
            model_id: Model identifier or alias
            tier: Pricing tier ("standard", "flex", "batch", "priority")

        Returns:
            PricingTier if found, None if model not found
        """
        model = self.get(model_id)
        if not model:
            return None

        return model.get_pricing(tier)

    def list_models(
        self,
        provider: str | None = None,
        author: str | None = None,
        active_only: bool = True,
    ) -> list[ModelEntry]:
        """List models with optional filtering.

        Args:
            provider: Filter by provider (None = all)
            author: Filter by author (None = all)
            active_only: Only return non-deprecated models

        Returns:
            List of ModelEntry objects matching filters
        """
        # Get candidate model IDs
        if provider:
            model_ids = self._by_provider.get(provider, [])
        elif author:
            model_ids = self._by_author.get(author, [])
        else:
            model_ids = list(self._models.keys())

        # Filter and return
        models = [self._models[mid] for mid in model_ids]

        if active_only:
            models = [m for m in models if m.metadata.deprecated is None]

        return models

    def get_all_providers(self) -> list[str]:
        """Get sorted list of all providers.

        Returns:
            Sorted list of provider slugs
        """
        return sorted(self._by_provider.keys())

    def get_all_authors(self) -> list[str]:
        """Get sorted list of all authors.

        Returns:
            Sorted list of author names
        """
        return sorted(self._by_author.keys())

    def clear(self) -> None:
        """Clear all registered models (mainly for testing)."""
        self._models.clear()
        self._by_provider.clear()
        self._by_author.clear()
        self._aliases.clear()


# Global registry instance
_registry = ModelRegistry()


def _load_all_models() -> None:
    """Load all model definitions into the global registry.

    This is called automatically on import to populate the registry.
    Models are loaded from the models/ subdirectory.
    """
    # Import model modules - each registers its models
    try:
        # Anthropic models
        # OpenAI models
        # Google models
        from consoul.registry.models import (
            anthropic,  # noqa: F401
            google,  # noqa: F401
            openai,  # noqa: F401
        )

        logger.info(
            f"Loaded {len(_registry._models)} models from "
            f"{len(_registry._by_provider)} providers"
        )
    except ImportError as e:
        logger.warning(f"Failed to load some model definitions: {e}")


def get_model(model_id: str) -> ModelEntry | None:
    """Get model by ID or alias.

    Args:
        model_id: Model identifier or alias

    Returns:
        ModelEntry if found, None otherwise

    Example:
        >>> model = get_model("claude-sonnet-4-5-20250929")
        >>> if model:
        ...     print(f"{model.name}: {model.metadata.context_window} tokens")
    """
    return _registry.get(model_id)


def get_pricing(model_id: str, tier: str = "standard") -> PricingTier | None:
    """Get pricing for a model.

    Args:
        model_id: Model identifier or alias
        tier: Pricing tier ("standard", "flex", "batch", "priority")

    Returns:
        PricingTier if found, None if model not found

    Example:
        >>> pricing = get_pricing("gpt-4o", tier="flex")
        >>> if pricing:
        ...     print(f"Input: ${pricing.input_price}/MTok")
    """
    return _registry.get_pricing(model_id, tier)


def list_models(
    provider: str | None = None,
    author: str | None = None,
    active_only: bool = True,
) -> list[ModelEntry]:
    """List models with optional filtering.

    Args:
        provider: Filter by provider (None = all)
        author: Filter by author (None = all)
        active_only: Only return non-deprecated models

    Returns:
        List of ModelEntry objects matching filters

    Example:
        >>> anthropic_models = list_models(provider="anthropic")
        >>> for model in anthropic_models:
        ...     print(f"{model.name}: {model.metadata.description}")
    """
    return _registry.list_models(
        provider=provider, author=author, active_only=active_only
    )


def get_all_providers() -> list[str]:
    """Get sorted list of all providers.

    Returns:
        Sorted list of provider slugs

    Example:
        >>> providers = get_all_providers()
        >>> print(", ".join(providers))
        anthropic, google, openai
    """
    return _registry.get_all_providers()


# Auto-load models on import
_load_all_models()
