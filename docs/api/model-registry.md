# Model Registry

The Model Registry is Consoul's centralized system for managing AI model metadata, pricing, and capabilities across all major providers. It provides SDK users with comprehensive, up-to-date information about 1,114+ AI models.

## Overview

The registry combines:

- **Static Definitions**: 21 flagship models with detailed metadata
- **External API Integration**: 1,114+ models from Helicone API with fresh pricing
- **Automatic Caching**: 7-day TTL for optimal performance
- **O(1) Lookups**: Indexed by ID, provider, author, and aliases

## Quick Start

```python
from consoul.config import load_config
from consoul.sdk.services.model import ModelService

# Initialize model service
config = load_config()
service = ModelService.from_config(config)

# List all available models
models = service.list_available_models()
for model in models[:5]:
    print(f"{model.name}: {model.context_window}")

# Get pricing for a specific model
pricing = service.get_model_pricing("claude-sonnet-4-5-20250929")
if pricing:
    print(f"Input: ${pricing.input_price}/MTok")
    print(f"Output: ${pricing.output_price}/MTok")
```

## Core Concepts

### Model Metadata

Complete information about each model:

- **Identity**: ID, name, provider, author
- **Context**: Context window size, max output tokens
- **Capabilities**: Vision, tools, reasoning, streaming, caching, batch
- **Dates**: Creation date, deprecation date (if applicable)
- **Aliases**: Alternative names/IDs

### Pricing Tiers

Different pricing options per model:

- **Standard**: Default pricing for all models
- **Batch**: 50% discount for batch processing (select models)
- **Priority**: Premium pricing for guaranteed capacity
- **Flex**: Flexible pricing based on usage (OpenAI)

### Capabilities

Feature flags for model capabilities:

| Capability | Description |
|------------|-------------|
| `supports_vision` | Can process image inputs |
| `supports_tools` | Supports function/tool calling |
| `supports_reasoning` | Has extended reasoning/thinking |
| `supports_streaming` | Supports streaming responses |
| `supports_json_mode` | Structured JSON output |
| `supports_caching` | Prompt caching support |
| `supports_batch` | Batch API support |

## SDK Methods

### List Available Models

Query all models with optional filters:

```python
# All models
all_models = service.list_available_models()

# Filter by provider
anthropic_models = service.list_available_models(provider="anthropic")
openai_models = service.list_available_models(provider="openai")
google_models = service.list_available_models(provider="google")

# Only active (non-deprecated) models
active_models = service.list_available_models(active_only=True)

# Combine filters
active_anthropic = service.list_available_models(
    provider="anthropic",
    active_only=True
)
```

**Returns**: List of `ModelInfo` objects with complete metadata.

### Get Model Pricing

Retrieve tier-specific pricing information:

```python
# Standard tier (default)
pricing = service.get_model_pricing("claude-sonnet-4-5-20250929")

# Batch tier
batch_pricing = service.get_model_pricing("gpt-4o", tier="batch")

# Priority tier
priority_pricing = service.get_model_pricing("gpt-4o", tier="priority")

if pricing:
    print(f"Input: ${pricing.input_price} per MTok")
    print(f"Output: ${pricing.output_price} per MTok")

    # Cache pricing (if available)
    if pricing.cache_read:
        print(f"Cache Read: ${pricing.cache_read} per MTok")
    if pricing.cache_write_5m:
        print(f"Cache Write (5min): ${pricing.cache_write_5m} per MTok")

    # Effective date
    print(f"Effective: {pricing.effective_date}")

    # Notes
    if pricing.notes:
        print(f"Notes: {pricing.notes}")
```

**Returns**: `PricingInfo` object or `None` if not found.

### Get Model Capabilities

Query what features a model supports:

```python
caps = service.get_model_capabilities("claude-sonnet-4-5-20250929")

if caps:
    if caps.supports_vision:
        print("✓ Supports image inputs")

    if caps.supports_tools:
        print("✓ Supports function calling")

    if caps.supports_reasoning:
        print("✓ Has extended reasoning")

    if caps.supports_caching:
        print("✓ Supports prompt caching")
```

**Returns**: `ModelCapabilities` object or `None` if not found.

### Get Complete Metadata

Access all available information for a model:

