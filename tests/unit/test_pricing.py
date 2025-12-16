"""Unit tests for pricing module."""

from consoul.pricing import calculate_cost, get_model_pricing


class TestPricingData:
    """Test pricing data availability."""

    def test_anthropic_claude_3_5_sonnet_pricing(self) -> None:
        """Test that Claude 3.5 Sonnet has pricing data."""
        pricing = get_model_pricing("claude-3-5-sonnet-20241022")
        assert pricing is not None
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] == 3.00  # $3 per MTok
        assert pricing["output"] == 15.00  # $15 per MTok

    def test_anthropic_claude_3_5_haiku_pricing(self) -> None:
        """Test that Claude 3.5 Haiku has pricing data."""
        pricing = get_model_pricing("claude-3-5-haiku-20241022")
        assert pricing is not None
        assert pricing["input"] == 1.00  # $1 per MTok
        assert pricing["output"] == 5.00  # $5 per MTok

    def test_google_gemini_2_flash_pricing(self) -> None:
        """Test that Gemini 2.0 Flash has pricing data."""
        pricing = get_model_pricing("gemini-2.0-flash")
        assert pricing is not None
        assert pricing["input"] == 0.30  # $0.30 per MTok (updated from scrape)
        assert pricing["output"] == 2.50  # $2.50 per MTok (updated from scrape)

    def test_openai_gpt4o_mini_pricing(self) -> None:
        """Test that GPT-4o-mini has pricing data."""
        pricing = get_model_pricing("gpt-4o-mini")
        assert pricing is not None
        assert pricing["input"] == 0.15  # $0.15 per MTok
        assert pricing["output"] == 0.60  # $0.60 per MTok

    def test_ollama_model_free(self) -> None:
        """Test that Ollama models are free."""
        pricing = get_model_pricing("llama2")
        assert pricing is not None
        assert pricing["input"] == 0.0
        assert pricing["output"] == 0.0

    def test_unknown_model_defaults_to_ollama(self) -> None:
        """Test that unknown models default to Ollama (free) pricing."""
        # Models without provider prefix are treated as Ollama models
        pricing = get_model_pricing("unknown-model-xyz")
        assert pricing is not None
        assert pricing["input"] == 0.0
        assert pricing["output"] == 0.0


