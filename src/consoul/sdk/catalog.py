"""Model catalog - Available AI models and their capabilities.

This module provides the central catalog of supported AI models across all providers.
Models are sourced from the centralized registry for a single source of truth.

Example:
    >>> from consoul.sdk.catalog import MODEL_CATALOG, get_model_info
    >>> model = get_model_info("gpt-4o")
    >>> if model and model.supports_vision:
    ...     print(f"{model.name} can process images")

Note:
    The catalog is now built from the model registry (consoul.registry) which
    contains 21 flagship models with verified metadata and pricing. The static
    list of 120+ models has been replaced with registry-sourced data.
"""

from __future__ import annotations

from consoul.sdk.models import ModelInfo

__all__ = [
    "MODEL_CATALOG",
    "get_all_providers",
    "get_model_info",
    "get_models_by_provider",
]


def _format_context(tokens: int) -> str:
    """Format context window size for display.

    Args:
        tokens: Context window size in tokens

    Returns:
        Human-readable string (e.g., "128K", "1M")
    """
    if tokens >= 1_000_000:
        return f"{tokens // 1_000_000}M"
    elif tokens >= 1_000:
        return f"{tokens // 1_000}K"
    return str(tokens)


def _build_catalog_from_registry() -> list[ModelInfo]:
    """Build model catalog from the centralized registry.

    Converts registry ModelEntry objects to SDK ModelInfo objects for
    use by the TUI Model Picker and other components.

    Returns:
        List of ModelInfo objects with model metadata
    """
    from consoul.registry import list_models

    # Get all active (non-deprecated) models from registry
    registry_models = list_models(active_only=True)

    catalog = []
    for entry in registry_models:
        # Convert registry entry to SDK ModelInfo
        model_info = ModelInfo(
            id=entry.metadata.id,
            name=entry.metadata.name,
            provider=entry.metadata.provider,
            context_window=_format_context(entry.metadata.context_window),
            description=entry.metadata.description,
            # Extract capability flags from registry
            supports_vision="vision" in [c.value for c in entry.metadata.capabilities],
            supports_tools="tools" in [c.value for c in entry.metadata.capabilities],
        )
        catalog.append(model_info)

    return catalog


# Central model catalog - Built from registry on import
# Contains 21 flagship models with verified metadata
MODEL_CATALOG: list[ModelInfo] = _build_catalog_from_registry()


def get_models_by_provider(provider: str) -> list[ModelInfo]:
    """Get all models for a specific provider.

    Args:
        provider: Provider name ("openai", "anthropic", "google", "huggingface", "ollama")

    Returns:
        List of ModelInfo objects for the specified provider

    Example:
        >>> openai_models = get_models_by_provider("openai")
        >>> print(f"Found {len(openai_models)} OpenAI models")
    """
    return [m for m in MODEL_CATALOG if m.provider.lower() == provider.lower()]


def get_model_info(model_id: str) -> ModelInfo | None:
    """Get model info by ID.

    Args:
        model_id: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet-20241022")

    Returns:
        ModelInfo if found, None otherwise

    Example:
        >>> model = get_model_info("gpt-4o")
        >>> if model:
        ...     print(f"{model.name}: {model.description}")
    """
    return next((m for m in MODEL_CATALOG if m.id == model_id), None)


def get_all_providers() -> list[str]:
    """Get unique list of providers.

    Returns:
        Sorted list of provider names

    Example:
        >>> providers = get_all_providers()
        >>> print(", ".join(providers))
        anthropic, google, openai
    """
    return sorted({m.provider for m in MODEL_CATALOG})
