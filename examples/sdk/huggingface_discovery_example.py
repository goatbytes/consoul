"""Example: Discovering Locally Cached HuggingFace Models.

This example demonstrates how to use the SDK to efficiently discover
and list locally cached HuggingFace models from the Hub.

Features:
- Fast discovery using HuggingFace scan_cache_dir() API
- Model type detection (safetensors, pytorch, flax)
- Filters out MLX and GGUF-only models
- Size and revision information

Requirements:
- At least one HuggingFace model downloaded to cache
- HuggingFace Hub library (pip install huggingface-hub)

Usage:
    python huggingface_discovery_example.py
"""

from consoul.config import load_config
from consoul.sdk.services.model import ModelService


def list_local_models() -> None:
    """Example 1: List all locally cached HuggingFace models."""
    print("=" * 70)
    print("Example 1: List Local HuggingFace Models")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Quick discovery using HuggingFace scan_cache_dir()
    print("\n🔍 Discovering local HuggingFace models...")
    local_models = service.list_huggingface_models()

    if not local_models:
        print("\n⚠️  No HuggingFace models found!")
        print("   Make sure you have models downloaded to HuggingFace cache.")
        print("   Try: huggingface-cli download meta-llama/Llama-3.2-1B-Instruct")
        return

    print(f"\n📦 Found {len(local_models)} cached model(s):\n")
    for model in local_models:
        print(f"  • {model.name}")
        print(f"    {model.description}")
        if model.supports_vision:
            print("    ▣ Vision support detected")
        print()


def show_model_types() -> None:
    """Example 2: Show models grouped by type."""
    print("=" * 70)
    print("Example 2: Models by Type")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    print("\n🔍 Analyzing model types...\n")
    models = service.list_huggingface_models()

    if not models:
        print("⚠️  No HuggingFace models found!")
        return

    # Group by model type
    from collections import defaultdict

    by_type: dict[str, list[str]] = defaultdict(list)
    for model in models:
        # Extract type from description
        desc = model.description
        if "safetensors)" in desc:
            model_type = "safetensors"
        elif "pytorch)" in desc:
            model_type = "pytorch"
        elif "flax)" in desc:
            model_type = "flax"
        else:
            model_type = "unknown"

        by_type[model_type].append(model.name)

    print("📊 Models by format:\n")
    for model_type in sorted(by_type.keys()):
        model_list = by_type[model_type]
        print(
            f"  {model_type.title()} ({len(model_list)} model{'s' if len(model_list) > 1 else ''}):"
        )
        for model_name in model_list[:3]:  # Show first 3
            print(f"    - {model_name}")
        if len(model_list) > 3:
            print(f"    ... and {len(model_list) - 3} more")
        print()

    print("💡 Model Format Guide:")
    print("    • Safetensors: Modern, safe format (recommended)")
    print("    • PyTorch: Traditional .bin files")
    print("    • Flax: JAX/Flax framework format")


def compare_local_vs_cloud() -> None:
    """Example 3: Compare local HuggingFace models with cloud alternatives."""
    print("\n" + "=" * 70)
    print("Example 3: Compare Local vs Cloud Models")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Get local HuggingFace models
    local_models = service.list_huggingface_models()

    # Get some cloud models for comparison
    cloud_models = service.list_available_models(provider="anthropic")[:3]

    print("\n🖥️  Local HuggingFace Models:")
    print("-" * 70)
    if local_models:
        for model in local_models[:5]:  # Show first 5
            # Extract size from description
            desc = model.description
            if "GB" in desc:
                size_info = desc.split("(")[1].split(")")[0].split(",")[0]
                print(f"  {model.name:<40} {size_info:>10}")
        if len(local_models) > 5:
            print(f"  ... and {len(local_models) - 5} more")
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
        print(f"  {model.name:<40} {price_str:>15}")

    print("\n💡 Tip: Local HuggingFace models:")
    print("    ✓ Can be loaded with transformers library")
    print("    ✓ No API costs for inference")
    print("    ✓ Private (all processing on-device)")
    print("    ✓ Flexible (fine-tune, modify, etc.)")
    print("    ✗ Require local disk space")
    print("    ✗ Require GPU/CPU for inference")


