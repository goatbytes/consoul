"""Tests for HuggingFace tokenizer-based token counting."""

import json
from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


class TestHuggingFaceTokenCounter:
    """Tests for HuggingFaceTokenCounter class."""

    def test_model_mapping_coverage(self):
        """Test that model mapping includes common Ollama models."""
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        mapping = HuggingFaceTokenCounter.HUGGINGFACE_MODEL_MAP

        # Granite models
        assert "granite4:3b" in mapping
        assert "granite4:1b" in mapping
        assert "granite4:32b" in mapping

        # Llama models
        assert "llama3:8b" in mapping
        assert "llama3.1:70b" in mapping
        assert "llama3.2:3b" in mapping

        # Qwen models
        assert "qwen2.5:7b" in mapping
        assert "qwen3:3b" in mapping

        # Mistral models
        assert "mistral:7b" in mapping
        assert "mistral-nemo:12b" in mapping
        assert "mixtral:8x7b" in mapping

    @patch("transformers.AutoTokenizer")
    def test_initialization_success(self, mock_auto_tokenizer):
        """Test successful tokenizer initialization."""
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 100352
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        counter = HuggingFaceTokenCounter("granite4:3b")

        assert counter.model_name == "granite4:3b"
        assert counter.tokenizer == mock_tokenizer
        mock_auto_tokenizer.from_pretrained.assert_called_once_with(
            "ibm-granite/granite-4.0-micro"
        )

    def test_initialization_transformers_not_installed(self):
        """Test initialization fails gracefully when transformers not installed."""
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        with (
            patch.dict("sys.modules", {"transformers": None}),
            pytest.raises(ImportError, match="transformers package required"),
        ):
            HuggingFaceTokenCounter("granite4:3b")

    def test_initialization_model_not_in_mapping(self):
        """Test initialization fails for unmapped models."""
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        with pytest.raises(ValueError, match="not found in HuggingFace model mapping"):
            HuggingFaceTokenCounter("unknown-model:1b")

    @patch("transformers.AutoTokenizer")
    def test_count_tokens_simple_message(self, mock_auto_tokenizer):
        """Test token counting for simple message."""
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        # Mock tokenizer with encode method
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 100352
        # Mock encode to return 4 tokens for "Hello world"
        mock_tokenizer.encode.return_value = [1234, 5678, 9012, 3456]
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        counter = HuggingFaceTokenCounter("granite4:3b")

        messages = [HumanMessage(content="Hello world")]
        tokens = counter.count_tokens(messages)

        # Expected: 4 (message overhead) + 4 (content tokens) + 2 (priming) = 10
        assert tokens == 10
        mock_tokenizer.encode.assert_called_once_with(
            "Hello world", add_special_tokens=False
        )

    @patch("transformers.AutoTokenizer")
    def test_count_tokens_multiple_messages(self, mock_auto_tokenizer):
        """Test token counting for conversation with multiple messages."""
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 100352
        # Return different token counts for different content
        mock_tokenizer.encode.side_effect = [
            [1, 2, 3, 4, 5],  # 5 tokens for system message
            [6, 7, 8],  # 3 tokens for user message
            [9, 10, 11, 12],  # 4 tokens for assistant message
        ]
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        counter = HuggingFaceTokenCounter("granite4:3b")

        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="What is 2+2?"),
            AIMessage(content="2+2 equals 4."),
        ]
        tokens = counter.count_tokens(messages)

        # Expected: 3 messages x 4 overhead + (5 + 3 + 4) content + 2 priming = 26
        assert tokens == 26

    @patch("transformers.AutoTokenizer")
    def test_count_tokens_multimodal_content(self, mock_auto_tokenizer):
        """Test token counting handles multimodal content (text + images)."""
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 100352
        # Should only encode the text parts, not images
        mock_tokenizer.encode.return_value = [1, 2, 3]  # 3 tokens for text
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        counter = HuggingFaceTokenCounter("granite4:3b")

        # Message with both text and image
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": "What is this?"},
                    {"type": "image_url", "image_url": "data:image/png;base64,abc123"},
                ]
            )
        ]
        tokens = counter.count_tokens(messages)

        # Expected: 4 (overhead) + 3 (text tokens, image ignored) + 2 (priming) = 9
        assert tokens == 9
        # Should only encode text, not image data
        mock_tokenizer.encode.assert_called_once()

    @patch("transformers.AutoTokenizer")
    def test_count_tokens_empty_message(self, mock_auto_tokenizer):
        """Test token counting for empty message."""
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 100352
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        counter = HuggingFaceTokenCounter("granite4:3b")

        messages = [HumanMessage(content="")]
        tokens = counter.count_tokens(messages)

        # Expected: 4 (overhead) + 0 (no content) + 2 (priming) = 6
        assert tokens == 6
        # Should not call encode for empty content
        mock_tokenizer.encode.assert_not_called()


