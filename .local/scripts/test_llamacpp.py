#!/usr/bin/env python3
"""Test llama.cpp with existing GGUF models."""

import sys
from pathlib import Path


def find_gguf_models():
    """Find GGUF models in HuggingFace cache."""
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"

    print("Searching for GGUF models in HuggingFace cache...")
    print(f"Cache directory: {cache_dir}")
    print("=" * 80)

    gguf_models = []

    for repo_dir in cache_dir.glob("models--*"):
        for gguf_file in repo_dir.rglob("*.gguf"):
            # Resolve symlink to get actual file
            actual_file = gguf_file.resolve()
            size_gb = actual_file.stat().st_size / (1024**3)

            # Extract quantization type from filename
            name = gguf_file.name
            quant = "unknown"
            for q in ["Q4", "Q5", "Q8", "IQ4", "IQ3", "F16", "F32"]:
                if q.lower() in name.lower():
                    quant = q
                    break

            model_info = {
                "path": str(gguf_file),
                "name": gguf_file.name,
                "size_gb": size_gb,
                "quant": quant,
                "repo": repo_dir.name.replace("models--", "").replace("--", "/"),
            }
            gguf_models.append(model_info)

    # Sort by size (smallest first for faster testing)
    gguf_models.sort(key=lambda m: m["size_gb"])

    print(f"\nFound {len(gguf_models)} GGUF models:\n")
    for i, model in enumerate(gguf_models[:10], 1):  # Show first 10
        print(
            f"{i:2d}. {model['name'][:60]:<60s} {model['size_gb']:>6.1f}GB {model['quant']}"
        )

    if len(gguf_models) > 10:
        print(f"\n... and {len(gguf_models) - 10} more")

    return gguf_models


def test_llamacpp_installation():
    """Test if llama-cpp-python is installed."""
    print("\n" + "=" * 80)
    print("TEST 1: Check llama-cpp-python Installation")
    print("=" * 80)

    try:
        import llama_cpp

        print(f"✓ llama-cpp-python installed: {llama_cpp.__version__}")
        return True
    except ImportError:
        print("✗ llama-cpp-python not installed")
        print("\nInstall with:")
        print("  # CPU only:")
        print("  pip install llama-cpp-python")
        print("\n  # macOS with Metal GPU acceleration:")
        print('  CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python')
        return False


def test_langchain_llamacpp():
    """Test if LangChain llama.cpp integration is available."""
    print("\n" + "=" * 80)
    print("TEST 2: Check LangChain Integration")
    print("=" * 80)

    try:
        import importlib.util

        if importlib.util.find_spec("langchain_community.chat_models") is not None:
            print("✓ ChatLlamaCpp available from langchain-community")
        return True
    except ImportError as e:
        print(f"✗ ChatLlamaCpp not available: {e}")
        print("\nInstall with:")
        print("  pip install langchain-community")
        return False


def test_model_loading(model_path: str, model_name: str):
    """Test loading and using a GGUF model."""
    print("\n" + "=" * 80)
    print("TEST 3: Load and Test Model")
    print("=" * 80)
    print(f"Model: {model_name}")
    print(f"Path: {model_path}")

    try:
        import multiprocessing

        from langchain_community.chat_models import ChatLlamaCpp
        from langchain_core.messages import HumanMessage

        print("\nInitializing ChatLlamaCpp...")
        print("  (This may take 10-30 seconds for large models)")

        llm = ChatLlamaCpp(
            model_path=model_path,
            n_ctx=4096,  # Context window
            n_gpu_layers=-1,  # Use all GPU layers (Metal on macOS)
            n_batch=512,  # Batch size for prompt processing
            n_threads=multiprocessing.cpu_count() - 1,
            temperature=0.7,
            max_tokens=100,
            verbose=False,  # Set to True to see llama.cpp logs
        )

        print("✓ Model loaded successfully!")

        # Test generation
        print("\nTesting text generation...")
        messages = [HumanMessage(content="What is Python? Answer in one sentence.")]

        print("Generating response...")
        response = llm.invoke(messages)

        print("\n" + "-" * 80)
        print("Prompt: What is Python? Answer in one sentence.")
        print(f"Response: {response.content}")
        print("-" * 80)

        print("\n✅ TEST 3 PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 80)
    print("LLAMA.CPP GGUF MODEL TEST")
    print("=" * 80)

    # Find GGUF models
    gguf_models = find_gguf_models()

    if not gguf_models:
        print("\n❌ No GGUF models found in HuggingFace cache!")
        print("\nYou need GGUF format models to use llama.cpp.")
        print("Your safetensors models (Qwen3-8B) need to be converted.")
        print("See LLAMACPP_SOLUTION.md for conversion instructions.")
        return 1

    # Test installation
    if not test_llamacpp_installation():
        return 1

    if not test_langchain_llamacpp():
        return 1

    # Test with smallest model (fastest)
    smallest_model = gguf_models[0]
    print(f"\n\nUsing smallest model for testing: {smallest_model['name']}")
    print(f"Size: {smallest_model['size_gb']:.1f}GB")
    print("\nPress Enter to continue, or Ctrl+C to cancel...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
        return 130

    success = test_model_loading(smallest_model["path"], smallest_model["name"])

    print("\n" + "=" * 80)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("\nllama.cpp works with your GGUF models!")
        print("This is the solution for local HuggingFace execution on macOS.")
        print("\nNext steps:")
        print("1. Review LLAMACPP_SOLUTION.md")
        print("2. Integrate ChatLlamaCpp into Consoul")
        print("3. Add as alternative to transformers-based loading")
    else:
        print("⚠️  TESTS FAILED")
        print("See error details above.")

    print("=" * 80)

    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests cancelled by user")
        sys.exit(130)
