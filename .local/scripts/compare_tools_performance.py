#!/usr/bin/env python3
"""Compare streaming performance with and without tool calls.

This script measures the overhead of tool calling infrastructure by comparing:
1. Simple streaming (no tools)
2. Streaming with tools available (but not called)
3. Streaming with actual tool execution

Usage:
    python compare_tools_performance.py [model_name]

Example:
    python compare_tools_performance.py qwen2.5-coder:7b
"""

import asyncio
import sys
import time
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama


# Define a simple test tool
@tool
def get_current_time() -> str:
    """Get the current time in ISO format.

    Returns:
        Current time as ISO string
    """
    from datetime import datetime

    return datetime.now().isoformat()


@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b


async def test_no_tools(model_name: str, prompt: str) -> dict[str, Any]:
    """Test streaming without any tools.

    Args:
        model_name: Ollama model to test
        prompt: Test prompt

    Returns:
        Dict with metrics
    """
    chat = ChatOllama(model=model_name, temperature=0.7)
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
        "tool_calls": 0,
    }


async def test_with_tools_available(model_name: str, prompt: str) -> dict[str, Any]:
    """Test streaming with tools bound but not called.

    Args:
        model_name: Ollama model to test
        prompt: Test prompt (shouldn't trigger tools)

    Returns:
        Dict with metrics
    """
    chat = ChatOllama(model=model_name, temperature=0.7)

    # Bind tools to the model
    chat_with_tools = chat.bind_tools([get_current_time, calculate_sum])

    message = HumanMessage(content=prompt)

    stream_start = time.time()
    first_token_time = None
    token_count = 0
    response_text = ""

    async for chunk in chat_with_tools.astream([message]):
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
        "tool_calls": 0,
    }


async def test_with_tool_execution(model_name: str, prompt: str) -> dict[str, Any]:
    """Test streaming with tools that get called and executed.

    Args:
        model_name: Ollama model to test
        prompt: Test prompt (should trigger tools)

    Returns:
        Dict with metrics
    """
    chat = ChatOllama(model=model_name, temperature=0.7)

    # Bind tools to the model
    chat_with_tools = chat.bind_tools([get_current_time, calculate_sum])

    message = HumanMessage(content=prompt)

    stream_start = time.time()
    first_token_time = None
    token_count = 0
    response_text = ""
    tool_call_count = 0
    tool_execution_time = 0.0

    async for chunk in chat_with_tools.astream([message]):
        if first_token_time is None:
            first_token_time = time.time() - stream_start
        token_count += 1

        if chunk.content:
            response_text += chunk.content

        # Check for tool calls
        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
            tool_call_count += len(chunk.tool_calls)

            # Simulate tool execution
            for _tool_call in chunk.tool_calls:
                exec_start = time.time()
                # In real scenario, we'd execute the tool here
                # For now, just simulate with a small delay
                await asyncio.sleep(0.001)  # 1ms per tool call
                tool_execution_time += time.time() - exec_start

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
        "tool_calls": tool_call_count,
        "tool_execution_time": tool_execution_time,
    }


