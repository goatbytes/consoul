"""Google Gemini model definitions.

This module defines all Google Gemini models with their metadata and pricing.
Models are automatically registered with the global registry on import.

Pricing source: https://ai.google.dev/gemini-api/docs/models (January 2025)
"""

from datetime import date

from consoul.registry.registry import _registry
from consoul.registry.types import (
    Capability,
    InputModality,
    ModelEntry,
    ModelMetadata,
    Modality,
    OutputModality,
    PricingTier,
)

# Gemini 2.5 Pro
gemini_2_5_pro = ModelEntry(
    metadata=ModelMetadata(
        id="gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        provider="google",
        author="Google",
        description="Most powerful with thinking - state-of-the-art reasoning model",
        context_window=1_048_576,
        max_output_tokens=65_535,
        modality=Modality(
            inputs=[InputModality.TEXT, InputModality.IMAGE, InputModality.AUDIO],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.REASONING,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.JSON_MODE,
        ],
        created=date(2025, 6, 17),
        aliases=["gemini-2.5-pro-latest"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=1.25,  # ≤200K tokens
            output_price=10.00,
            cache_read=0.12,
            effective_date=date(2025, 6, 17),
            notes="Tiered pricing: $1.25 for ≤200K, higher for >200K",
        ),
    },
)

# Gemini 2.5 Flash
gemini_2_5_flash = ModelEntry(
    metadata=ModelMetadata(
        id="gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        provider="google",
        author="Google",
        description="Fast multimodal with best price-performance",
        context_window=1_048_576,
        max_output_tokens=65_535,
        modality=Modality(
            inputs=[
                InputModality.TEXT,
                InputModality.IMAGE,
                InputModality.AUDIO,
                InputModality.VIDEO,
            ],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.REASONING,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.JSON_MODE,
        ],
        created=date(2025, 6, 17),
        aliases=["gemini-2.5-flash-latest"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=0.62,  # ≤200K tokens
            output_price=5.00,
            cache_read=0.12,
            effective_date=date(2025, 6, 17),
            notes="Tiered pricing: $0.62 for ≤200K, higher for >200K",
        ),
    },
)

# Gemini 2.5 Flash-Lite
gemini_2_5_flash_lite = ModelEntry(
    metadata=ModelMetadata(
        id="gemini-2.5-flash-lite",
        name="Gemini 2.5 Flash Lite",
        provider="google",
        author="Google",
        description="Speed & cost optimized multimodal",
        context_window=1_048_576,
        max_output_tokens=65_535,
        modality=Modality(
            inputs=[
                InputModality.TEXT,
                InputModality.IMAGE,
                InputModality.AUDIO,
                InputModality.VIDEO,
            ],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.JSON_MODE,
        ],
        created=date(2025, 6, 17),
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=0.15,
            output_price=1.25,
            cache_read=0.03,
            effective_date=date(2025, 6, 17),
        ),
    },
)

# Gemini 2.0 Flash
gemini_2_0_flash = ModelEntry(
    metadata=ModelMetadata(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider="google",
        author="Google",
        description="Latest stable flash model (free tier up to 10 RPM)",
        context_window=1_048_576,
        max_output_tokens=65_535,
        modality=Modality(
            inputs=[
                InputModality.TEXT,
                InputModality.IMAGE,
                InputModality.AUDIO,
                InputModality.VIDEO,
            ],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.JSON_MODE,
        ],
        created=date(2024, 12, 11),
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=0.30,
            output_price=2.50,
            cache_read=0.03,
            effective_date=date(2024, 12, 11),
            notes="Free tier: up to 10 RPM, 2M TPM",
        ),
    },
)

# Gemini 1.5 Pro (Legacy)
gemini_1_5_pro = ModelEntry(
    metadata=ModelMetadata(
        id="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        provider="google",
        author="Google",
        description="Legacy model with 2M context - use Gemini 2.5 Pro",
        context_window=2_097_152,
        max_output_tokens=8_192,
        modality=Modality(
            inputs=[
                InputModality.TEXT,
                InputModality.IMAGE,
                InputModality.AUDIO,
                InputModality.VIDEO,
            ],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.JSON_MODE,
        ],
        created=date(2024, 2, 15),
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=1.25,
            output_price=10.00,
            cache_read=0.12,
            effective_date=date(2024, 2, 15),
        ),
    },
)

# Gemini 1.5 Flash (Legacy)
gemini_1_5_flash = ModelEntry(
    metadata=ModelMetadata(
        id="gemini-1.5-flash",
        name="Gemini 1.5 Flash",
        provider="google",
        author="Google",
        description="Legacy flash model - use Gemini 2.5 Flash",
        context_window=1_048_576,
        max_output_tokens=8_192,
        modality=Modality(
            inputs=[
                InputModality.TEXT,
                InputModality.IMAGE,
                InputModality.AUDIO,
                InputModality.VIDEO,
            ],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.JSON_MODE,
        ],
        created=date(2024, 5, 14),
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=0.62,
            output_price=5.00,
            cache_read=0.12,
            effective_date=date(2024, 5, 14),
        ),
    },
)

# Register all models
_registry.register(gemini_2_5_pro)
_registry.register(gemini_2_5_flash)
_registry.register(gemini_2_5_flash_lite)
_registry.register(gemini_2_0_flash)
_registry.register(gemini_1_5_pro)
_registry.register(gemini_1_5_flash)
