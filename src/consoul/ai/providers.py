"""AI provider factory for dynamic model initialization.

This module provides a factory pattern for initializing LangChain chat models
from configuration, with automatic provider detection, API key resolution,
and comprehensive error handling.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING, Any, overload

from langchain.chat_models import init_chat_model
from pydantic import SecretStr  # noqa: TC002  # Used in runtime function signatures

from consoul.ai.exceptions import (
    InvalidModelError,
    MissingAPIKeyError,
    MissingDependencyError,
    OllamaServiceError,
    ProviderInitializationError,
)
from consoul.config.models import Provider

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

    from consoul.config.models import ModelConfig

# Provider package mapping
PROVIDER_PACKAGES = {
    Provider.OPENAI: "langchain_openai",
    Provider.ANTHROPIC: "langchain_anthropic",
    Provider.GOOGLE: "langchain_google_genai",
    Provider.OLLAMA: "langchain_ollama",
}

# Model name patterns for provider detection
PROVIDER_PATTERNS: dict[Provider, list[str]] = {
    Provider.OPENAI: ["gpt-", "o1-", "text-davinci"],
    Provider.ANTHROPIC: ["claude-"],
    Provider.GOOGLE: ["gemini-", "palm-"],
    Provider.OLLAMA: ["llama", "mistral", "phi", "qwen", "codellama"],
}

# Provider documentation URLs
PROVIDER_DOCS = {
    Provider.OPENAI: "https://platform.openai.com/docs/models",
    Provider.ANTHROPIC: "https://docs.anthropic.com/claude/docs/models-overview",
    Provider.GOOGLE: "https://ai.google.dev/models/gemini",
    Provider.OLLAMA: "https://ollama.com/library",
}

# API key environment variable names
API_KEY_ENV_VARS = {
    Provider.OPENAI: "OPENAI_API_KEY",
    Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
    Provider.GOOGLE: "GOOGLE_API_KEY",
    Provider.OLLAMA: None,  # Ollama doesn't require API key
}


def is_ollama_running(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama service is running locally.

    Args:
        base_url: The base URL for the Ollama service. Defaults to http://localhost:11434.

    Returns:
        True if Ollama is running and accessible, False otherwise.
    """
    try:
        import requests  # type: ignore[import-untyped]

        response = requests.get(f"{base_url}/api/tags", timeout=2)
        return bool(response.status_code == 200)
    except Exception:
        return False


def validate_provider_dependencies(provider: Provider) -> None:
    """Check if required langchain provider package is installed.

    Args:
        provider: The provider to validate.

    Raises:
        MissingDependencyError: If the required package is not installed.
    """
    package_name = PROVIDER_PACKAGES.get(provider)
    if not package_name:
        raise ProviderInitializationError(f"Unknown provider: {provider}")

    # Check if package is installed
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        pip_package = package_name.replace("_", "-")
        raise MissingDependencyError(
            f"Missing {pip_package} package.\n\n"
            f"To use {provider.value} models, install:\n"
            f"   pip install {pip_package}\n\n"
            f"Or install all providers:\n"
            f"   pip install consoul[all]"
        )


def get_provider_from_model(model_name: str) -> Provider | None:
    """Detect provider from model name.

    Args:
        model_name: The model name to analyze.

    Returns:
        Detected provider, or None if not recognized.

    Examples:
        >>> get_provider_from_model("gpt-4o")
        Provider.OPENAI
        >>> get_provider_from_model("claude-3-5-sonnet-20241022")
        Provider.ANTHROPIC
    """
    model_lower = model_name.lower()

    for provider, patterns in PROVIDER_PATTERNS.items():
        if any(model_lower.startswith(pattern) for pattern in patterns):
            return provider

    return None


