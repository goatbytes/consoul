"""Unit tests for ModelService.

Tests model initialization, switching, tool binding, and model discovery.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest


class TestModelServiceInitialization:
    """Test ModelService initialization."""

    def test_init_basic(self) -> None:
        """Test basic ModelService initialization."""
        from consoul.sdk.services.model import ModelService

        # Create mocks
        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        # Create service
        service = ModelService(model=mock_model, config=mock_config, tool_service=None)

        assert service._model is mock_model
        assert service.config is mock_config
        assert service.tool_service is None
        assert service.current_model_id == "gpt-4o"

    def test_init_with_tool_service(self) -> None:
        """Test ModelService initialization with tool service."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "claude-3-5-sonnet-20241022"
        mock_tool_service = Mock()

        service = ModelService(
            model=mock_model, config=mock_config, tool_service=mock_tool_service
        )

        assert service.tool_service is mock_tool_service


class TestFromConfig:
    """Test ModelService.from_config() factory method."""

    @patch("consoul.ai.get_chat_model")
    def test_from_config_basic(
        self, mock_get_chat_model: Mock, mock_config: Mock
    ) -> None:
        """Test factory with basic configuration."""
        from consoul.sdk.services.model import ModelService

        # Setup mocks
        mock_model = Mock()
        mock_model_config = Mock()
        mock_config.get_current_model_config = Mock(return_value=mock_model_config)
        mock_get_chat_model.return_value = mock_model

        service = ModelService.from_config(mock_config, tool_service=None)

        assert service is not None
        assert service._model is mock_model
        assert service.config is mock_config
        mock_get_chat_model.assert_called_once_with(
            mock_model_config, config=mock_config
        )

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.providers.supports_tool_calling")
    def test_from_config_with_tools(
        self,
        mock_supports_tools: Mock,
        mock_get_chat_model: Mock,
        mock_config: Mock,
    ) -> None:
        """Test factory with tool service (tools bound to model)."""
        from consoul.sdk.services.model import ModelService

        # Setup mocks
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model_with_tools)
        mock_model_config = Mock()
        mock_config.get_current_model_config = Mock(return_value=mock_model_config)
        mock_config.current_model = "gpt-4o"
        mock_get_chat_model.return_value = mock_model
        mock_supports_tools.return_value = True

        # Create mock tool service with enabled tools
        mock_tool_service = Mock()
        mock_tool_metadata = [Mock(tool=Mock(name="bash_execute"))]
        mock_tool_service.tool_registry.list_tools = Mock(
            return_value=mock_tool_metadata
        )

        service = ModelService.from_config(mock_config, tool_service=mock_tool_service)

        assert service is not None
        # Verify tools were bound
        mock_model.bind_tools.assert_called_once()


