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
    SessionMetadata,
    SessionState,
    Token,
    ToolFilter,
    ToolRequest,
)
from consoul.sdk.protocols import SessionHooks, ToolExecutionCallback
from consoul.sdk.services.conversation import ConversationService
from consoul.sdk.session_id import (
    ParsedSessionId,
    SessionIdBuilder,
    build_session_id,
    generate_session_id,
    parse_session_id,
)
from consoul.sdk.session_store import HookedSessionStore
from consoul.sdk.wrapper import (
    Consoul,
    ConsoulResponse,
    create_session,
    restore_session,
    save_session_state,
)

__all__ = [
    # High-level SDK (simple 5-line API)
    "Consoul",
    "ConsoulResponse",
    "create_session",
    "restore_session",
    "save_session_state",
    # Session management (new in v0.6.0)
    "SessionMetadata",
    "SessionHooks",
    "HookedSessionStore",
    "SessionIdBuilder",
    "ParsedSessionId",
    "build_session_id",
    "parse_session_id",
    "generate_session_id",
    # Service layer (advanced usage)
    "Attachment",
    "ConversationService",
    "ConversationStats",
    "ModelCapabilities",
    "ModelInfo",
    "PricingInfo",
    "SessionState",
    "Token",
    "ToolExecutionCallback",
    "ToolFilter",
    "ToolRequest",
]
