"""Consoul SDK - High-level service layer for headless AI conversation management.

This package provides TUI-agnostic services for building AI-powered applications
without UI dependencies. Suitable for CLIs, web backends, scripts, and notebooks.

Example:
    >>> from consoul.sdk import ConversationService
    >>> service = ConversationService.from_config()
    >>> async for token in service.send_message("Hello!"):
    ...     print(token.content, end="", flush=True)
"""

from consoul.sdk.models import (
    Attachment,
    ConversationStats,
    ModelInfo,
    Token,
    ToolRequest,
)
from consoul.sdk.protocols import ToolExecutionCallback
from consoul.sdk.services.conversation import ConversationService

__all__ = [
    "Attachment",
    "ConversationService",
    "ConversationStats",
    "ModelInfo",
    "Token",
    "ToolExecutionCallback",
    "ToolRequest",
]
