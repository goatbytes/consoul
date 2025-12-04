#!/usr/bin/env python3
"""Comprehensive comparison of Consoul overhead vs minimal baseline.

This script measures the overhead introduced by different layers:
1. Minimal Ollama streaming (baseline)
2. + ConversationHistory (context management, token counting)
3. + Database persistence
4. + Token counting with tiktoken/transformers

Usage:
    python compare_consoul_overhead.py [model_name]

Example:
    python compare_consoul_overhead.py granite4:1b
"""

import asyncio
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama


async def test_minimal_baseline(model_name: str, prompt: str) -> dict[str, Any]:
    """Test 1: Minimal Ollama streaming (baseline).

    Args:
        model_name: Ollama model to test
        prompt: Test prompt

    Returns:
        Dict with metrics
    """
    chat = ChatOllama(
        model=model_name, temperature=0.0
    )  # temperature=0 for consistent results
    message = HumanMessage(content=prompt)

    stream_start = time.time()
    first_token_time = None
    token_count = 0
    response_text = ""

    async for chunk in chat.astream([message]):
        if first_token_time is None:
            first_token_time = time.time() - stream_start
        token_count += 1
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


async def test_with_conversation_history(
    model_name: str, prompt: str
) -> dict[str, Any]:
    """Test 2: With ConversationHistory (no persistence, no token counting).

    Args:
        model_name: Ollama model to test
        prompt: Test prompt

    Returns:
        Dict with metrics
    """
    from consoul.ai.history import ConversationHistory

    # Create conversation without persistence or token counting
    conversation = ConversationHistory(
        model_name=model_name,
        persist=False,
        summarize=False,
    )

    conversation.add_user_message(prompt)
    messages = conversation.get_messages()

    chat = ChatOllama(model=model_name, temperature=0.0)

    stream_start = time.time()
    first_token_time = None
    token_count = 0
    response_text = ""

    async for chunk in chat.astream(messages):
        if first_token_time is None:
            first_token_time = time.time() - stream_start
        token_count += 1
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


async def test_with_profile(model_name: str, prompt: str) -> dict[str, Any]:
    """Test 2b: With Profile + ConversationHistory (simulating real Consoul usage).

    Args:
        model_name: Ollama model to test
        prompt: Test prompt

    Returns:
        Dict with metrics
    """
    from consoul.ai.history import ConversationHistory
    from consoul.config.models import (
        ContextConfig,
        ConversationConfig,
        ProfileConfig,
    )

    # Create a profile (like Consoul does)
    profile = ProfileConfig(
        name="test",
        description="Test profile",
        system_prompt="You are a helpful AI assistant.",
        conversation=ConversationConfig(
            persist=False,
            summarize=False,
        ),
        context=ContextConfig(
            max_context_tokens=0,  # Auto-size
        ),
    )

    # Create conversation with profile settings
    conversation = ConversationHistory(
        model_name=model_name,
        persist=profile.conversation.persist,
        summarize=profile.conversation.summarize,
        max_tokens=profile.context.max_context_tokens,
    )

    # Add system prompt if present
    if profile.system_prompt:
        conversation.add_system_message(profile.system_prompt)

    conversation.add_user_message(prompt)
    messages = conversation.get_messages()

    chat = ChatOllama(model=model_name, temperature=0.0)

    stream_start = time.time()
    first_token_time = None
    token_count = 0
    response_text = ""

    async for chunk in chat.astream(messages):
        if first_token_time is None:
            first_token_time = time.time() - stream_start
        token_count += 1
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


async def test_with_database(model_name: str, prompt: str) -> dict[str, Any]:
    """Test 3: With database persistence.

    Args:
        model_name: Ollama model to test
        prompt: Test prompt

    Returns:
        Dict with metrics
    """
    from consoul.ai.history import ConversationHistory

    # Create temp database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create conversation with persistence
        conversation = ConversationHistory(
            model_name=model_name,
            persist=True,
            db_path=db_path,
            summarize=False,
        )

        # Add user message (this will create DB session)
        conversation.add_user_message(prompt)
        messages = conversation.get_messages()

        chat = ChatOllama(model=model_name, temperature=0.0)

        stream_start = time.time()
        first_token_time = None
        token_count = 0
        response_text = ""
        final_message = None

        async for chunk in chat.astream(messages):
            if first_token_time is None:
                first_token_time = time.time() - stream_start
            token_count += 1
            if chunk.content:
                response_text += chunk.content
            final_message = chunk

        # Persist the response
        if final_message:
            await conversation._persist_message(final_message)

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


