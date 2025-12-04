#!/usr/bin/env python3
"""Compare streaming performance between minimal Ollama and Consoul.

This script runs the same prompt through both a minimal Ollama setup and
Consoul's full stack to identify performance bottlenecks.

Usage:
    python compare_streaming_performance.py [model_name]

Example:
    python compare_streaming_performance.py qwen2.5-coder:7b
"""

import asyncio
import sys
import time
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama


async def test_minimal_ollama(model_name: str, prompt: str) -> dict[str, Any]:
    """Test minimal Ollama streaming (baseline).

    Args:
        model_name: Ollama model to test
        prompt: Test prompt

    Returns:
        Dict with metrics: ttft, duration, tokens, tps, response_length
    """
    # Create chat model
    chat = ChatOllama(model=model_name, temperature=0.7)

    # Create message
    message = HumanMessage(content=prompt)

    # Track metrics
    stream_start = time.time()
    first_token_time = None
    token_count = 0
    response_text = ""

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

    stream_end = time.time()
    stream_duration = stream_end - stream_start
    tokens_per_second = token_count / stream_duration if stream_duration > 0 else 0

    return {
        "ttft": first_token_time,
        "duration": stream_duration,
        "tokens": token_count,
        "tps": tokens_per_second,
        "response_length": len(response_text),
        "response": response_text,
    }


async def test_consoul_stack(model_name: str, prompt: str) -> dict[str, Any]:
    """Test Consoul's full stack (with overhead).

    Args:
        model_name: Ollama model to test
        prompt: Test prompt

    Returns:
        Dict with metrics: ttft, duration, tokens, tps, response_length
    """
    from consoul.ai.history import ConversationHistory

    # Create conversation history (includes token counting, context management)
    conversation = ConversationHistory(
        model_name=model_name,
        persist=False,  # Disable DB for fair comparison
        summarize=False,  # Disable summarization
    )

    # Add test message
    conversation.add_user_message(prompt)

    # Get messages for streaming
    messages = conversation.get_messages()

    # Create chat model (same as baseline for fair comparison)
    from langchain_ollama import ChatOllama

    chat = ChatOllama(model=model_name, temperature=0.7)

    # Track metrics
    stream_start = time.time()
    first_token_time = None
    token_count = 0
    response_text = ""

    # Stream response (through Consoul's infrastructure)
    async for chunk in chat.astream(messages):
        # Record time to first token
        if first_token_time is None:
            first_token_time = time.time() - stream_start

        # Count tokens (chunks)
        token_count += 1

        # Accumulate response
        if chunk.content:
            response_text += chunk.content

    stream_end = time.time()
    stream_duration = stream_end - stream_start
    tokens_per_second = token_count / stream_duration if stream_duration > 0 else 0

    return {
        "ttft": first_token_time,
        "duration": stream_duration,
        "tokens": token_count,
        "tps": tokens_per_second,
        "response_length": len(response_text),
        "response": response_text,
    }


async def compare_performance(model_name: str = "qwen2.5-coder:7b"):
    """Run comparison between minimal and Consoul stack.

    Args:
        model_name: Ollama model to test
    """
    # Test prompt
    prompt = "Write a short hello world program in Python."

    print("=" * 80)
    print("STREAMING PERFORMANCE COMPARISON")
    print("=" * 80)
    print(f"\nModel: {model_name}")
    print(f"Prompt: {prompt}\n")

    # Warmup: Run each test once to load model into memory
    print("Warming up (loading model into memory)...")
    await test_minimal_ollama(model_name, "Hello")
    await asyncio.sleep(0.5)
    await test_consoul_stack(model_name, "Hello")
    await asyncio.sleep(1)

    print("\nRunning actual tests...\n")

    # Test 1: Minimal Ollama (baseline)
    print("Running Test 1: Minimal Ollama (baseline)...")
    minimal_metrics = await test_minimal_ollama(model_name, prompt)

    # Small delay between tests
    await asyncio.sleep(1)

    # Test 2: Consoul stack
    print("Running Test 2: Consoul Stack...")
    consoul_metrics = await test_consoul_stack(model_name, prompt)

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(
        "\n┌─────────────────────────────┬──────────────┬──────────────┬─────────────┐"
    )
    print("│ Metric                      │ Minimal      │ Consoul      │ Overhead    │")
    print("├─────────────────────────────┼──────────────┼──────────────┼─────────────┤")

    # Time to first token
    ttft_overhead = (
        ((consoul_metrics["ttft"] - minimal_metrics["ttft"]) / minimal_metrics["ttft"])
        * 100
        if minimal_metrics["ttft"] > 0
        else 0
    )
    print(
        f"│ Time to first token         │ {minimal_metrics['ttft']:>8.3f}s    │ {consoul_metrics['ttft']:>8.3f}s    │ {ttft_overhead:>7.1f}%    │"
    )

    # Total duration
    duration_overhead = (
        (
            (consoul_metrics["duration"] - minimal_metrics["duration"])
            / minimal_metrics["duration"]
        )
        * 100
        if minimal_metrics["duration"] > 0
        else 0
    )
    print(
        f"│ Total duration              │ {minimal_metrics['duration']:>8.3f}s    │ {consoul_metrics['duration']:>8.3f}s    │ {duration_overhead:>7.1f}%    │"
    )

    # Tokens per second
    tps_overhead = (
        ((minimal_metrics["tps"] - consoul_metrics["tps"]) / minimal_metrics["tps"])
        * 100
        if minimal_metrics["tps"] > 0
        else 0
    )
    print(
        f"│ Tokens/second               │ {minimal_metrics['tps']:>8.2f}     │ {consoul_metrics['tps']:>8.2f}     │ {-tps_overhead:>7.1f}%    │"
    )

    # Token count
    print(
        f"│ Token chunks                │ {minimal_metrics['tokens']:>8d}     │ {consoul_metrics['tokens']:>8d}     │ {'N/A':>11s} │"
    )

    # Response length
    print(
        f"│ Response length (chars)     │ {minimal_metrics['response_length']:>8d}     │ {consoul_metrics['response_length']:>8d}     │ {'N/A':>11s} │"
    )

    print("└─────────────────────────────┴──────────────┴──────────────┴─────────────┘")

    # Summary
    print("\nSUMMARY:")
    if duration_overhead < 5:
        print("  ✓ Consoul overhead is minimal (<5%)")
    elif duration_overhead < 15:
        print("  ⚠ Consoul has moderate overhead (5-15%)")
    else:
        print("  ✗ Consoul has significant overhead (>15%)")

    print(
        f"\n  Absolute overhead: {consoul_metrics['duration'] - minimal_metrics['duration']:.3f}s"
    )

    # Show first 200 chars of responses to verify they're similar
    print("\nRESPONSE PREVIEW (first 200 chars):")
    print(f"\nMinimal: {minimal_metrics['response'][:200]}...")
    print(f"\nConsoul: {consoul_metrics['response'][:200]}...")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Get model name from args or use default
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:7b"

    # Run comparison
    asyncio.run(compare_performance(model))
