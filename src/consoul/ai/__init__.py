"""AI provider integration module.

Handles integration with various AI providers through LangChain abstraction.
Supports OpenAI, Anthropic, Google, and other LangChain-compatible providers.
"""

from consoul.ai.context import (
    count_message_tokens,
    create_token_counter,
    get_model_token_limit,
)
from consoul.ai.exceptions import (
    ConsoulAIError,
    ContextError,
    InvalidModelError,
    MissingAPIKeyError,
    MissingDependencyError,
    ProviderInitializationError,
    StreamingError,
    TokenLimitExceededError,
)
from consoul.ai.history import ConversationHistory
from consoul.ai.providers import (
    build_model_params,
    get_chat_model,
    get_provider_from_model,
    validate_provider_dependencies,
)
from consoul.ai.streaming import stream_response

__all__ = [
    "ConsoulAIError",
    "ContextError",
    "ConversationHistory",
    "InvalidModelError",
    "MissingAPIKeyError",
    "MissingDependencyError",
    "ProviderInitializationError",
    "StreamingError",
    "TokenLimitExceededError",
    "build_model_params",
    "count_message_tokens",
    "create_token_counter",
    "get_chat_model",
    "get_model_token_limit",
    "get_provider_from_model",
    "stream_response",
    "validate_provider_dependencies",
]
