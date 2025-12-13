"""Core type definitions for the model registry.

This module defines the data structures for model metadata, pricing,
and capabilities. All types use Pydantic for validation and serialization.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "InputModality",
    "OutputModality",
    "Modality",
    "Capability",
    "ModelMetadata",
    "PricingTier",
    "ModelEntry",
]


class InputModality(str, Enum):
    """Supported input modalities for AI models."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class OutputModality(str, Enum):
    """Supported output modalities for AI models."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class Modality(BaseModel):
    """Input and output modalities supported by a model."""

    inputs: list[InputModality] = Field(
        description="Supported input types (text, image, audio, video)"
    )
    outputs: list[OutputModality] = Field(
        description="Supported output types (text, image, audio, video)"
    )


class Capability(str, Enum):
    """Model capabilities beyond basic text generation."""

    VISION = "vision"  # Can process images
    TOOLS = "tools"  # Supports function calling
    REASONING = "reasoning"  # Extended reasoning/thinking
    STREAMING = "streaming"  # Supports streaming responses
    JSON_MODE = "json_mode"  # Structured JSON output
    CACHING = "caching"  # Prompt caching support
    BATCH = "batch"  # Batch API support
    REALTIME = "realtime"  # Real-time voice/audio


class ModelMetadata(BaseModel):
    """Immutable metadata about an AI model.

    This contains facts about the model that don't change frequently:
    capabilities, context windows, release dates, etc.

    Attributes:
        id: Unique model identifier (e.g., "gpt-4o", "claude-sonnet-4-5-20250929")
        name: Human-readable display name
        provider: Provider slug ("openai", "anthropic", "google", "ollama")
        author: Organization that created the model
        description: Brief model description
        context_window: Maximum context window in tokens
        max_output_tokens: Maximum output tokens per request
        modality: Supported input/output types
        capabilities: List of model capabilities
        created: Release date
        deprecated: Deprecation date (None if active)
        aliases: Alternative names/IDs for the model
    """

    id: str = Field(description="Unique model identifier")
    name: str = Field(description="Human-readable display name")
    provider: str = Field(description="Provider slug (openai, anthropic, google, etc.)")
    author: str = Field(description="Organization that created the model")
    description: str = Field(description="Brief model description")
    context_window: int = Field(
        description="Maximum context window in tokens", gt=0
    )
    max_output_tokens: int = Field(
        description="Maximum output tokens per request", gt=0
    )
    modality: Modality = Field(description="Supported input/output modalities")
    capabilities: list[Capability] = Field(
        default_factory=list, description="Model capabilities"
    )
    created: date = Field(description="Release date")
    deprecated: date | None = Field(
        default=None, description="Deprecation date (None if active)"
    )
    aliases: list[str] = Field(
        default_factory=list, description="Alternative names/IDs"
    )

    class Config:
        frozen = True  # Immutable


class PricingTier(BaseModel):
    """Pricing information for a specific service tier.

    Prices are in USD per million tokens (MTok).

    Attributes:
        tier: Tier name ("standard", "flex", "batch", "priority")
        input_price: Cost per million input tokens
        output_price: Cost per million output tokens
        cache_read: Cost per million cached read tokens (optional)
        cache_write_5m: Cost per million cache write tokens (5min TTL, optional)
        cache_write_1h: Cost per million cache write tokens (1hr TTL, optional)
        thinking_price: Cost per million reasoning tokens (optional)
        effective_date: When this pricing took effect
        notes: Additional pricing notes
    """

    tier: Literal["standard", "flex", "batch", "priority"] = Field(
        description="Service tier name"
    )
    input_price: float = Field(description="USD per million input tokens", ge=0)
    output_price: float = Field(description="USD per million output tokens", ge=0)
    cache_read: float | None = Field(
        default=None, description="USD per million cached read tokens"
    )
    cache_write_5m: float | None = Field(
        default=None, description="USD per million cache write tokens (5min TTL)"
    )
    cache_write_1h: float | None = Field(
        default=None, description="USD per million cache write tokens (1hr TTL)"
    )
    thinking_price: float | None = Field(
        default=None, description="USD per million reasoning/thinking tokens"
    )
    effective_date: date = Field(description="When this pricing took effect")
    notes: str | None = Field(default=None, description="Additional pricing notes")


class ModelEntry(BaseModel):
    """Complete model registry entry combining metadata and pricing.

    This is the primary data structure returned by the registry.

    Attributes:
        metadata: Immutable model facts (capabilities, context, etc.)
        pricing: Pricing tiers (standard, flex, batch, priority)
    """

    metadata: ModelMetadata = Field(description="Model metadata")
    pricing: dict[str, PricingTier] = Field(
        description="Pricing by tier (standard, flex, batch, priority)"
    )

    @property
    def id(self) -> str:
        """Convenience property for model ID."""
        return self.metadata.id

    @property
    def name(self) -> str:
        """Convenience property for model name."""
        return self.metadata.name

    @property
    def provider(self) -> str:
        """Convenience property for provider."""
        return self.metadata.provider

    def get_pricing(
        self, tier: str = "standard"
    ) -> PricingTier:
        """Get pricing for a specific tier.

        Args:
            tier: Tier name ("standard", "flex", "batch", "priority")

        Returns:
            PricingTier for the requested tier

        Raises:
            KeyError: If tier doesn't exist for this model
        """
        # Normalize tier: "auto" and "default" map to "standard"
        normalized_tier = (
            tier if tier in ("flex", "batch", "priority") else "standard"
        )

        if normalized_tier in self.pricing:
            return self.pricing[normalized_tier]

        # Fallback to standard if tier not available
        if "standard" in self.pricing:
            return self.pricing["standard"]

        # Return first available tier
        return next(iter(self.pricing.values()))

    def supports_vision(self) -> bool:
        """Check if model supports vision/images."""
        return Capability.VISION in self.metadata.capabilities

    def supports_tools(self) -> bool:
        """Check if model supports function calling."""
        return Capability.TOOLS in self.metadata.capabilities

    def supports_reasoning(self) -> bool:
        """Check if model has extended reasoning capabilities."""
        return Capability.REASONING in self.metadata.capabilities

    def supports_streaming(self) -> bool:
        """Check if model supports streaming responses."""
        return Capability.STREAMING in self.metadata.capabilities
