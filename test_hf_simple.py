#!/usr/bin/env python3
"""Simple test for local HuggingFace model."""

import sys

from consoul.ai.providers import get_chat_model
from consoul.config.models import HuggingFaceModelConfig

print("=" * 60, flush=True)
print("Step 1: Importing dependencies...", flush=True)
print("✓ Imports successful", flush=True)

print("\nStep 2: Creating model config...", flush=True)
model_config = HuggingFaceModelConfig(
    model="gpt2",
    local=True,
    temperature=0.7,
    max_tokens=50,
)
print(f"✓ Config created: {model_config.model}, local={model_config.local}", flush=True)

print("\nStep 3: Initializing model (this may take time)...", flush=True)
try:
    chat_model = get_chat_model(model_config)
    print(f"✓ Model initialized: {type(chat_model).__name__}", flush=True)
except Exception as e:
    print(f"✗ Failed: {e}", flush=True)
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\nStep 4: Testing chat...", flush=True)
try:
    from langchain_core.messages import HumanMessage

    messages = [HumanMessage(content="Say 'Hello'")]
    print("   Sending message...", flush=True)

    response = chat_model.invoke(messages)
    print(f"✓ Response: {response.content}", flush=True)
    print("\n✅ SUCCESS!", flush=True)
except Exception as e:
    print(f"✗ Chat failed: {e}", flush=True)
    import traceback

    traceback.print_exc()
    sys.exit(1)
