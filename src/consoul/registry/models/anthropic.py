"""Anthropic Claude model definitions.

This module defines all Anthropic Claude models with their metadata and pricing.
Models are automatically registered with the global registry on import.

Pricing source: https://claude.com/pricing (January 2025)
"""

from datetime import date

from consoul.registry.registry import _registry
from consoul.registry.types import (
    Capability,
    InputModality,
    Modality,
    ModelEntry,
    ModelMetadata,
    OutputModality,
    PricingTier,
)

# Claude Opus 4.5 (November 2025 - 66% price drop!)
claude_opus_4_5 = ModelEntry(
    metadata=ModelMetadata(
        id="claude-opus-4-5-20251101",
        name="Claude Opus 4.5",
        provider="anthropic",
        author="Anthropic",
        description="Premium intelligence + performance with extended thinking",
        context_window=200_000,
        max_output_tokens=16_384,
        modality=Modality(
            inputs=[InputModality.TEXT, InputModality.IMAGE],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.REASONING,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.BATCH,
        ],
        created=date(2025, 11, 1),
        aliases=["claude-opus-4.5", "opus-4.5"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=5.00,
            output_price=25.00,
            cache_read=0.50,
            cache_write_5m=6.25,
            cache_write_1h=10.00,
            effective_date=date(2025, 11, 1),
            notes="66% price drop from original Claude 3 Opus pricing",
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=2.50,  # 50% discount
            output_price=12.50,  # 50% discount
            effective_date=date(2025, 11, 1),
            notes="50% discount for batch processing",
        ),
    },
)

# Claude Sonnet 4.5 (September 2025)
claude_sonnet_4_5 = ModelEntry(
    metadata=ModelMetadata(
        id="claude-sonnet-4-5-20250929",
        name="Claude Sonnet 4.5",
        provider="anthropic",
        author="Anthropic",
        description="Smartest for complex agents + coding with extended thinking",
        context_window=200_000,
        max_output_tokens=64_000,
        modality=Modality(
            inputs=[InputModality.TEXT, InputModality.IMAGE],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.REASONING,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.BATCH,
        ],
        created=date(2025, 9, 29),
        aliases=["claude-sonnet-4.5", "sonnet-4.5"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=3.00,  # <= 200K tokens
            output_price=15.00,  # <= 200K tokens
            cache_read=0.30,
            cache_write_5m=3.75,
            cache_write_1h=6.00,
            effective_date=date(2025, 9, 29),
            notes="Tiered pricing: $3/$15 for ≤200K, $6/$22.50 for >200K",
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=1.50,  # 50% discount
            output_price=7.50,  # 50% discount
            effective_date=date(2025, 9, 29),
            notes="50% discount for batch processing",
        ),
    },
)

# Claude Haiku 4.5 (October 2025)
claude_haiku_4_5 = ModelEntry(
    metadata=ModelMetadata(
        id="claude-haiku-4-5-20251001",
        name="Claude Haiku 4.5",
        provider="anthropic",
        author="Anthropic",
        description="Fastest near-frontier intelligence",
        context_window=200_000,
        max_output_tokens=16_384,
        modality=Modality(
            inputs=[InputModality.TEXT, InputModality.IMAGE],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.BATCH,
        ],
        created=date(2025, 10, 1),
        aliases=["claude-haiku-4.5", "haiku-4.5"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=1.00,
            output_price=5.00,
            cache_read=0.10,
            cache_write_5m=1.25,
            cache_write_1h=2.00,
            effective_date=date(2025, 10, 1),
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=0.50,  # 50% discount
            output_price=2.50,  # 50% discount
            effective_date=date(2025, 10, 1),
            notes="50% discount for batch processing",
        ),
    },
)

# Claude 3.5 Sonnet v2 (October 2024)
claude_3_5_sonnet_v2 = ModelEntry(
    metadata=ModelMetadata(
        id="claude-3-5-sonnet-20241022",
        name="Claude 3.5 Sonnet",
        provider="anthropic",
        author="Anthropic",
        description="Legacy model - use Sonnet 4.5 for best results",
        context_window=200_000,
        max_output_tokens=8_192,
        modality=Modality(
            inputs=[InputModality.TEXT, InputModality.IMAGE],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.STREAMING,
            Capability.CACHING,
        ],
        created=date(2024, 10, 22),
        aliases=["claude-3.5-sonnet", "claude-3-5-sonnet-latest"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=3.00,
            output_price=15.00,
            cache_read=0.30,
            cache_write_5m=3.75,
            cache_write_1h=6.00,
            effective_date=date(2024, 10, 22),
        ),
    },
)

