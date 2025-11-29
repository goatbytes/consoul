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

    def test_prompt_caching_cost(self) -> None:
        """Test cost calculation with prompt caching."""
        # Claude 3.5 Haiku with 1000 cached tokens
        # Input: 1000/1M * $1 = $0.001
        # Output: 500/1M * $5 = $0.0025
        # Cache: 2000/1M * $0.10 = $0.0002
        # Total: $0.0037
        cost = calculate_cost(
            "claude-3-5-haiku-20241022", 1000, 500, cached_tokens=2000
        )

        assert cost["cache_cost"] == 0.0002
        assert cost["total_cost"] == 0.0037

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
