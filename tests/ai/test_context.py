"""Tests for conversation context and token counting utilities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from consoul.ai.context import (
    count_message_tokens,
    create_token_counter,
    get_model_token_limit,
)


class TestModelTokenLimits:
    """Tests for model token limit lookup."""

    def test_get_known_openai_model_limit(self):
        """Test getting token limit for known OpenAI models."""
        assert get_model_token_limit("gpt-4o") == 128_000
        assert get_model_token_limit("gpt-4") == 8_192
        assert get_model_token_limit("gpt-3.5-turbo") == 16_385

    def test_get_known_anthropic_model_limit(self):
        """Test getting token limit for known Anthropic models."""
        # Claude 4
        assert get_model_token_limit("claude-sonnet-4-5") == 200_000
        assert get_model_token_limit("claude-sonnet-4") == 1_000_000
        # Claude 3.5
        assert get_model_token_limit("claude-3-5-sonnet-20241022") == 200_000
        assert get_model_token_limit("claude-3-5-sonnet") == 200_000
        # Claude 3
        assert get_model_token_limit("claude-3-opus") == 200_000
        assert get_model_token_limit("claude-3-sonnet") == 200_000
        assert get_model_token_limit("claude-3-haiku") == 200_000

    def test_get_known_google_model_limit(self):
        """Test getting token limit for known Google models."""
        # Gemini 2.5
        assert get_model_token_limit("gemini-2.5-pro") == 1_000_000
        assert (
            get_model_token_limit("gemini-2.5-flash") == 1_048_576
        )  # API spec: 1,048,576
        # Gemini 1.5
        assert get_model_token_limit("gemini-1.5-pro") == 2_000_000
        assert get_model_token_limit("gemini-1.5-flash") == 1_000_000
        # Gemini 1.0
        assert get_model_token_limit("gemini-pro") == 32_000

    def test_get_unknown_model_returns_default(self):
        """Test that unknown models return conservative default limit."""
        assert get_model_token_limit("unknown-model-xyz") == 4_096
        assert get_model_token_limit("custom-fine-tuned-model") == 4_096

    def test_get_model_with_version_suffix(self):
        """Test partial matching for models with version suffixes."""
        # OpenAI versioned models
        assert get_model_token_limit("gpt-4o-2024-08-06") == 128_000
        # Anthropic versioned models (from examples/README.md)
        assert get_model_token_limit("claude-sonnet-4-5-20250929") == 200_000
        assert get_model_token_limit("claude-3-5-sonnet-20241022") == 200_000
        assert get_model_token_limit("claude-3-opus-20240229") == 200_000
        assert get_model_token_limit("claude-3-sonnet-20240229") == 200_000
        assert get_model_token_limit("claude-3-haiku-20240307") == 200_000


class TestTokenCounterCreation:
    """Tests for token counter factory."""

    def test_create_openai_counter_uses_tiktoken(self):
        """Test that OpenAI models use tiktoken for token counting."""
        # Skip if tiktoken not available (it's optional in the implementation)
        pytest.importorskip("tiktoken")

        # Create counter for OpenAI model
        counter = create_token_counter("gpt-4o")

        # Test the counter (actual tiktoken will be used)
        messages = [HumanMessage(content="test")]
        tokens = counter(messages)

        # Should return a positive token count
        assert tokens > 0

    def test_create_openai_counter_fallback_encoding(self):
        """Test fallback to cl100k_base when model encoding not found."""
        # Skip if tiktoken not available
        pytest.importorskip("tiktoken")

        # Create counter for unknown OpenAI model
        counter = create_token_counter("gpt-unknown")

        # Should still work (fallback to cl100k_base)
        messages = [HumanMessage(content="test")]
        tokens = counter(messages)

        assert tokens > 0

    def test_create_non_openai_counter_uses_approximation(self):
        """Test that non-OpenAI models use character approximation."""
        # Create counter for Anthropic model (no model instance provided)
        counter = create_token_counter("claude-3-5-sonnet")

        # Test with known character count
        # "Hello world" = 11 chars → ~2-3 tokens (11 // 4 = 2)
        messages = [HumanMessage(content="Hello world")]
        tokens = counter(messages)

        assert tokens == 2  # 11 chars // 4 = 2 tokens

    def test_create_counter_with_model_instance(self):
        """Test counter creation with LangChain model instance."""
        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.return_value = 42

        counter = create_token_counter("claude-3-5-sonnet", model=mock_model)

        messages = [HumanMessage(content="test")]
        tokens = counter(messages)

        # Should use model's token counter
        assert tokens == 42
        mock_model.get_num_tokens_from_messages.assert_called_once_with(messages)

    def test_create_counter_model_method_fails(self):
        """Test fallback when model's token counter fails."""
        mock_model = MagicMock()
        mock_model.get_num_tokens_from_messages.side_effect = Exception("API error")

        counter = create_token_counter("claude-3-5-sonnet", model=mock_model)

        # Should fallback to character approximation
        messages = [HumanMessage(content="1234567890")]  # 10 chars
        tokens = counter(messages)

        assert tokens == 2  # 10 // 4 = 2 tokens


class TestCountMessageTokens:
    """Tests for message token counting convenience function."""

    def test_count_message_tokens_openai(self):
        """Test counting tokens for OpenAI messages."""
        pytest.importorskip("tiktoken")

        messages = [
            SystemMessage(content="system"),
            HumanMessage(content="hello"),
            AIMessage(content="hi"),
        ]

        tokens = count_message_tokens(messages, "gpt-4o")

        # Should return a positive count
        assert tokens > 0

    def test_count_message_tokens_approximation(self):
        """Test counting tokens using character approximation."""
        messages = [
            HumanMessage(content="a" * 100),  # 100 chars = 25 tokens
            AIMessage(content="b" * 200),  # 200 chars = 50 tokens
        ]

        tokens = count_message_tokens(messages, "claude-3-5-sonnet")

        # 300 chars total // 4 = 75 tokens
        assert tokens == 75

    def test_count_empty_messages(self):
        """Test counting tokens in empty message list."""
        pytest.importorskip("tiktoken")

        messages = []
        tokens = count_message_tokens(messages, "gpt-4o")

        # Empty list should return a small count (priming tokens)
        assert tokens >= 0


class TestDeterministicTokenCounting:
    """Tests for deterministic token counting in tests."""

    def test_fixed_strings_return_consistent_counts(self):
        """Test that same strings always return same token counts."""
        pytest.importorskip("tiktoken")

        counter = create_token_counter("gpt-4o")

        # Test multiple times with same input
        messages = [HumanMessage(content="test")]

        result1 = counter(messages)
        result2 = counter(messages)
        result3 = counter(messages)

        # Should be deterministic
        assert result1 == result2 == result3