def build_model_params(model_config: ModelConfig) -> dict[str, Any]:
    """Convert ModelConfig to LangChain init_chat_model parameters.

    Args:
        model_config: The model configuration from profile.

    Returns:
        Dictionary of parameters for init_chat_model.
    """
    from consoul.config.models import (
        AnthropicModelConfig,
        GoogleModelConfig,
        OllamaModelConfig,
        OpenAIModelConfig,
    )

    # Base parameters common to all providers
    params: dict[str, Any] = {
        "model": model_config.model,
        "temperature": model_config.temperature,
    }

    # Add max_tokens if specified
    if model_config.max_tokens is not None:
        params["max_tokens"] = model_config.max_tokens

    # Add stop sequences if specified
    if model_config.stop_sequences:
        params["stop"] = model_config.stop_sequences

    # Add provider-specific parameters
    if isinstance(model_config, OpenAIModelConfig):
        if model_config.top_p is not None:
            params["top_p"] = model_config.top_p
        if model_config.frequency_penalty is not None:
            params["frequency_penalty"] = model_config.frequency_penalty
        if model_config.presence_penalty is not None:
            params["presence_penalty"] = model_config.presence_penalty
        if model_config.seed is not None:
            params["seed"] = model_config.seed
        if model_config.logit_bias is not None:
            params["logit_bias"] = model_config.logit_bias
        if model_config.response_format is not None:
            params["response_format"] = model_config.response_format

    elif isinstance(model_config, AnthropicModelConfig):
        if model_config.top_p is not None:
            params["top_p"] = model_config.top_p
        if model_config.top_k is not None:
            params["top_k"] = model_config.top_k
        if model_config.thinking is not None:
            params["thinking"] = model_config.thinking
        if model_config.betas is not None:
            params["betas"] = model_config.betas
        if model_config.metadata is not None:
            params["metadata"] = model_config.metadata

    elif isinstance(model_config, GoogleModelConfig):
        if model_config.top_p is not None:
            params["top_p"] = model_config.top_p
        if model_config.top_k is not None:
            params["top_k"] = model_config.top_k
        if model_config.candidate_count is not None:
            params["candidate_count"] = model_config.candidate_count
        if model_config.safety_settings is not None:
            params["safety_settings"] = model_config.safety_settings
        if model_config.generation_config is not None:
            params["generation_config"] = model_config.generation_config

    elif isinstance(model_config, OllamaModelConfig):
        if model_config.top_p is not None:
            params["top_p"] = model_config.top_p
        if model_config.top_k is not None:
            params["top_k"] = model_config.top_k

    return params


@overload
def get_chat_model(
    model_config: str,
    api_key: SecretStr | None = None,
    config: Any = None,
    **kwargs: Any,
) -> BaseChatModel: ...


@overload
def get_chat_model(
    model_config: ModelConfig,
    api_key: SecretStr | None = None,
    config: Any = None,
    **kwargs: Any,
) -> BaseChatModel: ...


