"""AI provider integration module.

Handles integration with various AI providers through LangChain abstraction.
Supports OpenAI, Anthropic, Google, and other LangChain-compatible providers.

Includes tool calling system for executing tools (bash, Python, file operations)
with security controls, user approval, and audit logging.
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
from consoul.ai.tools import (
    BlockedCommandError,
    RiskLevel,
    ToolError,
    ToolExecutionError,
    ToolMetadata,
    ToolNotFoundError,
    ToolRegistry,
    ToolValidationError,
)

__all__ = [
    "BlockedCommandError",
    "ConsoulAIError",
    "ContextError",
    "ConversationHistory",
    "InvalidModelError",
    "MissingAPIKeyError",
    "MissingDependencyError",
    "ProviderInitializationError",
    "RiskLevel",
    "StreamingError",
    "TokenLimitExceededError",
    "ToolError",
    "ToolExecutionError",
    "ToolMetadata",
    "ToolNotFoundError",
    "ToolRegistry",
    "ToolValidationError",
    "build_model_params",
    "count_message_tokens",
    "create_token_counter",
    "get_chat_model",
    "get_model_token_limit",
    "get_provider_from_model",
    "stream_response",
    "validate_provider_dependencies",
]
