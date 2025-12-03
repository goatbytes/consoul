"""Integration tests for SDK token usage tracking.

These tests verify that real model providers populate usage_metadata correctly.
"""

import os

import pytest

from consoul import Consoul


# Helper to check for valid API keys by attempting a test call
def _has_valid_openai_key() -> bool:
    """Check if OPENAI_API_KEY is valid."""
    key = os.getenv("OPENAI_API_KEY", "")
    return bool(key and key.startswith("sk-"))


def _has_valid_google_key() -> bool:
    """Check if GOOGLE_API_KEY is valid."""
    key = os.getenv("GOOGLE_API_KEY", "")
    return bool(key and key.startswith("AIza"))


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


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY")
    or not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
    reason="Requires valid OPENAI_API_KEY (must start with 'sk-')",
)
def test_openai_usage_metadata() -> None:
    """Test that OpenAI models provide usage_metadata."""
    from openai import AuthenticationError, BadRequestError

    try:
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
    except AuthenticationError as e:
        # Skip test if API key is invalid
        pytest.skip(f"OpenAI API key is invalid or expired: {e}")
    except BadRequestError as e:
        # Skip test if API configuration is invalid
        pytest.skip(f"OpenAI API configuration error: {e}")
    except Exception as e:
        # Skip test if other API errors occur (rate limit, network, etc.)
        if (
            "401" in str(e)
            or "authentication" in str(e).lower()
            or "api key" in str(e).lower()
        ):
            pytest.skip(f"OpenAI API error: {type(e).__name__}: {e}")
        raise


@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY")
    or not os.getenv("GOOGLE_API_KEY", "").startswith("AIza"),
    reason="Requires valid GOOGLE_API_KEY (must start with 'AIza')",
)
def test_google_usage_metadata() -> None:
    """Test that Google Gemini models provide usage_metadata."""
    try:
        from google.api_core.exceptions import (
            PermissionDenied,
            ResourceExhausted,
            Unauthenticated,
        )
    except ImportError:
        # google-api-core not installed - create dummy types
        PermissionDenied = type(None)  # noqa: N806
        Unauthenticated = type(None)  # noqa: N806
        ResourceExhausted = type(None)  # noqa: N806

    try:
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
    except (PermissionDenied, Unauthenticated) as e:
        # Skip test if API key is invalid
        pytest.skip(f"Google API key is invalid or expired: {e}")
    except ResourceExhausted as e:
        # Skip test if quota is exceeded
        pytest.skip(f"Google API quota exceeded: {e}")
    except Exception as e:
        # Skip test if other API errors occur (rate limit, network, etc.)
        if (
            "400" in str(e)
            or "401" in str(e)
            or "403" in str(e)
            or "429" in str(e)
            or "api key" in str(e).lower()
        ):
            pytest.skip(f"Google API error: {type(e).__name__}: {e}")
        raise


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
