"""Example: Discovering Locally Installed MLX Models.

This example demonstrates how to use the SDK to efficiently discover
and list locally installed Apple MLX models on your device.

Features:
- Fast discovery using HuggingFace scan_cache_dir() API
- Model size information
- Multiple cache directory scanning
- Comparison with cloud models

Requirements:
- Apple Silicon Mac (M1/M2/M3/M4)
- At least one MLX model downloaded from HuggingFace
- HuggingFace Hub library (pip install huggingface-hub)

Usage:
    python mlx_discovery_example.py
"""

from consoul.config import load_config
from consoul.sdk.services.model import ModelService


def list_local_models() -> None:
    """Example 1: List all locally installed MLX models."""
    print("=" * 70)
    print("Example 1: List Local MLX Models")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Quick discovery using HuggingFace scan_cache_dir()
    print("\n🔍 Discovering local MLX models...")
    local_models = service.list_mlx_models()

    if not local_models:
        print("\n⚠️  No MLX models found!")
        print("   Make sure you have MLX models downloaded from HuggingFace.")
        print(
            "   Try: huggingface-cli download mlx-community/Llama-3.2-3B-Instruct-4bit"
        )
        return

    print(f"\n📦 Found {len(local_models)} installed model(s):\n")
    for model in local_models:
        print(f"  • {model.name}")
        print(f"    {model.description}")
        if model.supports_vision:
            print("    ▣ Vision support detected")
        print()


def compare_local_vs_cloud() -> None:
    """Example 2: Compare local MLX models with cloud alternatives."""
    print("=" * 70)
    print("Example 2: Compare Local vs Cloud Models")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Get local MLX models
    local_models = service.list_mlx_models()

    # Get some cloud models for comparison
    cloud_models = service.list_available_models(provider="anthropic")[:3]

    print("\n🖥️  Local MLX Models:")
    print("-" * 70)
    if local_models:
        for model in local_models:
            # Extract size from description
            size_info = model.description.split("(")[1].split(")")[0]
            print(f"  {model.name:<50} {size_info:>10}")
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
        print(f"  {model.name:<50} {price_str:>15}")

    print("\n💡 Tip: Local MLX models are:")
    print("    ✓ Free to run (no API costs)")
    print("    ✓ Private (all processing on-device)")
    print("    ✓ Fast on Apple Silicon (optimized for unified memory)")
    print("    ✗ Require local disk space")
    print("    ✗ Limited to Apple Silicon Macs")


def check_mlx_cache_locations() -> None:
    """Example 3: Show where MLX models are stored."""
    print("\n" + "=" * 70)
    print("Example 3: MLX Model Cache Locations")
    print("=" * 70)

    from pathlib import Path

    cache_dirs = [
        ("HuggingFace Hub Cache", Path.home() / ".cache" / "huggingface" / "hub"),
        ("MLX Local Cache", Path.home() / ".cache" / "mlx"),
        ("LM Studio Models", Path.home() / ".lmstudio" / "models"),
    ]

    print("\n📁 MLX models are stored in these locations:\n")
    for name, path in cache_dirs:
        exists = "✓" if path.exists() else "✗"
        print(f"  {exists} {name}")
        print(f"    {path}")
        if path.exists():
            # Count subdirectories
            try:
                model_count = len(list(path.iterdir()))
                print(f"    ({model_count} items)")
            except Exception:
                pass
        print()

    print("💡 Tip: The SDK uses HuggingFace scan_cache_dir() for efficient scanning")


def performance_comparison() -> None:
    """Example 4: Compare discovery performance."""
    print("\n" + "=" * 70)
    print("Example 4: Discovery Performance")
    print("=" * 70)

    import time

    from consoul.config import load_config
    from consoul.sdk.services.model import ModelService

    config = load_config()
    service = ModelService.from_config(config)

    print("\n⏱️  Measuring discovery time...\n")

    # Time MLX discovery (optimized with scan_cache_dir)
    start = time.time()
    mlx_models = service.list_mlx_models()
    mlx_time = time.time() - start

    print(
        f"  MLX Discovery (scan_cache_dir): {mlx_time:.3f}s ({len(mlx_models)} models)"
    )

    # Time Ollama discovery (API call)
    start = time.time()
    ollama_models = service.list_ollama_models()
    ollama_time = time.time() - start

    print(
        f"  Ollama Discovery (API):         {ollama_time:.3f}s ({len(ollama_models)} models)"
    )

    print("\n💡 Observations:")
    print("    • HuggingFace scan_cache_dir() is much faster than recursive glob")
    print("    • Both methods avoid loading full model catalog")
    print("    • Local discovery = zero network latency")


def main() -> None:
    """Run all examples."""
    print("\n🚀 Consoul SDK MLX Discovery Examples\n")

    try:
        # Run each example
        list_local_models()
        compare_local_vs_cloud()
        check_mlx_cache_locations()
        performance_comparison()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  • Use list_mlx_models() for fast local model discovery")
        print("  • Optimized with HuggingFace scan_cache_dir() API")
        print("  • Returns same ModelInfo type as other SDK methods")
        print("  • No catalog overhead - direct cache scanning")
        print("  • Works with HF Hub, ~/.cache/mlx, and LM Studio")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
