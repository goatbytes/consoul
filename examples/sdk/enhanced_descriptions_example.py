"""Example: Enhanced Local Model Descriptions.

This example demonstrates how the SDK enriches local model descriptions
with rich metadata from ollama.com instead of showing generic descriptions.

Features:
- Automatic enrichment from ollama.com library (cached for 24 hours)
- Falls back to generic description if ollama.com is unavailable
- Includes model size information in all descriptions
- Works seamlessly with EnhancedModelPicker in the TUI

Requirements:
- At least one Ollama model installed locally
- beautifulsoup4 (pip install beautifulsoup4)

Usage:
    python enhanced_descriptions_example.py
"""

from consoul.config import load_config
from consoul.sdk.services.model import ModelService


def compare_descriptions() -> None:
    """Example 1: Compare enhanced vs generic descriptions."""
    print("=" * 70)
    print("Example 1: Enhanced Descriptions")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    print("\n🎨 With Enhanced Descriptions (default):\n")
    enhanced_models = service.list_ollama_models(enrich_descriptions=True)

    if not enhanced_models:
        print("⚠️  No Ollama models found!")
        print("   Make sure Ollama is running and has models installed.")
        return

    for model in enhanced_models[:5]:
        print(f"  {model.name}")
        print(f"    {model.description}")
        print()

    print("\n📝 Without Enhanced Descriptions:\n")
    generic_models = service.list_ollama_models(enrich_descriptions=False)

    for model in generic_models[:5]:
        print(f"  {model.name}")
        print(f"    {model.description}")
        print()


def show_library_coverage() -> None:
    """Example 2: Show which models have rich descriptions."""
    print("=" * 70)
    print("Example 2: Library Coverage")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    print("\n🔍 Checking description coverage...\n")

    # Get models with enrichment
    models = service.list_ollama_models(enrich_descriptions=True)

    enriched = 0
    generic = 0

    for model in models:
        if "Local Ollama model" in model.description:
            generic += 1
            print(f"  ⚠️  {model.name:<30} (generic description)")
        else:
            enriched += 1
            print(f"  ✓  {model.name:<30} (enriched)")

    total = enriched + generic
    coverage = (enriched / total * 100) if total > 0 else 0

    print(f"\n📊 Coverage: {enriched}/{total} models ({coverage:.1f}%)")

    if generic > 0:
        print("\n💡 Note: Some models may not be in the ollama.com library catalog.")
        print("   Custom or private models will show generic descriptions.")


def demonstrate_caching() -> None:
    """Example 3: Demonstrate 24-hour caching."""
    print("\n" + "=" * 70)
    print("Example 3: Description Caching")
    print("=" * 70)

    import time

    config = load_config()
    service = ModelService.from_config(config)

    print("\n⏱️  Measuring description fetch time...\n")

    # First call - may fetch from ollama.com
    start = time.time()
    models1 = service.list_ollama_models(enrich_descriptions=True)
    time1 = time.time() - start

    print(f"  First call:  {time1:.3f}s ({len(models1)} models)")

    # Second call - should use cache
    start = time.time()
    models2 = service.list_ollama_models(enrich_descriptions=True)
    time2 = time.time() - start

    print(f"  Second call: {time2:.3f}s ({len(models2)} models)")

    if time2 < time1:
        speedup = (time1 / time2) if time2 > 0 else float("inf")
        print(f"\n✨ Cache speedup: {speedup:.1f}x faster!")

    print("\n💡 Cache Details:")
    print("    • Descriptions cached for 24 hours")
    print("    • Cache location: ~/.consoul/cache/ollama_library_library.json")
    print("    • Automatic refresh after expiry")


def show_tui_integration() -> None:
    """Example 4: Show how this integrates with the TUI."""
    print("\n" + "=" * 70)
    print("Example 4: TUI Integration")
    print("=" * 70)

    print(
        """
🖥️  Enhanced Model Picker Integration:

The EnhancedModelPicker automatically uses rich descriptions:

```python
from consoul.config import load_config
from consoul.config.models import Provider
from consoul.sdk.services.model import ModelService
from consoul.tui.widgets.enhanced_model_picker import EnhancedModelPicker

# Create service
config = load_config()
model_service = ModelService.from_config(config)

# Show picker with enhanced descriptions
picker = EnhancedModelPicker(
    current_model="llama3.2",
    current_provider=Provider.OLLAMA,
    model_service=model_service,
)
```

The Local tab will show:
  • Rich, descriptive model names from ollama.com
  • Model sizes in GB
  • Provider badges (Ollama, GGUF, MLX, HuggingFace)
  • Vision capability indicators

💡 To test the picker:
    poetry run python test_enhanced_picker.py
"""
    )


def main() -> None:
    """Run all examples."""
    print("\n🚀 Consoul SDK Enhanced Descriptions Examples\n")

    try:
        # Run each example
        compare_descriptions()
        show_library_coverage()
        demonstrate_caching()
        show_tui_integration()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  • list_ollama_models() enriches descriptions by default")
        print("  • Uses ollama.com library with 24-hour caching")
        print("  • Falls back to generic descriptions gracefully")
        print("  • Descriptions include model size information")
        print("  • Seamlessly integrates with EnhancedModelPicker TUI")
        print("  • Set enrich_descriptions=False to disable")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