def check_cache_location() -> None:
    """Example 4: Show where HuggingFace models are cached."""
    print("\n" + "=" * 70)
    print("Example 4: HuggingFace Cache Location")
    print("=" * 70)

    from pathlib import Path

    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"

    print("\n📁 HuggingFace models are cached at:\n")
    exists = "✓" if cache_dir.exists() else "✗"
    print(f"  {exists} {cache_dir}")

    if cache_dir.exists():
        # Count model directories
        try:
            model_dirs = [
                d
                for d in cache_dir.iterdir()
                if d.is_dir() and d.name.startswith("models--")
            ]
            print(f"    ({len(model_dirs)} model repositories)")

            # Calculate total size
            from consoul.config import load_config
            from consoul.sdk.services.model import ModelService

            service = ModelService.from_config(load_config())
            models = service.list_huggingface_models()

            if models:
                total_size = sum(
                    float(m.description.split("(")[1].split("GB")[0])
                    for m in models
                    if "GB" in m.description
                )
                print(f"    ({total_size:.1f}GB total)")
        except Exception:
            pass
        print()

    print("💡 Cache Management:")
    print("    • View cache: huggingface-cli scan-cache")
    print("    • Delete cache: huggingface-cli delete-cache")
    print("    • Set location: export HF_HOME=/path/to/cache")


def performance_comparison() -> None:
    """Example 5: Compare discovery performance."""
    print("\n" + "=" * 70)
    print("Example 5: Discovery Performance")
    print("=" * 70)

    import time

    config = load_config()
    service = ModelService.from_config(config)

    print("\n⏱️  Measuring discovery time...\n")

    # Time HuggingFace discovery
    start = time.time()
    hf_models = service.list_huggingface_models()
    hf_time = time.time() - start

    print(
        f"  HuggingFace Discovery (scan_cache_dir): {hf_time:.3f}s ({len(hf_models)} models)"
    )

    # Time other local discoveries
    start = time.time()
    gguf_models = service.list_gguf_models()
    gguf_time = time.time() - start

    print(
        f"  GGUF Discovery (scan_cache_dir):        {gguf_time:.3f}s ({len(gguf_models)} models)"
    )

    start = time.time()
    mlx_models = service.list_mlx_models()
    mlx_time = time.time() - start

    print(
        f"  MLX Discovery (scan_cache_dir):         {mlx_time:.3f}s ({len(mlx_models)} models)"
    )

    start = time.time()
    ollama_models = service.list_ollama_models()
    ollama_time = time.time() - start

    print(
        f"  Ollama Discovery (API):                 {ollama_time:.3f}s ({len(ollama_models)} models)"
    )

    print("\n💡 Observations:")
    print("    • HuggingFace scan_cache_dir() is very efficient")
    print("    • All local methods avoid loading full model catalog")
    print("    • Local discovery = zero network latency")
    print("    • Filters prevent duplicate discoveries (MLX, GGUF)")


def main() -> None:
    """Run all examples."""
    print("\n🚀 Consoul SDK HuggingFace Discovery Examples\n")

    try:
        # Run each example
        list_local_models()
        show_model_types()
        compare_local_vs_cloud()
        check_cache_location()
        performance_comparison()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  • Use list_huggingface_models() for fast cache discovery")
        print("  • Optimized with HuggingFace scan_cache_dir() API")
        print("  • Returns same ModelInfo type as other SDK methods")
        print("  • Filters out MLX and GGUF-only models")
        print("  • Includes model type info (safetensors, pytorch, flax)")
        print("  • Works with HuggingFace Hub cache")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