class TestGetModel:
    """Test getting current model."""

    def test_get_model(self) -> None:
        """Test getting current model instance."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        model = service.get_model()

        assert model is mock_model


class TestSwitchModel:
    """Test model switching functionality."""

    @patch("consoul.ai.get_chat_model")
    def test_switch_model_basic(
        self, mock_get_chat_model: Mock, mock_config: Mock
    ) -> None:
        """Test switching to different model."""
        from consoul.sdk.services.model import ModelService

        # Setup initial model
        initial_model = Mock()
        new_model = Mock()
        mock_model_config = Mock()
        mock_config.get_current_model_config = Mock(return_value=mock_model_config)
        mock_config.current_model = "gpt-4o"
        mock_get_chat_model.return_value = new_model

        service = ModelService(initial_model, mock_config)

        # Switch model
        result = service.switch_model("claude-3-5-sonnet-20241022")

        assert result is new_model
        assert service._model is new_model
        assert service.current_model_id == "claude-3-5-sonnet-20241022"
        assert mock_config.current_model == "claude-3-5-sonnet-20241022"

    @patch("consoul.ai.get_chat_model")
    def test_switch_model_with_provider(
        self, mock_get_chat_model: Mock, mock_config: Mock
    ) -> None:
        """Test switching model with explicit provider."""
        from consoul.config.models import Provider
        from consoul.sdk.services.model import ModelService

        initial_model = Mock()
        new_model = Mock()
        mock_model_config = Mock()
        mock_config.get_current_model_config = Mock(return_value=mock_model_config)
        mock_config.current_model = "gpt-4o"
        mock_config.current_provider = Provider.OPENAI
        mock_get_chat_model.return_value = new_model

        service = ModelService(initial_model, mock_config)

        # Switch with provider override
        service.switch_model("claude-3-5-sonnet-20241022", provider="anthropic")

        assert mock_config.current_provider == Provider("anthropic")

    @patch("consoul.ai.get_chat_model")
    @patch("consoul.ai.providers.supports_tool_calling")
    def test_switch_model_rebinds_tools(
        self,
        mock_supports_tools: Mock,
        mock_get_chat_model: Mock,
        mock_config: Mock,
    ) -> None:
        """Test switching model re-binds tools if tool service exists."""
        from consoul.sdk.services.model import ModelService

        # Setup mocks
        initial_model = Mock()
        new_model = Mock()
        new_model_with_tools = Mock()
        new_model.bind_tools = Mock(return_value=new_model_with_tools)
        mock_model_config = Mock()
        mock_config.get_current_model_config = Mock(return_value=mock_model_config)
        mock_config.current_model = "gpt-4o"
        mock_get_chat_model.return_value = new_model
        mock_supports_tools.return_value = True

        # Create tool service
        mock_tool_service = Mock()
        mock_tool_metadata = [Mock(tool=Mock(name="bash_execute"))]
        mock_tool_service.tool_registry.list_tools = Mock(
            return_value=mock_tool_metadata
        )

        service = ModelService(
            initial_model, mock_config, tool_service=mock_tool_service
        )

        # Switch model
        service.switch_model("claude-3-5-sonnet-20241022")

        # Verify tools were re-bound
        new_model.bind_tools.assert_called_once()


class TestBindTools:
    """Test tool binding functionality."""

    @patch("consoul.ai.providers.supports_tool_calling")
    def test_bind_tools_success(self, mock_supports_tools: Mock) -> None:
        """Test successful tool binding."""
        from consoul.sdk.services.model import ModelService

        # Setup mocks
        mock_model = Mock()
        mock_model_with_tools = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model_with_tools)
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_supports_tools.return_value = True

        # Create tool service with enabled tools
        mock_tool_service = Mock()
        mock_tool = Mock(name="bash_execute")
        mock_tool_metadata = [Mock(tool=mock_tool)]
        mock_tool_service.tool_registry.list_tools = Mock(
            return_value=mock_tool_metadata
        )

        service = ModelService(mock_model, mock_config, tool_service=mock_tool_service)

        # Bind tools
        service._bind_tools()

        # Verify tools bound
        mock_model.bind_tools.assert_called_once_with([mock_tool])
        assert service._model is mock_model_with_tools

    @patch("consoul.ai.providers.supports_tool_calling")
    def test_bind_tools_no_tool_support(self, mock_supports_tools: Mock) -> None:
        """Test tool binding skipped for models without tool support."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-3.5-turbo"  # Older model
        mock_supports_tools.return_value = False

        mock_tool_service = Mock()
        mock_tool_metadata = [Mock(tool=Mock())]
        mock_tool_service.tool_registry.list_tools = Mock(
            return_value=mock_tool_metadata
        )

        service = ModelService(mock_model, mock_config, tool_service=mock_tool_service)

        # Bind tools (should skip)
        service._bind_tools()

        # Verify bind_tools NOT called
        mock_model.bind_tools.assert_not_called()

    def test_bind_tools_no_enabled_tools(self) -> None:
        """Test tool binding skipped when no enabled tools."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        mock_tool_service = Mock()
        mock_tool_service.tool_registry.list_tools = Mock(return_value=[])  # No tools

        service = ModelService(mock_model, mock_config, tool_service=mock_tool_service)

        # Bind tools (should skip)
        service._bind_tools()

        # Verify bind_tools NOT called
        mock_model.bind_tools.assert_not_called()


class TestSupportsVision:
    """Test vision capability detection."""

    def test_supports_vision_from_catalog(self) -> None:
        """Test vision detection from catalog."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"  # Known to support vision

        service = ModelService(mock_model, mock_config)

        # Use patch to return ModelInfo with vision support
        with patch.object(service, "get_current_model_info") as mock_get_info:
            mock_info = Mock()
            mock_info.supports_vision = True
            mock_get_info.return_value = mock_info

            assert service.supports_vision() is True

    def test_supports_vision_fallback_detection(self) -> None:
        """Test vision detection fallback to name matching."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "llava:13b"  # Vision model

        service = ModelService(mock_model, mock_config)

        # Catalog returns None, should use name detection
        with patch.object(service, "get_current_model_info", return_value=None):
            assert service.supports_vision() is True


class TestSupportsTools:
    """Test tool calling capability detection."""

    @patch("consoul.ai.providers.supports_tool_calling")
    def test_supports_tools_true(self, mock_supports_tools: Mock) -> None:
        """Test tool support detection."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_supports_tools.return_value = True

        service = ModelService(mock_model, mock_config)

        assert service.supports_tools() is True
        mock_supports_tools.assert_called_once_with(mock_model)

    @patch("consoul.ai.providers.supports_tool_calling")
    def test_supports_tools_false(self, mock_supports_tools: Mock) -> None:
        """Test tool support detection for models without tools."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-3.5-turbo"
        mock_supports_tools.return_value = False

        service = ModelService(mock_model, mock_config)

        assert service.supports_tools() is False


class TestLocalModelDiscovery:
    """Test local model discovery methods."""

    @patch("consoul.ai.providers.is_ollama_running")
    @patch("consoul.ai.providers.get_ollama_models")
    def test_list_ollama_models(
        self, mock_get_models: Mock, mock_is_running: Mock
    ) -> None:
        """Test Ollama model discovery."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_is_running.return_value = True
        mock_get_models.return_value = [
            {
                "name": "llama3.2:latest",
                "size": 2_000_000_000,
                "context_length": 128000,
            },
            {
                "name": "qwen2.5-coder:7b",
                "size": 4_000_000_000,
                "context_length": 32768,
            },
        ]

        service = ModelService(mock_model, mock_config)

        models = service.list_ollama_models(
            include_context=False, enrich_descriptions=False
        )

        assert len(models) == 2
        assert models[0].name == "llama3.2:latest"
        assert models[0].provider == "ollama"
        assert models[1].name == "qwen2.5-coder:7b"

    @patch("consoul.ai.providers.is_ollama_running")
    def test_list_ollama_models_not_running(self, mock_is_running: Mock) -> None:
        """Test Ollama discovery when service not running."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_is_running.return_value = False

        service = ModelService(mock_model, mock_config)

        models = service.list_ollama_models()

        assert len(models) == 0

    @patch("consoul.ai.providers.get_local_mlx_models")
    def test_list_mlx_models(self, mock_get_models: Mock) -> None:
        """Test MLX model discovery."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_get_models.return_value = [
            {
                "name": "mlx-community/Llama-3.2-3B-Instruct-4bit",
                "size_gb": 1.8,
                "context_size": 128000,
            },
        ]

        service = ModelService(mock_model, mock_config)

        models = service.list_mlx_models()

        assert len(models) == 1
        assert models[0].name == "mlx-community/Llama-3.2-3B-Instruct-4bit"
        assert models[0].provider == "mlx"

    @patch("consoul.ai.providers.get_gguf_models_from_cache")
    def test_list_gguf_models(self, mock_get_models: Mock) -> None:
        """Test GGUF model discovery."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_get_models.return_value = [
            {
                "name": "llama-2-7b-chat.Q4_K_M.gguf",
                "size_gb": 3.8,
                "quant": "Q4_K_M",
                "repo": "TheBloke/Llama-2-7B-Chat-GGUF",
            },
        ]

        service = ModelService(mock_model, mock_config)

        models = service.list_gguf_models()

        assert len(models) == 1
        assert models[0].name == "llama-2-7b-chat.Q4_K_M.gguf"
        assert models[0].provider == "llamacpp"

    @patch("consoul.ai.providers.get_huggingface_local_models")
    def test_list_huggingface_models(self, mock_get_models: Mock) -> None:
        """Test HuggingFace model discovery."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_get_models.return_value = [
            {
                "name": "meta-llama/Llama-3.1-8B-Instruct",
                "size_gb": 8.5,
                "model_type": "safetensors",
                "context_size": 128000,
            },
        ]

        service = ModelService(mock_model, mock_config)

        models = service.list_huggingface_models()

        assert len(models) == 1
        assert models[0].name == "meta-llama/Llama-3.1-8B-Instruct"
        assert models[0].provider == "huggingface"


