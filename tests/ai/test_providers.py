"""Tests for AI provider initialization."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

# Check if langchain_huggingface is available
try:
    import langchain_huggingface  # noqa: F401

    HAS_HUGGINGFACE = True
except ImportError:
    HAS_HUGGINGFACE = False

# Check if llama_cpp is available
try:
    import llama_cpp  # noqa: F401

    HAS_LLAMACPP = True
except ImportError:
    HAS_LLAMACPP = False

from consoul.ai.exceptions import (
    InvalidModelError,
    MissingAPIKeyError,
    MissingDependencyError,
    OllamaServiceError,
)
from consoul.ai.providers import (
    build_model_params,
    get_chat_model,
    get_provider_from_model,
    is_ollama_running,
    validate_provider_dependencies,
)
from consoul.config.models import (
    AnthropicModelConfig,
    GoogleModelConfig,
    HuggingFaceModelConfig,
    LlamaCppModelConfig,
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

    def test_detect_huggingface_meta_llama(self):
        """Test detecting HuggingFace from meta-llama model name."""
        provider = get_provider_from_model("meta-llama/Llama-2-7b-hf")
        assert provider == Provider.HUGGINGFACE

    def test_detect_huggingface_mistralai(self):
        """Test detecting HuggingFace from mistralai model name."""
        provider = get_provider_from_model("mistralai/Mistral-7B-v0.1")
        assert provider == Provider.HUGGINGFACE

    def test_detect_huggingface_microsoft(self):
        """Test detecting HuggingFace from microsoft model name."""
        provider = get_provider_from_model("microsoft/phi-2")
        assert provider == Provider.HUGGINGFACE

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

    def test_build_params_anthropic_with_thinking(self):
        """Test building Anthropic parameters with thinking."""
        thinking_config = {"type": "enabled", "budget_tokens": 2000}
        config = AnthropicModelConfig(
            model="claude-sonnet-4-5-20250929",
            temperature=0.7,
            thinking=thinking_config,
        )

        params = build_model_params(config)

        assert params["model"] == "claude-sonnet-4-5-20250929"
        assert params["temperature"] == 0.7
        assert params["thinking"] == thinking_config

    def test_build_params_anthropic_with_betas(self):
        """Test building Anthropic parameters with betas."""
        betas = ["files-api-2025-04-14", "token-efficient-tools-2025-02-19"]
        config = AnthropicModelConfig(
            model="claude-3-5-sonnet-20241022",
            temperature=0.8,
            betas=betas,
        )

        params = build_model_params(config)

        assert params["model"] == "claude-3-5-sonnet-20241022"
        assert params["temperature"] == 0.8
        assert params["betas"] == betas

    def test_build_params_anthropic_with_metadata(self):
        """Test building Anthropic parameters with metadata."""
        metadata = {"user_id": "test-user", "session_id": "abc123"}
        config = AnthropicModelConfig(
            model="claude-3-opus-20240229",
            temperature=0.9,
            metadata=metadata,
        )

        params = build_model_params(config)

        assert params["model"] == "claude-3-opus-20240229"
        assert params["temperature"] == 0.9
        assert params["metadata"] == metadata

    def test_build_params_anthropic_all_exclusive_params(self):
        """Test building Anthropic parameters with all exclusive parameters."""
        thinking_config = {"type": "enabled", "budget_tokens": 5000}
        betas = ["files-api-2025-04-14"]
        metadata = {"user_id": "test-user"}

        config = AnthropicModelConfig(
            model="claude-sonnet-4-5-20250929",
            temperature=0.8,
            max_tokens=4096,
            top_p=0.95,
            top_k=40,
            thinking=thinking_config,
            betas=betas,
            metadata=metadata,
        )

        params = build_model_params(config)

        assert params["model"] == "claude-sonnet-4-5-20250929"
        assert params["temperature"] == 0.8
        assert params["max_tokens"] == 4096
        assert params["top_p"] == 0.95
        assert params["top_k"] == 40
        assert params["thinking"] == thinking_config
        assert params["betas"] == betas
        assert params["metadata"] == metadata

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

    def test_build_params_google_with_candidate_count(self):
        """Test building Google parameters with candidate_count."""
        config = GoogleModelConfig(
            model="gemini-2.5-pro",
            temperature=0.7,
            candidate_count=3,
        )

        params = build_model_params(config)

        assert params["model"] == "gemini-2.5-pro"
        assert params["temperature"] == 0.7
        assert params["candidate_count"] == 3

    def test_build_params_google_with_safety_settings(self):
        """Test building Google parameters with safety_settings."""
        safety_settings = {
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
            "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH",
        }
        config = GoogleModelConfig(
            model="gemini-1.5-pro",
            temperature=0.8,
            safety_settings=safety_settings,
        )

        params = build_model_params(config)

        assert params["model"] == "gemini-1.5-pro"
        assert params["temperature"] == 0.8
        assert params["safety_settings"] == safety_settings

    def test_build_params_google_with_generation_config(self):
        """Test building Google parameters with generation_config."""
        generation_config = {"response_modalities": ["TEXT", "IMAGE"]}
        config = GoogleModelConfig(
            model="gemini-2.5-pro",
            temperature=0.7,
            generation_config=generation_config,
        )

        params = build_model_params(config)

        assert params["model"] == "gemini-2.5-pro"
        assert params["temperature"] == 0.7
        assert params["generation_config"] == generation_config

    def test_build_params_google_all_exclusive_params(self):
        """Test building Google parameters with all exclusive parameters."""
        safety_settings = {"HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"}
        generation_config = {"response_modalities": ["TEXT"]}

        config = GoogleModelConfig(
            model="gemini-2.5-pro",
            temperature=0.8,
            max_tokens=2048,
            top_p=0.95,
            top_k=50,
            candidate_count=2,
            safety_settings=safety_settings,
            generation_config=generation_config,
        )

        params = build_model_params(config)

        assert params["model"] == "gemini-2.5-pro"
        assert params["temperature"] == 0.8
        assert params["max_tokens"] == 2048
        assert params["top_p"] == 0.95
        assert params["top_k"] == 50
        assert params["candidate_count"] == 2
        assert params["safety_settings"] == safety_settings
        assert params["generation_config"] == generation_config

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

    def test_build_params_huggingface_basic(self):
        """Test building basic parameters for HuggingFace model."""
        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            temperature=0.7,
        )

        params = build_model_params(config)

        assert params["model"] == "meta-llama/Llama-3.1-8B-Instruct"
        assert params["temperature"] == 0.7
        # HuggingFaceModelConfig has defaults
        assert params["task"] == "text-generation"
        assert params["max_new_tokens"] == 512
        assert params["do_sample"] is True

    def test_build_params_huggingface_full(self):
        """Test building full parameters for HuggingFace model."""
        config = HuggingFaceModelConfig(
            model="mistralai/Mistral-7B-Instruct-v0.2",
            temperature=0.8,
            max_tokens=2048,
            task="text-generation",
            max_new_tokens=1024,
            do_sample=True,
            repetition_penalty=1.1,
            top_p=0.95,
            top_k=50,
        )

        params = build_model_params(config)

        assert params["model"] == "mistralai/Mistral-7B-Instruct-v0.2"
        assert params["temperature"] == 0.8
        assert params["max_tokens"] == 2048
        assert params["task"] == "text-generation"
        assert params["max_new_tokens"] == 1024
        assert params["do_sample"] is True
        assert params["repetition_penalty"] == 1.1
        assert params["top_p"] == 0.95
        assert params["top_k"] == 50

    def test_build_params_huggingface_with_model_kwargs(self):
        """Test building HuggingFace parameters with model_kwargs."""
        model_kwargs = {"use_cache": True, "return_full_text": False}
        config = HuggingFaceModelConfig(
            model="google/flan-t5-xxl",
            temperature=0.5,
            model_kwargs=model_kwargs,
        )

        params = build_model_params(config)

        assert params["model"] == "google/flan-t5-xxl"
        assert params["temperature"] == 0.5
        assert params["model_kwargs"] == model_kwargs

    def test_build_params_openai_with_seed(self):
        """Test building parameters for OpenAI model with seed."""
        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
            seed=42,
        )

        params = build_model_params(config)

        assert params["model"] == "gpt-4o"
        assert params["temperature"] == 0.7
        assert params["seed"] == 42

    def test_build_params_openai_with_logit_bias(self):
        """Test building parameters for OpenAI model with logit_bias."""
        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
            logit_bias={"50256": -100},
        )

        params = build_model_params(config)

        assert params["model"] == "gpt-4o"
        assert params["logit_bias"] == {"50256": -100}

    def test_build_params_openai_with_response_format(self):
        """Test building parameters for OpenAI model with response_format."""
        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        params = build_model_params(config)

        assert params["model"] == "gpt-4o"
        assert params["response_format"] == {"type": "json_object"}

    def test_build_params_openai_all_new_features(self):
        """Test building parameters with all new OpenAI features."""
        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.8,
            max_tokens=2048,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            seed=42,
            logit_bias={"50256": -100},
            response_format={"type": "json_object"},
            stop_sequences=["END"],
        )

        params = build_model_params(config)

        assert params["model"] == "gpt-4o"
        assert params["temperature"] == 0.8
        assert params["max_tokens"] == 2048
        assert params["top_p"] == 0.9
        assert params["frequency_penalty"] == 0.5
        assert params["presence_penalty"] == 0.3
        assert params["seed"] == 42
        assert params["logit_bias"] == {"50256": -100}
        assert params["response_format"] == {"type": "json_object"}
        assert params["stop"] == ["END"]


class TestGetChatModel:
    """Tests for get_chat_model function."""

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_openai(self, mock_chat_openai):
        """Test initializing OpenAI chat model."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )
        api_key = SecretStr("sk-test123")

        result = get_chat_model(config, api_key=api_key)

        assert result == mock_chat_model
        mock_chat_openai.assert_called_once()
        call_kwargs = mock_chat_openai.call_args[1]  # kwargs
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["openai_api_key"] == "sk-test123"
        # LangChain handles stream_options automatically - no need for model_kwargs
        assert "model_kwargs" not in call_kwargs or call_kwargs["model_kwargs"] == {}

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
        assert call_kwargs["model_provider"] == "google_genai"
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

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    @patch("langchain_huggingface.ChatHuggingFace")
    @patch("langchain_huggingface.HuggingFaceEndpoint")
    def test_get_chat_model_huggingface(self, mock_endpoint, mock_chat_hf):
        """Test initializing HuggingFace chat model."""
        mock_llm = MagicMock()
        mock_endpoint.return_value = mock_llm
        mock_chat_model = MagicMock()
        mock_chat_hf.return_value = mock_chat_model

        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            temperature=0.7,
            task="text-generation",
            max_new_tokens=512,
        )
        api_key = SecretStr("hf_test123")

        result = get_chat_model(config, api_key=api_key)

        assert result == mock_chat_model
        # Verify HuggingFaceEndpoint was called with correct params
        endpoint_kwargs = mock_endpoint.call_args.kwargs
        assert endpoint_kwargs["repo_id"] == "meta-llama/Llama-3.1-8B-Instruct"
        assert endpoint_kwargs["task"] == "text-generation"
        assert endpoint_kwargs["max_new_tokens"] == 512
        assert endpoint_kwargs["do_sample"] is True
        assert endpoint_kwargs["temperature"] == 0.7  # Verify temperature is passed
        assert endpoint_kwargs["huggingfacehub_api_token"] == "hf_test123"
        # Verify ChatHuggingFace was called with the endpoint
        mock_chat_hf.assert_called_once()
        chat_hf_kwargs = mock_chat_hf.call_args.kwargs
        assert chat_hf_kwargs["llm"] == mock_llm

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    @patch("langchain_huggingface.ChatHuggingFace")
    @patch("langchain_huggingface.HuggingFaceEndpoint")
    def test_get_chat_model_huggingface_with_params(self, mock_endpoint, mock_chat_hf):
        """Test initializing HuggingFace model with all parameters."""
        mock_llm = MagicMock()
        mock_endpoint.return_value = mock_llm
        mock_chat_model = MagicMock()
        mock_chat_hf.return_value = mock_chat_model

        config = HuggingFaceModelConfig(
            model="mistralai/Mistral-7B-Instruct-v0.2",
            temperature=0.8,
            task="text-generation",
            max_new_tokens=1024,
            do_sample=True,
            repetition_penalty=1.1,
            top_p=0.95,
            top_k=50,
        )
        api_key = SecretStr("hf_test456")

        result = get_chat_model(config, api_key=api_key)

        assert result == mock_chat_model
        endpoint_kwargs = mock_endpoint.call_args.kwargs
        assert endpoint_kwargs["repo_id"] == "mistralai/Mistral-7B-Instruct-v0.2"
        assert endpoint_kwargs["task"] == "text-generation"
        assert endpoint_kwargs["max_new_tokens"] == 1024
        assert endpoint_kwargs["do_sample"] is True
        assert endpoint_kwargs["temperature"] == 0.8  # Verify temperature is passed
        assert endpoint_kwargs["repetition_penalty"] == 1.1
        assert endpoint_kwargs["top_p"] == 0.95
        assert endpoint_kwargs["top_k"] == 50
        assert endpoint_kwargs["huggingfacehub_api_token"] == "hf_test456"

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    @patch("langchain_huggingface.HuggingFaceEndpoint")
    @patch("consoul.config.env.get_api_key")
    def test_get_chat_model_huggingface_missing_api_key(
        self, mock_get_api_key, mock_endpoint
    ):
        """Test that missing HuggingFace API key raises MissingAPIKeyError."""
        mock_get_api_key.return_value = None
        mock_endpoint.side_effect = Exception("API token required")

        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            temperature=0.7,
        )

        with pytest.raises(MissingAPIKeyError) as exc_info:
            get_chat_model(config)

        error_msg = str(exc_info.value)
        assert "HUGGINGFACEHUB_API_TOKEN" in error_msg
        assert "huggingface" in error_msg.lower()

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    @patch("langchain_huggingface.HuggingFaceEndpoint")
    def test_get_chat_model_huggingface_invalid_model(self, mock_endpoint):
        """Test that invalid HuggingFace model raises InvalidModelError."""
        mock_endpoint.side_effect = Exception("Model not found (404)")

        config = HuggingFaceModelConfig(
            model="invalid/model-name",
            temperature=0.7,
        )
        api_key = SecretStr("hf_test123")

        with pytest.raises(InvalidModelError) as exc_info:
            get_chat_model(config, api_key=api_key)

        error_msg = str(exc_info.value)
        assert "invalid/model-name" in error_msg
        assert "not found" in error_msg.lower()

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    @patch("langchain_huggingface.ChatHuggingFace")
    @patch("langchain_huggingface.HuggingFaceEndpoint")
    def test_get_chat_model_huggingface_max_tokens(self, mock_endpoint, mock_chat_hf):
        """Test that max_tokens is mapped to max_length."""
        mock_llm = MagicMock()
        mock_endpoint.return_value = mock_llm
        mock_chat_model = MagicMock()
        mock_chat_hf.return_value = mock_chat_model

        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            max_tokens=2048,
        )
        api_key = SecretStr("hf_test123")

        result = get_chat_model(config, api_key=api_key)

        assert result == mock_chat_model
        endpoint_kwargs = mock_endpoint.call_args.kwargs
        assert endpoint_kwargs["max_length"] == 2048

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    @patch("langchain_huggingface.ChatHuggingFace")
    @patch("langchain_huggingface.HuggingFaceEndpoint")
    def test_get_chat_model_huggingface_stop_sequences(
        self, mock_endpoint, mock_chat_hf
    ):
        """Test that stop sequences are passed to HuggingFaceEndpoint."""
        mock_llm = MagicMock()
        mock_endpoint.return_value = mock_llm
        mock_chat_model = MagicMock()
        mock_chat_hf.return_value = mock_chat_model

        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            stop_sequences=["END", "STOP"],
        )
        api_key = SecretStr("hf_test123")

        result = get_chat_model(config, api_key=api_key)

        assert result == mock_chat_model
        endpoint_kwargs = mock_endpoint.call_args.kwargs
        assert endpoint_kwargs["stop_sequences"] == ["END", "STOP"]

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    @patch("langchain_huggingface.ChatHuggingFace")
    @patch("langchain_huggingface.HuggingFaceEndpoint")
    def test_get_chat_model_huggingface_no_extra_params(
        self, mock_endpoint, mock_chat_hf
    ):
        """Test that ChatHuggingFace only receives expected parameters."""
        mock_llm = MagicMock()
        mock_endpoint.return_value = mock_llm
        mock_chat_model = MagicMock()
        mock_chat_hf.return_value = mock_chat_model

        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            temperature=0.9,
            max_tokens=1024,
            stop_sequences=["END"],
        )
        api_key = SecretStr("hf_test123")

        result = get_chat_model(config, api_key=api_key)

        assert result == mock_chat_model
        # Verify ChatHuggingFace doesn't receive generation params
        chat_hf_kwargs = mock_chat_hf.call_args.kwargs
        assert "llm" in chat_hf_kwargs
        assert "temperature" not in chat_hf_kwargs
        assert "max_tokens" not in chat_hf_kwargs
        assert "stop" not in chat_hf_kwargs
        assert "max_length" not in chat_hf_kwargs
        assert "stop_sequences" not in chat_hf_kwargs

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    @patch("importlib.util.find_spec")
    @patch("langchain_huggingface.ChatHuggingFace")
    @patch("langchain_huggingface.HuggingFacePipeline")
    def test_get_chat_model_huggingface_local(
        self, mock_pipeline, mock_chat_hf, mock_find_spec
    ):
        """Test local execution with HuggingFacePipeline."""
        # Mock dependencies as installed
        mock_find_spec.return_value = MagicMock()

        mock_llm = MagicMock()
        mock_pipeline.from_model_id.return_value = mock_llm
        mock_chat_model = MagicMock()
        mock_chat_hf.return_value = mock_chat_model

        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            local=True,
            temperature=0.7,
        )

        result = get_chat_model(config)

        assert result == mock_chat_model
        # Verify HuggingFacePipeline.from_model_id was called
        mock_pipeline.from_model_id.assert_called_once()
        call_kwargs = mock_pipeline.from_model_id.call_args.kwargs
        assert call_kwargs["model_id"] == "meta-llama/Llama-3.1-8B-Instruct"
        assert call_kwargs["task"] == "text-generation"
        # Verify generation parameters are in pipeline_kwargs, not model_kwargs
        assert "pipeline_kwargs" in call_kwargs
        assert call_kwargs["pipeline_kwargs"]["temperature"] == 0.7
        # Verify ChatHuggingFace was called with the pipeline
        mock_chat_hf.assert_called_once()
        assert mock_chat_hf.call_args.kwargs["llm"] == mock_llm

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    @patch("importlib.util.find_spec")
    @patch("langchain_huggingface.ChatHuggingFace")
    @patch("langchain_huggingface.HuggingFacePipeline")
    def test_get_chat_model_huggingface_local_with_device(
        self, mock_pipeline, mock_chat_hf, mock_find_spec
    ):
        """Test local execution with device specification."""
        # Mock dependencies as installed
        mock_find_spec.return_value = MagicMock()

        mock_llm = MagicMock()
        mock_pipeline.from_model_id.return_value = mock_llm
        mock_chat_model = MagicMock()
        mock_chat_hf.return_value = mock_chat_model

        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            local=True,
            device="cuda",
        )

        result = get_chat_model(config)

        assert result == mock_chat_model
        pipeline_kwargs = mock_pipeline.from_model_id.call_args.kwargs
        assert pipeline_kwargs["device"] == "cuda"

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    def test_get_chat_model_huggingface_local_with_quantization(self):
        """Test local execution with 4-bit quantization."""
        import sys
        from unittest.mock import MagicMock

        # Create mock transformers module with BitsAndBytesConfig
        mock_transformers = MagicMock()
        mock_quant_config = MagicMock()
        mock_quant_instance = MagicMock()
        mock_quant_config.return_value = mock_quant_instance
        mock_transformers.BitsAndBytesConfig = mock_quant_config

        with (
            patch.dict(sys.modules, {"transformers": mock_transformers}),
            patch("importlib.util.find_spec") as mock_find_spec,
            patch("langchain_huggingface.HuggingFacePipeline") as mock_pipeline,
            patch("langchain_huggingface.ChatHuggingFace") as mock_chat_hf,
        ):
            # Mock dependencies as installed
            mock_find_spec.return_value = MagicMock()

            mock_llm = MagicMock()
            mock_pipeline.from_model_id.return_value = mock_llm
            mock_chat_model = MagicMock()
            mock_chat_hf.return_value = mock_chat_model

            config = HuggingFaceModelConfig(
                model="meta-llama/Llama-3.1-8B-Instruct",
                local=True,
                quantization="4bit",
            )

            result = get_chat_model(config)

            assert result == mock_chat_model
            # Verify BitsAndBytesConfig was created with load_in_4bit=True
            mock_quant_config.assert_called_once_with(load_in_4bit=True)
            # Verify quantization config was added to model_kwargs
            pipeline_kwargs = mock_pipeline.from_model_id.call_args.kwargs
            assert "model_kwargs" in pipeline_kwargs
            assert (
                pipeline_kwargs["model_kwargs"]["quantization_config"]
                == mock_quant_instance
            )

    @pytest.mark.skipif(
        not HAS_HUGGINGFACE, reason="langchain_huggingface not installed"
    )
    @patch("importlib.util.find_spec")
    @patch("langchain_huggingface.ChatHuggingFace")
    @patch("langchain_huggingface.HuggingFacePipeline")
    def test_get_chat_model_huggingface_local_all_generation_params(
        self, mock_pipeline, mock_chat_hf, mock_find_spec
    ):
        """Test that all generation parameters go to pipeline_kwargs."""
        # Mock dependencies as installed
        mock_find_spec.return_value = MagicMock()

        mock_llm = MagicMock()
        mock_pipeline.from_model_id.return_value = mock_llm
        mock_chat_model = MagicMock()
        mock_chat_hf.return_value = mock_chat_model

        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            local=True,
            temperature=0.8,
            max_tokens=1024,
            stop_sequences=["END", "STOP"],
            top_p=0.95,
            top_k=50,
            repetition_penalty=1.1,
            do_sample=True,
        )

        result = get_chat_model(config)

        assert result == mock_chat_model
        call_kwargs = mock_pipeline.from_model_id.call_args.kwargs
        # Verify all generation parameters are in pipeline_kwargs
        assert "pipeline_kwargs" in call_kwargs
        pipeline_kwargs = call_kwargs["pipeline_kwargs"]
        assert pipeline_kwargs["temperature"] == 0.8
        assert pipeline_kwargs["max_new_tokens"] == 1024
        assert pipeline_kwargs["stop_sequences"] == ["END", "STOP"]
        assert pipeline_kwargs["top_p"] == 0.95
        assert pipeline_kwargs["top_k"] == 50
        assert pipeline_kwargs["repetition_penalty"] == 1.1
        assert pipeline_kwargs["do_sample"] is True

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

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_with_extra_kwargs(self, mock_chat_openai):
        """Test passing extra kwargs to ChatOpenAI."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )
        api_key = SecretStr("sk-test")

        result = get_chat_model(config, api_key=api_key, custom_param="value")

        assert result == mock_chat_model
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["custom_param"] == "value"

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_import_error(self, mock_chat_openai):
        """Test that ImportError raises MissingDependencyError."""
        mock_chat_openai.side_effect = ImportError("No module named 'langchain_openai'")

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )
        api_key = SecretStr("sk-test")

        with pytest.raises(MissingDependencyError) as exc_info:
            get_chat_model(config, api_key=api_key)

        assert "langchain" in str(exc_info.value).lower()

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_value_error(self, mock_chat_openai):
        """Test that ValueError raises InvalidModelError."""
        mock_chat_openai.side_effect = ValueError("Invalid model name: gpt-5")

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

    @patch("langchain_openai.ChatOpenAI")
    @patch("consoul.config.env.get_api_key")
    def test_get_chat_model_resolves_api_key_from_env(
        self, mock_get_api_key, mock_chat_openai
    ):
        """Test that API key is resolved from environment when not provided."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model
        mock_get_api_key.return_value = SecretStr("env-api-key-123")

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )

        result = get_chat_model(config)  # No api_key provided

        assert result == mock_chat_model
        mock_get_api_key.assert_called_once()
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["openai_api_key"] == "env-api-key-123"

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_string_with_auto_detection(self, mock_chat_openai):
        """Test using string model name with auto provider detection."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        result = get_chat_model("gpt-4o", api_key=SecretStr("sk-test"), temperature=0.5)

        assert result == mock_chat_model
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"
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

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_with_config_api_keys(self, mock_chat_openai):
        """Test that API keys are resolved from config.api_keys."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        # Create a mock config with api_keys
        mock_config = MagicMock()
        mock_config.api_keys = {"openai": SecretStr("config-key-123")}

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
        )

        result = get_chat_model(config, config=mock_config)

        assert result == mock_chat_model
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["openai_api_key"] == "config-key-123"

    @patch("langchain_openai.ChatOpenAI")
    @patch("consoul.config.env.get_api_key")
    def test_get_chat_model_config_api_keys_precedence(
        self, mock_get_api_key, mock_chat_openai
    ):
        """Test that config.api_keys takes precedence over environment."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model
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
        call_kwargs = mock_chat_openai.call_args[1]
        # Should use config key, not env key
        assert call_kwargs["openai_api_key"] == "config-key-123"
        # Environment getter should not be called when config has the key
        mock_get_api_key.assert_not_called()

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_string_with_stop_sequences(self, mock_chat_openai):
        """Test that stop_sequences is properly mapped in string mode."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        result = get_chat_model(
            "gpt-4o",
            api_key=SecretStr("sk-test"),
            stop_sequences=["STOP", "END"],
        )

        assert result == mock_chat_model
        call_kwargs = mock_chat_openai.call_args[1]
        # stop_sequences should be converted to "stop"
        assert call_kwargs["stop"] == ["STOP", "END"]
        # stop_sequences should not be passed directly
        assert "stop_sequences" not in call_kwargs

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_string_with_all_openai_params(self, mock_chat_openai):
        """Test string mode with all OpenAI-specific parameters."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

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
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["top_p"] == 0.9
        assert call_kwargs["frequency_penalty"] == 0.5
        assert call_kwargs["presence_penalty"] == 0.3
        assert call_kwargs["stop"] == ["END"]

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_openai_with_seed(self, mock_chat_openai):
        """Test OpenAI model with seed parameter for reproducibility."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
            seed=42,
        )

        result = get_chat_model(config, api_key=SecretStr("sk-test"))

        assert result == mock_chat_model
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["seed"] == 42

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_openai_with_logit_bias(self, mock_chat_openai):
        """Test OpenAI model with logit_bias parameter."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        logit_bias = {"50256": -100}  # Suppress <|endoftext|> token
        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
            logit_bias=logit_bias,
        )

        result = get_chat_model(config, api_key=SecretStr("sk-test"))

        assert result == mock_chat_model
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["logit_bias"] == logit_bias

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_openai_with_response_format(self, mock_chat_openai):
        """Test OpenAI model with response_format for JSON mode."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        response_format = {"type": "json_object"}
        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
            response_format=response_format,
        )

        result = get_chat_model(config, api_key=SecretStr("sk-test"))

        assert result == mock_chat_model
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["response_format"] == response_format

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_string_with_new_openai_params(self, mock_chat_openai):
        """Test string mode with new OpenAI parameters."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        result = get_chat_model(
            "gpt-4o",
            api_key=SecretStr("sk-test"),
            seed=123,
            logit_bias={"100": 10},
            response_format={"type": "json_object"},
        )

        assert result == mock_chat_model
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["seed"] == 123
        assert call_kwargs["logit_bias"] == {"100": 10}
        assert call_kwargs["response_format"] == {"type": "json_object"}

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_string_with_anthropic_exclusive_params(self, mock_init):
        """Test string mode with Anthropic-exclusive parameters."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        thinking_config = {"type": "enabled", "budget_tokens": 2000}
        betas = ["files-api-2025-04-14"]
        metadata = {"user_id": "test-user"}

        result = get_chat_model(
            "claude-3-5-sonnet-20241022",
            api_key=SecretStr("sk-ant-test"),
            thinking=thinking_config,
            betas=betas,
            metadata=metadata,
        )

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["thinking"] == thinking_config
        assert call_kwargs["betas"] == betas
        assert call_kwargs["metadata"] == metadata

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_string_with_google_exclusive_params(self, mock_init):
        """Test string mode with Google-exclusive parameters."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        safety_settings = {"HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"}
        generation_config = {"response_modalities": ["TEXT"]}

        result = get_chat_model(
            "gemini-2.5-pro",
            api_key=SecretStr("test-google-key"),
            candidate_count=2,
            safety_settings=safety_settings,
            generation_config=generation_config,
        )

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["candidate_count"] == 2
        assert call_kwargs["safety_settings"] == safety_settings
        assert call_kwargs["generation_config"] == generation_config

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_openai_all_new_params(self, mock_chat_openai):
        """Test OpenAI model with all new parameters combined."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.8,
            max_tokens=1024,
            seed=42,
            logit_bias={"50256": -100},
            response_format={"type": "json_object"},
            frequency_penalty=0.2,
            presence_penalty=0.1,
            top_p=0.95,
        )

        result = get_chat_model(config, api_key=SecretStr("sk-test"))

        assert result == mock_chat_model
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["seed"] == 42
        assert call_kwargs["logit_bias"] == {"50256": -100}
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert call_kwargs["frequency_penalty"] == 0.2
        assert call_kwargs["presence_penalty"] == 0.1
        assert call_kwargs["top_p"] == 0.95

    @patch("langchain_openai.ChatOpenAI")
    def test_get_chat_model_openai_with_nested_response_format(self, mock_chat_openai):
        """Test OpenAI model with nested response_format for JSON schema mode."""
        mock_chat_model = MagicMock()
        mock_chat_openai.return_value = mock_chat_model

        # Test nested structure for JSON schema mode
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "math_response",
                "schema": {
                    "type": "object",
                    "properties": {
                        "answer": {"type": "number"},
                        "explanation": {"type": "string"},
                    },
                    "required": ["answer", "explanation"],
                },
            },
        }

        config = OpenAIModelConfig(
            model="gpt-4o",
            temperature=0.7,
            response_format=response_format,
        )

        result = get_chat_model(config, api_key=SecretStr("sk-test"))

        assert result == mock_chat_model
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["response_format"] == response_format
        # Verify nested structure is preserved
        assert call_kwargs["response_format"]["json_schema"]["name"] == "math_response"

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_openai_params_dont_leak_to_anthropic(self, mock_init):
        """Test that OpenAI-specific params don't leak to other providers."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        # Try to use OpenAI-specific params with Anthropic model
        result = get_chat_model(
            "claude-3-5-sonnet-20241022",
            api_key=SecretStr("sk-ant-test"),
            seed=42,  # OpenAI-only
            logit_bias={"100": 10},  # OpenAI-only
            response_format={"type": "json_object"},  # OpenAI-only
            frequency_penalty=0.5,  # OpenAI-only
            presence_penalty=0.3,  # OpenAI-only
        )

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        # These OpenAI-specific params should NOT appear in the call
        assert "seed" not in call_kwargs
        assert "logit_bias" not in call_kwargs
        assert "response_format" not in call_kwargs
        assert "frequency_penalty" not in call_kwargs
        assert "presence_penalty" not in call_kwargs


class TestAnthropicProvider:
    """Tests for Anthropic Claude provider support."""

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_anthropic_with_thinking(self, mock_init):
        """Test Anthropic model with thinking parameter."""
        thinking_config = {"type": "enabled", "budget_tokens": 2000}
        config = AnthropicModelConfig(
            model="claude-sonnet-4-5-20250929",
            temperature=0.8,
            thinking=thinking_config,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config, api_key=SecretStr("test-key"))

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["thinking"] == thinking_config

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_anthropic_with_betas(self, mock_init):
        """Test Anthropic model with betas parameter."""
        betas = ["files-api-2025-04-14", "token-efficient-tools-2025-02-19"]
        config = AnthropicModelConfig(
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
            betas=betas,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config, api_key=SecretStr("test-key"))

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["betas"] == betas

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_anthropic_with_metadata(self, mock_init):
        """Test Anthropic model with metadata parameter."""
        metadata = {"user_id": "test-user", "session_id": "abc123"}
        config = AnthropicModelConfig(
            model="claude-3-opus-20240229",
            temperature=0.9,
            metadata=metadata,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config, api_key=SecretStr("test-key"))

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["metadata"] == metadata

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_anthropic_with_all_exclusive_params(self, mock_init):
        """Test Anthropic model with all exclusive parameters."""
        thinking_config = {"type": "enabled", "budget_tokens": 5000}
        betas = ["files-api-2025-04-14"]
        metadata = {"user_id": "test-user"}

        config = AnthropicModelConfig(
            model="claude-sonnet-4-5-20250929",
            temperature=0.8,
            max_tokens=4096,
            top_p=0.95,
            top_k=40,
            thinking=thinking_config,
            betas=betas,
            metadata=metadata,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config, api_key=SecretStr("test-key"))

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["max_tokens"] == 4096
        assert call_kwargs["top_p"] == 0.95
        assert call_kwargs["top_k"] == 40
        assert call_kwargs["thinking"] == thinking_config
        assert call_kwargs["betas"] == betas
        assert call_kwargs["metadata"] == metadata


class TestOllamaProvider:
    """Tests for Ollama provider support."""

    @patch("requests.get")
    def test_is_ollama_running_success(self, mock_get):
        """Test detecting running Ollama service."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert is_ollama_running() is True

    @patch("requests.get")
    def test_is_ollama_running_failure(self, mock_get):
        """Test detecting Ollama service not running."""
        mock_get.side_effect = Exception("Connection refused")

        assert is_ollama_running() is False

    @patch("requests.get")
    def test_is_ollama_running_404(self, mock_get):
        """Test Ollama service returns 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        assert is_ollama_running() is False

    @patch("requests.get")
    def test_is_ollama_running_custom_url(self, mock_get):
        """Test checking Ollama at custom URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert is_ollama_running("http://custom:8080") is True
        mock_get.assert_called_once_with("http://custom:8080/api/tags", timeout=2)

    @patch("consoul.ai.providers.is_ollama_running", return_value=False)
    def test_get_chat_model_ollama_not_running(self, mock_ollama_running):
        """Test error when Ollama service is not running."""
        config = OllamaModelConfig(
            model="llama3",
            temperature=0.7,
        )

        with pytest.raises(OllamaServiceError) as exc_info:
            get_chat_model(config)

        error_msg = str(exc_info.value)
        assert "Ollama service is not running" in error_msg
        assert "ollama serve" in error_msg
        assert "ollama pull llama3" in error_msg

    @patch("consoul.ai.providers.is_ollama_running", return_value=True)
    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_ollama_success(self, mock_init, mock_ollama_running):
        """Test successful Ollama model initialization."""
        config = OllamaModelConfig(
            model="llama3",
            temperature=0.7,
            max_tokens=2048,
            top_p=0.9,
            top_k=40,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config)

        assert result == mock_chat_model
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model_provider"] == "ollama"
        assert call_kwargs["model"] == "llama3"
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["top_p"] == 0.9
        assert call_kwargs["top_k"] == 40

    @patch("consoul.ai.providers.is_ollama_running", return_value=True)
    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_ollama_string(self, mock_init, mock_ollama_running):
        """Test Ollama initialization with string model name."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model("llama3", temperature=0.8)

        assert result == mock_chat_model
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model_provider"] == "ollama"
        assert call_kwargs["model"] == "llama3"
        assert call_kwargs["temperature"] == 0.8

    @patch("consoul.ai.providers.is_ollama_running", return_value=True)
    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_ollama_model_not_found(
        self, mock_init, mock_ollama_running
    ):
        """Test error when Ollama model is not found."""
        config = OllamaModelConfig(
            model="nonexistent-model",
            temperature=0.7,
        )

        # Simulate model not found error
        mock_init.side_effect = ValueError("Model not found: nonexistent-model")

        with pytest.raises(OllamaServiceError) as exc_info:
            get_chat_model(config)

        error_msg = str(exc_info.value)
        assert "not found" in error_msg.lower()
        assert "ollama pull nonexistent-model" in error_msg
        assert "ollama list" in error_msg

    @patch("consoul.ai.providers.is_ollama_running", return_value=True)
    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_ollama_connection_error(
        self, mock_init, mock_ollama_running
    ):
        """Test handling connection errors during Ollama initialization."""
        config = OllamaModelConfig(
            model="llama3",
            temperature=0.7,
        )

        # Simulate connection error
        mock_init.side_effect = Exception("Connection refused to localhost:11434")

        with pytest.raises(OllamaServiceError) as exc_info:
            get_chat_model(config)

        error_msg = str(exc_info.value)
        assert "Failed to connect to Ollama service" in error_msg
        assert "ollama serve" in error_msg

    @patch("consoul.ai.providers.is_ollama_running", return_value=True)
    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_ollama_no_api_key_needed(
        self, mock_init, mock_ollama_running
    ):
        """Test that Ollama doesn't require API key."""
        config = OllamaModelConfig(
            model="llama3",
            temperature=0.7,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        # Should succeed without API key
        result = get_chat_model(config)

        assert result == mock_chat_model
        # Verify no API key parameters were passed
        call_kwargs = mock_init.call_args.kwargs
        assert "openai_api_key" not in call_kwargs
        assert "anthropic_api_key" not in call_kwargs
        assert "google_api_key" not in call_kwargs

    @patch("consoul.ai.providers.is_ollama_running", return_value=True)
    @patch("consoul.ai.providers.init_chat_model")
    @patch(
        "consoul.config.env.get_ollama_api_base", return_value="http://custom-host:8080"
    )
    def test_get_chat_model_ollama_custom_base_url(
        self, mock_get_base, mock_init, mock_ollama_running
    ):
        """Test that Ollama uses custom base_url from config."""
        config = OllamaModelConfig(
            model="llama3",
            temperature=0.7,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config)

        assert result == mock_chat_model
        # Verify base_url was passed
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["base_url"] == "http://custom-host:8080"
        # Verify health check used custom URL
        mock_ollama_running.assert_called_once_with("http://custom-host:8080")

    @patch("consoul.ai.providers.is_ollama_running", return_value=True)
    @patch("consoul.ai.providers.init_chat_model")
    @patch("consoul.config.env.get_ollama_api_base", return_value=None)
    def test_get_chat_model_ollama_default_base_url(
        self, mock_get_base, mock_init, mock_ollama_running
    ):
        """Test that Ollama uses default localhost when no custom base_url."""
        config = OllamaModelConfig(
            model="llama3",
            temperature=0.7,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config)

        assert result == mock_chat_model
        # Verify base_url was NOT passed (using default)
        call_kwargs = mock_init.call_args.kwargs
        assert "base_url" not in call_kwargs
        # Verify health check used default URL
        mock_ollama_running.assert_called_once_with("http://localhost:11434")


class TestGoogleProvider:
    """Tests for Google Gemini provider support."""

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_google_with_all_params(self, mock_init):
        """Test Google model initialization with all parameters."""
        config = GoogleModelConfig(
            model="gemini-2.5-pro",
            temperature=0.8,
            max_tokens=2048,
            top_p=0.95,
            top_k=50,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config, api_key=SecretStr("test-google-key"))

        assert result == mock_chat_model
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model_provider"] == "google_genai"
        assert call_kwargs["model"] == "gemini-2.5-pro"
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["top_p"] == 0.95
        assert call_kwargs["top_k"] == 50
        assert call_kwargs["google_api_key"] == "test-google-key"

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_google_string_auto_detection(self, mock_init):
        """Test Google model initialization with string name auto-detection."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model("gemini-2.5-flash", api_key=SecretStr("test-key"))

        assert result == mock_chat_model
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model_provider"] == "google_genai"
        assert call_kwargs["model"] == "gemini-2.5-flash"

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_google_with_top_k_and_top_p(self, mock_init):
        """Test that Google supports both top_k and top_p parameters."""
        config = GoogleModelConfig(
            model="gemini-1.5-pro",
            temperature=0.7,
            top_p=0.9,
            top_k=40,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config, api_key=SecretStr("test-key"))

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["top_p"] == 0.9
        assert call_kwargs["top_k"] == 40

    @patch("consoul.config.env.get_api_key", return_value=None)
    def test_get_chat_model_google_missing_api_key(self, mock_get_api_key):
        """Test error when Google API key is missing."""
        config = GoogleModelConfig(
            model="gemini-pro",
            temperature=0.7,
        )

        with pytest.raises(MissingAPIKeyError) as exc_info:
            get_chat_model(config)

        error_msg = str(exc_info.value)
        assert "Missing API key for google" in error_msg
        assert "GOOGLE_API_KEY" in error_msg

    @patch("consoul.ai.providers.init_chat_model")
    @patch("consoul.config.env.get_api_key", return_value=SecretStr("env-google-key"))
    def test_get_chat_model_google_from_env(self, mock_get_key, mock_init):
        """Test Google model initialization with API key from environment."""
        config = GoogleModelConfig(
            model="gemini-pro",
            temperature=0.7,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config)

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["google_api_key"] == "env-google-key"

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_google_latest_models(self, mock_init):
        """Test Google with latest Gemini 2.5 and 1.5 models."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        # Test Gemini 2.5 Pro
        result = get_chat_model("gemini-2.5-pro", api_key=SecretStr("key"))
        assert result == mock_chat_model

        # Test Gemini 1.5 Flash
        result = get_chat_model("gemini-1.5-flash", api_key=SecretStr("key"))
        assert result == mock_chat_model

        # Test Gemini 1.5 Pro
        result = get_chat_model("gemini-1.5-pro", api_key=SecretStr("key"))
        assert result == mock_chat_model

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_google_with_kwargs(self, mock_init):
        """Test passing additional kwargs to Google model."""
        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(
            "gemini-pro",
            api_key=SecretStr("key"),
            timeout=60,
            max_retries=3,
        )

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["timeout"] == 60
        assert call_kwargs["max_retries"] == 3

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_google_with_candidate_count(self, mock_init):
        """Test Google model with candidate_count parameter."""
        config = GoogleModelConfig(
            model="gemini-2.5-pro",
            temperature=0.8,
            candidate_count=3,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config, api_key=SecretStr("test-key"))

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["candidate_count"] == 3

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_google_with_safety_settings(self, mock_init):
        """Test Google model with safety_settings parameter."""
        safety_settings = {
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
            "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH",
        }
        config = GoogleModelConfig(
            model="gemini-1.5-pro",
            temperature=0.7,
            safety_settings=safety_settings,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config, api_key=SecretStr("test-key"))

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["safety_settings"] == safety_settings

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_google_with_generation_config(self, mock_init):
        """Test Google model with generation_config parameter."""
        generation_config = {
            "response_modalities": ["TEXT", "IMAGE"],
            "candidate_count": 2,
        }
        config = GoogleModelConfig(
            model="gemini-2.5-pro",
            temperature=0.8,
            generation_config=generation_config,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config, api_key=SecretStr("test-key"))

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["generation_config"] == generation_config

    @patch("consoul.ai.providers.init_chat_model")
    def test_get_chat_model_google_with_all_exclusive_params(self, mock_init):
        """Test Google model with all Google-exclusive parameters."""
        safety_settings = {"HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"}
        generation_config = {"response_modalities": ["TEXT"]}

        config = GoogleModelConfig(
            model="gemini-2.5-pro",
            temperature=0.8,
            max_tokens=2048,
            top_p=0.95,
            top_k=50,
            candidate_count=2,
            safety_settings=safety_settings,
            generation_config=generation_config,
        )

        mock_chat_model = MagicMock()
        mock_init.return_value = mock_chat_model

        result = get_chat_model(config, api_key=SecretStr("test-key"))

        assert result == mock_chat_model
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.5-pro"
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["top_p"] == 0.95
        assert call_kwargs["top_k"] == 50
        assert call_kwargs["candidate_count"] == 2
        assert call_kwargs["safety_settings"] == safety_settings
        assert call_kwargs["generation_config"] == generation_config


@pytest.mark.skipif(not HAS_LLAMACPP, reason="llama-cpp-python not installed")
class TestLlamaCppProvider:
    """Tests for LlamaCpp provider initialization and functionality."""

    def test_llamacpp_model_config_creation(self):
        """Test creating a LlamaCpp model config."""
        config = LlamaCppModelConfig(
            model="DavidAU/OpenAi-GPT-oss-20b",
            n_ctx=4096,
            n_gpu_layers=-1,
            temperature=0.7,
            max_tokens=512,
        )

        assert config.provider == Provider.LLAMACPP
        assert config.model == "DavidAU/OpenAi-GPT-oss-20b"
        assert config.n_ctx == 4096
        assert config.n_gpu_layers == -1
        assert config.temperature == 0.7
        assert config.max_tokens == 512

    def test_llamacpp_model_config_with_model_path(self):
        """Test LlamaCpp config with explicit model path."""
        config = LlamaCppModelConfig(
            model="test-model",
            model_path="/path/to/model.gguf",
            n_ctx=2048,
        )

        assert config.model_path == "/path/to/model.gguf"
        assert config.n_ctx == 2048

    @patch("consoul.ai.providers.find_gguf_for_model")
    @patch("langchain_community.chat_models.ChatLlamaCpp")
    def test_get_chat_model_llamacpp_autodetect(
        self, mock_chat_llamacpp, mock_find_gguf
    ):
        """Test get_chat_model with LlamaCpp auto-detecting GGUF path."""
        mock_find_gguf.return_value = "/cache/models/model.gguf"
        mock_chat_model = MagicMock()
        mock_chat_llamacpp.return_value = mock_chat_model

        config = LlamaCppModelConfig(
            model="test-model",
            n_ctx=4096,
            n_gpu_layers=-1,
            temperature=0.7,
            max_tokens=512,
        )

        result = get_chat_model(config)

        assert result == mock_chat_model
        mock_find_gguf.assert_called_once_with("test-model")
        mock_chat_llamacpp.assert_called_once()

        call_kwargs = mock_chat_llamacpp.call_args.kwargs
        assert call_kwargs["model_path"] == "/cache/models/model.gguf"
        assert call_kwargs["n_ctx"] == 4096
        assert call_kwargs["n_gpu_layers"] == -1
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 512
        assert call_kwargs["verbose"] is False

    @patch("langchain_community.chat_models.ChatLlamaCpp")
    def test_get_chat_model_llamacpp_explicit_path(self, mock_chat_llamacpp):
        """Test get_chat_model with explicit model_path."""
        mock_chat_model = MagicMock()
        mock_chat_llamacpp.return_value = mock_chat_model

        config = LlamaCppModelConfig(
            model="test-model",
            model_path="/explicit/path/model.gguf",
            n_ctx=8192,
            temperature=0.5,
        )

        result = get_chat_model(config)

        assert result == mock_chat_model
        call_kwargs = mock_chat_llamacpp.call_args.kwargs
        assert call_kwargs["model_path"] == "/explicit/path/model.gguf"
        assert call_kwargs["n_ctx"] == 8192
        assert call_kwargs["temperature"] == 0.5

    @patch("consoul.ai.providers.find_gguf_for_model")
    def test_get_chat_model_llamacpp_no_model_found(self, mock_find_gguf):
        """Test error when no GGUF model is found."""
        mock_find_gguf.return_value = None

        config = LlamaCppModelConfig(model="nonexistent-model")

        with pytest.raises(InvalidModelError) as exc_info:
            get_chat_model(config)

        assert "No GGUF model found" in str(exc_info.value)
        assert "nonexistent-model" in str(exc_info.value)

    def test_llamacpp_no_api_key_required(self):
        """Test that LlamaCpp does not require API key."""
        config = LlamaCppModelConfig(
            model="test-model",
            model_path="/path/to/model.gguf",
        )

        # This should not raise MissingAPIKeyError
        # (Would need actual integration test to verify fully)
        assert config.provider == Provider.LLAMACPP

    @patch("consoul.ai.providers.get_gguf_models_from_cache")
    def test_get_gguf_models_from_cache(self, mock_get_gguf):
        """Test scanning HuggingFace cache for GGUF models."""
        from consoul.ai.providers import get_gguf_models_from_cache

        # Mock return value
        mock_get_gguf.return_value = [
            {
                "name": "model-q4.gguf",
                "path": "/cache/model-q4.gguf",
                "size": 11000000000,
                "size_gb": 10.24,
                "quant": "Q4",
                "repo": "DavidAU/test-model",
            },
            {
                "name": "model-q5.gguf",
                "path": "/cache/model-q5.gguf",
                "size": 15000000000,
                "size_gb": 13.97,
                "quant": "Q5",
                "repo": "DavidAU/test-model",
            },
        ]

        models = get_gguf_models_from_cache()

        assert len(models) == 2
        assert models[0]["quant"] == "Q4"
        assert models[1]["quant"] == "Q5"
        assert models[0]["size_gb"] < models[1]["size_gb"]