# Claude 3.5 Haiku (October 2024)
claude_3_5_haiku = ModelEntry(
    metadata=ModelMetadata(
        id="claude-3-5-haiku-20241022",
        name="Claude 3.5 Haiku",
        provider="anthropic",
        author="Anthropic",
        description="Legacy model - use Haiku 4.5 for best results",
        context_window=200_000,
        max_output_tokens=8_192,
        modality=Modality(
            inputs=[InputModality.TEXT, InputModality.IMAGE],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.STREAMING,
            Capability.CACHING,
        ],
        created=date(2024, 10, 22),
        aliases=["claude-3.5-haiku"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=1.00,
            output_price=5.00,
            cache_read=0.10,
            cache_write_5m=1.25,
            cache_write_1h=2.00,
            effective_date=date(2024, 10, 22),
        ),
    },
)

# Claude 3 Opus (February 2024)
claude_3_opus = ModelEntry(
    metadata=ModelMetadata(
        id="claude-3-opus-20240229",
        name="Claude 3 Opus",
        provider="anthropic",
        author="Anthropic",
        description="Legacy model - use Opus 4.5 for best results and 66% savings",
        context_window=200_000,
        max_output_tokens=4_096,
        modality=Modality(
            inputs=[InputModality.TEXT, InputModality.IMAGE],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.STREAMING,
            Capability.CACHING,
        ],
        created=date(2024, 2, 29),
        aliases=["claude-3-opus"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=5.00,  # Updated to match Opus 4.5 pricing
            output_price=25.00,  # Updated to match Opus 4.5 pricing
            cache_read=0.50,
            cache_write_5m=6.25,
            cache_write_1h=10.00,
            effective_date=date(2025, 11, 1),
            notes="Price dropped 66% with Opus 4.5 release",
        ),
    },
)

# Claude 3 Haiku (March 2024)
claude_3_haiku = ModelEntry(
    metadata=ModelMetadata(
        id="claude-3-haiku-20240307",
        name="Claude 3 Haiku",
        provider="anthropic",
        author="Anthropic",
        description="Legacy model - use Haiku 4.5 for best results",
        context_window=200_000,
        max_output_tokens=4_096,
        modality=Modality(
            inputs=[InputModality.TEXT, InputModality.IMAGE],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.STREAMING,
            Capability.CACHING,
        ],
        created=date(2024, 3, 7),
        aliases=["claude-3-haiku"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=0.80,
            output_price=4.00,
            cache_read=0.08,
            cache_write_5m=1.00,
            cache_write_1h=1.60,
            effective_date=date(2024, 3, 7),
        ),
    },
)

# Claude Opus 4.1
claude_opus_4_1 = ModelEntry(
    metadata=ModelMetadata(
        id="claude-opus-4-1-20250805",
        name="Claude Opus 4.1",
        provider="anthropic",
        author="Anthropic",
        description="Upgraded for agentic tasks, real-world coding, and reasoning",
        context_window=200_000,
        max_output_tokens=16_384,
        modality=Modality(
            inputs=[InputModality.TEXT, InputModality.IMAGE],
            outputs=[OutputModality.TEXT],
        ),
        capabilities=[
            Capability.VISION,
            Capability.TOOLS,
            Capability.REASONING,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.BATCH,
        ],
        created=date(2025, 8, 5),
        aliases=["claude-opus-4.1"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=5.0,
            output_price=25.0,
            cache_read=0.5,
            cache_write_5m=6.25,
            cache_write_1h=10.0,
            effective_date=date(2025, 8, 5),
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=2.5,
            output_price=12.5,
            effective_date=date(2025, 8, 5),
            notes="50% discount for batch processing",
        ),
    },
)

# Register all models
_registry.register(claude_opus_4_5)
_registry.register(claude_opus_4_1)
_registry.register(claude_sonnet_4_5)
_registry.register(claude_haiku_4_5)
_registry.register(claude_3_5_sonnet_v2)
_registry.register(claude_3_5_haiku)
_registry.register(claude_3_opus)
_registry.register(claude_3_haiku)