```python
model = service.get_model_metadata("claude-sonnet-4-5-20250929")

if model:
    # Basic info
    print(f"Name: {model.name}")
    print(f"Provider: {model.provider}")
    print(f"Description: {model.description}")
    print(f"Context Window: {model.context_window}")
    print(f"Max Output: {model.max_output_tokens:,} tokens")

    # Capabilities
    if model.capabilities:
        print(f"Vision: {model.capabilities.supports_vision}")
        print(f"Tools: {model.capabilities.supports_tools}")

    # Pricing
    if model.pricing:
        print(f"Cost: ${model.pricing.input_price}/${model.pricing.output_price} per MTok")
```

**Returns**: `ModelInfo` object with complete data or `None` if not found.

## Data Models

### PricingInfo

```python
from consoul.sdk import PricingInfo

@dataclass
class PricingInfo:
    input_price: float              # Cost per million input tokens
    output_price: float             # Cost per million output tokens
    cache_read: float | None        # Cache read cost (optional)
    cache_write_5m: float | None    # 5-min cache write cost (optional)
    cache_write_1h: float | None    # 1-hr cache write cost (optional)
    thinking_price: float | None    # Reasoning token cost (optional)
    tier: str                       # Pricing tier name
    effective_date: str | None      # ISO date string
    notes: str | None               # Additional information
```

### ModelCapabilities

```python
from consoul.sdk import ModelCapabilities

@dataclass
class ModelCapabilities:
    supports_vision: bool = False
    supports_tools: bool = False
    supports_reasoning: bool = False
    supports_streaming: bool = False
    supports_json_mode: bool = False
    supports_caching: bool = False
    supports_batch: bool = False
```

### ModelInfo

```python
from consoul.sdk import ModelInfo

@dataclass
class ModelInfo:
    id: str                                    # Model identifier
    name: str                                  # Display name
    provider: str                              # Provider name
    context_window: str                        # Context size (e.g., "128K")
    description: str                           # Model description
    supports_vision: bool = False              # Vision support flag
    supports_tools: bool = True                # Tool support flag
    max_output_tokens: int | None = None       # Max output size
    created: str | None = None                 # Creation date
    pricing: PricingInfo | None = None         # Pricing information
    capabilities: ModelCapabilities | None = None  # Full capabilities
```

## Common Patterns

### Finding the Cheapest Model

```python
def find_cheapest_model(provider: str = None):
    """Find the most cost-effective model."""
    models = service.list_available_models(provider=provider)

    cheapest = None
    cheapest_cost = float('inf')

    for model in models:
        if model.pricing:
            # Combined input + output cost
            cost = model.pricing.input_price + model.pricing.output_price
            if cost < cheapest_cost:
                cheapest_cost = cost
                cheapest = model

    return cheapest

# Find cheapest Anthropic model
cheapest = find_cheapest_model("anthropic")
if cheapest:
    print(f"Cheapest: {cheapest.name}")
    print(f"Cost: ${cheapest.pricing.input_price + cheapest.pricing.output_price}/MTok")
```

### Comparing Pricing Across Tiers

```python
def compare_tiers(model_id: str):
    """Compare pricing across all tiers."""
    tiers = ["standard", "batch", "priority", "flex"]

    print(f"Pricing for {model_id}:")
    for tier in tiers:
        pricing = service.get_model_pricing(model_id, tier=tier)
        if pricing:
            print(f"  {tier:10s}: ${pricing.input_price:.2f} / ${pricing.output_price:.2f}")

compare_tiers("gpt-4o")
```

### Filtering by Capabilities

```python
def find_vision_models():
    """Find all models with vision support."""
    all_models = service.list_available_models()

    vision_models = []
    for model in all_models:
        caps = service.get_model_capabilities(model.id)
        if caps and caps.supports_vision:
            vision_models.append(model)

    return vision_models

# Get all vision-capable models
vision_models = find_vision_models()
for model in vision_models[:5]:
    print(f"• {model.name} ({model.provider})")
```

### Cost Estimation

```python
def estimate_cost(model_id: str, input_tokens: int, output_tokens: int, tier: str = "standard"):
    """Estimate cost for a specific usage."""
    pricing = service.get_model_pricing(model_id, tier=tier)

    if not pricing:
        return None

    # Convert tokens to millions
    input_mtok = input_tokens / 1_000_000
    output_mtok = output_tokens / 1_000_000

    # Calculate cost
    input_cost = pricing.input_price * input_mtok
    output_cost = pricing.output_price * output_mtok
    total_cost = input_cost + output_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "tier": tier
    }

# Estimate cost for 50K input + 10K output tokens
cost = estimate_cost("claude-sonnet-4-5-20250929", 50_000, 10_000)
if cost:
    print(f"Total: ${cost['total_cost']:.4f}")
```

