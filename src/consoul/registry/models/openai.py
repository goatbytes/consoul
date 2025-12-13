"""OpenAI GPT model definitions.

This module defines all OpenAI models with their metadata and pricing.
Models are automatically registered with the global registry on import.

Pricing source: https://platform.openai.com/docs/pricing (January 2025)
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

# GPT-4.1 (1M context, April 2025)
gpt_4_1 = ModelEntry(
    metadata=ModelMetadata(
        id="gpt-4.1",
        name="GPT-4.1",
        provider="openai",
        author="OpenAI",
        description="Improved coding & long context with 1M context window",
        context_window=1_047_576,
        max_output_tokens=32_768,
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
            Capability.JSON_MODE,
        ],
        created=date(2025, 4, 14),
        aliases=["gpt-4-1"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=2.00,
            output_price=8.00,
            cache_read=0.50,
            effective_date=date(2025, 4, 14),
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=1.00,  # 50% discount
            output_price=4.00,  # 50% discount
            effective_date=date(2025, 4, 14),
            notes="50% discount for batch processing",
        ),
        "priority": PricingTier(
            tier="priority",
            input_price=3.50,
            output_price=14.00,
            cache_read=0.875,
            effective_date=date(2025, 4, 14),
        ),
    },
)

# GPT-4.1 Mini
gpt_4_1_mini = ModelEntry(
    metadata=ModelMetadata(
        id="gpt-4.1-mini",
        name="GPT-4.1 Mini",
        provider="openai",
        author="OpenAI",
        description="Fast with 1M context window",
        context_window=1_047_576,
        max_output_tokens=32_768,
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
            Capability.JSON_MODE,
        ],
        created=date(2025, 4, 14),
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=0.40,
            output_price=1.60,
            cache_read=0.10,
            effective_date=date(2025, 4, 14),
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=0.20,
            output_price=0.80,
            effective_date=date(2025, 4, 14),
        ),
        "priority": PricingTier(
            tier="priority",
            input_price=0.70,
            output_price=2.80,
            cache_read=0.175,
            effective_date=date(2025, 4, 14),
        ),
    },
)

# GPT-4.1 Nano
gpt_4_1_nano = ModelEntry(
    metadata=ModelMetadata(
        id="gpt-4.1-nano",
        name="GPT-4.1 Nano",
        provider="openai",
        author="OpenAI",
        description="Smallest GPT-4.1 variant with 1M context",
        context_window=1_047_576,
        max_output_tokens=32_768,
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
            Capability.JSON_MODE,
        ],
        created=date(2025, 4, 14),
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=0.10,
            output_price=0.40,
            cache_read=0.025,
            effective_date=date(2025, 4, 14),
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=0.05,
            output_price=0.20,
            effective_date=date(2025, 4, 14),
        ),
        "priority": PricingTier(
            tier="priority",
            input_price=0.20,
            output_price=0.80,
            cache_read=0.05,
            effective_date=date(2025, 4, 14),
        ),
    },
)

# GPT-4o
gpt_4o = ModelEntry(
    metadata=ModelMetadata(
        id="gpt-4o",
        name="GPT-4o",
        provider="openai",
        author="OpenAI",
        description="Multimodal flagship with 128K context",
        context_window=128_000,
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
            Capability.JSON_MODE,
        ],
        created=date(2024, 5, 13),
        aliases=["gpt-4o-latest"],
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=2.50,
            output_price=10.00,
            cache_read=1.25,
            effective_date=date(2024, 5, 13),
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=1.25,
            output_price=5.00,
            effective_date=date(2024, 5, 13),
        ),
        "priority": PricingTier(
            tier="priority",
            input_price=4.25,
            output_price=17.00,
            cache_read=2.125,
            effective_date=date(2024, 5, 13),
        ),
    },
)

# GPT-4o Mini
gpt_4o_mini = ModelEntry(
    metadata=ModelMetadata(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider="openai",
        author="OpenAI",
        description="Cost-efficient multimodal",
        context_window=128_000,
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
            Capability.JSON_MODE,
        ],
        created=date(2024, 7, 18),
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=0.15,
            output_price=0.60,
            cache_read=0.075,
            effective_date=date(2024, 7, 18),
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=0.075,
            output_price=0.30,
            effective_date=date(2024, 7, 18),
        ),
        "priority": PricingTier(
            tier="priority",
            input_price=0.25,
            output_price=1.00,
            cache_read=0.125,
            effective_date=date(2024, 7, 18),
        ),
    },
)

# O1 (reasoning model)
o1 = ModelEntry(
    metadata=ModelMetadata(
        id="o1",
        name="O1",
        provider="openai",
        author="OpenAI",
        description="Reasoning model series 1 with extended thinking",
        context_window=200_000,
        max_output_tokens=100_000,
        modality=Modality(
            inputs=[InputModality.TEXT], outputs=[OutputModality.TEXT]
        ),
        capabilities=[
            Capability.TOOLS,
            Capability.REASONING,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.BATCH,
        ],
        created=date(2024, 12, 17),
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=15.00,
            output_price=60.00,
            cache_read=7.50,
            thinking_price=60.00,  # Reasoning tokens priced as output
            effective_date=date(2024, 12, 17),
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=7.50,
            output_price=30.00,
            effective_date=date(2024, 12, 17),
        ),
    },
)

# O1 Mini
o1_mini = ModelEntry(
    metadata=ModelMetadata(
        id="o1-mini",
        name="O1 Mini",
        provider="openai",
        author="OpenAI",
        description="Faster, cheaper reasoning model",
        context_window=128_000,
        max_output_tokens=65_536,
        modality=Modality(
            inputs=[InputModality.TEXT], outputs=[OutputModality.TEXT]
        ),
        capabilities=[
            Capability.TOOLS,
            Capability.REASONING,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.BATCH,
        ],
        created=date(2024, 9, 12),
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=1.10,
            output_price=4.40,
            cache_read=0.55,
            effective_date=date(2024, 9, 12),
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=0.55,
            output_price=2.20,
            effective_date=date(2024, 9, 12),
        ),
    },
)

# O3 Mini
o3_mini = ModelEntry(
    metadata=ModelMetadata(
        id="o3-mini",
        name="O3 Mini",
        provider="openai",
        author="OpenAI",
        description="Efficient reasoning model",
        context_window=128_000,
        max_output_tokens=65_536,
        modality=Modality(
            inputs=[InputModality.TEXT], outputs=[OutputModality.TEXT]
        ),
        capabilities=[
            Capability.TOOLS,
            Capability.REASONING,
            Capability.STREAMING,
            Capability.CACHING,
            Capability.BATCH,
        ],
        created=date(2025, 1, 31),
    ),
    pricing={
        "standard": PricingTier(
            tier="standard",
            input_price=1.10,
            output_price=4.40,
            cache_read=0.55,
            effective_date=date(2025, 1, 31),
        ),
        "batch": PricingTier(
            tier="batch",
            input_price=0.55,
            output_price=2.20,
            effective_date=date(2025, 1, 31),
        ),
    },
)

# Register all models
_registry.register(gpt_4_1)
_registry.register(gpt_4_1_mini)
_registry.register(gpt_4_1_nano)
_registry.register(gpt_4o)
_registry.register(gpt_4o_mini)
_registry.register(o1)
_registry.register(o1_mini)
_registry.register(o3_mini)
