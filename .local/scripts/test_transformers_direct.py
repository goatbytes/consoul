#!/usr/bin/env python3
"""Test transformers pipeline directly without LangChain."""

import sys

print("Step 1: Import transformers...", flush=True)
try:
    from transformers import pipeline

    print("✓ Imported transformers", flush=True)
except Exception as e:
    print(f"✗ Import failed: {e}", flush=True)
    sys.exit(1)

print("\nStep 2: Create pipeline directly...", flush=True)
try:
    print("   Creating text-generation pipeline with gpt2...", flush=True)

    # Create pipeline without device specification (let transformers decide)
    pipe = pipeline(
        "text-generation",
        model="gpt2",
        max_new_tokens=50,
        temperature=0.7,
    )

    print(f"✓ Pipeline created: {type(pipe).__name__}", flush=True)
except Exception as e:
    print(f"✗ Pipeline creation failed: {e}", flush=True)
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\nStep 3: Generate text...", flush=True)
try:
    prompt = "Hello, how are you?"
    print(f"   Prompt: '{prompt}'", flush=True)

    result = pipe(prompt)

    print("✓ Generation successful!", flush=True)
    print(f"   Result: {result}", flush=True)
    print("\n✅ SUCCESS!", flush=True)
except Exception as e:
    print(f"✗ Generation failed: {e}", flush=True)
    import traceback

    traceback.print_exc()
    sys.exit(1)