class TestHelperMethods:
    """Test helper methods."""

    def test_format_context_length_millions(self) -> None:
        """Test formatting context length in millions."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        result = service._format_context_length(2_000_000)

        assert result == "2M"

    def test_format_context_length_thousands(self) -> None:
        """Test formatting context length in thousands."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        result = service._format_context_length(128_000)

        assert result == "128K"

    def test_format_context_length_none(self) -> None:
        """Test formatting None context length."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        result = service._format_context_length(None)

        assert result == "?"

    def test_format_context_length_small(self) -> None:
        """Test formatting small context length."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        result = service._format_context_length(500)

        assert result == "500"

    def test_detect_vision_from_name(self) -> None:
        """Test vision detection from model name."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        assert service._detect_vision_from_name("llava:13b") is True
        assert service._detect_vision_from_name("bakllava:latest") is True
        assert service._detect_vision_from_name("llama3.2:latest") is False

    def test_detect_tool_support_from_name(self) -> None:
        """Test tool support detection from model name."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        assert service._detect_tool_support_from_name("gpt-4o") is True
        assert service._detect_tool_support_from_name("claude-3-5-sonnet") is True
        assert service._detect_tool_support_from_name("nomic-embed-text") is False
        assert service._detect_tool_support_from_name("llama-3-base") is False


class TestProviderDetectionEdgeCases:
    """Test provider detection edge cases and error handling."""

    def test_detect_provider_openai(self) -> None:
        """Test provider detection for OpenAI models."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        assert service._detect_provider("gpt-4o") == "openai"
        assert service._detect_provider("o1-preview") == "openai"
        assert service._detect_provider("o3-mini") == "openai"
        assert service._detect_provider("chatgpt-4o-latest") == "openai"

    def test_detect_provider_anthropic(self) -> None:
        """Test provider detection for Anthropic models."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "claude-3-5-sonnet"

        service = ModelService(mock_model, mock_config)

        assert service._detect_provider("claude-3-5-sonnet-20241022") == "anthropic"
        assert service._detect_provider("claude-opus-4") == "anthropic"

    def test_detect_provider_google(self) -> None:
        """Test provider detection for Google models."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gemini-pro"

        service = ModelService(mock_model, mock_config)

        assert service._detect_provider("gemini-1.5-pro") == "google"
        assert service._detect_provider("gemini-2.0-flash-exp") == "google"

    def test_detect_provider_huggingface(self) -> None:
        """Test provider detection for HuggingFace models."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "meta-llama/Llama-3.1-8B"

        service = ModelService(mock_model, mock_config)

        assert service._detect_provider("meta-llama/Llama-3.1-8B") == "huggingface"
        assert service._detect_provider("mistralai/Mistral-7B") == "huggingface"

    def test_detect_provider_unknown_fallback_to_config(self) -> None:
        """Test provider detection fallback to config for unknown models."""
        from consoul.config.models import Provider
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "unknown-model"
        mock_config.current_provider = Provider.OLLAMA

        service = ModelService(mock_model, mock_config)

        assert service._detect_provider("unknown-model") == "ollama"

    def test_detect_provider_unknown_no_config(self) -> None:
        """Test provider detection when config has no provider."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "unknown-model"
        mock_config.current_provider = None

        service = ModelService(mock_model, mock_config)

        assert service._detect_provider("unknown-model") == "unknown"

    def test_detect_vision_all_patterns(self) -> None:
        """Test vision detection for all known patterns."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "test"

        service = ModelService(mock_model, mock_config)

        # Test all vision indicators
        assert service._detect_vision_from_name("test-vision-model") is True
        assert service._detect_vision_from_name("minicpm-v-2.6") is True
        assert service._detect_vision_from_name("cogvlm-chat") is True
        assert service._detect_vision_from_name("yi-vl-plus") is True
        assert service._detect_vision_from_name("moondream2") is True
        assert service._detect_vision_from_name("omnivision-968m") is True