async def test_with_token_counting(model_name: str, prompt: str) -> dict[str, Any]:
    """Test 4: With proper token counting.

    Args:
        model_name: Ollama model to test
        prompt: Test prompt

    Returns:
        Dict with metrics
    """
    from langchain_core.messages import AIMessage

    from consoul.ai.history import ConversationHistory

    # Create conversation with token counting
    conversation = ConversationHistory(
        model_name=model_name,
        persist=False,
        summarize=False,
    )

    conversation.add_user_message(prompt)
    messages = conversation.get_messages()

    chat = ChatOllama(model=model_name, temperature=0.0)

    stream_start = time.time()
    first_token_time = None
    token_count = 0
    response_text = ""

    async for chunk in chat.astream(messages):
        if first_token_time is None:
            first_token_time = time.time() - stream_start
        token_count += 1
        if chunk.content:
            response_text += chunk.content

    # Count tokens properly (this is where overhead happens)
    token_count_start = time.time()
    try:
        loop = asyncio.get_event_loop()
        actual_tokens = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                conversation._token_counter,
                [AIMessage(content=response_text)],
            ),
            timeout=2.0,  # Shorter timeout
        )
    except Exception as e:
        print(f"  Token counting failed or timed out: {e}")
        actual_tokens = len(response_text) // 4  # Fallback
    token_count_duration = time.time() - token_count_start

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
        "actual_tokens": actual_tokens,
        "token_count_duration": token_count_duration,
    }


