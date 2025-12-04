#!/usr/bin/env python3
"""Test script for HuggingFace and alternative providers.

This script tests current options for using LLM models, including:
- HuggingFace (now paid only)
- Free alternatives (Groq, Ollama, MLX)
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def main():
    """Main test function."""
    print()
    print("=" * 70)
    print("Consoul LLM Provider Test")
    print("=" * 70)
    print()

    print("⚠️  IMPORTANT: HuggingFace Inference API Update (2024)")
    print()
    print("The old HuggingFace endpoint has been DEPRECATED.")
    print("Old endpoint: https://api-inference.huggingface.co (returns 410)")
    print("New endpoint: https://router.huggingface.co (FREE tier available)")
    print()
    print("✅ HuggingFace Serverless Inference is STILL FREE!")
    print("   - Rate limits: ~few hundred requests/hour")
    print("   - Update packages if seeing 410 errors")
    print("   - Only works with models deployed by Inference Providers")
    print()
    print("Free alternatives:")
    print("  1. Groq (FREE - fastest, recommended)")
    print("  2. Ollama (FREE - local, unlimited)")
    print("  3. MLX (FREE - Apple Silicon)")
    print()
    print("See HUGGINGFACE_SETUP.md for complete guide.")
    print()
    print("=" * 70)
    print()

    # Check what's available
    results = {}

    # Test 1: HuggingFace Token (still needed for serverless inference/gated models)
    print("1. Checking HuggingFace Token...")
    hf_token = (
        os.getenv("HUGGINGFACEHUB_API_TOKEN")
        or os.getenv("HUGGINGFACE_API_KEY")
        or os.getenv("HF_TOKEN")
    )
    if hf_token:
        print(f"   ✓ Token found: {hf_token[:8]}...{hf_token[-4:]}")
        print("   ✅ Can use HuggingFace Serverless Inference (FREE tier)")
        print("   (i) Only models deployed by Inference Providers work")
        print("   (i) Check model page for 'Inference Providers' section")
        results["huggingface_token"] = True
    else:
        print("   ❌ No HuggingFace token found")
        print("   (i) Required for HuggingFace serverless inference")
        print("   (i) Not required for Groq/Ollama/MLX")
        results["huggingface_token"] = False
    print()

    # Test 2: Groq (Free alternative)
    print("2. Checking Groq API...")
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print(f"   ✓ Groq API key found: {groq_key[:8]}...{groq_key[-4:]}")
        print("   ✓ Groq is FREE and FAST - recommended alternative")
        print("   Models: llama-3.1-8b-instant, mixtral-8x7b, gemma2-9b")
        results["groq"] = True

        # Test Groq
        try:
            test_groq()
            results["groq_working"] = True
        except Exception as e:
            print(f"   ❌ Groq test failed: {e}")
            results["groq_working"] = False
    else:
        print("   ❌ No Groq API key found")
        print("   📝 Get free key at: https://console.groq.com")
        results["groq"] = False
    print()

    # Test 3: Ollama (Local)
    print("3. Checking Ollama (Local)...")
    try:
        import subprocess

        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print("   ✓ Ollama is installed and running")
            models = [
                line.split()[0]
                for line in result.stdout.split("\n")[1:]
                if line.strip()
            ]
            if models:
                print(f"   ✓ Available models: {', '.join(models[:5])}")
                results["ollama"] = True
            else:
                print("   ⚠️  Ollama installed but no models found")
                print("   📝 Pull a model: ollama pull llama3.1:8b")
                results["ollama"] = False
        else:
            print("   ❌ Ollama not responding")
            results["ollama"] = False
    except FileNotFoundError:
        print("   ❌ Ollama not installed")
        print("   📝 Install: curl -fsSL https://ollama.com/install.sh | sh")
        results["ollama"] = False
    except Exception as e:
        print(f"   ❌ Error checking Ollama: {e}")
        results["ollama"] = False
    print()

    # Test 4: MLX (Apple Silicon)
    print("4. Checking MLX (Apple Silicon)...")
    try:
        import platform

        if platform.processor() == "arm" and platform.system() == "Darwin":
            try:
                import importlib.util

                mlx_spec = importlib.util.find_spec("mlx.core")
                if mlx_spec is not None:
                    print("   ✓ MLX is installed (Apple Silicon detected)")
                    print("   ✓ Can use MLX models from mlx-community")
                    results["mlx"] = True
                else:
                    print("   ⚠️  Apple Silicon detected but MLX not installed")
                    print("   📝 Install: pip install mlx")
                    results["mlx"] = False
            except ImportError:
                print("   ⚠️  Apple Silicon detected but MLX not installed")
                print("   📝 Install: pip install mlx")
                results["mlx"] = False
        else:
            print("   (i) Not Apple Silicon (MLX requires M-series chips)")
            results["mlx"] = False
    except Exception as e:
        print(f"   ❌ Error checking MLX: {e}")
        results["mlx"] = False
    print()

    # Summary
    print("=" * 70)
    print("Summary & Recommendations")
    print("=" * 70)
    print()

    working_providers = []
    if results.get("groq_working"):
        working_providers.append("Groq (FREE API)")
    if results.get("ollama"):
        working_providers.append("Ollama (FREE local)")
    if results.get("mlx"):
        working_providers.append("MLX (FREE local)")

    if working_providers:
        print("✅ You have working FREE providers:")
        for provider in working_providers:
            print(f"   - {provider}")
        print()
        print("🎉 You're all set! No need to pay for HuggingFace.")
        print()
    else:
        print("⚠️  No working providers found. Recommendations:")
        print()
        if not results.get("groq"):
            print("1. Set up Groq (EASIEST - free API):")
            print("   - Visit: https://console.groq.com")
            print("   - Create free account & get API key")
            print("   - Run: export GROQ_API_KEY='your-key'")
            print()
        if not results.get("ollama"):
            print("2. Install Ollama (BEST for privacy):")
            print("   - Run: curl -fsSL https://ollama.com/install.sh | sh")
            print("   - Run: ollama pull llama3.1:8b")
            print()
        if not results.get("mlx") and "arm" in platform.processor().lower():
            print("3. Install MLX (Apple Silicon):")
            print("   - Run: pip install mlx mlx-lm")
            print()

    print("=" * 70)
    print("HuggingFace Status")
    print("=" * 70)
    print()
    print("❌ Old Inference API: DEPRECATED (returns 410)")
    print("✅ New Serverless Inference: FREE tier available!")
    print("   - Rate limits: ~few hundred requests/hour")
    print("   - Only works with models deployed by Inference Providers")
    print("   - Update packages: pip install --upgrade langchain-huggingface")
    print("💰 PRO Subscription: $9/month for 20x more credits (optional)")
    print("💰 Dedicated Endpoints: $0.033+/hour (optional)")
    print("✅ Model Downloads: Always FREE")
    print()
    print("For detailed setup instructions, see:")
    print("  → HUGGINGFACE_SETUP.md")
    print("  → HUGGINGFACE_API_CHANGE.md")
    print()

    # Exit code
    if working_providers:
        sys.exit(0)
    else:
        print("⚠️  No providers configured. Please set up at least one.")
        sys.exit(1)


def test_groq():
    """Test Groq API with a simple request."""
    try:
        from langchain_groq import ChatGroq

        print("   Testing Groq API...")

        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0,
            max_tokens=20,
        )

        response = llm.invoke("What is 2+2? Answer with just the number.")
        print(f"   ✓ Groq API working! Response: {response.content}")

    except ImportError:
        print("   ⚠️  langchain-groq not installed")
        print("      Run: poetry install")
        raise
    except Exception as e:
        print(f"   ❌ Groq API test failed: {str(e)[:100]}")
        raise


if __name__ == "__main__":
    main()
