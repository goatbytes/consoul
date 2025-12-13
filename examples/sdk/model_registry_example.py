"""Example: Using the Model Registry in Consoul SDK.

This example demonstrates how to use the model registry integration in the SDK
to access comprehensive model metadata, pricing information, and capabilities.

The registry provides access to 1,114+ AI models from all major providers with
up-to-date pricing and capability information.

Features:
- List all available models with filters
- Get detailed pricing for specific tiers
- Query model capabilities
- Access complete model metadata

Usage:
    python model_registry_example.py
"""

from consoul.config import load_config
from consoul.sdk.services.model import ModelService


def list_models_example():
    """Example 1: List available models."""
    print("=" * 70)
    print("Example 1: List Available Models")
    print("=" * 70)

    # Initialize model service
    config = load_config()
    service = ModelService.from_config(config)

    # List all Anthropic models
    print("\n📋 All Anthropic Models:")
    anthropic_models = service.list_available_models(provider="anthropic")
    for model in anthropic_models[:5]:  # Show first 5
        print(f"  • {model.name} ({model.id})")
        print(f"    Context: {model.context_window}")
        print(f"    {model.description}")

    # List all models (first 10)
    print("\n📋 All Available Models (first 10):")
    all_models = service.list_available_models()
    for model in all_models[:10]:
        print(f"  • {model.name} ({model.provider}) - {model.context_window}")


def pricing_example():
    """Example 2: Get model pricing information."""
    print("\n" + "=" * 70)
    print("Example 2: Get Model Pricing")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Get standard tier pricing for Claude Sonnet 4.5
    print("\n💰 Claude Sonnet 4.5 Pricing (Standard Tier):")
    pricing = service.get_model_pricing("claude-sonnet-4-5-20250929")
    if pricing:
        print(f"  Input:  ${pricing.input_price:.2f} per million tokens")
        print(f"  Output: ${pricing.output_price:.2f} per million tokens")
        if pricing.cache_read:
            print(f"  Cache Read: ${pricing.cache_read:.2f} per million tokens")
        if pricing.cache_write_5m:
            print(
                f"  Cache Write (5min TTL): ${pricing.cache_write_5m:.2f} per million tokens"
            )
        print(f"  Tier: {pricing.tier}")
        print(f"  Effective Date: {pricing.effective_date}")
        if pricing.notes:
            print(f"  Notes: {pricing.notes}")

    # Compare pricing across tiers for GPT-4o
    print("\n💰 GPT-4o Pricing Across Tiers:")
    for tier in ["standard", "batch", "priority"]:
        pricing = service.get_model_pricing("gpt-4o", tier=tier)
        if pricing:
            print(
                f"  {tier.title():10s}: ${pricing.input_price:.2f} / ${pricing.output_price:.2f}"
            )


def capabilities_example():
    """Example 3: Query model capabilities."""
    print("\n" + "=" * 70)
    print("Example 3: Query Model Capabilities")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    models_to_check = [
        "claude-sonnet-4-5-20250929",
        "gpt-4o",
        "gemini-2-5-flash",
        "o1",
    ]

    print("\n🔍 Model Capability Comparison:")
    print(f"{'Model':<30} Vision  Tools  Reasoning  Cache  Batch")
    print("-" * 70)

    for model_id in models_to_check:
        caps = service.get_model_capabilities(model_id)
        if caps:
            print(
                f"{model_id:<30} "
                f"{'✓' if caps.supports_vision else '✗':^7} "
                f"{'✓' if caps.supports_tools else '✗':^7} "
                f"{'✓' if caps.supports_reasoning else '✗':^10} "
                f"{'✓' if caps.supports_caching else '✗':^7} "
                f"{'✓' if caps.supports_batch else '✗':^5}"
            )


def metadata_example():
    """Example 4: Get complete model metadata."""
    print("\n" + "=" * 70)
    print("Example 4: Complete Model Metadata")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    model_id = "claude-sonnet-4-5-20250929"
    print(f"\n📊 Complete Metadata for {model_id}:")

    metadata = service.get_model_metadata(model_id)
    if metadata:
        print(f"\n  Name: {metadata.name}")
        print(f"  Provider: {metadata.provider}")
        print(f"  Description: {metadata.description}")
        print(f"  Context Window: {metadata.context_window}")
        print(f"  Max Output Tokens: {metadata.max_output_tokens:,}")
        print(f"  Created: {metadata.created}")

        if metadata.capabilities:
            print("\n  Capabilities:")
            print(f"    • Vision: {metadata.capabilities.supports_vision}")
            print(f"    • Tools: {metadata.capabilities.supports_tools}")
            print(f"    • Reasoning: {metadata.capabilities.supports_reasoning}")
            print(f"    • Streaming: {metadata.capabilities.supports_streaming}")
            print(f"    • JSON Mode: {metadata.capabilities.supports_json_mode}")
            print(f"    • Caching: {metadata.capabilities.supports_caching}")
            print(f"    • Batch API: {metadata.capabilities.supports_batch}")

        if metadata.pricing:
            print("\n  Pricing (Standard Tier):")
            print(f"    • Input: ${metadata.pricing.input_price}/MTok")
            print(f"    • Output: ${metadata.pricing.output_price}/MTok")
            if metadata.pricing.cache_read:
                print(f"    • Cache Read: ${metadata.pricing.cache_read}/MTok")
            if metadata.pricing.thinking_price:
                print(
                    f"    • Thinking: ${metadata.pricing.thinking_price}/MTok"
                )


def find_cheapest_model():
    """Example 5: Find cheapest model by provider."""
    print("\n" + "=" * 70)
    print("Example 5: Find Cheapest Model by Provider")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    for provider in ["anthropic", "openai", "google"]:
        print(f"\n💵 Cheapest {provider.title()} Model:")
        models = service.list_available_models(provider=provider)

        # Find model with lowest combined input + output price
        cheapest = None
        cheapest_cost = float("inf")

        for model in models:
            if model.pricing:
                cost = model.pricing.input_price + model.pricing.output_price
                if cost < cheapest_cost:
                    cheapest_cost = cost
                    cheapest = model

        if cheapest and cheapest.pricing:
            print(f"  Model: {cheapest.name} ({cheapest.id})")
            print(
                f"  Cost: ${cheapest.pricing.input_price} + ${cheapest.pricing.output_price} = "
                f"${cheapest_cost:.2f} per MTok"
            )
            print(f"  Context: {cheapest.context_window}")


def main():
    """Run all examples."""
    print("\n🚀 Consoul SDK Model Registry Examples\n")

    try:
        # Run each example
        list_models_example()
        pricing_example()
        capabilities_example()
        metadata_example()
        find_cheapest_model()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  • Use list_available_models() to discover available models")
        print("  • Use get_model_pricing() for tier-specific pricing")
        print("  • Use get_model_capabilities() to check feature support")
        print("  • Use get_model_metadata() for complete model information")
        print("\nThe registry provides access to 1,114+ models with fresh pricing!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
