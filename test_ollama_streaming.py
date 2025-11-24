#!/usr/bin/env python3
"""Minimal Ollama streaming test to compare performance with Consoul.

This script tests raw Ollama streaming performance without any of Consoul's
overhead (TUI, database, context management, etc.) to establish a baseline.

Usage:
    python test_ollama_streaming.py [model_name]

Example:
    python test_ollama_streaming.py qwen2.5-coder:7b
"""

import asyncio
import sys
import time

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama


async def test_streaming(model_name: str = "qwen2.5-coder:7b"):
    """Test Ollama streaming with minimal overhead.

    Args:
        model_name: Ollama model to test (default: qwen2.5-coder:7b)
    """
    print(f"Testing streaming with model: {model_name}")
    print("=" * 80)

    # Create chat model
    chat = ChatOllama(
        model=model_name,
        temperature=0.7,
    )

    # Test prompt
    prompt = "Write a short hello world program in Python."
    print(f"\nPrompt: {prompt}\n")

    # Create message
    message = HumanMessage(content=prompt)

    # Track metrics
    stream_start = time.time()
    first_token_time = None
    token_count = 0
    response_text = ""

    print("Response:")
    print("-" * 80)

    # Stream response
    async for chunk in chat.astream([message]):
        # Record time to first token
        if first_token_time is None:
            first_token_time = time.time() - stream_start

        # Count tokens (chunks)
        token_count += 1

        # Accumulate response
        if chunk.content:
            response_text += chunk.content
            print(chunk.content, end="", flush=True)

    stream_end = time.time()
    stream_duration = stream_end - stream_start

    # Calculate metrics
    tokens_per_second = token_count / stream_duration if stream_duration > 0 else 0

    print("\n" + "-" * 80)
    print("\nMetrics:")
    print(f"  Time to first token: {first_token_time:.3f}s")
    print(f"  Total duration: {stream_duration:.3f}s")
    print(f"  Token chunks: {token_count}")
    print(f"  Tokens/sec: {tokens_per_second:.2f}")
    print(f"  Response length: {len(response_text)} chars")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Get model name from args or use default
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:7b"

    # Run test
    asyncio.run(test_streaming(model))