class TestLocalModelDiscoveryErrors:
    """Test local model discovery error handling."""

    @patch("consoul.ai.providers.is_ollama_running")
    @patch("consoul.ai.providers.get_ollama_models")
    def test_list_ollama_models_exception_handling(
        self, mock_get_models: Mock, mock_is_running: Mock
    ) -> None:
        """Test Ollama discovery handles exceptions gracefully."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_is_running.return_value = True
        mock_get_models.side_effect = Exception("Connection error")

        service = ModelService(mock_model, mock_config)

        models = service.list_ollama_models()

        assert len(models) == 0

    @patch("consoul.ai.providers.is_ollama_running")
    @patch("consoul.ai.providers.get_ollama_models")
    def test_list_ollama_models_with_context_cache(
        self, mock_get_models: Mock, mock_is_running: Mock
    ) -> None:
        """Test Ollama discovery with context cache."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_is_running.return_value = True
        mock_get_models.return_value = [
            {
                "name": "llama3.2:latest",
                "size": 2_000_000_000,
            },
        ]

        service = ModelService(mock_model, mock_config)

        # Mock context cache
        with patch("consoul.ai.context_cache.get_global_cache") as mock_cache:
            mock_cache_instance = Mock()
            mock_cache_instance.get_all.return_value = {"llama3.2:latest": 128000}
            mock_cache.return_value = mock_cache_instance

            models = service.list_ollama_models(use_context_cache=True)

            assert len(models) == 1
            assert models[0].context_window == "128K"

    @patch("consoul.ai.providers.is_ollama_running")
    @patch("consoul.ai.providers.get_ollama_models")
    def test_list_ollama_models_with_library_enrichment(
        self, mock_get_models: Mock, mock_is_running: Mock
    ) -> None:
        """Test Ollama discovery with library description enrichment."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_is_running.return_value = True
        mock_get_models.return_value = [
            {
                "name": "llama3.2:latest",
                "size": 2_000_000_000,
            },
        ]

        service = ModelService(mock_model, mock_config)

        # Mock library fetch
        with patch("consoul.ai.ollama_library.fetch_library_models") as mock_fetch:
            mock_lib_model = Mock()
            mock_lib_model.name = "llama3.2"
            mock_lib_model.description = "Llama 3.2 model from Meta"
            mock_lib_model.supports_vision = False
            mock_lib_model.supports_tools = True
            mock_lib_model.supports_reasoning = False
            mock_fetch.return_value = [mock_lib_model]

            models = service.list_ollama_models(enrich_descriptions=True)

            assert len(models) == 1
            assert "Llama 3.2 model from Meta" in models[0].description

    @patch("consoul.ai.providers.is_ollama_running")
    @patch("consoul.ai.providers.get_ollama_models")
    def test_list_ollama_models_skip_empty_names(
        self, mock_get_models: Mock, mock_is_running: Mock
    ) -> None:
        """Test Ollama discovery skips models with empty names."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_is_running.return_value = True
        mock_get_models.return_value = [
            {"name": "", "size": 2_000_000_000},
            {"name": "llama3.2:latest", "size": 2_000_000_000},
        ]

        service = ModelService(mock_model, mock_config)

        models = service.list_ollama_models()

        assert len(models) == 1
        assert models[0].name == "llama3.2:latest"

    @patch("consoul.ai.providers.get_local_mlx_models")
    def test_list_mlx_models_exception_handling(self, mock_get_models: Mock) -> None:
        """Test MLX discovery handles exceptions gracefully."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_get_models.side_effect = Exception("Directory not found")

        service = ModelService(mock_model, mock_config)

        models = service.list_mlx_models()

        assert len(models) == 0

    @patch("consoul.ai.providers.get_local_mlx_models")
    def test_list_mlx_models_skip_empty_names(self, mock_get_models: Mock) -> None:
        """Test MLX discovery skips models with empty names."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_get_models.return_value = [
            {"name": "", "size_gb": 1.8},
            {
                "name": "mlx-community/Llama-3.2-3B-Instruct-4bit",
                "size_gb": 1.8,
                "context_size": 128000,
            },
        ]

        service = ModelService(mock_model, mock_config)

        models = service.list_mlx_models()

        assert len(models) == 1
        assert models[0].name == "mlx-community/Llama-3.2-3B-Instruct-4bit"

    @patch("consoul.ai.providers.get_gguf_models_from_cache")
    def test_list_gguf_models_exception_handling(self, mock_get_models: Mock) -> None:
        """Test GGUF discovery handles exceptions gracefully."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_get_models.side_effect = Exception("Cache error")

        service = ModelService(mock_model, mock_config)

        models = service.list_gguf_models()

        assert len(models) == 0

    @patch("consoul.ai.providers.get_gguf_models_from_cache")
    def test_list_gguf_models_skip_empty_names(self, mock_get_models: Mock) -> None:
        """Test GGUF discovery skips models with empty names."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_get_models.return_value = [
            {"name": "", "size_gb": 3.8},
            {
                "name": "llama-2-7b-chat.Q4_K_M.gguf",
                "size_gb": 3.8,
                "quant": "Q4_K_M",
                "repo": "TheBloke/Llama-2-7B-Chat-GGUF",
            },
        ]

        service = ModelService(mock_model, mock_config)

        models = service.list_gguf_models()

        assert len(models) == 1
        assert models[0].name == "llama-2-7b-chat.Q4_K_M.gguf"

    @patch("consoul.ai.providers.get_huggingface_local_models")
    def test_list_huggingface_models_exception_handling(
        self, mock_get_models: Mock
    ) -> None:
        """Test HuggingFace discovery handles exceptions gracefully."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_get_models.side_effect = Exception("Cache scan failed")

        service = ModelService(mock_model, mock_config)

        models = service.list_huggingface_models()

        assert len(models) == 0

    @patch("consoul.ai.providers.get_huggingface_local_models")
    def test_list_huggingface_models_skip_empty_names(
        self, mock_get_models: Mock
    ) -> None:
        """Test HuggingFace discovery skips models with empty names."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_get_models.return_value = [
            {"name": "", "size_gb": 8.5},
            {
                "name": "meta-llama/Llama-3.1-8B-Instruct",
                "size_gb": 8.5,
                "model_type": "safetensors",
                "context_size": 128000,
            },
        ]

        service = ModelService(mock_model, mock_config)

        models = service.list_huggingface_models()

        assert len(models) == 1
        assert models[0].name == "meta-llama/Llama-3.1-8B-Instruct"


