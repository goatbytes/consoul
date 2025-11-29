"""Integration tests for SDK token usage tracking.

These tests verify that real model providers populate usage_metadata correctly.
"""

import os

import pytest

from consoul import Consoul


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"), reason="Requires ANTHROPIC_API_KEY"
)
def test_anthropic_usage_metadata() -> None:
    """Test that Anthropic models provide usage_metadata."""
    console = Consoul(model="claude-3-5-haiku-20241022", tools=False, persist=False)

    console.chat("Say 'hello' in exactly one word")
    cost = console.last_cost

    # Verify we got actual usage metadata
    assert cost["source"] == "usage_metadata"
    assert cost["input_tokens"] > 0
    assert cost["output_tokens"] > 0
    assert cost["total_tokens"] == cost["input_tokens"] + cost["output_tokens"]
    assert cost["estimated_cost"] > 0
    assert cost["model"] == "claude-3-5-haiku-20241022"


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY")
def test_openai_usage_metadata() -> None:
    """Test that OpenAI models provide usage_metadata."""
    console = Consoul(model="gpt-4o-mini", tools=False, persist=False)

    console.chat("Say 'hello' in exactly one word")
    cost = console.last_cost

    # Verify we got actual usage metadata
    assert cost["source"] == "usage_metadata"
    assert cost["input_tokens"] > 0
    assert cost["output_tokens"] > 0
    assert cost["total_tokens"] == cost["input_tokens"] + cost["output_tokens"]
    assert cost["estimated_cost"] > 0
    assert cost["model"] == "gpt-4o-mini"


@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="Requires GOOGLE_API_KEY")
def test_google_usage_metadata() -> None:
    """Test that Google Gemini models provide usage_metadata."""
    console = Consoul(model="gemini-2.0-flash-exp", tools=False, persist=False)

    console.chat("Say 'hello' in exactly one word")
    cost = console.last_cost

    # Verify we got actual usage metadata
    assert cost["source"] == "usage_metadata"
    assert cost["input_tokens"] > 0
    assert cost["output_tokens"] > 0
    assert cost["total_tokens"] == cost["input_tokens"] + cost["output_tokens"]
    assert cost["estimated_cost"] > 0
    assert cost["model"] == "gemini-2.0-flash-exp"


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"), reason="Requires ANTHROPIC_API_KEY"
)
def test_anthropic_multi_turn_conversation() -> None:
    """Test that usage_metadata is updated across multiple messages."""
    console = Consoul(model="claude-3-5-haiku-20241022", tools=False, persist=False)

    # First message
    console.chat("Count to 3")
    cost1 = console.last_cost
    assert cost1["source"] == "usage_metadata"

    # Second message
    console.chat("Now count to 5")
    cost2 = console.last_cost
    assert cost2["source"] == "usage_metadata"
    tokens2 = cost2["total_tokens"]

    # Second message should have different token count
    # (may be higher due to conversation context)
    assert tokens2 > 0
    assert cost2["input_tokens"] > 0
    assert cost2["output_tokens"] > 0