class TestCostCalculation:
    """Test cost calculation functionality."""

    def test_claude_3_5_haiku_cost(self) -> None:
        """Test accurate cost calculation for Claude 3.5 Haiku."""
        # 1000 input tokens, 500 output tokens
        # Input: 1000/1M * $1 = $0.001
        # Output: 500/1M * $5 = $0.0025
        # Total: $0.0035
        cost = calculate_cost("claude-3-5-haiku-20241022", 1000, 500)

        assert cost["pricing_available"] is True
        assert cost["source"] == "consoul"
        assert cost["input_cost"] == 0.001
        assert cost["output_cost"] == 0.0025
        assert cost["total_cost"] == 0.0035

    def test_claude_3_5_sonnet_cost(self) -> None:
        """Test accurate cost calculation for Claude 3.5 Sonnet."""
        # 10000 input tokens, 5000 output tokens
        # Input: 10000/1M * $3 = $0.03
        # Output: 5000/1M * $15 = $0.075
        # Total: $0.105
        cost = calculate_cost("claude-3-5-sonnet-20241022", 10000, 5000)

        assert cost["pricing_available"] is True
        assert cost["input_cost"] == 0.03
        assert cost["output_cost"] == 0.075
        assert cost["total_cost"] == 0.105

    def test_gemini_2_flash_cost(self) -> None:
        """Test accurate cost calculation for Gemini 2.0 Flash."""
        # 5000 input tokens, 2000 output tokens
        # Input: 5000/1M * $0.30 = $0.0015
        # Output: 2000/1M * $2.50 = $0.0050
        # Total: $0.0065
        cost = calculate_cost("gemini-2.0-flash", 5000, 2000)

        assert cost["pricing_available"] is True
        assert cost["input_cost"] == 0.0015
        assert cost["output_cost"] == 0.0050
        assert abs(cost["total_cost"] - 0.0065) < 0.0001  # Allow for floating point

    def test_prompt_caching_cost_backward_compat(self) -> None:
        """Test cost calculation with prompt caching (backward compatibility)."""
        # Claude 3.5 Haiku with 2000 cached tokens (old API)
        # Input: 1000/1M * $1 = $0.001
        # Output: 500/1M * $5 = $0.0025
        # Cache read: 2000/1M * $0.10 = $0.0002
        # Total: $0.0037
        cost = calculate_cost(
            "claude-3-5-haiku-20241022", 1000, 500, cached_tokens=2000
        )

        assert cost["cache_cost"] == 0.0002
        assert cost["total_cost"] == 0.0037

    def test_anthropic_cache_read_cost(self) -> None:
        """Test Anthropic cache read cost (90% discount)."""
        # Claude 3.5 Haiku with 8000 cache read tokens
        # Input: 1000/1M * $1 = $0.001
        # Output: 500/1M * $5 = $0.0025
        # Cache read: 8000/1M * $0.10 = $0.0008
        # Total: $0.0043
        cost = calculate_cost(
            "claude-3-5-haiku-20241022",
            1000,
            500,
            cache_read_tokens=8000,
        )

        assert cost["cache_cost"] == 0.0008
        assert cost["cache_read_cost"] == 0.0008
        assert cost["cache_write_cost"] == 0.0
        # Savings: 8000/1M * $1 * 0.9 = $0.0072
        assert abs(cost["cache_savings"] - 0.0072) < 0.0001
        assert abs(cost["total_cost"] - 0.0043) < 0.0001

    def test_anthropic_cache_write_5m_cost(self) -> None:
        """Test Anthropic 5-minute cache write cost (1.25x)."""
        # Claude 3.5 Sonnet with 1000 5-min cache writes
        # Input: 500/1M * $3 = $0.0015
        # Output: 200/1M * $15 = $0.003
        # Cache write 5m: 1000/1M * $3.75 = $0.00375
        # Total: $0.00825
        cost = calculate_cost(
            "claude-3-5-sonnet-20241022",
            500,
            200,
            cache_write_5m_tokens=1000,
        )

        assert cost["cache_write_cost"] == 0.00375
        assert cost["cache_cost"] == 0.00375
        assert abs(cost["total_cost"] - 0.00825) < 0.00001

    def test_anthropic_cache_write_1h_cost(self) -> None:
        """Test Anthropic 1-hour cache write cost (2x)."""
        # Claude 3.5 Haiku with 2000 1-hour cache writes
        # Input: 500/1M * $1 = $0.0005
        # Output: 200/1M * $5 = $0.001
        # Cache write 1h: 2000/1M * $2.00 = $0.004
        # Total: $0.0055
        cost = calculate_cost(
            "claude-3-5-haiku-20241022",
            500,
            200,
            cache_write_1h_tokens=2000,
        )

        assert cost["cache_write_cost"] == 0.004
        assert cost["cache_cost"] == 0.004
        assert abs(cost["total_cost"] - 0.0055) < 0.0001

    def test_anthropic_mixed_cache_scenario(self) -> None:
        """Test mixed cache scenario with reads and writes."""
        # Claude 3.5 Sonnet with cache reads and mixed writes
        # Input: 1000/1M * $3 = $0.003
        # Output: 500/1M * $15 = $0.0075
        # Cache read: 8000/1M * $0.30 = $0.0024
        # Cache write 5m: 250/1M * $3.75 = $0.0009375
        # Cache write 1h: 750/1M * $6.00 = $0.0045
        # Total: $0.0183375
        cost = calculate_cost(
            "claude-3-5-sonnet-20241022",
            1000,
            500,
            cache_read_tokens=8000,
            cache_write_5m_tokens=250,
            cache_write_1h_tokens=750,
        )

        assert abs(cost["cache_read_cost"] - 0.0024) < 0.0001
        assert abs(cost["cache_write_cost"] - 0.0054375) < 0.0001
        assert abs(cost["cache_cost"] - 0.0078375) < 0.0001
        # Savings: 8000/1M * $3 * 0.9 = $0.0216
        assert abs(cost["cache_savings"] - 0.0216) < 0.0001
        assert abs(cost["total_cost"] - 0.0183375) < 0.0001

    def test_anthropic_streaming_fallback(self) -> None:
        """Test fallback when only total cache_creation available (streaming)."""
        # When TTL-specific tokens not available, should use worst-case (1h) pricing
        # This is handled in sdk.py and tui/app.py, but we can test the function
        # Claude 3.5 Haiku with 1000 cache writes (no TTL breakdown)
        # Should use 1h pricing: 1000/1M * $2.00 = $0.002
        cost = calculate_cost(
            "claude-3-5-haiku-20241022",
            500,
            200,
            cache_write_1h_tokens=1000,  # Worst-case fallback
        )

        assert cost["cache_write_cost"] == 0.002
        assert cost["cache_cost"] == 0.002

    def test_anthropic_defensive_token_counting(self) -> None:
        """Test defensive logic if Anthropic changes to include cache in input_tokens.

        REGRESSION TEST: This detects if Anthropic's API changes semantics.
        Current behavior: input_tokens excludes cached tokens.
        If they change to include cached tokens, this defensive logic prevents double-charging.
        """
        # Scenario 1: Current behavior (input_tokens excludes cache) - should work as-is
        cost1 = calculate_cost(
            "claude-3-5-haiku-20241022",
            input_tokens=100,  # Base only (current behavior)
            output_tokens=500,
            cache_read_tokens=8000,
            cache_write_5m_tokens=250,
        )
        assert cost1["input_cost"] == 0.0001  # 100 tokens @ $1/M
        assert "_defensive_adjustment" not in cost1  # No adjustment needed

        # Scenario 2: Hypothetical upstream change (input_tokens includes cache)
        # If Anthropic changes to: input_tokens = base + cache_read + cache_creation
        # Then: input_tokens = 100 + 8000 + 250 = 8350
        # Our defensive logic should detect this and subtract cache tokens
        cost2 = calculate_cost(
            "claude-3-5-haiku-20241022",
            input_tokens=8350,  # Total (hypothetical future behavior)
            output_tokens=500,
            cache_read_tokens=8000,
            cache_write_5m_tokens=250,
        )
        # Should subtract cache tokens: 8350 - 8000 - 250 = 100
        assert cost2["input_cost"] == 0.0001  # Still 100 base tokens @ $1/M
        assert cost2["_defensive_adjustment"] is True  # Flag set
        assert cost2["base_input_tokens"] == 100  # Calculated base

        # Total cost should be same in both scenarios (defensive logic working)
        assert abs(cost1["total_cost"] - cost2["total_cost"]) < 0.00001

    def test_ollama_model_zero_cost(self) -> None:
        """Test that Ollama models have zero cost."""
        cost = calculate_cost("llama2", 10000, 5000)

        assert cost["pricing_available"] is True
        assert cost["total_cost"] == 0.0
        assert cost["input_cost"] == 0.0
        assert cost["output_cost"] == 0.0

    def test_openai_langchain_fallback(self) -> None:
        """Test that OpenAI models fall back to LangChain pricing."""
        # This should use LangChain's pricing data
        cost = calculate_cost("gpt-4o", 1000, 500)

        # Should have pricing available from either source
        assert cost["pricing_available"] is True
        assert cost["source"] in ["consoul", "langchain"]
        assert cost["total_cost"] > 0

    def test_unknown_model_defaults_to_free(self) -> None:
        """Test that unknown models default to free (Ollama) pricing."""
        cost = calculate_cost("unknown-model-xyz", 1000, 500)

        # Models without provider prefix are treated as Ollama
        assert cost["pricing_available"] is True
        assert cost["source"] == "consoul"
        assert cost["total_cost"] == 0.0


class TestCostAccuracy:
    """Test cost calculation accuracy with real-world scenarios."""

    def test_small_message_cost(self) -> None:
        """Test cost for a small message (typical chat)."""
        # Typical small message: ~100 input, ~50 output tokens
        cost = calculate_cost("claude-3-5-haiku-20241022", 100, 50)

        # Should be very small cost
        assert cost["total_cost"] < 0.001
        assert cost["total_cost"] > 0

    def test_large_context_cost(self) -> None:
        """Test cost for large context window."""
        # Large context: 100K input, 1K output tokens
        cost = calculate_cost("claude-3-5-sonnet-20241022", 100_000, 1_000)

        # Input: 100K/1M * $3 = $0.30
        # Output: 1K/1M * $15 = $0.015
        # Total: $0.315
        assert (
            abs(cost["total_cost"] - 0.315) < 0.0001
        )  # Allow for floating point precision

    def test_cost_precision(self) -> None:
        """Test that cost calculations maintain precision."""
        # Very small token counts
        cost = calculate_cost("claude-3-5-haiku-20241022", 1, 1)

        # Should have non-zero cost with proper precision
        assert cost["total_cost"] > 0
        assert isinstance(cost["total_cost"], float)