class TestModelMetadataAndPricing:
    """Test model metadata and pricing retrieval from registry."""

    @patch("consoul.registry.list_models")
    def test_list_available_models_all(self, mock_list_models: Mock) -> None:
        """Test listing all available models from registry."""
        from consoul.sdk.services.model import ModelService

        # Create mock registry model
        mock_entry = Mock()
        mock_entry.metadata.id = "gpt-4o"
        mock_entry.metadata.name = "GPT-4o"
        mock_entry.metadata.provider = "openai"
        mock_entry.metadata.context_window = 128000
        mock_entry.metadata.description = "Most advanced GPT-4o model"
        mock_entry.metadata.max_output_tokens = 16384
        mock_entry.metadata.created = Mock()
        mock_entry.metadata.created.isoformat.return_value = "2024-05-13"
        mock_entry.metadata.capabilities = []
        mock_entry.pricing = {}

        mock_list_models.return_value = [mock_entry]

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        models = service.list_available_models()

        assert len(models) == 1
        assert models[0].id == "gpt-4o"
        assert models[0].context_window == "128K"
        mock_list_models.assert_called_once_with(provider=None, active_only=True)

    @patch("consoul.registry.list_models")
    def test_list_available_models_filter_by_provider(
        self, mock_list_models: Mock
    ) -> None:
        """Test listing models filtered by provider."""
        from consoul.sdk.services.model import ModelService

        mock_entry = Mock()
        mock_entry.metadata.id = "claude-sonnet-4-5"
        mock_entry.metadata.name = "Claude Sonnet 4.5"
        mock_entry.metadata.provider = "anthropic"
        mock_entry.metadata.context_window = 200000
        mock_entry.metadata.description = "Claude Sonnet 4.5"
        mock_entry.metadata.max_output_tokens = 8192
        mock_entry.metadata.created = Mock()
        mock_entry.metadata.created.isoformat.return_value = "2025-09-29"
        mock_entry.metadata.capabilities = []
        mock_entry.pricing = {}

        mock_list_models.return_value = [mock_entry]

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        models = service.list_available_models(provider="anthropic")

        assert len(models) == 1
        assert models[0].provider == "anthropic"
        mock_list_models.assert_called_once_with(provider="anthropic", active_only=True)

    @patch("consoul.registry.get_pricing")
    def test_get_model_pricing_success(self, mock_get_pricing: Mock) -> None:
        """Test getting pricing for a model."""
        from consoul.sdk.services.model import ModelService

        mock_tier = Mock()
        mock_tier.input_price = 2.50
        mock_tier.output_price = 10.00
        mock_tier.cache_read = None
        mock_tier.cache_write_5m = None
        mock_tier.cache_write_1h = None
        mock_tier.thinking_price = None
        mock_tier.tier = "standard"
        mock_tier.effective_date = Mock()
        mock_tier.effective_date.isoformat.return_value = "2024-05-13"
        mock_tier.notes = None

        mock_get_pricing.return_value = mock_tier

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        pricing = service.get_model_pricing("gpt-4o")

        assert pricing is not None
        assert pricing.input_price == 2.50
        assert pricing.output_price == 10.00
        mock_get_pricing.assert_called_once_with("gpt-4o", tier="standard")

    @patch("consoul.registry.get_pricing")
    def test_get_model_pricing_not_found(self, mock_get_pricing: Mock) -> None:
        """Test getting pricing for unknown model."""
        from consoul.sdk.services.model import ModelService

        mock_get_pricing.return_value = None

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        pricing = service.get_model_pricing("unknown-model")

        assert pricing is None

    @patch("consoul.registry.get_model")
    def test_get_model_capabilities_success(self, mock_get_model: Mock) -> None:
        """Test getting capabilities for a model."""
        from consoul.sdk.services.model import ModelService

        mock_entry = Mock()
        mock_cap_vision = Mock()
        mock_cap_vision.value = "vision"
        mock_cap_tools = Mock()
        mock_cap_tools.value = "tools"
        mock_entry.metadata.capabilities = [mock_cap_vision, mock_cap_tools]

        mock_get_model.return_value = mock_entry

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        caps = service.get_model_capabilities("gpt-4o")

        assert caps is not None
        assert caps.supports_vision is True
        assert caps.supports_tools is True

    @patch("consoul.registry.get_model")
    def test_get_model_capabilities_not_found(self, mock_get_model: Mock) -> None:
        """Test getting capabilities for unknown model."""
        from consoul.sdk.services.model import ModelService

        mock_get_model.return_value = None

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        caps = service.get_model_capabilities("unknown-model")

        assert caps is None

    @patch("consoul.registry.get_model")
    def test_get_model_metadata_success(self, mock_get_model: Mock) -> None:
        """Test getting complete metadata for a model."""
        from consoul.sdk.services.model import ModelService

        mock_entry = Mock()
        mock_entry.metadata.id = "gpt-4o"
        mock_entry.metadata.name = "GPT-4o"
        mock_entry.metadata.provider = "openai"
        mock_entry.metadata.context_window = 128000
        mock_entry.metadata.description = "Most advanced GPT-4o model"
        mock_entry.metadata.max_output_tokens = 16384
        mock_entry.metadata.created = Mock()
        mock_entry.metadata.created.isoformat.return_value = "2024-05-13"
        mock_entry.metadata.capabilities = []
        mock_entry.pricing = {}

        mock_get_model.return_value = mock_entry

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        metadata = service.get_model_metadata("gpt-4o")

        assert metadata is not None
        assert metadata.id == "gpt-4o"
        assert metadata.name == "GPT-4o"
        assert metadata.context_window == "128K"

    @patch("consoul.registry.get_model")
    def test_get_model_metadata_not_found(self, mock_get_model: Mock) -> None:
        """Test getting metadata for unknown model."""
        from consoul.sdk.services.model import ModelService

        mock_get_model.return_value = None

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        metadata = service.get_model_metadata("unknown-model")

        assert metadata is None


