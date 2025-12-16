"""Example: Discovering Locally Installed Ollama Models.

This example demonstrates how to use the SDK to efficiently discover
and list locally installed Ollama models on your device.

Features:
- Fast discovery of installed models (no catalog overhead)
- Optional detailed context window fetching
- Model size and capability information
- Comparison with cloud models

Requirements:
- Ollama installed and running (http://localhost:11434)
- At least one model pulled (e.g., `ollama pull llama3.2`)

Usage:
    python ollama_discovery_example.py
"""

from consoul.config import load_config
from consoul.sdk.services.model import ModelService


def list_local_models():
    """Example 1: List all locally installed Ollama models."""
    print("=" * 70)
    print("Example 1: List Local Ollama Models")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Quick discovery (context window from metadata, may be "?")
    print("\n🔍 Discovering local Ollama models...")
    local_models = service.list_ollama_models()

    if not local_models:
        print("\n⚠️  No Ollama models found!")
        print("   Make sure Ollama is running and you have models installed.")
        print("   Try: ollama pull llama3.2")
        return

    print(f"\n📦 Found {len(local_models)} installed model(s):\n")
    for model in local_models:
        print(f"  • {model.name}")
        print(f"    Context: {model.context_window}")
        print(f"    {model.description}")
        if model.supports_vision:
            print("    ▣ Vision support detected")
        print()


def list_local_models_detailed():
    """Example 2: Get detailed context information (slower)."""
    print("=" * 70)
    print("Example 2: Detailed Model Information")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Detailed discovery with context fetching (slower, hits /api/show per model)
    print("\n🔍 Fetching detailed model information...")
    print("   (This may take a few seconds per model)\n")

    detailed_models = service.list_ollama_models(include_context=True)

    if not detailed_models:
        print("⚠️  No Ollama models found!")
        return

    print(f"📊 Detailed info for {len(detailed_models)} model(s):\n")
    for model in detailed_models:
        print(f"  {model.name}")
        print(f"  ├─ Context Window: {model.context_window}")
        print(f"  ├─ Description: {model.description}")
        print(f"  └─ Vision: {'Yes' if model.supports_vision else 'No'}")
        print()


def compare_local_vs_cloud():
    """Example 3: Compare local models with cloud alternatives."""
    print("=" * 70)
    print("Example 3: Compare Local vs Cloud Models")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Get local Ollama models
    local_models = service.list_ollama_models()

    # Get some cloud models for comparison
    cloud_models = service.list_available_models(provider="anthropic")[:3]

    print("\n🖥️  Local Ollama Models:")
    print("-" * 70)
    if local_models:
        for model in local_models:
            print(f"  {model.name:<30} {model.context_window:>10}")
    else:
        print("  (No local models found)")

    print("\n☁️  Cloud Models (Anthropic sample):")
    print("-" * 70)
    for model in cloud_models:
        pricing = model.pricing
        price_str = (
            f"${pricing.input_price:.2f}/${pricing.output_price:.2f}"
            if pricing
            else "N/A"
        )
        print(f"  {model.name:<30} {model.context_window:>10}  {price_str:>15}")

    print("\n💡 Tip: Local models are free to run but require local resources.")
    print("    Cloud models require API keys and have per-token costs.")


def check_specific_model():
    """Example 4: Check if specific model is installed."""
    print("\n" + "=" * 70)
    print("Example 4: Check for Specific Model")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Models to check
    target_models = ["llama3.2:latest", "qwen2.5-coder:7b", "mistral:latest"]

    local_models = service.list_ollama_models()
    installed_names = {model.id for model in local_models}

    print("\n🔎 Checking for specific models:\n")
    for target in target_models:
        status = "✓ Installed" if target in installed_names else "✗ Not installed"
        print(f"  {target:<25} {status}")

    print("\n💡 Tip: Install models with: ollama pull <model_name>")


def main():
    """Run all examples."""
    print("\n🚀 Consoul SDK Ollama Discovery Examples\n")

    try:
        # Run each example
        list_local_models()
        list_local_models_detailed()
        compare_local_vs_cloud()
        check_specific_model()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  • Use list_ollama_models() for fast local model discovery")
        print("  • Add include_context=True for detailed info (slower)")
        print("  • Returns same ModelInfo type as other SDK methods")
        print("  • No catalog overhead - direct Ollama API query")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