class TestCreateHuggingFaceTokenCounter:
    """Tests for create_huggingface_token_counter factory function."""

    @patch("transformers.AutoTokenizer")
    def test_factory_function_returns_callable(self, mock_auto_tokenizer):
        """Test factory function returns a callable."""
        from consoul.ai.tokenizers import create_huggingface_token_counter

        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 100352
        mock_tokenizer.encode.return_value = [1, 2, 3, 4]
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        counter_fn = create_huggingface_token_counter("granite4:3b")

        assert callable(counter_fn)

        # Test it works
        messages = [HumanMessage(content="Hello")]
        tokens = counter_fn(messages)

        # Expected: 4 (overhead) + 4 (content) + 2 (priming) = 10
        assert tokens == 10

    @patch("transformers.AutoTokenizer")
    def test_factory_different_models(self, mock_auto_tokenizer):
        """Test factory function works for different model types."""
        from consoul.ai.tokenizers import create_huggingface_token_counter

        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 100352
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        # Test granite model
        granite_counter = create_huggingface_token_counter("granite4:3b")
        assert callable(granite_counter)

        # Test llama model
        llama_counter = create_huggingface_token_counter("llama3:8b")
        assert callable(llama_counter)

        # Test qwen model
        qwen_counter = create_huggingface_token_counter("qwen2.5:7b")
        assert callable(qwen_counter)

        # Verify correct HF models were loaded
        assert mock_auto_tokenizer.from_pretrained.call_count == 3
        calls = [
            call[0][0] for call in mock_auto_tokenizer.from_pretrained.call_args_list
        ]
        assert "ibm-granite/granite-4.0-micro" in calls
        assert "meta-llama/Llama-3.3-8B-Instruct" in calls
        assert "Qwen/Qwen2.5-7B-Instruct" in calls


class TestCreateCustomTokenIdsEncoder:
    """Tests for create_custom_token_ids_encoder function."""

    @patch("transformers.AutoTokenizer")
    def test_encoder_returns_token_ids(self, mock_auto_tokenizer):
        """Test encoder returns list of token IDs."""
        from consoul.ai.tokenizers import create_custom_token_ids_encoder

        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 100352
        mock_tokenizer.encode.return_value = [1234, 5678, 9012]
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        encoder = create_custom_token_ids_encoder("granite4:3b")

        # Test encoding a string
        token_ids = encoder("Hello world")

        assert token_ids == [1234, 5678, 9012]
        mock_tokenizer.encode.assert_called_once_with(
            "Hello world", add_special_tokens=False
        )

    @patch("transformers.AutoTokenizer")
    def test_encoder_callable(self, mock_auto_tokenizer):
        """Test encoder is a callable function."""
        from consoul.ai.tokenizers import create_custom_token_ids_encoder

        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 100352
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        encoder = create_custom_token_ids_encoder("llama3:8b")

        assert callable(encoder)


class TestPerformance:
    """Performance-related tests."""

    @patch("transformers.AutoTokenizer")
    def test_tokenizer_caching(self, mock_auto_tokenizer):
        """Test tokenizer is loaded only once and cached."""
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 100352
        mock_tokenizer.encode.return_value = [1, 2, 3]
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        counter = HuggingFaceTokenCounter("granite4:3b")

        # Count tokens multiple times
        messages = [HumanMessage(content="test")]
        for _ in range(5):
            counter.count_tokens(messages)

        # Tokenizer should be loaded only once during init
        assert mock_auto_tokenizer.from_pretrained.call_count == 1


