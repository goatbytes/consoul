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
