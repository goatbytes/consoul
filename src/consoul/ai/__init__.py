"""AI provider integration module.

Handles integration with various AI providers through LangChain abstraction.
Supports OpenAI, Anthropic, Google, and other LangChain-compatible providers.
"""

from consoul.ai.exceptions import (
    ConsoulAIError,
    InvalidModelError,
    MissingAPIKeyError,
    MissingDependencyError,
    ProviderInitializationError,
    StreamingError,
)
from consoul.ai.providers import (
    build_model_params,
    get_chat_model,
    get_provider_from_model,
    validate_provider_dependencies,
)
from consoul.ai.streaming import stream_response

__all__ = [
    "ConsoulAIError",
    "InvalidModelError",
    "MissingAPIKeyError",
    "MissingDependencyError",
    "ProviderInitializationError",
    "StreamingError",
    "build_model_params",
    "get_chat_model",
    "get_provider_from_model",
    "stream_response",
    "validate_provider_dependencies",
]
