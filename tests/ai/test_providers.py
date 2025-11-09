"""Tests for AI provider initialization."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from consoul.ai.exceptions import (
    InvalidModelError,
    MissingAPIKeyError,
    MissingDependencyError,
)
from consoul.ai.providers import (
    build_model_params,
    get_chat_model,
    get_provider_from_model,
    validate_provider_dependencies,
)
from consoul.config.models import (
    AnthropicModelConfig,
    GoogleModelConfig,
    OllamaModelConfig,
    OpenAIModelConfig,
    Provider,
)


class TestProviderDetection:
    """Tests for provider detection from model names."""

    def test_detect_openai_gpt4(self):
        """Test detecting OpenAI from gpt-4 model name."""
        provider = get_provider_from_model("gpt-4o")
        assert provider == Provider.OPENAI

    def test_detect_openai_gpt35(self):
        """Test detecting OpenAI from gpt-3.5 model name."""
        provider = get_provider_from_model("gpt-3.5-turbo")
        assert provider == Provider.OPENAI

    def test_detect_openai_o1(self):
        """Test detecting OpenAI from o1 model name."""
        provider = get_provider_from_model("o1-preview")
        assert provider == Provider.OPENAI

    def test_detect_anthropic_claude3(self):
        """Test detecting Anthropic from claude-3 model name."""
        provider = get_provider_from_model("claude-3-5-sonnet-20241022")
        assert provider == Provider.ANTHROPIC

    def test_detect_anthropic_claude2(self):
        """Test detecting Anthropic from claude-2 model name."""
        provider = get_provider_from_model("claude-2.1")
        assert provider == Provider.ANTHROPIC

    def test_detect_google_gemini(self):
        """Test detecting Google from gemini model name."""
        provider = get_provider_from_model("gemini-pro")
        assert provider == Provider.GOOGLE

    def test_detect_ollama_llama(self):
        """Test detecting Ollama from llama model name."""
        provider = get_provider_from_model("llama2")
        assert provider == Provider.OLLAMA

    def test_detect_ollama_mistral(self):
        """Test detecting Ollama from mistral model name."""
        provider = get_provider_from_model("mistral")
        assert provider == Provider.OLLAMA

    def test_detect_unknown_model(self):
        """Test that unknown model returns None."""
        provider = get_provider_from_model("unknown-model-123")
        assert provider is None

    def test_case_insensitive_detection(self):
        """Test that provider detection is case-insensitive."""
        provider = get_provider_from_model("GPT-4O")
        assert provider == Provider.OPENAI


class TestValidateProviderDependencies:
    """Tests for provider dependency validation."""

    def test_validate_openai_dependency_installed(self):
        """Test that OpenAI dependency validation passes when installed."""
        # Should not raise since langchain-openai is in dependencies
        validate_provider_dependencies(Provider.OPENAI)

    def test_validate_anthropic_dependency_installed(self):
        """Test that Anthropic dependency validation passes when installed."""
        # Should not raise since langchain-anthropic is in dependencies
        validate_provider_dependencies(Provider.ANTHROPIC)

    def test_validate_google_dependency_installed(self):
        """Test that Google dependency validation passes when installed."""
        # Should not raise since langchain-google-genai is in dependencies
        validate_provider_dependencies(Provider.GOOGLE)

    @patch("importlib.util.find_spec")
    def test_validate_missing_dependency_raises(self, mock_find_spec):
        """Test that missing dependency raises MissingDependencyError."""
        mock_find_spec.return_value = None

        with pytest.raises(MissingDependencyError) as exc_info:
            validate_provider_dependencies(Provider.OPENAI)

        assert "langchain-openai" in str(exc_info.value)
        assert "pip install" in str(exc_info.value)


class TestBuildModelParams:
    """Tests for converting ModelConfig to LangChain parameters."""

    def test_build_params_openai_basic(self):
        """Test building basic parameters for OpenAI model."""
        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )

        params = build_model_params(config)

        assert params["model"] == "gpt-4o"
        assert params["temperature"] == 0.7
        assert "max_tokens" not in params  # Not specified

    def test_build_params_openai_full(self):
        """Test building full parameters for OpenAI model."""
        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
            max_tokens=2048,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            stop_sequences=["END"],
        )

        params = build_model_params(config)

        assert params["model"] == "gpt-4o"
        assert params["temperature"] == 0.7
        assert params["max_tokens"] == 2048
        assert params["top_p"] == 0.9
        assert params["frequency_penalty"] == 0.5
        assert params["presence_penalty"] == 0.3
        assert params["stop"] == ["END"]

    def test_build_params_anthropic(self):
        """Test building parameters for Anthropic model."""
        config = AnthropicModelConfig(
            model="claude-3-5-sonnet-20241022",
            temperature=1.0,
            max_tokens=4096,
            top_p=0.95,
            top_k=40,
        )

        params = build_model_params(config)

        assert params["model"] == "claude-3-5-sonnet-20241022"
        assert params["temperature"] == 1.0
        assert params["max_tokens"] == 4096
        assert params["top_p"] == 0.95
        assert params["top_k"] == 40

    def test_build_params_google(self):
        """Test building parameters for Google model."""
        config = GoogleModelConfig(
            model="gemini-pro",
            temperature=0.8,
            top_p=0.9,
            top_k=50,
        )

        params = build_model_params(config)

        assert params["model"] == "gemini-pro"
        assert params["temperature"] == 0.8
        assert params["top_p"] == 0.9
        assert params["top_k"] == 50

    def test_build_params_ollama(self):
        """Test building parameters for Ollama model."""
        config = OllamaModelConfig(
            model="llama2",
            temperature=0.5,
            top_p=0.9,
            top_k=40,
        )

        params = build_model_params(config)

        assert params["model"] == "llama2"
        assert params["temperature"] == 0.5
        assert params["top_p"] == 0.9
        assert params["top_k"] == 40


class TestGetChatModel:
    """Tests for get_chat_model function."""

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_openai(self, mock_init):
        """Test initializing OpenAI chat model."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )
        api_key = SecretStr("sk-test123")

        result = get_chat_model(config, api_key=api_key)

        assert result == mock_chat_model
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["model_provider"] == "openai"
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["openai_api_key"] == "sk-test123"

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_anthropic(self, mock_init):
        """Test initializing Anthropic chat model."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        config = AnthropicModelConfig(
            model="claude-3-5-sonnet-20241022",
            temperature=1.0,
        )
        api_key = SecretStr("sk-ant-test456")

        result = get_chat_model(config, api_key=api_key)

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"
        assert call_kwargs["model_provider"] == "anthropic"
        assert call_kwargs["anthropic_api_key"] == "sk-ant-test456"

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_google(self, mock_init):
        """Test initializing Google chat model."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        config = GoogleModelConfig(
            model="gemini-pro",
            temperature=0.8,
        )
        api_key = SecretStr("test789")

        result = get_chat_model(config, api_key=api_key)

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model"] == "gemini-pro"
        assert call_kwargs["model_provider"] == "google"
        assert call_kwargs["google_api_key"] == "test789"

    @patch("consoul.ai.providers.init_chat_model")
    @patch("consoul.ai.providers.validate_provider_dependencies")
    def test_get_chat_model_ollama_no_api_key(self, mock_validate, mock_init):
        """Test initializing Ollama chat model without API key."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        config = OllamaModelConfig(
            model="llama2",
            temperature=0.5,
        )

        result = get_chat_model(config)

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model"] == "llama2"
        assert call_kwargs["model_provider"] == "ollama"
        # No API key for Ollama
        assert "ollama_api_key" not in call_kwargs

    @patch("consoul.config.env.get_api_key")
    def test_get_chat_model_missing_api_key(self, mock_get_api_key):
        """Test that missing API key raises MissingAPIKeyError."""
        mock_get_api_key.return_value = None  # No API key in environment

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )

        with pytest.raises(MissingAPIKeyError) as exc_info:
            get_chat_model(config)

        error_msg = str(exc_info.value)
        assert "OPENAI_API_KEY" in error_msg
        assert "openai" in error_msg.lower()
        assert "gpt-4o" in error_msg

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_with_extra_kwargs(self, mock_init):
        """Test passing extra kwargs to init_chat_model."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )
        api_key = SecretStr("sk-test")

        result = get_chat_model(config, api_key=api_key, custom_param="value")

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["custom_param"] == "value"

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_import_error(self, mock_init):
        """Test that ImportError raises MissingDependencyError."""
        mock_init.side_effect = ImportError("No module named 'langchain_openai'")

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )
        api_key = SecretStr("sk-test")

        with pytest.raises(MissingDependencyError) as exc_info:
            get_chat_model(config, api_key=api_key)

        assert "langchain" in str(exc_info.value).lower()

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_value_error(self, mock_init):
        """Test that ValueError raises InvalidModelError."""
        mock_init.side_effect = ValueError("Invalid model name: gpt-5")

        config = OpenAIModelConfig(
            model="gpt-5",
            temperature=0.7,
        )
        api_key = SecretStr("sk-test")

        with pytest.raises(InvalidModelError) as exc_info:
            get_chat_model(config, api_key=api_key)

        error_msg = str(exc_info.value)
        assert "gpt-5" in error_msg
        assert "Invalid" in error_msg

    @patch("importlib.util.find_spec")
    def test_get_chat_model_missing_dependency(self, mock_find_spec):
        """Test that missing dependency is caught early."""
        mock_find_spec.return_value = None

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )
        api_key = SecretStr("sk-test")

        with pytest.raises(MissingDependencyError) as exc_info:
            get_chat_model(config, api_key=api_key)

        assert "langchain-openai" in str(exc_info.value)

    @patch("consoul.ai.providers.init_chat_model")
    @patch("consoul.config.env.get_api_key")
    def test_get_chat_model_resolves_api_key_from_env(
        self, mock_get_api_key, mock_init
    ):
        """Test that API key is resolved from environment when not provided."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model
        mock_get_api_key.return_value = SecretStr("env-api-key-123")

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )

        result = get_chat_model(config)  # No api_key provided

        assert result == mock_chat_model
        mock_get_api_key.assert_called_once()
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["openai_api_key"] == "env-api-key-123"

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_string_with_auto_detection(self, mock_init):
        """Test using string model name with auto provider detection."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model("gpt-4o", api_key=SecretStr("sk-test"), temperature=0.5)

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["model_provider"] == "openai"
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["openai_api_key"] == "sk-test"

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_string_anthropic_auto_detection(self, mock_init):
        """Test auto-detection for Anthropic models."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(
            "claude-3-5-sonnet-20241022", api_key=SecretStr("sk-ant-test")
        )

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"
        assert call_kwargs["model_provider"] == "anthropic"

    def test_get_chat_model_string_unknown_model(self):
        """Test that unknown model string raises InvalidModelError."""
        with pytest.raises(InvalidModelError) as exc_info:
            get_chat_model("unknown-model-xyz")

        error_msg = str(exc_info.value)
        assert "Could not detect provider" in error_msg
        assert "unknown-model-xyz" in error_msg

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_with_config_api_keys(self, mock_init):
        """Test that API keys are resolved from config.api_keys."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        # Create a mock config with api_keys
        mock_config = MagicMock()
        mock_config.api_keys = {"openai": SecretStr("config-key-123")}

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )

        result = get_chat_model(config, config=mock_config)

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["openai_api_key"] == "config-key-123"

    @patch("consoul.ai.providers.init_chat_model")
    @patch("consoul.config.env.get_api_key")
    def test_get_chat_model_config_api_keys_precedence(
        self, mock_get_api_key, mock_init
    ):
        """Test that config.api_keys takes precedence over environment."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model
        mock_get_api_key.return_value = SecretStr("env-key-456")

        # Create a mock config with api_keys
        mock_config = MagicMock()
        mock_config.api_keys = {"openai": SecretStr("config-key-123")}

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )

        result = get_chat_model(config, config=mock_config)

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        # Should use config key, not env key
        assert call_kwargs["openai_api_key"] == "config-key-123"
        # Environment getter should not be called when config has the key
        mock_get_api_key.assert_not_called()

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_string_with_stop_sequences(self, mock_init):
        """Test that stop_sequences is properly mapped in string mode."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(
            "gpt-4o",
            api_key=SecretStr("sk-test"),
            stop_sequences=["STOP", "END"],
        )

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        # stop_sequences should be converted to "stop"
        assert call_kwargs["stop"] == ["STOP", "END"]
        # stop_sequences should not be passed directly
        assert "stop_sequences" not in call_kwargs

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_string_with_all_openai_params(self, mock_init):
        """Test string mode with all OpenAI-specific parameters."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(
            "gpt-4o",
            api_key=SecretStr("sk-test"),
            temperature=0.8,
            max_tokens=2048,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            stop_sequences=["END"],
        )

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["top_p"] == 0.9
        assert call_kwargs["frequency_penalty"] == 0.5
        assert call_kwargs["presence_penalty"] == 0.3
        assert call_kwargs["stop"] == ["END"]
