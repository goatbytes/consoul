"""Data models for SDK service layer.

This module defines TUI-agnostic data structures for conversation management,
streaming responses, and tool execution. These models replace LangChain-specific
types in the public API to maintain clean separation from implementation details.

Example:
    >>> token = Token(content="Hello", cost=0.0001)
    >>> attachment = Attachment(path="image.png", type="image")
    >>> stats = ConversationStats(message_count=5, total_tokens=150,
    ...                           total_cost=0.05, session_id="abc123")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Token:
    """Single streaming token from AI response.

    Represents an incremental piece of the AI's response during streaming.
    Includes optional cost and metadata for monitoring and analysis.

    Attributes:
        content: The text content of this token
        cost: Estimated cost in USD for this token (None if unknown)
        metadata: Additional information (tool_calls, reasoning, etc.)

    Example:
        >>> token = Token(content="Hello", cost=0.00001)
        >>> print(token.content, end="", flush=True)
        Hello
        >>> total_cost += token.cost if token.cost else 0
    """

    content: str
    cost: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return content for easy printing."""
        return self.content


@dataclass
class Attachment:
    """File attachment for messages.

    Represents a file to be sent along with a user message. Supports
    images (for multimodal models) and text files (prepended to message).

    Attributes:
        path: Absolute or relative path to the file
        type: File type - "image", "code", "document", or "data"

    Example:
        >>> image = Attachment(path="screenshot.png", type="image")
        >>> code = Attachment(path="main.py", type="code")
        >>> attachments = [image, code]
    """

    path: str
    type: str  # "image", "code", "document", "data"

    def __post_init__(self) -> None:
        """Validate attachment type."""
        valid_types = {"image", "code", "document", "data"}
        if self.type not in valid_types:
            raise ValueError(
                f"Invalid attachment type '{self.type}'. "
                f"Must be one of: {', '.join(valid_types)}"
            )


@dataclass
class ConversationStats:
    """Statistics about a conversation.

    Provides metrics for monitoring conversation history, token usage,
    and costs. Useful for analytics and cost tracking.

    Attributes:
        message_count: Total number of messages in conversation
        total_tokens: Cumulative token count across all messages
        total_cost: Total estimated cost in USD
        session_id: Unique session identifier (None if not persisted)

    Example:
        >>> stats = service.get_stats()
        >>> print(f"Messages: {stats.message_count}")
        Messages: 10
        >>> print(f"Cost: ${stats.total_cost:.4f}")
        Cost: $0.0523
    """

    message_count: int
    total_tokens: int
    total_cost: float
    session_id: str | None


@dataclass
class ToolRequest:
    """Tool execution request for approval callback.

    Encapsulates a tool call that requires approval before execution.
    Passed to the on_tool_request callback to allow the caller to
    approve or deny the execution.

    Attributes:
        id: Unique identifier for this tool call (from AI provider)
        name: Tool name to execute (e.g., "bash_execute")
        arguments: Dictionary of arguments to pass to the tool
        risk_level: Security risk level ("safe", "caution", "dangerous")

    Example:
        >>> async def approve_tool(request: ToolRequest) -> bool:
        ...     if request.risk_level == "safe":
        ...         return True  # Auto-approve safe tools
        ...     print(f"Allow {request.name}({request.arguments})? [y/n]")
        ...     return input().lower() == 'y'
        >>> async for token in service.send_message(
        ...     "List files",
        ...     on_tool_request=approve_tool
        ... ):
        ...     print(token, end="")
    """

    id: str
    name: str
    arguments: dict[str, Any]
    risk_level: str  # "safe", "caution", "dangerous", "blocked"

    def __repr__(self) -> str:
        """Human-readable representation with truncated arguments."""
        args_str = str(self.arguments)[:50]
        if len(str(self.arguments)) > 50:
            args_str += "..."
        return (
            f"ToolRequest(id={self.id!r}, name={self.name!r}, "
            f"risk={self.risk_level!r}, args={args_str})"
        )
