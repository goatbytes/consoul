"""Consoul SDK - High-level service layer for headless AI conversation management.

This package provides TUI-agnostic services for building AI-powered applications
without UI dependencies. Suitable for CLIs, web backends, scripts, and notebooks.

Example (High-level API):
    >>> from consoul.sdk import Consoul
    >>> console = Consoul()
    >>> console.chat("Hello!")
    'Hi! How can I help you?'

Example (Service layer):
    >>> from consoul.sdk import ConversationService
    >>> service = ConversationService.from_config()
    >>> async for token in service.send_message("Hello!"):
    ...     print(token.content, end="", flush=True)
"""
# ruff: noqa: RUF022

from consoul.sdk.models import (
    Attachment,
    ConversationStats,
    ModelCapabilities,
    ModelInfo,
    PricingInfo,
    Token,
    ToolRequest,
)
from consoul.sdk.protocols import ToolExecutionCallback
from consoul.sdk.services.conversation import ConversationService
from consoul.sdk.wrapper import Consoul, ConsoulResponse

__all__ = [
    # High-level SDK (simple 5-line API)
    "Consoul",
    "ConsoulResponse",
    # Service layer (advanced usage)
    "Attachment",
    "ConversationService",
    "ConversationStats",
    "ModelCapabilities",
    "ModelInfo",
    "PricingInfo",
    "Token",
    "ToolExecutionCallback",
    "ToolRequest",
]