class TestManifestDiscovery:
    """Tests for Tier 2 manifest-based tokenizer discovery."""

    def test_discover_from_manifest_library_model(self, tmp_path):
        """Test discovery from library model manifest."""
        from consoul.ai.tokenizers import discover_hf_model_from_manifest

        # Create fake Ollama manifest structure
        manifest_dir = (
            tmp_path / ".ollama" / "models" / "manifests" / "registry.ollama.ai"
        )
        library_path = manifest_dir / "library" / "granite4" / "latest"
        library_path.parent.mkdir(parents=True)

        # Create manifest with HuggingFace source annotation
        manifest = {
            "layers": [
                {
                    "annotations": {
                        "org.opencontainers.image.source": "https://huggingface.co/ibm-granite/granite-4.0-micro"
                    }
                }
            ]
        }
        library_path.write_text(json.dumps(manifest))

        # Mock Path.home() to use tmp_path
        with patch("consoul.ai.tokenizers.Path.home", return_value=tmp_path):
            result = discover_hf_model_from_manifest("granite4:3b")

        assert result == "ibm-granite/granite-4.0-micro"

    def test_discover_from_manifest_community_model(self, tmp_path):
        """Test discovery from community model manifest."""
        from consoul.ai.tokenizers import discover_hf_model_from_manifest

        # Create fake community model manifest
        manifest_dir = (
            tmp_path / ".ollama" / "models" / "manifests" / "registry.ollama.ai"
        )
        community_path = manifest_dir / "community" / "custom-model" / "latest"
        community_path.parent.mkdir(parents=True)

        manifest = {
            "layers": [
                {
                    "annotations": {
                        "org.opencontainers.image.source": "https://huggingface.co/user/custom-model"
                    }
                }
            ]
        }
        community_path.write_text(json.dumps(manifest))

        with patch("consoul.ai.tokenizers.Path.home", return_value=tmp_path):
            result = discover_hf_model_from_manifest("custom-model:latest")

        assert result == "user/custom-model"

    def test_discover_no_manifest(self, tmp_path):
        """Test discovery returns None when manifest doesn't exist."""
        from consoul.ai.tokenizers import discover_hf_model_from_manifest

        with patch("consoul.ai.tokenizers.Path.home", return_value=tmp_path):
            result = discover_hf_model_from_manifest("nonexistent:1b")

        assert result is None

    def test_discover_manifest_no_hf_source(self, tmp_path):
        """Test discovery returns None when manifest has no HF source."""
        from consoul.ai.tokenizers import discover_hf_model_from_manifest

        manifest_dir = (
            tmp_path / ".ollama" / "models" / "manifests" / "registry.ollama.ai"
        )
        library_path = manifest_dir / "library" / "test" / "latest"
        library_path.parent.mkdir(parents=True)

        # Manifest without HF source
        manifest = {"layers": [{"annotations": {}}]}
        library_path.write_text(json.dumps(manifest))

        with patch("consoul.ai.tokenizers.Path.home", return_value=tmp_path):
            result = discover_hf_model_from_manifest("test:1b")

        assert result is None

    @patch("transformers.AutoTokenizer")
    def test_tokenizer_uses_manifest_discovery_fallback(
        self, mock_auto_tokenizer, tmp_path
    ):
        """Test that unmapped models fall back to manifest discovery."""
        from consoul.ai.tokenizers import HuggingFaceTokenCounter

        # Create manifest for unmapped model
        manifest_dir = (
            tmp_path / ".ollama" / "models" / "manifests" / "registry.ollama.ai"
        )
        library_path = manifest_dir / "library" / "unmapped" / "latest"
        library_path.parent.mkdir(parents=True)

        manifest = {
            "layers": [
                {
                    "annotations": {
                        "org.opencontainers.image.source": "https://huggingface.co/test/unmapped-model"
                    }
                }
            ]
        }
        library_path.write_text(json.dumps(manifest))

        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.vocab_size = 50000
        mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

        with patch("consoul.ai.tokenizers.Path.home", return_value=tmp_path):
            counter = HuggingFaceTokenCounter("unmapped:1b")

        # Should have loaded tokenizer from discovered HF model
        assert counter.tokenizer == mock_tokenizer
        mock_auto_tokenizer.from_pretrained.assert_called_once_with(
            "test/unmapped-model"
        )
