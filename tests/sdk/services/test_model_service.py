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
