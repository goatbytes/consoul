"""AI provider integration module.

Handles integration with various AI providers through LangChain abstraction.
Supports OpenAI, Anthropic, Google, and other LangChain-compatible providers.
"""

from consoul.ai.exceptions import (
    InvalidModelError,
    MissingAPIKeyError,
    MissingDependencyError,
    ProviderInitializationError,
)
from consoul.ai.providers import (
    build_model_params,
    get_chat_model,
    get_provider_from_model,
    validate_provider_dependencies,
)

__all__ = [
    "InvalidModelError",
    "MissingAPIKeyError",
    "MissingDependencyError",
    "ProviderInitializationError",
    "build_model_params",
    "get_chat_model",
    "get_provider_from_model",
    "validate_provider_dependencies",
]