## Provider Coverage

The registry includes models from:

| Provider | Flagship Models | Total Models (via Helicone) |
|----------|----------------|----------------------------|
| **Anthropic** | 7 | 20+ |
| **OpenAI** | 8 | 50+ |
| **Google** | 6 | 30+ |
| **Others** | - | 1,000+ |

### Supported Providers

- Anthropic (Claude)
- OpenAI (GPT, O1)
- Google (Gemini)
- Ollama (local models)
- xAI (Grok)
- Mistral AI
- Cohere
- And many more via Helicone...

## Registry Architecture

### Static Definitions

21 flagship models with complete metadata:

```
src/consoul/registry/
├── types.py           # Type definitions
├── registry.py        # Core registry with O(1) lookups
└── models/
    ├── anthropic.py   # 7 Claude models
    ├── openai.py      # 8 OpenAI models
    └── google.py      # 6 Gemini models
```

### External Integration

Helicone API integration for 1,114+ models:

```
src/consoul/registry/
└── external.py        # Helicone API client
```

**Features**:
- HTTP caching with 7-day TTL
- Automatic fallback to static definitions
- Pattern matching (equals, startsWith, includes)

### Hybrid Approach

The registry intelligently combines both sources:

1. **Static First**: Fast O(1) lookups for flagship models
2. **External Fallback**: Query Helicone for additional models
3. **Automatic Caching**: 7-day cache prevents redundant API calls
4. **Graceful Degradation**: Works offline with static definitions

## Performance

- **O(1) Lookups**: Indexed by ID, provider, author, aliases
- **Lazy Loading**: Models loaded on first access
- **HTTP Caching**: 7-day TTL reduces API calls
- **Minimal Memory**: ~500KB for 21 flagship models

## Data Freshness

### Static Definitions

Updated with each Consoul release:

- Pricing verified against official docs
- New models added as they're released
- Deprecated models marked appropriately

### Helicone API

Automatically updated:

- Pricing synced from provider APIs
- New models appear within 24-48 hours
- Cache refreshed weekly

## Examples

See [`examples/sdk/model_registry_example.py`](https://github.com/goatbytes/consoul/blob/main/examples/sdk/model_registry_example.py) for comprehensive examples:

1. **List Models**: Browse available models with filters
2. **Pricing Comparison**: Compare costs across tiers
3. **Capability Queries**: Find models by feature support
4. **Complete Metadata**: Access all model information
5. **Find Cheapest**: Locate most cost-effective options

## Best Practices

### 1. Cache Service Instance

```python
# Good - reuse service
service = ModelService.from_config(config)
for model_id in model_ids:
    pricing = service.get_model_pricing(model_id)

# Bad - creates new service each time
for model_id in model_ids:
    service = ModelService.from_config(config)  # Wasteful
    pricing = service.get_model_pricing(model_id)
```

### 2. Check for None

```python
# Always check return values
pricing = service.get_model_pricing("unknown-model")
if pricing:
    print(f"Cost: ${pricing.input_price}")
else:
    print("Model not found")
```

### 3. Use Filters

```python
# Filter early for better performance
active_models = service.list_available_models(
    provider="anthropic",
    active_only=True
)

# vs. filtering later
all_models = service.list_available_models()
active_models = [m for m in all_models if not m.deprecated]
```

### 4. Tier Fallback

```python
# Handle missing tiers gracefully
pricing = service.get_model_pricing(model_id, tier="flex")
if not pricing:
    # Fall back to standard tier
    pricing = service.get_model_pricing(model_id, tier="standard")
```

## API Reference

For complete API documentation, see:

- [`ModelService`](reference.md#modelservice)
- [`PricingInfo`](reference.md#pricinginfo)
- [`ModelCapabilities`](reference.md#modelcapabilities)
- [`ModelInfo`](reference.md#modelinfo)

## Related Documentation

- [SDK Overview](index.md)
- [Tutorial](tutorial.md)
- [Integration Guide](integration-guide.md)
- [Building Agents](agents.md)

## Contributing

To add new model definitions:

1. Create entry in appropriate `models/*.py` file
2. Include complete metadata and pricing
3. Add pricing source in docstring
4. Submit PR with verification

See [Contributing Guide](../contributing.md) for details.