class TestModelSwitchingErrors:
    """Test model switching error scenarios."""

    @patch("consoul.ai.get_chat_model")
    def test_switch_model_exception_propagates(
        self, mock_get_chat_model: Mock, mock_config: Mock
    ) -> None:
        """Test that model switching exceptions propagate."""
        from consoul.sdk.services.model import ModelService

        initial_model = Mock()
        mock_config.current_model = "gpt-4o"
        mock_get_chat_model.side_effect = Exception("Model not available")

        service = ModelService(initial_model, mock_config)

        with pytest.raises(Exception, match="Model not available"):
            service.switch_model("unavailable-model")

    @patch("consoul.ai.get_chat_model")
    def test_switch_model_without_provider(
        self, mock_get_chat_model: Mock, mock_config: Mock
    ) -> None:
        """Test switching model without explicit provider."""
        from consoul.config.models import Provider
        from consoul.sdk.services.model import ModelService

        initial_model = Mock()
        new_model = Mock()
        mock_model_config = Mock()
        mock_config.get_current_model_config = Mock(return_value=mock_model_config)
        mock_config.current_model = "gpt-4o"
        mock_config.current_provider = Provider.OPENAI
        mock_get_chat_model.return_value = new_model

        service = ModelService(initial_model, mock_config)

        # Switch without provider (should keep existing)
        service.switch_model("gpt-4o-mini")

        assert service.current_model_id == "gpt-4o-mini"
        assert mock_config.current_provider == Provider.OPENAI

    @patch("consoul.ai.get_chat_model")
    def test_switch_model_no_tool_service(
        self, mock_get_chat_model: Mock, mock_config: Mock
    ) -> None:
        """Test switching model when no tool service exists."""
        from consoul.sdk.services.model import ModelService

        initial_model = Mock()
        new_model = Mock()
        mock_model_config = Mock()
        mock_config.get_current_model_config = Mock(return_value=mock_model_config)
        mock_config.current_model = "gpt-4o"
        mock_get_chat_model.return_value = new_model

        service = ModelService(initial_model, mock_config, tool_service=None)

        result = service.switch_model("claude-3-5-sonnet")

        assert result is new_model
        # Should not attempt to bind tools
        new_model.bind_tools.assert_not_called()

    @patch("consoul.ai.get_chat_model")
    def test_bind_tools_no_tool_service(self, mock_get_chat_model: Mock) -> None:
        """Test binding tools when tool_service is None."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config, tool_service=None)

        # Should return early without error
        service._bind_tools()

        mock_model.bind_tools.assert_not_called()

    @patch("consoul.ai.get_chat_model")
    def test_from_config_no_tool_service(self, mock_get_chat_model: Mock) -> None:
        """Test factory method without tool service."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_model_config = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_config.get_current_model_config = Mock(return_value=mock_model_config)
        mock_get_chat_model.return_value = mock_model

        service = ModelService.from_config(mock_config, tool_service=None)

        assert service.tool_service is None
        # Should not attempt to bind tools
        mock_model.bind_tools.assert_not_called()


