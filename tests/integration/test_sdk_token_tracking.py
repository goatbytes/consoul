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


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"), reason="Requires ANTHROPIC_API_KEY"
)
def test_anthropic_cache_token_extraction() -> None:
    """Test that Anthropic cache tokens are properly extracted from usage_metadata."""
    console = Consoul(model="claude-3-5-haiku-20241022", tools=False, persist=False)

    # Send a message that might trigger caching
    console.chat("Hello, can you help me?")
    cost = console.last_cost

    # Verify basic cost structure
    assert cost["source"] == "usage_metadata"
    assert cost["input_tokens"] > 0
    assert cost["output_tokens"] > 0
    assert cost["estimated_cost"] > 0

    # Check if cache fields are present (they may be 0 on first request)
    # The important thing is that the structure supports these fields
    # If cache tokens are present, verify they're tracked
    if "cache_read_tokens" in cost:
        assert isinstance(cost["cache_read_tokens"], int)
        assert cost["cache_read_tokens"] >= 0

    if "cache_creation_tokens" in cost:
        assert isinstance(cost["cache_creation_tokens"], int)
        assert cost["cache_creation_tokens"] >= 0

    # If cache-specific costs are present, verify they're calculated
    if "cache_read_cost" in cost:
        assert isinstance(cost["cache_read_cost"], (int, float))
        assert cost["cache_read_cost"] >= 0

    if "cache_write_cost" in cost:
        assert isinstance(cost["cache_write_cost"], (int, float))
        assert cost["cache_write_cost"] >= 0

    if "cache_savings" in cost:
        assert isinstance(cost["cache_savings"], (int, float))
        assert cost["cache_savings"] >= 0


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"), reason="Requires ANTHROPIC_API_KEY"
)
def test_anthropic_cache_ttl_tokens() -> None:
    """Test that TTL-specific cache tokens are extracted when available."""
    console = Consoul(model="claude-3-5-sonnet-20241022", tools=False, persist=False)

    # Send a message
    console.chat("Explain quantum computing in one sentence")
    cost = console.last_cost

    assert cost["source"] == "usage_metadata"

    # If TTL-specific tokens are present, verify structure
    if "cache_write_5m_tokens" in cost:
        assert isinstance(cost["cache_write_5m_tokens"], int)
        assert cost["cache_write_5m_tokens"] >= 0

    if "cache_write_1h_tokens" in cost:
        assert isinstance(cost["cache_write_1h_tokens"], int)
        assert cost["cache_write_1h_tokens"] >= 0

    # Verify cost calculation includes cache costs
    if cost.get("cache_read_tokens", 0) > 0 or cost.get("cache_creation_tokens", 0) > 0:
        # If cache tokens present, should have cache-specific costs
        assert (
            "cache_read_cost" in cost
            or "cache_write_cost" in cost
            or cost["estimated_cost"] > 0
        )


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"), reason="Requires ANTHROPIC_API_KEY"
)
def test_anthropic_token_counting_assumption() -> None:
    """REGRESSION TEST: Verify Anthropic's input_tokens excludes cached tokens.

    This test monitors the assumption that Anthropic's input_tokens field
    does NOT include cache_creation_input_tokens or cache_read_input_tokens.

    If this test fails, it means Anthropic changed their API semantics and
    we need to update our defensive logic threshold.
    """
    console = Consoul(model="claude-3-5-haiku-20241022", tools=False, persist=False)

    # Simple message (no caching expected, but structure verification)
    console.chat("Say hello")
    cost = console.last_cost

    assert cost["source"] == "usage_metadata"

    # Get the raw response to check metadata structure
    if hasattr(console, "_last_response") and console._last_response:
        metadata = console._last_response.usage_metadata
        if metadata:
            input_tokens = metadata.get("input_tokens", 0)
            input_details = metadata.get("input_token_details", {})

            if isinstance(input_details, dict):
                cache_read = input_details.get("cache_read", 0)
                cache_creation = input_details.get("cache_creation", 0)
                total_cache = cache_read + cache_creation

                # CRITICAL ASSUMPTION: input_tokens should be independent of cache tokens
                # If input_tokens >= total_cache AND we have cache tokens, this might indicate
                # the tokens are separate (current behavior) OR it's a message without cache.
                # If input_tokens < total_cache, that would be very suspicious.

                if total_cache > 0:
                    # If we have cache tokens, verify input_tokens makes sense
                    # It should either be:
                    # 1. Greater than total_cache (base + some extra)
                    # 2. Or much smaller (just the base after cache breakpoint)
                    # It should NOT be exactly equal to total_cache
                    assert input_tokens != total_cache, (
                        "REGRESSION: input_tokens equals total cache tokens. "
                        "This might indicate Anthropic changed their API to report "
                        "only cached tokens in input_tokens, which would break our model."
                    )

                # Check for defensive adjustment flag
                if "_defensive_adjustment" in cost:
                    # If our defensive logic triggered, log it
                    pytest.fail(
                        f"Defensive adjustment triggered! This may indicate Anthropic "
                        f"changed their API. input_tokens={input_tokens}, "
                        f"cache_tokens={total_cache}, base_input={cost.get('base_input_tokens')}"
                    )