def get_chat_model(
    model_config: ModelConfig | str,
    api_key: SecretStr | None = None,
    config: Any = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Initialize chat model from configuration with provider detection.

    This function provides a unified interface for initializing LangChain chat
    models from Consoul configuration, handling provider detection, API key
    resolution, dependency validation, and error handling.

    Args:
        model_config: Either a ModelConfig object or a model name string.
            If a string is provided, the provider will be auto-detected.
        api_key: Optional API key override. If None, resolves from config/environment.
        config: Optional ConsoulConfig instance to check for API keys in config.api_keys.
        **kwargs: Additional parameters to pass to init_chat_model.
            For string model names, you can pass temperature, max_tokens, stop_sequences, etc.

    Returns:
        Initialized LangChain chat model ready for use.

    Raises:
        MissingAPIKeyError: If API key is required but not found.
        MissingDependencyError: If provider package is not installed.
        InvalidModelError: If model name is not recognized.
        ProviderInitializationError: If initialization fails for other reasons.

    Examples:
        >>> # Using ModelConfig from profile
        >>> from consoul.config import load_config
        >>> config = load_config()
        >>> profile = config.get_active_profile()
        >>> chat_model = get_chat_model(profile.model)

        >>> # Using model name string with auto-detection
        >>> chat_model = get_chat_model("gpt-4o", temperature=0.7)
        >>> chat_model = get_chat_model("claude-3-5-sonnet-20241022")
    """
    # Handle string model names with provider auto-detection
    if isinstance(model_config, str):
        model_name = model_config
        provider = get_provider_from_model(model_name)

        if provider is None:
            raise InvalidModelError(
                f"Could not detect provider for model '{model_name}'.\n\n"
                f"Supported model patterns:\n"
                + "\n".join(
                    f"  - {prov.value}: {', '.join(patterns)}"
                    for prov, patterns in PROVIDER_PATTERNS.items()
                )
                + "\n\nPlease use a recognized model name or pass a ModelConfig object."
            )

        # Create a minimal ModelConfig-like object for parameter building
        from consoul.config.models import (
            AnthropicModelConfig,
            GoogleModelConfig,
            OllamaModelConfig,
            OpenAIModelConfig,
        )

        # Extract common parameters from kwargs
        temperature = kwargs.pop("temperature", 0.7)
        max_tokens = kwargs.pop("max_tokens", None)
        stop_sequences = kwargs.pop("stop_sequences", None)

        # Extract provider-specific parameters to prevent them from leaking to other providers
        # These will only be used if the provider supports them
        top_p = kwargs.pop("top_p", None)
        top_k = kwargs.pop("top_k", None)

        # OpenAI-specific parameters
        frequency_penalty = kwargs.pop("frequency_penalty", None)
        presence_penalty = kwargs.pop("presence_penalty", None)
        seed = kwargs.pop("seed", None)
        logit_bias = kwargs.pop("logit_bias", None)
        response_format = kwargs.pop("response_format", None)

        # Anthropic-specific parameters
        thinking = kwargs.pop("thinking", None)
        betas = kwargs.pop("betas", None)
        metadata = kwargs.pop("metadata", None)

        # Google-specific parameters
        candidate_count = kwargs.pop("candidate_count", None)
        safety_settings = kwargs.pop("safety_settings", None)
        generation_config = kwargs.pop("generation_config", None)

        # Build appropriate config based on provider
        if provider == Provider.OPENAI:
            model_config = OpenAIModelConfig(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                seed=seed,
                logit_bias=logit_bias,
                response_format=response_format,
            )
        elif provider == Provider.ANTHROPIC:
            model_config = AnthropicModelConfig(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                top_p=top_p,
                top_k=top_k,
                thinking=thinking,
                betas=betas,
                metadata=metadata,
            )
        elif provider == Provider.GOOGLE:
            model_config = GoogleModelConfig(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                top_p=top_p,
                top_k=top_k,
                candidate_count=candidate_count,
                safety_settings=safety_settings,
                generation_config=generation_config,
            )
        elif provider == Provider.OLLAMA:
            model_config = OllamaModelConfig(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                top_p=top_p,
                top_k=top_k,
            )

    provider = model_config.provider

    # Validate dependencies
    try:
        validate_provider_dependencies(provider)
    except MissingDependencyError:
        raise  # Re-raise with helpful message

    # Check Ollama service availability before attempting initialization
    if provider == Provider.OLLAMA:
        # Get Ollama API base URL from config/env
        from consoul.config.env import get_ollama_api_base

        ollama_base_url = get_ollama_api_base()
        if not ollama_base_url:
            ollama_base_url = "http://localhost:11434"

        if not is_ollama_running(ollama_base_url):
            raise OllamaServiceError(
                f"Ollama service is not running.\n\n"
                f"To use Ollama models:\n"
                f"1. Start Ollama service:\n"
                f"   ollama serve\n\n"
                f"2. Pull the model if not already available:\n"
                f"   ollama pull {model_config.model}\n\n"
                f"3. Verify Ollama is running:\n"
                f"   curl {ollama_base_url}/api/tags\n\n"
                f"Current base URL: {ollama_base_url}\n"
                f"(Set OLLAMA_API_BASE to use a different endpoint)\n\n"
                f"See: {PROVIDER_DOCS.get(Provider.OLLAMA, 'https://ollama.com')}"
            )

    # Resolve API key (if required for this provider)
    resolved_api_key: str | None = None
    if provider != Provider.OLLAMA:  # Ollama doesn't need API key
        if api_key is not None:
            # Explicit override provided
            resolved_api_key = api_key.get_secret_value()
        else:
            # Try multiple sources in order of precedence:
            # 1. config.api_keys (runtime injection)
            # 2. Environment variables / .env files

            # Check config.api_keys first
            if config is not None and hasattr(config, "api_keys"):
                config_key = config.api_keys.get(provider.value)
                if config_key is not None:
                    resolved_api_key = config_key.get_secret_value()

            # Fall back to environment if not found in config
            if resolved_api_key is None:
                from consoul.config.env import get_api_key

                env_api_key = get_api_key(provider)
                if env_api_key is not None:
                    resolved_api_key = env_api_key.get_secret_value()

            # If still not found, raise error
            if resolved_api_key is None:
                env_var = API_KEY_ENV_VARS.get(
                    provider, f"{provider.value.upper()}_API_KEY"
                )
                docs_url = PROVIDER_DOCS.get(provider, "")

                raise MissingAPIKeyError(
                    f"Missing API key for {provider.value}.\n\n"
                    f"Please set your API key using one of these methods:\n\n"
                    f"1. Runtime (ConsoulConfig.api_keys):\n"
                    f"   config.api_keys['{provider.value}'] = SecretStr('your-key')\n\n"
                    f"2. Environment variable:\n"
                    f"   export {env_var}=your-key-here\n\n"
                    f"3. .env file (in project or ~/.consoul/):\n"
                    f"   {env_var}=your-key-here\n\n"
                    + (f"4. Get your key from: {docs_url}\n\n" if docs_url else "")
                    + f"Current provider: {provider.value}\n"
                    f"Current model: {model_config.model}"
                )

    # Build parameters for init_chat_model
    params = build_model_params(model_config)

    # Add provider-specific API key parameter
    if resolved_api_key:
        if provider == Provider.OPENAI:
            params["openai_api_key"] = resolved_api_key
        elif provider == Provider.ANTHROPIC:
            params["anthropic_api_key"] = resolved_api_key
        elif provider == Provider.GOOGLE:
            params["google_api_key"] = resolved_api_key

    # Add Ollama-specific base_url parameter
    if provider == Provider.OLLAMA:
        from consoul.config.env import get_ollama_api_base

        ollama_base_url = get_ollama_api_base()
        if ollama_base_url:
            params["base_url"] = ollama_base_url

    # Merge with any additional kwargs
    params.update(kwargs)

    # Initialize the model
    try:
        return init_chat_model(
            model_provider=provider.value,
            **params,
        )
    except ImportError as e:
        # Dependency import failed (shouldn't happen after validation)
        package = PROVIDER_PACKAGES.get(provider, provider.value)
        raise MissingDependencyError(
            f"Failed to import {package}: {e}\n\n"
            f"Install with: pip install {package.replace('_', '-')}"
        ) from e
    except ValueError as e:
        # Invalid model name or configuration
        docs_url = PROVIDER_DOCS.get(provider, "")
        error_msg = str(e).lower()

        # Special handling for Ollama model not found errors
        if provider == Provider.OLLAMA and (
            "not found" in error_msg or "404" in error_msg
        ):
            raise OllamaServiceError(
                f"Model '{model_config.model}' not found in Ollama.\n\n"
                f"To download the model:\n"
                f"   ollama pull {model_config.model}\n\n"
                f"To list available models:\n"
                f"   ollama list\n\n"
                f"See available models: {docs_url}"
            ) from e

        raise InvalidModelError(
            f"Invalid model '{model_config.model}' for {provider.value}.\n\n"
            f"Error: {e}\n\n"
            + (f"See available models: {docs_url}" if docs_url else "")
        ) from e
    except Exception as e:
        # Other initialization errors
        error_msg = str(e).lower()

        # Catch additional Ollama connection errors
        if provider == Provider.OLLAMA and (
            "connection" in error_msg or "refused" in error_msg
        ):
            raise OllamaServiceError(
                f"Failed to connect to Ollama service.\n\n"
                f"To use Ollama models:\n"
                f"1. Start Ollama service:\n"
                f"   ollama serve\n\n"
                f"2. Verify service is running:\n"
                f"   curl http://localhost:11434/api/tags\n\n"
                f"Original error: {e}"
            ) from e

        raise ProviderInitializationError(
            f"Failed to initialize {provider.value} model '{model_config.model}': {e}"
        ) from e