class TestCapabilityDetectionEdgeCases:
    """Test capability detection edge cases."""

    def test_supports_vision_no_catalog_info(self) -> None:
        """Test vision support when catalog returns None."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "unknown-model-123"

        service = ModelService(mock_model, mock_config)

        with patch.object(service, "get_current_model_info", return_value=None):
            # Should fall back to name detection
            result = service.supports_vision()
            assert result is False

    def test_supports_vision_with_vision_name(self) -> None:
        """Test vision support fallback with vision model name."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "llava:13b"

        service = ModelService(mock_model, mock_config)

        with patch.object(service, "get_current_model_info", return_value=None):
            result = service.supports_vision()
            assert result is True

    def test_get_current_model_info_from_catalog(self) -> None:
        """Test getting current model info from catalog."""
        from consoul.sdk.models import ModelInfo
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        with patch("consoul.sdk.catalog.get_model_info") as mock_get_info:
            mock_info = ModelInfo(
                id="gpt-4o",
                name="GPT-4o",
                provider="openai",
                context_window="128K",
                description="Test model",
            )
            mock_get_info.return_value = mock_info

            result = service.get_current_model_info()

            assert result == mock_info

    def test_get_current_model_info_dynamic_discovery(self) -> None:
        """Test getting current model info via dynamic discovery."""
        from consoul.config.models import Provider
        from consoul.sdk.models import ModelInfo
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "llama3.2:latest"
        mock_config.current_provider = Provider.OLLAMA

        service = ModelService(mock_model, mock_config)

        # Mock catalog returns None, should try dynamic discovery
        with patch("consoul.sdk.catalog.get_model_info", return_value=None):
            with patch.object(service, "_discover_local_models") as mock_discover:
                mock_discovered = ModelInfo(
                    id="llama3.2:latest",
                    name="llama3.2:latest",
                    provider="ollama",
                    context_window="128K",
                    description="Local Ollama model",
                )
                mock_discover.return_value = [mock_discovered]

                result = service.get_current_model_info()

                assert result == mock_discovered
                mock_discover.assert_called_once_with("ollama")

    def test_get_current_model_info_not_found(self) -> None:
        """Test getting current model info when not found anywhere."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "unknown-model"

        service = ModelService(mock_model, mock_config)

        with patch("consoul.sdk.catalog.get_model_info", return_value=None):
            with patch.object(service, "_discover_local_models", return_value=[]):
                result = service.get_current_model_info()

                assert result is None

    def test_list_models_with_provider_filter(self) -> None:
        """Test listing models with provider filter."""
        from consoul.sdk.models import ModelInfo
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        with patch("consoul.sdk.catalog.get_models_by_provider") as mock_get:
            mock_static = [
                ModelInfo(
                    id="llama3.2:latest",
                    name="Llama 3.2",
                    provider="ollama",
                    context_window="128K",
                    description="Static catalog model",
                )
            ]
            mock_get.return_value = mock_static

            with patch.object(service, "_discover_local_models") as mock_discover:
                mock_dynamic = [
                    ModelInfo(
                        id="llama3.2:3b",
                        name="Llama 3.2 3B",
                        provider="ollama",
                        context_window="128K",
                        description="Dynamic local model",
                    )
                ]
                mock_discover.return_value = mock_dynamic

                result = service.list_models(provider="ollama")

                assert len(result) == 2
                mock_discover.assert_called_once_with("ollama")

    def test_list_models_no_provider_filter(self) -> None:
        """Test listing all models without provider filter."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        with patch("consoul.sdk.catalog.MODEL_CATALOG", []):
            with patch.object(service, "_discover_local_models") as mock_discover:
                mock_discover.return_value = []

                result = service.list_models()

                assert isinstance(result, list)
                # Should call discover with None to get all local models
                mock_discover.assert_called_once_with(None)


class TestBackgroundContextRefresh:
    """Test background Ollama context refresh functionality."""

    @patch("consoul.ai.providers.is_ollama_running")
    def test_refresh_ollama_context_not_running(self, mock_is_running: Mock) -> None:
        """Test refresh does nothing when Ollama not running."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_is_running.return_value = False

        service = ModelService(mock_model, mock_config)

        # Should return early without error
        service.refresh_ollama_context_in_background()

        mock_is_running.assert_called_once()

    @patch("consoul.ai.providers.is_ollama_running")
    @patch("consoul.ai.providers.get_ollama_models")
    @patch("consoul.ai.context_cache.get_global_cache")
    def test_refresh_ollama_context_with_model_ids(
        self,
        mock_get_cache: Mock,
        mock_get_models: Mock,
        mock_is_running: Mock,
    ) -> None:
        """Test refresh with explicit model IDs."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_is_running.return_value = True

        # Mock cache
        mock_cache = Mock()
        mock_cache.refresh_in_background = Mock()
        mock_get_cache.return_value = mock_cache

        service = ModelService(mock_model, mock_config)

        service.refresh_ollama_context_in_background(
            model_ids=["llama3.2:latest", "qwen2.5-coder:7b"]
        )

        # Should call refresh_in_background with model IDs
        mock_cache.refresh_in_background.assert_called_once()

    @patch("consoul.ai.providers.is_ollama_running")
    @patch("consoul.ai.providers.get_ollama_models")
    @patch("consoul.ai.context_cache.get_global_cache")
    def test_refresh_ollama_context_auto_discover_models(
        self,
        mock_get_cache: Mock,
        mock_get_models: Mock,
        mock_is_running: Mock,
    ) -> None:
        """Test refresh auto-discovers models when not provided."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_is_running.return_value = True
        mock_get_models.return_value = [
            {"name": "llama3.2:latest"},
            {"name": "qwen2.5-coder:7b"},
        ]

        # Mock cache
        mock_cache = Mock()
        mock_cache.refresh_in_background = Mock()
        mock_get_cache.return_value = mock_cache

        service = ModelService(mock_model, mock_config)

        service.refresh_ollama_context_in_background()

        # Should discover models and call refresh
        mock_get_models.assert_called_once()
        mock_cache.refresh_in_background.assert_called_once()

    @patch("consoul.ai.providers.is_ollama_running")
    def test_refresh_ollama_context_exception_handling(
        self, mock_is_running: Mock
    ) -> None:
        """Test refresh handles exceptions gracefully."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_is_running.side_effect = Exception("Connection error")

        service = ModelService(mock_model, mock_config)

        # Should not raise exception
        service.refresh_ollama_context_in_background()


