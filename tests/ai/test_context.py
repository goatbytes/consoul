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


class TestOllamaModelDetection:
    """Tests for Ollama model detection and HuggingFace tokenizer integration."""

    def test_is_ollama_model_detection(self):
        """Test _is_ollama_model correctly identifies Ollama models."""
        from consoul.ai.context import _is_ollama_model

        # Should detect Ollama models
        assert _is_ollama_model("llama3:8b")
        assert _is_ollama_model("llama3.1:70b")
        assert _is_ollama_model("granite4:3b")
        assert _is_ollama_model("qwen2.5:7b")
        assert _is_ollama_model("mistral:7b")
        assert _is_ollama_model("mixtral:8x7b")
        assert _is_ollama_model("phi:latest")
        assert _is_ollama_model("codellama:13b")

        # Should not detect non-Ollama models
        assert not _is_ollama_model("gpt-4o")
        assert not _is_ollama_model("claude-3-5-sonnet")
        assert not _is_ollama_model("gemini-2.5-pro")

    def test_ollama_model_uses_huggingface_tokenizer(self):
        """Test Ollama models try to use HuggingFace tokenizer."""
        from unittest.mock import MagicMock, patch

        # Mock the HuggingFace tokenizer module
        with patch("consoul.ai.context._create_huggingface_counter") as mock_hf_counter:
            mock_hf_counter.return_value = MagicMock()

            create_token_counter("granite4:3b")

            # Should attempt to use HuggingFace tokenizer
            mock_hf_counter.assert_called_once_with("granite4:3b")

    def test_ollama_model_fallback_to_approximation(self):
        """Test Ollama models fall back to approximation when HF unavailable."""
        from unittest.mock import patch

        # Mock _create_huggingface_counter to raise ImportError
        with patch(
            "consoul.ai.context._create_huggingface_counter",
            side_effect=ImportError("transformers not installed"),
        ):
            counter = create_token_counter("granite4:3b")

            # Should fall back to approximation counter
            messages = [HumanMessage(content="test message")]  # 12 chars
            tokens = counter(messages)

            # Character approximation: 12 chars // 4 = 3 tokens
            assert tokens == 3

    def test_ollama_model_fallback_on_model_not_mapped(self):
        """Test fallback when Ollama model not in HuggingFace mapping."""
        from unittest.mock import patch

        # Mock _create_huggingface_counter to raise ValueError
        with patch(
            "consoul.ai.context._create_huggingface_counter",
            side_effect=ValueError("Model not found in mapping"),
        ):
            # Use an Ollama-style model name that's not in mapping
            counter = create_token_counter("custom-local-model:7b")

            # Should fall back to approximation counter
            messages = [HumanMessage(content="Hello world")]  # 11 chars
            tokens = counter(messages)

            # Character approximation: 11 chars // 4 = 2 tokens
            assert tokens == 2

    def test_chat_ollama_model_instance_with_hf_unavailable(self):
        """Test ChatOllama model instances use approximation when HF unavailable."""
        from unittest.mock import patch

        # Mock ChatOllama model
        mock_model = MagicMock()
        mock_model.__class__.__name__ = "ChatOllama"

        # Mock HF tokenizer as unavailable
        with patch(
            "consoul.ai.context._create_huggingface_counter",
            side_effect=ImportError("transformers not available"),
        ):
            counter = create_token_counter("granite4:3b", model=mock_model)

            # Should use approximation counter, not model's slow token counter
            messages = [HumanMessage(content="test")]  # 4 chars
            tokens = counter(messages)

            # Character approximation: 4 chars // 4 = 1 token
            assert tokens == 1

    def test_openai_model_still_uses_tiktoken(self):
        """Test OpenAI models still use tiktoken (not affected by Ollama changes)."""
        pytest.importorskip("tiktoken")

        counter = create_token_counter("gpt-4o")

        # Should use tiktoken, not HuggingFace or approximation
        messages = [HumanMessage(content="Hello world")]
        tokens = counter(messages)

        # tiktoken should give accurate count (not char approximation)
        # "Hello world" = ~8 tokens with tiktoken, not 11//4 = 2
        assert tokens > 2


class TestLlamaCppContextCaching:
    """Tests for LlamaCpp GGUF model context size caching."""

    def test_save_and_retrieve_llamacpp_context(self, tmp_path, monkeypatch):
        """Test saving and retrieving context size for GGUF model."""
        from consoul.ai.context import (
            _get_llamacpp_context_length,
            save_llamacpp_context_length,
        )

        # Use tmp_path for cache file
        monkeypatch.setenv("HOME", str(tmp_path))

        # Create .consoul directory
        (tmp_path / ".consoul").mkdir()

        # Test model path
        model_path = "/Users/test/.lmstudio/models/test-model.gguf"
        n_ctx = 8192

        # Save context size
        save_llamacpp_context_length(model_path, n_ctx)

        # Retrieve context size
        retrieved = _get_llamacpp_context_length(model_path)
        assert retrieved == n_ctx

    def test_llamacpp_context_uses_absolute_path(self, tmp_path, monkeypatch):
        """Test that relative and absolute paths both work."""
        import os

        from consoul.ai.context import (
            _get_llamacpp_context_length,
            save_llamacpp_context_length,
        )

        # Use tmp_path for cache file
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".consoul").mkdir()

        # Create a test GGUF file
        test_file = tmp_path / "model.gguf"
        test_file.touch()

        # Change to tmp_path directory so relative path works
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Save with relative path
            save_llamacpp_context_length("model.gguf", 16384)

            # Retrieve with absolute path should work
            retrieved = _get_llamacpp_context_length(str(test_file))
            assert retrieved == 16384

            # Retrieve with relative path should also work
            retrieved2 = _get_llamacpp_context_length("model.gguf")
            assert retrieved2 == 16384
        finally:
            os.chdir(original_cwd)

    def test_get_token_limit_for_gguf_path(self, tmp_path, monkeypatch):
        """Test get_model_token_limit works with GGUF file paths."""
        from consoul.ai.context import (
            get_model_token_limit,
            save_llamacpp_context_length,
        )

        # Use tmp_path for cache
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".consoul").mkdir()

        model_path = "/path/to/custom-model.gguf"
        n_ctx = 32768

        # Cache the context size
        save_llamacpp_context_length(model_path, n_ctx)

        # get_model_token_limit should find it
        limit = get_model_token_limit(model_path)
        assert limit == n_ctx

    def test_gguf_path_without_cache_returns_default(self):
        """Test that uncached GGUF paths return default limit."""
        from consoul.ai.context import get_model_token_limit

        # Path that doesn't exist in cache
        limit = get_model_token_limit("/nonexistent/model.gguf")
        assert limit == 4096  # DEFAULT_TOKEN_LIMIT

    def test_llamacpp_cache_handles_errors_gracefully(self, monkeypatch):
        """Test that cache operations handle errors gracefully."""
        from consoul.ai.context import (
            _get_llamacpp_context_length,
            save_llamacpp_context_length,
        )

        # Make Path operations fail
        def mock_path_fail(*args, **kwargs):
            raise OSError("Permission denied")

        monkeypatch.setattr("pathlib.Path.resolve", mock_path_fail)

        # Should not raise exceptions
        save_llamacpp_context_length("/some/path.gguf", 8192)
        result = _get_llamacpp_context_length("/some/path.gguf")
        assert result is None
