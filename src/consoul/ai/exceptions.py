"""Custom exceptions for AI provider initialization and operations.

This module defines exception classes for handling errors during AI provider
initialization, including missing API keys, dependencies, and invalid models.
"""

from __future__ import annotations


class ProviderInitializationError(Exception):
    """Base exception for AI provider initialization errors.

    Raised when provider initialization fails for any reason including
    missing credentials, invalid configuration, or unavailable dependencies.
    """


class MissingAPIKeyError(ProviderInitializationError):
    """Exception raised when required API key is not found.

    This error indicates that the API key for the selected provider
    is missing from both environment variables and configuration.
    """


class MissingDependencyError(ProviderInitializationError):
    """Exception raised when required provider package is not installed.

    This error indicates that the langchain provider package
    (e.g., langchain-openai, langchain-anthropic) is not installed.
    """


class InvalidModelError(ProviderInitializationError):
    """Exception raised when model name is invalid or not recognized.

    This error indicates that the specified model name is not valid
    for the selected provider or cannot be found.
    """


class OllamaServiceError(ProviderInitializationError):
    """Exception raised when Ollama service is not running or unavailable.

    This error indicates that the Ollama service is not running locally
    or the specified model is not available. Users should start Ollama
    with 'ollama serve' or pull the model with 'ollama pull {model}'.
    """


class ConsoulAIError(Exception):
    """Base exception for Consoul AI operations."""


class StreamingError(ConsoulAIError):
    """Exception raised when response streaming fails.

    This error is raised when streaming tokens from an AI model fails
    mid-stream. The partial response received before the error is
    preserved in the partial_response attribute for debugging or recovery.

    Attributes:
        partial_response: Text received before the error occurred.

    Example:
        >>> try:
        ...     response = stream_response(model, messages)
        ... except StreamingError as e:
        ...     print(f"Failed after: {e.partial_response}")
    """

    def __init__(self, message: str, partial_response: str = ""):
        """Initialize StreamingError with message and partial response.

        Args:
            message: Error description.
            partial_response: Partial response received before error.
        """
        super().__init__(message)
        self.partial_response = partial_response


class ContextError(ConsoulAIError):
    """Base exception for conversation context management errors.

    This error is raised when there are issues with managing conversation
    context, such as token limit violations or message formatting problems.
    """


class TokenLimitExceededError(ContextError):
    """Exception raised when conversation exceeds model's token limit.

    This error indicates that the conversation history contains more tokens
    than the model can handle, even after trimming. This typically means
    individual messages are too large.

    Attributes:
        current_tokens: Number of tokens in the conversation
        max_tokens: Maximum tokens allowed by the model

    Example:
        >>> try:
        ...     history.add_message("user", very_long_message)
        ... except TokenLimitExceededError as e:
        ...     print(f"Exceeded: {e.current_tokens}/{e.max_tokens}")
    """

    def __init__(self, message: str, current_tokens: int, max_tokens: int):
        """Initialize TokenLimitExceededError.

        Args:
            message: Error description
            current_tokens: Number of tokens in conversation
            max_tokens: Maximum allowed tokens
        """
        super().__init__(message)
        self.current_tokens = current_tokens
        self.max_tokens = max_tokens