async def compare_overhead(model_name: str = "granite4:1b"):
    """Run comprehensive overhead comparison.

    Args:
        model_name: Ollama model to test
    """
    print("=" * 80)
    print("CONSOUL OVERHEAD ANALYSIS")
    print("=" * 80)
    print(f"\nModel: {model_name}")
    print("Temperature: 0.0 (for consistent results)")

    # Use a consistent prompt
    prompt = "Explain what a Python list is in one sentence."

    print("\n" + "─" * 80)
    print("WARMUP")
    print("─" * 80)
    print("Loading model into memory...")
    await test_minimal_baseline(model_name, "Hi")
    await asyncio.sleep(1)

    print("\n" + "─" * 80)
    print("TEST 1: MINIMAL BASELINE")
    print("─" * 80)
    print("Direct ChatOllama streaming (no Consoul infrastructure)")
    print(f"\nPrompt: {prompt}\n")
    print("Running...")
    baseline = await test_minimal_baseline(model_name, prompt)

    await asyncio.sleep(1)

    print("\n" + "─" * 80)
    print("TEST 2: + CONVERSATION HISTORY")
    print("─" * 80)
    print("ConversationHistory with message management (no DB, no token counting)")
    print(f"\nPrompt: {prompt}\n")
    print("Running...")
    with_history = await test_with_conversation_history(model_name, prompt)

    await asyncio.sleep(1)

    print("\n" + "─" * 80)
    print("TEST 2B: + PROFILE (system prompt)")
    print("─" * 80)
    print("Profile + ConversationHistory with system prompt (simulating real usage)")
    print(f"\nPrompt: {prompt}\n")
    print("Running...")
    with_profile = await test_with_profile(model_name, prompt)

    await asyncio.sleep(1)

    print("\n" + "─" * 80)
    print("TEST 3: + DATABASE PERSISTENCE")
    print("─" * 80)
    print("Full ConversationHistory with SQLite persistence")
    print(f"\nPrompt: {prompt}\n")
    print("Running...")
    with_db = await test_with_database(model_name, prompt)

    await asyncio.sleep(1)

    print("\n" + "─" * 80)
    print("TEST 4: + TOKEN COUNTING")
    print("─" * 80)
    print("With tiktoken/transformers token counting")
    print(f"\nPrompt: {prompt}\n")
    print("Running...")
    with_tokens = await test_with_token_counting(model_name, prompt)

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(
        "\n┌─────────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐"
    )
    print(
        "│ Metric              │ Baseline │ +History │ +Profile │  +DB     │ +Tokens  │ Overhead │"
    )
    print(
        "├─────────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤"
    )

    # Time to first token
    ttft_overhead = (
        ((with_tokens["ttft"] - baseline["ttft"]) / baseline["ttft"] * 100)
        if baseline["ttft"] > 0
        else 0
    )
    print(
        f"│ TTFT                │ {baseline['ttft']:>6.3f}s  │ {with_history['ttft']:>6.3f}s  │ "
        f"{with_profile['ttft']:>6.3f}s  │ {with_db['ttft']:>6.3f}s  │ {with_tokens['ttft']:>6.3f}s  │ {ttft_overhead:>6.1f}%  │"
    )

    # Total duration (streaming only, excluding token counting)
    duration_overhead = (
        ((with_db["duration"] - baseline["duration"]) / baseline["duration"] * 100)
        if baseline["duration"] > 0
        else 0
    )
    print(
        f"│ Stream duration     │ {baseline['duration']:>6.3f}s  │ {with_history['duration']:>6.3f}s  │ "
        f"{with_profile['duration']:>6.3f}s  │ {with_db['duration']:>6.3f}s  │ {with_tokens['duration']:>6.3f}s  │ {duration_overhead:>6.1f}%  │"
    )

    # Token counting time (separate measurement)
    if "token_count_duration" in with_tokens:
        print(
            f"│ Token count time    │ {'N/A':>8s} │ {'N/A':>8s} │ "
            f"{'N/A':>8s} │ {'N/A':>8s} │ {with_tokens['token_count_duration']:>6.3f}s  │ {'N/A':>8s} │"
        )

    # Tokens per second
    print(
        f"│ Tokens/sec          │ {baseline['tps']:>6.2f}   │ {with_history['tps']:>6.2f}   │ "
        f"{with_profile['tps']:>6.2f}   │ {with_db['tps']:>6.2f}   │ {with_tokens['tps']:>6.2f}   │ {'N/A':>8s} │"
    )

    # Token chunks
    print(
        f"│ Chunks streamed     │ {baseline['tokens']:>6d}   │ {with_history['tokens']:>6d}   │ "
        f"{with_profile['tokens']:>6d}   │ {with_db['tokens']:>6d}   │ {with_tokens['tokens']:>6d}   │ {'N/A':>8s} │"
    )

    # Actual tokens (if available)
    if "actual_tokens" in with_tokens:
        print(
            f"│ Actual tokens       │ {'~' + str(baseline['response_length'] // 4):>6s}   │ {'~' + str(with_history['response_length'] // 4):>6s}   │ "
            f"{'~' + str(with_profile['response_length'] // 4):>6s}   │ {'~' + str(with_db['response_length'] // 4):>6s}   │ {with_tokens['actual_tokens']:>6d}   │ {'N/A':>8s} │"
        )

    print(
        "└─────────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘"
    )

    # Analysis
    print("\n" + "─" * 80)
    print("OVERHEAD BREAKDOWN")
    print("─" * 80)

    history_overhead = (
        ((with_history["duration"] - baseline["duration"]) / baseline["duration"] * 100)
        if baseline["duration"] > 0
        else 0
    )
    profile_overhead = (
        (
            (with_profile["duration"] - with_history["duration"])
            / with_history["duration"]
            * 100
        )
        if with_history["duration"] > 0
        else 0
    )
    db_overhead = (
        (
            (with_db["duration"] - with_profile["duration"])
            / with_profile["duration"]
            * 100
        )
        if with_profile["duration"] > 0
        else 0
    )

    print(f"\n1. ConversationHistory overhead: {history_overhead:+.1f}%")
    print(f"   Absolute: {with_history['duration'] - baseline['duration']:+.3f}s")

    print(f"\n2. Profile + system prompt overhead: {profile_overhead:+.1f}%")
    print(f"   Absolute: {with_profile['duration'] - with_history['duration']:+.3f}s")

    print(f"\n3. Database persistence overhead: {db_overhead:+.1f}%")
    print(f"   Absolute: {with_db['duration'] - with_profile['duration']:+.3f}s")

    if "token_count_duration" in with_tokens:
        print(f"\n4. Token counting time: {with_tokens['token_count_duration']:.3f}s")
        print("   (This happens after streaming completes)")

    print(f"\n5. Total overhead (History + Profile + DB): {duration_overhead:+.1f}%")
    print(f"   Absolute: {with_db['duration'] - baseline['duration']:+.3f}s")

    # Summary
    print("\n" + "─" * 80)
    print("SUMMARY")
    print("─" * 80)

    if abs(duration_overhead) < 5:
        print("\n  ✓ Consoul streaming overhead is minimal (<5%)")
    elif abs(duration_overhead) < 15:
        print("\n  ⚠ Consoul has moderate streaming overhead (5-15%)")
    else:
        print("\n  ✗ Consoul has significant streaming overhead (>15%)")

    if "token_count_duration" in with_tokens:
        if with_tokens["token_count_duration"] < 0.1:
            print("  ✓ Token counting is fast (<100ms)")
        elif with_tokens["token_count_duration"] < 0.5:
            print("  ⚠ Token counting adds noticeable delay (100-500ms)")
        else:
            print("  ✗ Token counting is slow (>500ms)")

    print("\n  Note: Token counting happens after streaming, so it doesn't affect")
    print("        the perceived responsiveness during message display.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Get model name from args or use default
    model = sys.argv[1] if len(sys.argv) > 1 else "granite4:1b"

    # Run comparison
    asyncio.run(compare_overhead(model))