async def compare_tool_performance(model_name: str = "qwen2.5-coder:7b"):
    """Run comparison of different tool configurations.

    Args:
        model_name: Ollama model to test
    """
    print("=" * 80)
    print("TOOL INFRASTRUCTURE PERFORMANCE COMPARISON")
    print("=" * 80)
    print(f"\nModel: {model_name}")

    # Test prompts
    simple_prompt = "Write a short hello world program in Python."
    tool_prompt = "What is the sum of 42 and 58? Also, what is the current time?"

    print("\n" + "─" * 80)
    print("WARMUP")
    print("─" * 80)
    print("Loading model into memory...")
    await test_no_tools(model_name, "Hi")
    await asyncio.sleep(1)

    print("\n" + "─" * 80)
    print("TEST 1: NO TOOLS")
    print("─" * 80)
    print(f"Prompt: {simple_prompt}")
    print("\nRunning...")
    no_tools_metrics = await test_no_tools(model_name, simple_prompt)

    await asyncio.sleep(1)

    print("\n" + "─" * 80)
    print("TEST 2: TOOLS AVAILABLE (but not called)")
    print("─" * 80)
    print(f"Prompt: {simple_prompt}")
    print("\nRunning...")
    tools_available_metrics = await test_with_tools_available(model_name, simple_prompt)

    await asyncio.sleep(1)

    print("\n" + "─" * 80)
    print("TEST 3: TOOLS CALLED")
    print("─" * 80)
    print(f"Prompt: {tool_prompt}")
    print("\nRunning...")
    tools_called_metrics = await test_with_tool_execution(model_name, tool_prompt)

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(
        "\n┌─────────────────────────────┬──────────────┬──────────────┬──────────────┐"
    )
    print(
        "│ Metric                      │ No Tools     │ Tools Avail  │ Tools Called │"
    )
    print(
        "├─────────────────────────────┼──────────────┼──────────────┼──────────────┤"
    )

    # Time to first token
    print(
        f"│ Time to first token         │ {no_tools_metrics['ttft']:>8.3f}s    │ "
        f"{tools_available_metrics['ttft']:>8.3f}s    │ {tools_called_metrics['ttft']:>8.3f}s    │"
    )

    # Total duration
    print(
        f"│ Total duration              │ {no_tools_metrics['duration']:>8.3f}s    │ "
        f"{tools_available_metrics['duration']:>8.3f}s    │ {tools_called_metrics['duration']:>8.3f}s    │"
    )

    # Tokens per second
    print(
        f"│ Tokens/second               │ {no_tools_metrics['tps']:>8.2f}     │ "
        f"{tools_available_metrics['tps']:>8.2f}     │ {tools_called_metrics['tps']:>8.2f}     │"
    )

    # Token count
    print(
        f"│ Token chunks                │ {no_tools_metrics['tokens']:>8d}     │ "
        f"{tools_available_metrics['tokens']:>8d}     │ {tools_called_metrics['tokens']:>8d}     │"
    )

    # Tool calls
    print(
        f"│ Tool calls made             │ {no_tools_metrics['tool_calls']:>8d}     │ "
        f"{tools_available_metrics['tool_calls']:>8d}     │ {tools_called_metrics['tool_calls']:>8d}     │"
    )

    # Tool execution time (if available)
    if tools_called_metrics.get("tool_execution_time", 0) > 0:
        print(
            f"│ Tool execution time         │ {'N/A':>12s} │ "
            f"{'N/A':>12s} │ {tools_called_metrics['tool_execution_time']:>8.3f}s    │"
        )

    print(
        "└─────────────────────────────┴──────────────┴──────────────┴──────────────┘"
    )

    # Calculate overhead
    print("\n" + "─" * 80)
    print("OVERHEAD ANALYSIS")
    print("─" * 80)

    # Tools available overhead
    tools_avail_overhead = (
        (tools_available_metrics["duration"] - no_tools_metrics["duration"])
        / no_tools_metrics["duration"]
        * 100
        if no_tools_metrics["duration"] > 0
        else 0
    )

    print(f"\nTools Available Overhead: {tools_avail_overhead:+.1f}%")
    print(
        f"  Absolute: {tools_available_metrics['duration'] - no_tools_metrics['duration']:+.3f}s"
    )

    if abs(tools_avail_overhead) < 5:
        print("  ✓ Tool binding has minimal overhead (<5%)")
    elif abs(tools_avail_overhead) < 15:
        print("  ⚠ Tool binding has moderate overhead (5-15%)")
    else:
        print("  ✗ Tool binding has significant overhead (>15%)")

    # Note about different prompts
    print("\nNote: Test 3 uses a different prompt designed to trigger tools,")
    print("so duration comparison with Tests 1-2 is not directly meaningful.")

    # Show response previews
    print("\n" + "─" * 80)
    print("RESPONSE PREVIEWS (first 150 chars)")
    print("─" * 80)

    print(f"\nNo Tools:\n  {no_tools_metrics['response'][:150]}...")
    print(f"\nTools Available:\n  {tools_available_metrics['response'][:150]}...")
    print(f"\nTools Called:\n  {tools_called_metrics['response'][:150]}...")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Get model name from args or use default
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:7b"

    # Run comparison
    asyncio.run(compare_tool_performance(model))