class TestRegistryIntegration:
    """Test registry integration with pricing metadata."""

    @patch("consoul.registry.list_models")
    def test_list_available_models_with_pricing(self, mock_list_models: Mock) -> None:
        """Test listing models with pricing information."""
        from consoul.sdk.services.model import ModelService

        # Create mock registry model with pricing
        mock_entry = Mock()
        mock_entry.metadata.id = "gpt-4o"
        mock_entry.metadata.name = "GPT-4o"
        mock_entry.metadata.provider = "openai"
        mock_entry.metadata.context_window = 128000
        mock_entry.metadata.description = "Most advanced GPT-4o model"
        mock_entry.metadata.max_output_tokens = 16384
        mock_entry.metadata.created = Mock()
        mock_entry.metadata.created.isoformat.return_value = "2024-05-13"

        # Add capabilities
        mock_cap_vision = Mock()
        mock_cap_vision.value = "vision"
        mock_cap_tools = Mock()
        mock_cap_tools.value = "tools"
        mock_cap_streaming = Mock()
        mock_cap_streaming.value = "streaming"
        mock_entry.metadata.capabilities = [
            mock_cap_vision,
            mock_cap_tools,
            mock_cap_streaming,
        ]

        # Add pricing
        mock_tier = Mock()
        mock_tier.input_price = 2.50
        mock_tier.output_price = 10.00
        mock_tier.cache_read = 1.25
        mock_tier.cache_write_5m = 3.00
        mock_tier.cache_write_1h = 1.50
        mock_tier.thinking_price = None
        mock_tier.effective_date = Mock()
        mock_tier.effective_date.isoformat.return_value = "2024-05-13"
        mock_tier.notes = "Standard pricing"
        mock_entry.pricing = {"standard": mock_tier}

        mock_list_models.return_value = [mock_entry]

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        models = service.list_available_models()

        assert len(models) == 1
        assert models[0].id == "gpt-4o"
        assert models[0].pricing is not None
        assert models[0].pricing.input_price == 2.50
        assert models[0].capabilities is not None
        assert models[0].capabilities.supports_vision is True

    @patch("consoul.registry.get_model")
    def test_get_model_metadata_with_all_pricing(self, mock_get_model: Mock) -> None:
        """Test getting metadata with complete pricing tier."""
        from consoul.sdk.services.model import ModelService

        mock_entry = Mock()
        mock_entry.metadata.id = "gpt-4o"
        mock_entry.metadata.name = "GPT-4o"
        mock_entry.metadata.provider = "openai"
        mock_entry.metadata.context_window = 128000
        mock_entry.metadata.description = "Most advanced GPT-4o model"
        mock_entry.metadata.max_output_tokens = 16384
        mock_entry.metadata.created = Mock()
        mock_entry.metadata.created.isoformat.return_value = "2024-05-13"
        mock_entry.metadata.capabilities = []

        # Add complete pricing tier
        mock_tier = Mock()
        mock_tier.input_price = 2.50
        mock_tier.output_price = 10.00
        mock_tier.cache_read = 1.25
        mock_tier.cache_write_5m = 3.00
        mock_tier.cache_write_1h = 1.50
        mock_tier.thinking_price = 5.00
        mock_tier.effective_date = Mock()
        mock_tier.effective_date.isoformat.return_value = "2024-05-13"
        mock_tier.notes = "Standard tier with all features"
        mock_entry.pricing = {"standard": mock_tier}

        mock_get_model.return_value = mock_entry

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        metadata = service.get_model_metadata("gpt-4o")

        assert metadata is not None
        assert metadata.pricing is not None
        assert metadata.pricing.cache_read == 1.25
        assert metadata.pricing.thinking_price == 5.00


class TestDiscoverLocalModels:
    """Test _discover_local_models method."""

    def test_discover_local_models_all_providers(self) -> None:
        """Test discovering from all local providers."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        with patch.object(service, "list_ollama_models") as mock_ollama:
            with patch.object(service, "list_mlx_models") as mock_mlx:
                with patch.object(service, "list_gguf_models") as mock_gguf:
                    with patch.object(service, "list_huggingface_models") as mock_hf:
                        mock_ollama.return_value = []
                        mock_mlx.return_value = []
                        mock_gguf.return_value = []
                        mock_hf.return_value = []

                        service._discover_local_models(provider=None)

                        # Should call all discovery methods
                        mock_ollama.assert_called_once()
                        mock_mlx.assert_called_once()
                        mock_gguf.assert_called_once()
                        mock_hf.assert_called_once()

    def test_discover_local_models_specific_provider(self) -> None:
        """Test discovering from specific provider."""
        from consoul.sdk.services.model import ModelService

        mock_model = Mock()
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"

        service = ModelService(mock_model, mock_config)

        with patch.object(service, "list_ollama_models") as mock_ollama:
            with patch.object(service, "list_mlx_models") as mock_mlx:
                mock_ollama.return_value = []
                mock_mlx.return_value = []

                service._discover_local_models(provider="ollama")

                # Should only call ollama
                mock_ollama.assert_called_once()
                mock_mlx.assert_not_called()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config() -> Mock:
    """Create mock ConsoulConfig for testing."""
    from consoul.config.models import Provider

    config = Mock()
    config.current_model = "gpt-4o"
    config.current_provider = Provider.OPENAI

    # Mock get_current_model_config
    config.get_current_model_config = Mock()

    return config
