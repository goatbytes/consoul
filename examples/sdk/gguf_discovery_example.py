"""Example: Discovering Locally Installed GGUF Models.

This example demonstrates how to use the SDK to efficiently discover
and list locally installed GGUF models on your device.

Features:
- Fast discovery using HuggingFace scan_cache_dir() API
- Quantization information (Q4, Q8, etc.)
- Model size and repo identification
- Comparison with cloud models

Requirements:
- At least one GGUF model downloaded from HuggingFace or stored locally
- HuggingFace Hub library (pip install huggingface-hub)

GGUF models can be used with llama.cpp for efficient local inference.

Usage:
    python gguf_discovery_example.py
"""

from consoul.config import load_config
from consoul.sdk.services.model import ModelService


def list_local_models() -> None:
    """Example 1: List all locally installed GGUF models."""
    print("=" * 70)
    print("Example 1: List Local GGUF Models")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Quick discovery using HuggingFace scan_cache_dir()
    print("\n🔍 Discovering local GGUF models...")
    local_models = service.list_gguf_models()

    if not local_models:
        print("\n⚠️  No GGUF models found!")
        print("   Make sure you have GGUF models downloaded.")
        print("   Try: huggingface-cli download TheBloke/Llama-2-7B-Chat-GGUF")
        return

    print(f"\n📦 Found {len(local_models)} installed model(s):\n")
    for model in local_models:
        print(f"  • {model.name}")
        print(f"    {model.description}")
        if model.supports_vision:
            print("    ▣ Vision support detected")
        print()


def show_quantization_details() -> None:
    """Example 2: Show quantization details and recommendations."""
    print("=" * 70)
    print("Example 2: Quantization Details")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    print("\n🔍 Analyzing GGUF quantizations...\n")
    models = service.list_gguf_models()

    if not models:
        print("⚠️  No GGUF models found!")
        return

    # Group by quantization
    from collections import defaultdict

    by_quant: dict[str, list[str]] = defaultdict(list)
    for model in models:
        # Extract quant from description
        desc = model.description
        if "quant)" in desc:
            quant = desc.split("quant)")[0].split(",")[-1].strip()
            by_quant[quant].append(model.name)

    print("📊 Models by quantization:\n")
    for quant in sorted(by_quant.keys()):
        model_list = by_quant[quant]
        print(
            f"  {quant} ({len(model_list)} model{'s' if len(model_list) > 1 else ''}):"
        )
        for model_name in model_list[:3]:  # Show first 3
            print(f"    - {model_name}")
        if len(model_list) > 3:
            print(f"    ... and {len(model_list) - 3} more")
        print()

    print("💡 Quantization Guide:")
    print("    • Q2/Q3: Smallest, fastest, lower quality")
    print("    • Q4: Good balance (recommended)")
    print("    • Q5/Q6: Better quality, larger size")
    print("    • Q8: Best quality, largest size")
    print("    • F16/F32: Full precision (very large)")


def compare_local_vs_cloud() -> None:
    """Example 3: Compare local GGUF models with cloud alternatives."""
    print("\n" + "=" * 70)
    print("Example 3: Compare Local vs Cloud Models")
    print("=" * 70)

    config = load_config()
    service = ModelService.from_config(config)

    # Get local GGUF models
    local_models = service.list_gguf_models()

    # Get some cloud models for comparison
    cloud_models = service.list_available_models(provider="openai")[:3]

    print("\n🖥️  Local GGUF Models:")
    print("-" * 70)
    if local_models:
        for model in local_models[:5]:  # Show first 5
            # Extract size from description
            desc = model.description
            if "GB" in desc:
                size_info = desc.split("(")[1].split(")")[0]
                print(f"  {model.name:<40} {size_info}")
        if len(local_models) > 5:
            print(f"  ... and {len(local_models) - 5} more")
    else:
        print("  (No local models found)")

    print("\n☁️  Cloud Models (OpenAI sample):")
    print("-" * 70)
    for model in cloud_models:
        pricing = model.pricing
        price_str = (
            f"${pricing.input_price:.2f}/${pricing.output_price:.2f}"
            if pricing
            else "N/A"
        )
        print(f"  {model.name:<40} {price_str}")

    print("\n💡 Tip: Local GGUF models are:")
    print("    ✓ Free to run (no API costs)")
    print("    ✓ Private (all processing on-device)")
    print("    ✓ Cross-platform (works on CPU/GPU)")
    print("    ✓ Flexible quantization options")
    print("    ✗ Require local disk space")
    print("    ✗ Slower than cloud APIs")


def check_gguf_cache_locations() -> None:
    """Example 4: Show where GGUF models are stored."""
    print("\n" + "=" * 70)
    print("Example 4: GGUF Model Cache Locations")
    print("=" * 70)

    from pathlib import Path

    cache_dirs = [
        ("HuggingFace Hub Cache", Path.home() / ".cache" / "huggingface" / "hub"),
        ("LM Studio Models", Path.home() / ".lmstudio" / "models"),
    ]

    print("\n📁 GGUF models are stored in these locations:\n")
    for name, path in cache_dirs:
        exists = "✓" if path.exists() else "✗"
        print(f"  {exists} {name}")
        print(f"    {path}")
        if path.exists():
            # Count GGUF files
            try:
                gguf_count = len(list(path.rglob("*.gguf")))
                if gguf_count > 0:
                    print(
                        f"    ({gguf_count} .gguf file{'s' if gguf_count != 1 else ''})"
                    )
            except Exception:
                pass
        print()

    print("💡 Tip: The SDK uses HuggingFace scan_cache_dir() for efficient scanning")


def performance_comparison() -> None:
    """Example 5: Compare discovery performance."""
    print("\n" + "=" * 70)
    print("Example 5: Discovery Performance")
    print("=" * 70)

    import time

    config = load_config()
    service = ModelService.from_config(config)

    print("\n⏱️  Measuring discovery time...\n")

    # Time GGUF discovery (optimized with scan_cache_dir)
    start = time.time()
    gguf_models = service.list_gguf_models()
    gguf_time = time.time() - start

    print(
        f"  GGUF Discovery (scan_cache_dir): {gguf_time:.3f}s ({len(gguf_models)} models)"
    )

    # Time Ollama discovery (API call)
    start = time.time()
    ollama_models = service.list_ollama_models()
    ollama_time = time.time() - start

    print(
        f"  Ollama Discovery (API):          {ollama_time:.3f}s ({len(ollama_models)} models)"
    )

    # Time MLX discovery
    start = time.time()
    mlx_models = service.list_mlx_models()
    mlx_time = time.time() - start

    print(
        f"  MLX Discovery (scan_cache_dir):  {mlx_time:.3f}s ({len(mlx_models)} models)"
    )

    print("\n💡 Observations:")
    print("    • HuggingFace scan_cache_dir() is much faster than recursive glob")
    print("    • All methods avoid loading full model catalog")
    print("    • Local discovery = zero network latency")


def main() -> None:
    """Run all examples."""
    print("\n🚀 Consoul SDK GGUF Discovery Examples\n")

    try:
        # Run each example
        list_local_models()
        show_quantization_details()
        compare_local_vs_cloud()
        check_gguf_cache_locations()
        performance_comparison()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  • Use list_gguf_models() for fast local model discovery")
        print("  • Optimized with HuggingFace scan_cache_dir() API")
        print("  • Returns same ModelInfo type as other SDK methods")
        print("  • No catalog overhead - direct cache scanning")
        print("  • Includes quantization info (Q4, Q8, etc.)")
        print("  • Works with HF Hub and LM Studio")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
