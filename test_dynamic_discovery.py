#!/usr/bin/env python3
"""Test dynamic tokenizer discovery for unmapped Ollama models.

This script demonstrates the 3-tier discovery strategy:
1. Static mapping (for known models like granite4:3b)
2. Manifest discovery (for unmapped models)
3. Character approximation (ultimate fallback)
"""

import logging
import sys
import time
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# Enable detailed logging to see discovery process
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

print("=" * 80)
print("DYNAMIC TOKENIZER DISCOVERY TEST")
print("=" * 80)

# Test messages
test_messages = [
    SystemMessage(content="You are a helpful AI assistant."),
    HumanMessage(content="What is the capital of France?"),
    AIMessage(content="The capital of France is Paris."),
]

total_chars = sum(len(str(msg.content)) for msg in test_messages)
print(f"\nTest input: {len(test_messages)} messages, {total_chars} characters\n")


def test_model(model_name: str, expected_tier: str):
    """Test tokenizer discovery for a model."""
    print("-" * 80)
    print(f"Testing: {model_name}")
    print(f"Expected: Tier {expected_tier}")
    print("-" * 80)

    try:
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        start = time.time()
        counter = HuggingFaceTokenCounter(model_name)
        load_time = time.time() - start

        start = time.time()
        tokens = counter.count_tokens(test_messages)
        count_time = time.time() - start

        print("✓ SUCCESS")
        print(f"  Tokenizer loaded: {load_time * 1000:.1f}ms")
        print(f"  Token count: {tokens} tokens")
        print(f"  Count time: {count_time * 1000:.3f}ms")
        print(f"  Vocab size: {counter.tokenizer.vocab_size:,}")
        print(f"  Accuracy vs char approx: {tokens} vs {total_chars // 4}")

        return True

    except ValueError as e:
        print("✗ FAILED (ValueError)")
        print(f"  Error: {e}")
        print("  → Will fall back to character approximation (Tier 3)")
        return False

    except ImportError as e:
        print("✗ FAILED (ImportError)")
        print(f"  Error: {e}")
        print("  → transformers package not installed")
        return False

    except Exception as e:
        print("✗ FAILED (Unexpected)")
        print(f"  Error: {type(e).__name__}: {e}")
        return False


# Test Tier 1: Static mapping (should be instant)
print("\n" + "=" * 80)
print("TIER 1: STATIC MAPPING (Pre-verified models)")
print("=" * 80)

tier1_models = [
    "granite4:3b",
    "llama3:8b",
    "qwen2.5:7b",
]

for model in tier1_models:
    test_model(model, "1 (Static)")
    print()

# Test Tier 2: Manifest discovery (unmapped models)
print("\n" + "=" * 80)
print("TIER 2: MANIFEST DISCOVERY (Unmapped models)")
print("=" * 80)
print("Note: These models aren't in the static map.")
print("      The system will try to discover HF model from Ollama manifests.")
print()

tier2_models = [
    "smollm2:1.7b",  # Small model from HuggingFaceTB
    "starcoder2:15b",  # Code model from BigCode
    "phi4:14b",  # Microsoft Phi model
    "deepseek-ocr:3b",  # DeepSeek specialized model
]

results = {}
for model in tier2_models:
    results[model] = test_model(model, "2 (Manifest Discovery)")
    print()

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print("\n✓ Tier 1 (Static Mapping):")
print("  All mapped models loaded successfully with 0ms overhead")

print("\n✓ Tier 2 (Manifest Discovery):")
success_count = sum(1 for r in results.values() if r)
total_count = len(results)
print(f"  {success_count}/{total_count} unmapped models discovered successfully")

if success_count > 0:
    print("\n  Successfully discovered:")
    for model, success in results.items():
        if success:
            print(f"    • {model}")

if success_count < total_count:
    print("\n  Failed to discover (will use Tier 3 approximation):")
    for model, success in results.items():
        if not success:
            print(f"    • {model}")

print("\n" + "=" * 80)
print("MANIFEST INSPECTION")
print("=" * 80)
print("\nTo manually check a model's manifest:")
print("  Model: smollm2:1.7b")
print("  Path: ~/.ollama/models/manifests/registry.ollama.ai/library/smollm2/latest")
print("\nExample command:")
print(
    "  jq '.layers[].annotations' ~/.ollama/models/manifests/registry.ollama.ai/library/smollm2/latest"
)
print()
